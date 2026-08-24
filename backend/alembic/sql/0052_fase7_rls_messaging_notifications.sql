-- ============================================================================
-- 0052 · RLS de mensajería y notificaciones (fase 7.8/7.9)
-- ----------------------------------------------------------------------------
-- Sin FORCE ROW LEVEL SECURITY — mismo motivo de siempre (0010_hardening.sql).
--
-- Mensajería: Patrón F (docs/01-ARQUITECTURA.md §I.3) — visible a cualquier
-- organización participante del hilo, vía conversation_participants. No hay
-- backstop de permisos acá: ser participante ES el criterio, no un permiso
-- de recurso.
--
-- Notificaciones: recipient_id = app.current_user_id() para select/update
-- (marcar leída); insert solo desde contexto de sistema — es la escritura
-- "para otro usuario" descrita en 0051, uso legítimo agregado a la lista de
-- docs/RLS.md. notification_deliveries es interno: sin acceso de usuario,
-- mismo criterio que domain_events ("solo contexto de sistema").
-- ============================================================================

-- ============================================================================
-- Mensajería
-- ============================================================================

-- app.is_conversation_participant() existe para romper una recursión real:
-- conversation_participants_select necesitaba preguntar "¿hay OTRA fila de
-- esta misma tabla donde mi organización sea participante?" — un EXISTS
-- contra la propia conversation_participants dentro de SU PROPIA policy de
-- SELECT. Postgres evalúa esa subconsulta re-aplicando la misma policy sobre
-- cada fila candidata, que vuelve a disparar la subconsulta, indefinidamente
-- ("infinite recursion detected in policy for relation
-- conversation_participants" — encontrado en vivo, verificación manual en el
-- navegador, no en los tests, que nunca ejercitaron mensajería). Una función
-- SECURITY DEFINER rompe el ciclo por la misma razón que el resto de los
-- helpers de RLS de este proyecto (docs/RLS.md, "toda comprobación va por un
-- helper de app"): corre con los privilegios de su dueño (postgres, que no
-- está sujeto a RLS sin FORCE ROW LEVEL SECURITY — no usado en este proyecto,
-- 0010_hardening.sql) — la consulta interna nunca vuelve a evaluar la policy
-- que la está llamando.
create or replace function app.is_conversation_participant(p_conversation_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.conversation_participants cp
    where cp.conversation_id = p_conversation_id and app.is_member_of(cp.organization_id)
  );
$$;

grant execute on function app.is_conversation_participant(uuid) to app_user;

comment on function app.is_conversation_participant(uuid) is
  '¿Alguna organización del usuario actual participa en esta conversación? SECURITY DEFINER a propósito — evita la recursión de RLS que produce un EXISTS contra conversation_participants escrito directo dentro de la policy de esa misma tabla.';


alter table public.conversations enable row level security;

create policy conversations_select
  on public.conversations for select
  using (
    app.is_conversation_participant(id)
    -- El creador ve su propia conversación incluso antes de que exista la
    -- fila de conversation_participants correspondiente: el INSERT de esta
    -- tabla pide RETURNING id (el ORM siempre lo hace), y Postgres exige que
    -- la fila recién insertada también pase la policy de SELECT — en ese
    -- instante conversation_participants todavía no tiene ninguna fila para
    -- esta conversación (se inserta después, en la misma transacción, no en
    -- el mismo INSERT). Mismo gotcha ya documentado para `notifications` en
    -- docs/RLS.md.
    or app.is_member_of(created_by_organization_id)
    or app.is_platform_admin()
  );

create policy conversations_insert
  on public.conversations for insert
  with check (app.is_member_of(created_by_organization_id));

create policy conversations_system_context
  on public.conversations for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.conversation_participants enable row level security;

create policy conversation_participants_select
  on public.conversation_participants for select
  using (
    app.is_member_of(organization_id)
    or app.is_conversation_participant(conversation_id)
    or app.is_platform_admin()
  );

create policy conversation_participants_insert
  on public.conversation_participants for insert
  with check (
    app.is_member_of(organization_id)
    or app.is_conversation_participant(conversation_id)
    or exists (
      select 1 from public.conversations c
      where c.id = conversation_participants.conversation_id
        and app.is_member_of(c.created_by_organization_id)
    )
  );

create policy conversation_participants_system_context
  on public.conversation_participants for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.messages enable row level security;

create policy messages_select
  on public.messages for select
  using (
    exists (
      select 1 from public.conversation_participants cp
      where cp.conversation_id = messages.conversation_id and app.is_member_of(cp.organization_id)
    )
    or app.is_platform_admin()
  );

create policy messages_insert
  on public.messages for insert
  with check (
    exists (
      select 1 from public.conversation_participants cp
      where cp.conversation_id = messages.conversation_id and app.is_member_of(cp.organization_id)
    )
    and (
      sender_organization_id is null
      or app.is_member_of(sender_organization_id)
    )
  );

create policy messages_system_context
  on public.messages for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.message_attachments enable row level security;

create policy message_attachments_select
  on public.message_attachments for select
  using (
    exists (
      select 1 from public.messages m
      join public.conversation_participants cp on cp.conversation_id = m.conversation_id
      where m.id = message_attachments.message_id and app.is_member_of(cp.organization_id)
    )
    or app.is_platform_admin()
  );

create policy message_attachments_insert
  on public.message_attachments for insert
  with check (
    exists (
      select 1 from public.messages m
      join public.conversation_participants cp on cp.conversation_id = m.conversation_id
      where m.id = message_attachments.message_id and app.is_member_of(cp.organization_id)
    )
  );

create policy message_attachments_system_context
  on public.message_attachments for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.message_reads enable row level security;

create policy message_reads_select
  on public.message_reads for select
  using (
    exists (
      select 1 from public.messages m
      join public.conversation_participants cp on cp.conversation_id = m.conversation_id
      where m.id = message_reads.message_id and app.is_member_of(cp.organization_id)
    )
    or app.is_platform_admin()
  );

create policy message_reads_insert
  on public.message_reads for insert
  with check (reader_id = app.current_user_id());

create policy message_reads_system_context
  on public.message_reads for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- Notificaciones
-- ============================================================================

alter table public.notifications enable row level security;

create policy notifications_select
  on public.notifications for select
  using (recipient_id = app.current_user_id() or app.is_system_context());

create policy notifications_update
  on public.notifications for update
  using (recipient_id = app.current_user_id())
  with check (recipient_id = app.current_user_id());

create policy notifications_insert_system_context
  on public.notifications for insert
  with check (app.is_system_context());
-- notifications_select necesita el OR is_system_context() además del INSERT:
-- Postgres exige que la fila insertada también pase la policy de SELECT
-- cuando el INSERT lleva RETURNING (el ORM siempre pide RETURNING id,
-- created_at) — sin este OR, notify_org()/notify_user() fallan con "new row
-- violates row-level security policy" aunque el INSERT en sí esté permitido.
-- Encontrado por tests/test_invitations.py y tests/test_quotations.py.


alter table public.notification_preferences enable row level security;

create policy notification_preferences_all
  on public.notification_preferences for all
  using (user_id = app.current_user_id())
  with check (user_id = app.current_user_id());

create policy notification_preferences_system_context
  on public.notification_preferences for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.notification_deliveries enable row level security;

create policy notification_deliveries_system_context
  on public.notification_deliveries for all
  using (app.is_system_context()) with check (app.is_system_context());
-- sin más policies: es interno, igual que domain_events ("solo contexto de
-- sistema") — ningún usuario lee/escribe esta tabla directo.
