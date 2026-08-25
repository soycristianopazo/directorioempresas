-- ============================================================================
-- 0056 · RLS de plantillas, comité y evaluaciones (fase 8.2/8.3/8.4)
-- ----------------------------------------------------------------------------
-- evaluation_templates/evaluation_criteria/event_evaluation_setup/
-- evaluation_assignments: backstop-permiso estándar (evaluation.read/manage),
-- mismo patrón que requirements/sourcing_events (0043).
--
-- evaluations/evaluation_scores: autoservicio — el evaluador asignado (cuyo
-- organization_member_id resuelve al usuario actual) lee/escribe SOLO su
-- propia fila; el comprador con evaluation.manage lee todas pero nunca
-- escribe la evaluación de otro (evaluar es un acto personal del comité, no
-- delegable por permiso). Nótese: esta policy NO expone montos — evaluations/
-- evaluation_scores no tienen columnas de precio, solo status/comentario/
-- puntaje. El bloqueo económico real es sobre las funciones de 0057.
-- ============================================================================

alter table public.evaluation_templates enable row level security;

create policy evaluation_templates_select
  on public.evaluation_templates for select
  using (app.has_permission(organization_id, 'evaluation.read'));

create policy evaluation_templates_write
  on public.evaluation_templates for all
  using (app.has_permission(organization_id, 'evaluation.manage'))
  with check (app.has_permission(organization_id, 'evaluation.manage'));

create policy evaluation_templates_system_context
  on public.evaluation_templates for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.evaluation_criteria enable row level security;

create policy evaluation_criteria_select
  on public.evaluation_criteria for select
  using (
    exists (
      select 1 from public.evaluation_templates t
      where t.id = template_id and app.has_permission(t.organization_id, 'evaluation.read')
    )
  );

create policy evaluation_criteria_write
  on public.evaluation_criteria for all
  using (
    exists (
      select 1 from public.evaluation_templates t
      where t.id = template_id and app.has_permission(t.organization_id, 'evaluation.manage')
    )
  )
  with check (
    exists (
      select 1 from public.evaluation_templates t
      where t.id = template_id and app.has_permission(t.organization_id, 'evaluation.manage')
    )
  );

create policy evaluation_criteria_system_context
  on public.evaluation_criteria for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.event_evaluation_setup enable row level security;

create policy event_evaluation_setup_select
  on public.event_evaluation_setup for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.read')
    )
  );

create policy event_evaluation_setup_write
  on public.event_evaluation_setup for all
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.manage')
    )
  )
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.manage')
    )
  );

create policy event_evaluation_setup_system_context
  on public.event_evaluation_setup for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.evaluation_assignments enable row level security;

create policy evaluation_assignments_select
  on public.evaluation_assignments for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.read')
    )
    or exists (
      select 1 from public.organization_members om
      where om.id = organization_member_id and om.user_id = app.current_user_id()
    )
  );

create policy evaluation_assignments_write
  on public.evaluation_assignments for all
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.manage')
    )
  )
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.manage')
    )
  );

create policy evaluation_assignments_system_context
  on public.evaluation_assignments for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ─── Autoservicio: evaluations / evaluation_scores ────────────────────────────

alter table public.evaluations enable row level security;

create policy evaluations_select
  on public.evaluations for select
  using (
    exists (
      select 1 from public.organization_members om
      where om.id = organization_member_id and om.user_id = app.current_user_id()
    )
    or exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.read')
    )
  );

create policy evaluations_write
  on public.evaluations for all
  using (
    exists (
      select 1 from public.organization_members om
      where om.id = organization_member_id and om.user_id = app.current_user_id()
    )
  )
  with check (
    exists (
      select 1 from public.organization_members om
      where om.id = organization_member_id and om.user_id = app.current_user_id()
    )
    and exists (
      select 1 from public.evaluation_assignments ea
      where ea.sourcing_event_id = evaluations.sourcing_event_id
        and ea.organization_member_id = evaluations.organization_member_id
    )
  );
-- el evaluador solo puede escribir su propia fila, y solo si tiene una
-- evaluation_assignments real para ese evento — no basta con crear
-- organization_members.id propio y adivinar un quotation_id ajeno.

create policy evaluations_system_context
  on public.evaluations for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.evaluation_scores enable row level security;

create policy evaluation_scores_select
  on public.evaluation_scores for select
  using (
    exists (
      select 1 from public.evaluations e
      join public.organization_members om on om.id = e.organization_member_id
      where e.id = evaluation_id and om.user_id = app.current_user_id()
    )
    or exists (
      select 1 from public.evaluations e
      join public.sourcing_events se on se.id = e.sourcing_event_id
      where e.id = evaluation_id and app.has_permission(se.organization_id, 'evaluation.read')
    )
  );

create policy evaluation_scores_write
  on public.evaluation_scores for all
  using (
    exists (
      select 1 from public.evaluations e
      join public.organization_members om on om.id = e.organization_member_id
      where e.id = evaluation_id and om.user_id = app.current_user_id() and e.status = 'DRAFT'
    )
  )
  with check (
    exists (
      select 1 from public.evaluations e
      join public.organization_members om on om.id = e.organization_member_id
      where e.id = evaluation_id and om.user_id = app.current_user_id() and e.status = 'DRAFT'
    )
  );
-- solo mientras la evaluación padre sigue en DRAFT — una vez SUBMITTED,
-- congelada de facto (services/evaluations.py nunca vuelve a DRAFT).

create policy evaluation_scores_system_context
  on public.evaluation_scores for all
  using (app.is_system_context()) with check (app.is_system_context());
