-- ============================================================================
-- 0043 · RLS de demanda y matching (fase 6)
-- ----------------------------------------------------------------------------
-- Sin FORCE ROW LEVEL SECURITY — mismo motivo de siempre, ver 0010_hardening.sql.
--
-- A diferencia de organizations/supplier_offerings, NADA de esto es público
-- ni siquiera parcialmente: la demanda de un comprador (requirements,
-- sourcing_events y todo lo que cuelga) es información privada de su
-- organización. Nunca hay una policy "select using (true)" ni
-- "using (can_view_organization(...))" en este archivo.
-- ============================================================================

-- ============================================================================
-- requirements y sus hijas
-- ============================================================================

alter table public.requirements enable row level security;

create policy requirements_select
  on public.requirements for select
  using (app.has_permission(organization_id, 'requirement.read'));

create policy requirements_write
  on public.requirements for all
  using (app.has_permission(organization_id, 'requirement.write'))
  with check (app.has_permission(organization_id, 'requirement.write'));

create policy requirements_system_context
  on public.requirements for all
  using (app.is_system_context()) with check (app.is_system_context());


do $$
declare
  t text;
  tables text[] := array['requirement_items', 'requirement_locations', 'requirement_documents'];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using ('
      '  exists (select 1 from public.requirements r '
      '          where r.id = requirement_id and app.has_permission(r.organization_id, ''requirement.read''))'
      ')', t || '_select', t
    );
    execute format(
      'create policy %I on public.%I for all using ('
      '  exists (select 1 from public.requirements r '
      '          where r.id = requirement_id and app.has_permission(r.organization_id, ''requirement.write''))'
      ') with check ('
      '  exists (select 1 from public.requirements r '
      '          where r.id = requirement_id and app.has_permission(r.organization_id, ''requirement.write''))'
      ')', t || '_write', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;


-- ============================================================================
-- sourcing_events y sus hijas — backstop grueso: cualquiera de los permisos
-- de sourcing_event toca la fila; CUÁL permiso hace falta para CADA acción
-- (crear/editar borrador vs publicar vs cancelar vs abrir ofertas) lo decide
-- services/sourcing.py, no la policy — mismo patrón que supplier_offerings.
-- ============================================================================

alter table public.sourcing_events enable row level security;

create policy sourcing_events_select
  on public.sourcing_events for select
  using (app.has_permission(organization_id, 'sourcing_event.read'));

create policy sourcing_events_write
  on public.sourcing_events for all
  using (
    app.has_permission(organization_id, 'sourcing_event.create')
    or app.has_permission(organization_id, 'sourcing_event.publish')
    or app.has_permission(organization_id, 'sourcing_event.cancel')
    or app.has_permission(organization_id, 'sourcing_event.open_bids')
  )
  with check (
    app.has_permission(organization_id, 'sourcing_event.create')
    or app.has_permission(organization_id, 'sourcing_event.publish')
    or app.has_permission(organization_id, 'sourcing_event.cancel')
    or app.has_permission(organization_id, 'sourcing_event.open_bids')
  );

create policy sourcing_events_system_context
  on public.sourcing_events for all
  using (app.is_system_context()) with check (app.is_system_context());


do $$
declare
  t text;
  tables text[] := array[
    'sourcing_event_lots', 'sourcing_event_items', 'sourcing_event_stages',
    'sourcing_event_documents', 'sourcing_event_criteria'
  ];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using ('
      '  exists (select 1 from public.sourcing_events se '
      '          where se.id = sourcing_event_id and app.has_permission(se.organization_id, ''sourcing_event.read''))'
      ')', t || '_select', t
    );
    execute format(
      'create policy %I on public.%I for all using ('
      '  exists (select 1 from public.sourcing_events se '
      '          where se.id = sourcing_event_id and ('
      '            app.has_permission(se.organization_id, ''sourcing_event.create'')'
      '            or app.has_permission(se.organization_id, ''sourcing_event.publish'')'
      '            or app.has_permission(se.organization_id, ''sourcing_event.cancel'')'
      '          ))'
      ') with check ('
      '  exists (select 1 from public.sourcing_events se '
      '          where se.id = sourcing_event_id and ('
      '            app.has_permission(se.organization_id, ''sourcing_event.create'')'
      '            or app.has_permission(se.organization_id, ''sourcing_event.publish'')'
      '            or app.has_permission(se.organization_id, ''sourcing_event.cancel'')'
      '          ))'
      ')', t || '_write', t
    );
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;


-- ============================================================================
-- match_runs / match_results — mismo criterio de visibilidad que el evento
-- dueño; escritura solo desde services/matching.py (requiere
-- sourcing_event.create, igual que el resto de mutaciones del borrador) o
-- contexto de sistema. REVOKE UPDATE/DELETE ya aplicado en 0041 — acá solo
-- falta el SELECT/INSERT.
-- ============================================================================

alter table public.match_runs enable row level security;

create policy match_runs_select
  on public.match_runs for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'sourcing_event.read')
    )
  );

create policy match_runs_insert
  on public.match_runs for insert
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'sourcing_event.create')
    )
  );

create policy match_runs_system_context
  on public.match_runs for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.match_results enable row level security;

create policy match_results_select
  on public.match_results for select
  using (
    exists (
      select 1 from public.match_runs mr
      join public.sourcing_events se on se.id = mr.sourcing_event_id
      where mr.id = match_run_id and app.has_permission(se.organization_id, 'sourcing_event.read')
    )
  );

create policy match_results_insert
  on public.match_results for insert
  with check (
    exists (
      select 1 from public.match_runs mr
      join public.sourcing_events se on se.id = mr.sourcing_event_id
      where mr.id = match_run_id and app.has_permission(se.organization_id, 'sourcing_event.create')
    )
  );

create policy match_results_system_context
  on public.match_results for all
  using (app.is_system_context()) with check (app.is_system_context());
