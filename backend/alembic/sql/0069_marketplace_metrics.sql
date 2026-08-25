-- ============================================================================
-- 0069 · Analítica agregada del marketplace (fase 8.9)
-- ----------------------------------------------------------------------------
-- dimension_id no lleva FK propia: su tabla referenciada depende del valor
-- de `dimension` (organizations si 'organization', taxonomy_nodes si
-- 'category', admin_divisions si 'region', NULL si 'global') — mismo criterio
-- de columna polimórfica ya usado en otras partes del proyecto donde una FK
-- única no puede cubrir varias tablas posibles; la integridad la garantiza
-- backend/scripts/aggregate_marketplace_metrics.py, el único escritor real
-- (session_for_system, sin flujo de escritura de usuario).
-- ============================================================================

create table public.marketplace_metrics_daily (
  id              uuid primary key default gen_random_uuid(),
  metric_date     date not null,
  dimension       text not null,
  dimension_id    uuid,

  metrics         jsonb not null,

  computed_at     timestamptz not null default now(),

  constraint marketplace_metrics_daily_dimension check (dimension in ('global', 'organization', 'category', 'region')),
  constraint marketplace_metrics_daily_dimension_id check (
    (dimension = 'global' and dimension_id is null)
    or (dimension <> 'global' and dimension_id is not null)
  ),
  constraint marketplace_metrics_daily_unique unique (metric_date, dimension, dimension_id)
);

comment on table public.marketplace_metrics_daily is
  'Agregados diarios (fase 8.9) — el día corriente se calcula en vivo desde las tablas fuente en services/analytics.py, esta tabla solo cubre "ayer hacia atrás". metrics es jsonb libre: {sourcing_events_published, quotations_received, avg_time_to_quote_hours, profile_views, ...} según dimension.';

create index marketplace_metrics_daily_lookup_idx
  on public.marketplace_metrics_daily (dimension, dimension_id, metric_date desc);

-- Sin revoke update/delete: backend/scripts/aggregate_marketplace_metrics.py
-- hace upsert idempotente (on conflict do update) sobre metric_date/
-- dimension/dimension_id, mismo criterio de atomicidad que la secuencia de
-- 0053. update/delete quedan permitidos a nivel de grant, pero RLS (0070)
-- los restringe a is_system_context() — nunca a app_user en una sesión de
-- usuario normal.
