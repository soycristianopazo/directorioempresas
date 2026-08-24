-- ============================================================================
-- 0048 · RLS de invitaciones, NDA y Q&A (fase 7.1/7.2/7.4) + cierre del vacío
-- de visibilidad del proveedor invitado sobre el evento de fase 6
-- ----------------------------------------------------------------------------
-- Sin FORCE ROW LEVEL SECURITY — mismo motivo de siempre (0010_hardening.sql).
--
-- Todas las escrituras del lado comprador reutilizan el mismo backstop de 4
-- permisos de 0043_fase6_rls.sql (sourcing_event.create/publish/cancel/
-- open_bids) — ningún permiso nuevo, confirmado leyendo
-- 0009_seed_roles_permissions.sql directo. Las acciones de autoservicio del
-- proveedor (ver su invitación, aceptar/declinar, aceptar NDA, preguntar) se
-- autorizan solo por app.is_member_of() sobre la fila de su propia
-- organización — ninguna necesita permiso de plataforma tampoco.
-- ============================================================================

-- ============================================================================
-- sourcing_event_invitations / invitation_status_history
-- ============================================================================

alter table public.sourcing_event_invitations enable row level security;

create policy sourcing_event_invitations_select
  on public.sourcing_event_invitations for select
  using (
    app.is_member_of(supplier_organization_id)
    or exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_invitations.sourcing_event_id
        and app.has_permission(se.organization_id, 'sourcing_event.read')
    )
    or app.is_platform_admin()
  );

create policy sourcing_event_invitations_insert
  on public.sourcing_event_invitations for insert
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_invitations.sourcing_event_id
        and app.has_permission(se.organization_id, 'sourcing_event.publish')
    )
  );

create policy sourcing_event_invitations_update
  on public.sourcing_event_invitations for update
  using (
    app.is_member_of(supplier_organization_id)
    or exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_invitations.sourcing_event_id
        and (
          app.has_permission(se.organization_id, 'sourcing_event.publish')
          or app.has_permission(se.organization_id, 'sourcing_event.cancel')
        )
    )
  )
  with check (
    app.is_member_of(supplier_organization_id)
    or exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_invitations.sourcing_event_id
        and (
          app.has_permission(se.organization_id, 'sourcing_event.publish')
          or app.has_permission(se.organization_id, 'sourcing_event.cancel')
        )
    )
  );

create policy sourcing_event_invitations_system_context
  on public.sourcing_event_invitations for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.invitation_status_history enable row level security;

create policy invitation_status_history_select
  on public.invitation_status_history for select
  using (
    exists (
      select 1 from public.sourcing_event_invitations sei
      where sei.id = invitation_status_history.invitation_id
        and (
          app.is_member_of(sei.supplier_organization_id)
          or exists (
            select 1 from public.sourcing_events se
            where se.id = sei.sourcing_event_id
              and app.has_permission(se.organization_id, 'sourcing_event.read')
          )
        )
    )
  );

create policy invitation_status_history_insert
  on public.invitation_status_history for insert
  with check (
    exists (
      select 1 from public.sourcing_event_invitations sei
      where sei.id = invitation_status_history.invitation_id
        and (
          app.is_member_of(sei.supplier_organization_id)
          or exists (
            select 1 from public.sourcing_events se
            where se.id = sei.sourcing_event_id
              and (
                app.has_permission(se.organization_id, 'sourcing_event.publish')
                or app.has_permission(se.organization_id, 'sourcing_event.cancel')
              )
          )
        )
    )
  );

create policy invitation_status_history_system_context
  on public.invitation_status_history for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- sourcing_event_ndas / nda_acceptances
-- ============================================================================

alter table public.sourcing_event_ndas enable row level security;

create policy sourcing_event_ndas_select
  on public.sourcing_event_ndas for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_ndas.sourcing_event_id
        and app.has_permission(se.organization_id, 'sourcing_event.read')
    )
    or app.has_active_sourcing_invitation(sourcing_event_id)
    or app.is_platform_admin()
  );

create policy sourcing_event_ndas_write
  on public.sourcing_event_ndas for all
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_ndas.sourcing_event_id
        and (
          app.has_permission(se.organization_id, 'sourcing_event.create')
          or app.has_permission(se.organization_id, 'sourcing_event.publish')
        )
    )
  )
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_ndas.sourcing_event_id
        and (
          app.has_permission(se.organization_id, 'sourcing_event.create')
          or app.has_permission(se.organization_id, 'sourcing_event.publish')
        )
    )
  );

create policy sourcing_event_ndas_system_context
  on public.sourcing_event_ndas for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.nda_acceptances enable row level security;

create policy nda_acceptances_select
  on public.nda_acceptances for select
  using (
    app.is_member_of(organization_id)
    or exists (
      select 1 from public.sourcing_event_ndas nda
      join public.sourcing_events se on se.id = nda.sourcing_event_id
      where nda.id = nda_acceptances.nda_id
        and app.has_permission(se.organization_id, 'sourcing_event.read')
    )
    or app.is_platform_admin()
  );

