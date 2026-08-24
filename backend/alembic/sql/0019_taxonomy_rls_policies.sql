-- ============================================================================
-- 0019 · RLS de datos de referencia y taxonomía
-- ----------------------------------------------------------------------------
-- Fase 2.8 del roadmap.
--
-- Todas las tablas de 0011-0016 son datos de referencia/taxonomía: públicos
-- por diseño (incluso para un visitante anónimo — un selector de comuna o el
-- árbol de categorías no tiene nada que ocultar), con escritura restringida a
-- quien tenga 'platform.manage_taxonomy'.
--
-- Misma matriz de tres policies permisivas en las quince tablas, así que se
-- aplica en un loop en vez de repetir el bloque a mano quince veces — más
-- fácil de auditar que quince copias que podrían divergir en silencio.
--
-- Sin FORCE ROW LEVEL SECURITY: mismo motivo documentado extensamente en
-- 0010_hardening.sql. app.has_platform_permission() (0018) es SECURITY
-- DEFINER, propiedad de `postgres`; forzar RLS sobre el dueño rompería la vía
-- de escape que ese helper necesita para no recursionar contra sus propias
-- policies. ENABLE sin FORCE alcanza: `app_user` no es dueño de ninguna
-- tabla, así que ENABLE ya lo cubre sin ambigüedad.
-- ============================================================================

do $$
declare
  t text;
  tables text[] := array[
    'countries', 'currencies', 'fx_rates', 'units_of_measure', 'languages',
    'admin_divisions',
    'taxonomy_nodes', 'taxonomy_node_translations', 'taxonomy_node_synonyms',
    'taxonomy_external_mappings', 'industries', 'industry_translations',
    'attribute_definitions', 'attribute_options', 'taxonomy_node_attributes'
  ];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);

    execute format(
      'create policy %I on public.%I for select using (true)',
      t || '_select_public', t
    );

    execute format(
      'create policy %I on public.%I for all '
      'using (app.has_platform_permission(''platform.manage_taxonomy'')) '
      'with check (app.has_platform_permission(''platform.manage_taxonomy''))',
      t || '_write_platform', t
    );

    execute format(
      'create policy %I on public.%I for all '
      'using (app.is_system_context()) with check (app.is_system_context())',
      t || '_system_context', t
    );
  end loop;
end $$;
