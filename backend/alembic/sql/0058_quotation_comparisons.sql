-- ============================================================================
-- 0058 · Comparador horizontal (fase 8.1)
-- ----------------------------------------------------------------------------
-- Append-only — mismo criterio que match_runs (0041): cada corrida del
-- comparador es una fila nueva, reproducible con su propio snapshot de
-- pesos, nunca se sobrescribe una corrida anterior.
-- ============================================================================

create table public.quotation_comparisons (
  id                     uuid primary key default gen_random_uuid(),
  sourcing_event_id      uuid not null references public.sourcing_events (id) on delete cascade,

  criteria_snapshot      jsonb not null,
  ranking                jsonb not null,

  executed_at            timestamptz not null default now(),
  executed_by            uuid references public.profiles (id) on delete set null
);

comment on table public.quotation_comparisons is
  'Corrida del comparador ponderado (fase 8.1) — agrega evaluation_scores por evaluador × criterio, pondera por evaluation_criteria.weight (congelado en criteria_snapshot, igual que event_evaluation_setup) y produce ranking (jsonb: array de {quotation_id, supplier_organization_id, total_score, breakdown}).';

create index quotation_comparisons_event_idx on public.quotation_comparisons (sourcing_event_id, executed_at desc);

revoke update, delete on public.quotation_comparisons from app_user;


alter table public.quotation_comparisons enable row level security;

create policy quotation_comparisons_select
  on public.quotation_comparisons for select
  using (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.read')
    )
  );

create policy quotation_comparisons_insert
  on public.quotation_comparisons for insert
  with check (
    exists (
      select 1 from public.sourcing_events se
      where se.id = sourcing_event_id and app.has_permission(se.organization_id, 'evaluation.manage')
    )
  );
-- crear una corrida del comparador es una acción de configuración/gestión,
-- igual que correr matching está gateado por sourcing_event.create hoy —
-- mismo criterio de "quien puede armar el proceso, puede correr el análisis".

create policy quotation_comparisons_system_context
  on public.quotation_comparisons for all
  using (app.is_system_context()) with check (app.is_system_context());