create policy nda_acceptances_insert
  on public.nda_acceptances for insert
  with check (
    app.is_member_of(organization_id)
    and exists (
      select 1 from public.sourcing_event_ndas nda
      where nda.id = nda_acceptances.nda_id
        and app.has_active_sourcing_invitation(nda.sourcing_event_id)
    )
  );

create policy nda_acceptances_system_context
  on public.nda_acceptances for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- sourcing_questions / sourcing_answers
-- ============================================================================

alter table public.sourcing_questions enable row level security;

create policy sourcing_questions_select
  on public.sourcing_questions for select
  using (
    app.is_member_of(asked_by_organization_id)
    or exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_questions.sourcing_event_id
        and app.has_permission(se.organization_id, 'sourcing_event.read')
    )
    or (
      app.has_active_sourcing_invitation(sourcing_event_id)
      and exists (
        select 1 from public.sourcing_answers a
        where a.question_id = sourcing_questions.id
          and a.visibility = 'ALL_PARTICIPANTS'
          and a.published_at is not null
      )
    )
    or app.is_platform_admin()
  );

create policy sourcing_questions_insert
  on public.sourcing_questions for insert
  with check (
    app.is_member_of(asked_by_organization_id)
    and app.has_active_sourcing_invitation(sourcing_event_id)
  );

create policy sourcing_questions_update
  on public.sourcing_questions for update
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_questions.sourcing_event_id
        and app.has_permission(se.organization_id, 'sourcing_event.publish')
    )
  )
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_questions.sourcing_event_id
        and app.has_permission(se.organization_id, 'sourcing_event.publish')
    )
  );

create policy sourcing_questions_system_context
  on public.sourcing_questions for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.sourcing_answers enable row level security;

create policy sourcing_answers_select
  on public.sourcing_answers for select
  using (
    exists (
      select 1 from public.sourcing_questions q
      join public.sourcing_events se on se.id = q.sourcing_event_id
      where q.id = sourcing_answers.question_id
        and app.has_permission(se.organization_id, 'sourcing_event.read')
    )
    or (
      published_at is not null
      and exists (
        select 1 from public.sourcing_questions q
        where q.id = sourcing_answers.question_id
          and (
            (sourcing_answers.visibility = 'PRIVATE_TO_ASKER' and app.is_member_of(q.asked_by_organization_id))
            or (sourcing_answers.visibility = 'ALL_PARTICIPANTS' and app.has_active_sourcing_invitation(q.sourcing_event_id))
          )
      )
    )
    or app.is_platform_admin()
  );

create policy sourcing_answers_write
  on public.sourcing_answers for all
  using (
    exists (
      select 1 from public.sourcing_questions q
      join public.sourcing_events se on se.id = q.sourcing_event_id
      where q.id = sourcing_answers.question_id
        and app.has_permission(se.organization_id, 'sourcing_event.publish')
    )
  )
  with check (
    exists (
      select 1 from public.sourcing_questions q
      join public.sourcing_events se on se.id = q.sourcing_event_id
      where q.id = sourcing_answers.question_id
        and app.has_permission(se.organization_id, 'sourcing_event.publish')
    )
  );

create policy sourcing_answers_system_context
  on public.sourcing_answers for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- Vacío real de fase 6: hoy ningún proveedor invitado puede leer el evento al
-- que fue invitado (0043_fase6_rls.sql solo da SELECT al comprador dueño).
-- Se agregan policies SELECT ADICIONALES (permisivas — Postgres las OR
-- automático con las de 0043, ese archivo no se toca) usando
-- app.has_active_sourcing_invitation(), ya creado en 0044.
-- ============================================================================

create policy sourcing_events_select_invited
  on public.sourcing_events for select
  using (app.has_active_sourcing_invitation(id));

do $$
declare
  t text;
  tables text[] := array[
    'sourcing_event_lots', 'sourcing_event_items', 'sourcing_event_stages', 'sourcing_event_criteria'
  ];
begin
  foreach t in array tables loop
    execute format(
      'create policy %I on public.%I for select using (app.has_active_sourcing_invitation(sourcing_event_id))',
      t || '_select_invited', t
    );
  end loop;
end $$;

-- sourcing_event_documents lleva un gate extra: si requires_nda, exige haber
-- aceptado el NDA vigente del evento antes de dejar ver la fila (y, en el
-- service, antes de servir la URL firmada — RLS es la defensa 1, no la
-- única).
create policy sourcing_event_documents_select_invited
  on public.sourcing_event_documents for select
  using (
    app.has_active_sourcing_invitation(sourcing_event_id)
    and (
      not requires_nda
      or exists (
        select 1 from public.nda_acceptances na
        join public.sourcing_event_ndas nda on nda.id = na.nda_id
        where nda.sourcing_event_id = sourcing_event_documents.sourcing_event_id
          and app.is_member_of(na.organization_id)
      )
    )
  );
