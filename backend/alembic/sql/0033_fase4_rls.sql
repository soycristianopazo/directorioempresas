-- ============================================================================
-- 0033 · RLS de búsqueda, listas guardadas y analítica
-- ----------------------------------------------------------------------------
-- Fase 4 del roadmap. Sin FORCE ROW LEVEL SECURITY — mismo motivo de
-- siempre, ver 0010_hardening.sql.
-- ============================================================================

-- ============================================================================
-- supplier_search_index — lectura pública si is_public. Escritura: el mismo
-- usuario que ya puede escribir la oferta (reindex corre en la MISMA
-- transacción que la mutación que lo dispara — mismo patrón que
-- recompute_completion_pct en services/completion.py, no una sesión de
-- sistema aparte, para que el reindexado vea los cambios recién hechos sin
-- esperar un commit cruzado entre conexiones), o el script de
-- reconciliación completa (session_for_system).
-- ============================================================================

alter table public.supplier_search_index enable row level security;

create policy supplier_search_index_select
  on public.supplier_search_index for select
  using (is_public);

create policy supplier_search_index_write
  on public.supplier_search_index for all
  using (
    app.has_permission(organization_id, 'offering.write')
    or app.has_permission(organization_id, 'offering.publish')
    or app.has_permission(organization_id, 'offering.delete')
    or app.has_permission(organization_id, 'organization.update')
  )
  with check (
    app.has_permission(organization_id, 'offering.write')
    or app.has_permission(organization_id, 'offering.publish')
    or app.has_permission(organization_id, 'offering.delete')
    or app.has_permission(organization_id, 'organization.update')
  );

create policy supplier_search_index_system_context
  on public.supplier_search_index for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- supplier_lists, supplier_list_items — herramienta privada de comprador,
-- nunca pública ni siquiera vía can_view_organization (nadie fuera de la
-- organización dueña debe ver las listas guardadas de otra empresa).
-- Reutiliza vendor_list.read/vendor_list.manage, ya sembrados en 0009 para
-- esta fase.
-- ============================================================================

alter table public.supplier_lists enable row level security;

create policy supplier_lists_select
  on public.supplier_lists for select
  using (app.has_permission(organization_id, 'vendor_list.read'));

create policy supplier_lists_write
  on public.supplier_lists for all
  using (app.has_permission(organization_id, 'vendor_list.manage'))
  with check (app.has_permission(organization_id, 'vendor_list.manage'));

create policy supplier_lists_system_context
  on public.supplier_lists for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.supplier_list_items enable row level security;

create policy supplier_list_items_select
  on public.supplier_list_items for select
  using (
    exists (
      select 1 from public.supplier_lists sl
      where sl.id = list_id and app.has_permission(sl.organization_id, 'vendor_list.read')
    )
  );

create policy supplier_list_items_write
  on public.supplier_list_items for all
  using (
    exists (
      select 1 from public.supplier_lists sl
      where sl.id = list_id and app.has_permission(sl.organization_id, 'vendor_list.manage')
    )
  )
  with check (
    exists (
      select 1 from public.supplier_lists sl
      where sl.id = list_id and app.has_permission(sl.organization_id, 'vendor_list.manage')
    )
  );

create policy supplier_list_items_system_context
  on public.supplier_list_items for all
  using (app.is_system_context()) with check (app.is_system_context());


-- ============================================================================
-- Analítica — sin policy de usuario, solo sistema (mismo criterio que
-- domain_events, 0010_hardening.sql). Los conteos se exponen agregados
-- desde endpoints propios, nunca por SELECT directo del cliente.
-- ============================================================================

do $$
declare
  t text;
  tables text[] := array[
    'search_logs', 'search_impressions', 'profile_views', 'offering_views'
  ];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);
    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;
