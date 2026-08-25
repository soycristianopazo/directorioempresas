-- ============================================================================
-- 0063 · RLS de adjudicación (fase 8.6)
-- ----------------------------------------------------------------------------
-- awards/award_items/organization_approval_policies: backstop-permiso
-- estándar (award.create para escribir, award.create/award.approve para
-- leer). Sin visibilidad para el proveedor adjudicado en esta tabla — el
-- proveedor se entera del resultado por el cambio de estado de su propia
-- invitación (ya visible desde fase 7, sourcing_event_invitations) y la
-- notificación in-app, no leyendo awards directamente (misma decisión que
-- 0068 para buyer_supplier_relationships: mínimo necesario, sin exponer una
-- tabla interna del comprador).
--
-- award_approvals: autoservicio ESTRICTO en UPDATE — nadie decide el paso
-- de otro aunque tenga award.approve a nivel de organización. Es la misma
-- idea de autoservicio que evaluations/evaluation_scores (0056): el permiso
-- de plataforma abre la puerta de LECTURA de la cola, pero solo
-- approver_member_id (resuelto al usuario actual) puede decidir SU fila.
-- ============================================================================

alter table public.organization_approval_policies enable row level security;

create policy organization_approval_policies_select
  on public.organization_approval_policies for select
  using (
    app.has_permission(organization_id, 'award.create')
    or app.has_permission(organization_id, 'award.approve')
  );

create policy organization_approval_policies_write
  on public.organization_approval_policies for all
  using (app.has_permission(organization_id, 'award.create'))
  with check (app.has_permission(organization_id, 'award.create'));

create policy organization_approval_policies_system_context
  on public.organization_approval_policies for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.awards enable row level security;

create policy awards_select
  on public.awards for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id
        and (app.has_permission(se.organization_id, 'award.create')
             or app.has_permission(se.organization_id, 'award.approve'))
    )
  );

create policy awards_write
  on public.awards for all
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'award.create')
    )
  )
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'award.create')
    )
  );

create policy awards_system_context
  on public.awards for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.award_items enable row level security;

create policy award_items_select
  on public.award_items for select
  using (
    exists (
      select 1 from public.awards a
      join public.sourcing_events se on se.id = a.sourcing_event_id
      where a.id = award_id
        and (app.has_permission(se.organization_id, 'award.create')
             or app.has_permission(se.organization_id, 'award.approve'))
    )
  );

create policy award_items_insert
  on public.award_items for insert
  with check (
    exists (
      select 1 from public.awards a
      join public.sourcing_events se on se.id = a.sourcing_event_id
      where a.id = award_id and app.has_permission(se.organization_id, 'award.create')
    )
  );

create policy award_items_system_context
  on public.award_items for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.award_approvals enable row level security;

create policy award_approvals_select
  on public.award_approvals for select
  using (
    exists (
      select 1 from public.organization_members om
      where om.id = approver_member_id and om.user_id = app.current_user_id()
    )
    or exists (
      select 1 from public.awards a
      join public.sourcing_events se on se.id = a.sourcing_event_id
      where a.id = award_id and app.has_permission(se.organization_id, 'award.approve')
    )
  );

create policy award_approvals_insert
  on public.award_approvals for insert
  with check (
    exists (
      select 1 from public.awards a
      join public.sourcing_events se on se.id = a.sourcing_event_id
      where a.id = award_id and app.has_permission(se.organization_id, 'award.create')
    )
  );

create policy award_approvals_decide
  on public.award_approvals for update
  using (
    exists (
      select 1 from public.organization_members om
      where om.id = approver_member_id and om.user_id = app.current_user_id()
    )
  )
  with check (
    exists (
      select 1 from public.organization_members om
      where om.id = approver_member_id and om.user_id = app.current_user_id()
    )
  );
-- nadie aprueba el paso de otro aunque tenga award.approve a nivel de
-- organización — defensa doble junto con el chequeo explícito en
-- services/awards.py::decide().

create policy award_approvals_system_context
  on public.award_approvals for all
  using (app.is_system_context()) with check (app.is_system_context());
