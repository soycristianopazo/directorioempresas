-- ============================================================================
-- 0041 · Motor de matching — match_runs / match_results (§H)
-- ----------------------------------------------------------------------------
-- Fase 6.4-6.7 del roadmap. Ver docs/03-MATCHING-ENGINE.md.
--
-- Append-only por diseño (§H.1: "misma entrada + misma versión del motor +
-- mismos pesos = mismo resultado, siempre" — reproducible ante una
-- auditoría). services/matching.py::run_matching() es quien escribe estas
-- filas, nunca un UPDATE — REVOKE UPDATE/DELETE mismo criterio que
-- audit_logs/accreditation_status_history.
-- ============================================================================

create type app.match_run_trigger as enum ('MANUAL', 'PUBLISH', 'NIGHTLY');

create table public.match_runs (
  id                     uuid primary key default gen_random_uuid(),
  sourcing_event_id      uuid not null references public.sourcing_events (id) on delete cascade,

  engine_version         text not null,
  weights_snapshot       jsonb not null,
  trigger_source         app.match_run_trigger not null default 'MANUAL',
  triggered_by_member_id uuid references public.profiles (id) on delete set null,

  candidates_evaluated   int not null,
  eligible_count         int not null,
  duration_ms            int not null,
  executed_at            timestamptz not null default now()
);

comment on table public.match_runs is
  'Una corrida real del motor (dry_run nunca persiste — ver services/matching.py). engine_version + weights_snapshot hacen reproducible cualquier resultado histórico aunque la fórmula cambie después.';

create index match_runs_event_idx on public.match_runs (sourcing_event_id, executed_at desc);

revoke update, delete on public.match_runs from app_user;


create table public.match_results (
  id               uuid primary key default gen_random_uuid(),
  match_run_id     uuid not null references public.match_runs (id) on delete cascade,
  organization_id  uuid not null references public.organizations (id),
  offering_id      uuid not null references public.supplier_offerings (id),

  total_score      numeric not null,
  is_eligible      boolean not null,
  blocking_reasons text[] not null default '{}',
  score_breakdown  jsonb not null,
  -- rank es null para los no elegibles — nunca se mezclan con los elegibles
  -- en el ranking (§H.1: "elegibilidad y puntaje son dos cosas distintas").
  rank             int,

  created_at       timestamptz not null default now(),

  constraint match_results_unique unique (match_run_id, offering_id)
);

comment on table public.match_results is
  'Resultado por offering candidato de una corrida. v_match_results_by_org (más adelante, si hace falta) agregaría por organización según §H.5 — por ahora la agregación la hace services/matching.py en Python, sobre un conjunto ya chico.';

create index match_results_run_idx on public.match_results (match_run_id);
create index match_results_run_eligible_rank_idx
  on public.match_results (match_run_id, rank)
  where is_eligible;

revoke update, delete on public.match_results from app_user;
