-- ============================================================================
-- 0070 · RLS de analítica agregada (fase 8.9)
-- ----------------------------------------------------------------------------
-- dimension='organization': visible solo a los miembros de esa organización
-- (is_member_of(dimension_id)). dimension in ('global','category','region'):
-- visible a cualquier usuario autenticado con capacidad BUYER o SUPPLIER
-- (app.viewer_has_capability, ya existente desde fase 1) — son agregados de
-- mercado, no datos de una empresa particular. Admin de plataforma ve todo.
-- Sin policy de escritura para app_user en sesión de usuario — solo
-- is_system_context() (el script de agregación), mismo criterio que
-- domain_events (0010).
-- ============================================================================

alter table public.marketplace_metrics_daily enable row level security;

create policy marketplace_metrics_daily_select
  on public.marketplace_metrics_daily for select
  using (
    (dimension = 'organization' and app.is_member_of(dimension_id))
    or (dimension in ('global', 'category', 'region')
        and (app.viewer_has_capability('BUYER') or app.viewer_has_capability('SUPPLIER')))
    or app.is_platform_admin()
  );

create policy marketplace_metrics_daily_system_context
  on public.marketplace_metrics_daily for all
  using (app.is_system_context()) with check (app.is_system_context());
