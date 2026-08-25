-- ============================================================================
-- 0061 · RLS de negociación + reemplazo de quotation_revisions_insert (fase 8.5)
-- ----------------------------------------------------------------------------
-- negotiation_rounds/negotiation_round_participants: negotiation.manage para
-- el comprador; autoservicio is_member_of(supplier_organization_id) para el
-- proveedor participante — mismo patrón que sourcing_event_invitations.
--
-- quotation_revisions_insert se REEMPLAZA COMPLETO (mismo patrón de
-- "reemplazo total de policy" ya usado varias veces en fase 7): la condición
-- original de round_type='INITIAL' queda intacta tal cual, y se agrega una
-- rama OR para round_type in ('COUNTER','BAFO') cuando existe una
-- negotiation_round_participants pendiente de responder, de ESE mismo tipo
-- de ronda, antes de su deadline. La condición `nr.round_type =
-- quotation_revisions.round_type` evita que una ronda COUNTER abierta
-- habilite el envío de una revisión BAFO (y viceversa) — no estaba escrito
-- explícitamente en el plan, se agrega acá por ser la lectura estricta
-- correcta de "está participando en ESTA ronda".
-- ============================================================================

alter table public.negotiation_rounds enable row level security;

create policy negotiation_rounds_select
  on public.negotiation_rounds for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'negotiation.manage')
    )
    or exists (
      select 1 from public.negotiation_round_participants nrp
      where nrp.negotiation_round_id = negotiation_rounds.id
        and app.is_member_of(nrp.supplier_organization_id)
    )
  );

create policy negotiation_rounds_write
  on public.negotiation_rounds for all
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'negotiation.manage')
    )
  )
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'negotiation.manage')
    )
  );

create policy negotiation_rounds_system_context
  on public.negotiation_rounds for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.negotiation_round_participants enable row level security;

create policy negotiation_round_participants_select
  on public.negotiation_round_participants for select
  using (
    app.is_member_of(supplier_organization_id)
    or exists (
      select 1 from public.negotiation_rounds nr
      join public.sourcing_events se on se.id = nr.sourcing_event_id
      where nr.id = negotiation_round_id and app.has_permission(se.organization_id, 'negotiation.manage')
    )
  );

create policy negotiation_round_participants_buyer_write
  on public.negotiation_round_participants for insert
  with check (
    exists (
      select 1 from public.negotiation_rounds nr
      join public.sourcing_events se on se.id = nr.sourcing_event_id
      where nr.id = negotiation_round_id and app.has_permission(se.organization_id, 'negotiation.manage')
    )
  );

create policy negotiation_round_participants_supplier_respond
  on public.negotiation_round_participants for update
  using (app.is_member_of(supplier_organization_id))
  with check (app.is_member_of(supplier_organization_id));
-- el proveedor solo puede marcar SU propia respuesta (responded_*); el
-- comprador nunca actualiza esta fila (solo la crea al abrir la ronda).

create policy negotiation_round_participants_system_context
  on public.negotiation_round_participants for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- Reemplazo completo de quotation_revisions_insert (definida en 0049)
-- ============================================================================

drop policy quotation_revisions_insert on public.quotation_revisions;

create policy quotation_revisions_insert
  on public.quotation_revisions for insert
  with check (
    exists (
      select 1 from public.quotations q
      where q.id = quotation_revisions.quotation_id
        and app.is_member_of(q.supplier_organization_id)
        and (
          (
            quotation_revisions.round_type = 'INITIAL'
            and exists (
              select 1 from public.sourcing_event_invitations sei
              where sei.sourcing_event_id = q.sourcing_event_id
                and sei.supplier_organization_id = q.supplier_organization_id
                and sei.status in ('INTERESTED', 'PARTICIPATING', 'QUOTED')
            )
            and not exists (
              select 1 from public.sourcing_event_stages st
              where st.sourcing_event_id = q.sourcing_event_id and st.stage_type = 'BID_DEADLINE'
                and st.scheduled_at is not null and now() > st.scheduled_at
            )
          )
          or (
            quotation_revisions.round_type in ('COUNTER', 'BAFO')
            and exists (
              select 1 from public.negotiation_round_participants nrp
              join public.negotiation_rounds nr on nr.id = nrp.negotiation_round_id
              where nr.sourcing_event_id = q.sourcing_event_id
                and nrp.supplier_organization_id = q.supplier_organization_id
                and nrp.responded_quotation_revision_id is null
                and nr.round_type = quotation_revisions.round_type
                and (nr.deadline is null or now() <= nr.deadline)
            )
          )
        )
    )
  );
