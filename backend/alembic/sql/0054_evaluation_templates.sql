-- ============================================================================
-- 0054 · Plantillas y criterios de evaluación (fase 8.1/8.2)
-- ----------------------------------------------------------------------------
-- Fase 8.2 del roadmap. Ver docs/05-MEJORAS-PROPUESTAS.md N.11, plan de fase 8.
--
-- evaluation_criteria (dimensión TECHNICAL/COMMERCIAL/HSE/LEGAL/FINANCIAL,
-- con peso para el comparador) es una tabla GENUINAMENTE DISTINTA de
-- sourcing_event_criteria (fase 6, MUST/NICE_TO_HAVE de 7 tipos, usados por
-- el motor de matching) — sin relación FK entre ambas. Una es "qué exige el
-- comprador para invitar", la otra es "cómo pondera el comité al comparar
-- ofertas ya recibidas".
--
-- event_evaluation_setup es un SNAPSHOT (jsonb), no una FK viva a
-- evaluation_templates — mismo criterio que match_runs.weights_snapshot
-- (0041): si la plantilla cambia después de aplicarse a un evento, el
-- proceso en curso no debe alterarse retroactivamente. template_id se
-- conserva solo como referencia de origen/trazabilidad, nunca se relee para
-- resolver pesos vigentes.
-- ============================================================================

create type app.evaluation_dimension as enum (
  'TECHNICAL', 'COMMERCIAL', 'HSE', 'LEGAL', 'FINANCIAL'
);

create table public.evaluation_templates (
  id               uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references public.organizations (id) on delete cascade,

  name             text not null,
  description      text,

  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  created_by       uuid references public.profiles (id) on delete set null,
  updated_by       uuid references public.profiles (id) on delete set null
);

comment on table public.evaluation_templates is
  'Plantilla de evaluación reutilizable a nivel de organización (fase 8.2). Se aplica a un evento vía event_evaluation_setup, que congela una copia — editar la plantilla después no altera procesos ya configurados.';

create index evaluation_templates_org_idx on public.evaluation_templates (organization_id);

select app.apply_table_conventions('public.evaluation_templates');


create table public.evaluation_criteria (
  id            uuid primary key default gen_random_uuid(),
  template_id   uuid not null references public.evaluation_templates (id) on delete cascade,

  dimension     app.evaluation_dimension not null,
  name          text not null,
  description   text,
  weight        numeric not null default 1,
  sort_order    int not null default 0,

  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  constraint evaluation_criteria_weight check (weight >= 0)
);

comment on table public.evaluation_criteria is
  'Criterios de una plantilla, cada uno con su dimensión y peso (fase 8.2). weight es relativo dentro del template (no forzado a sumar 100 en la base — services/evaluations.py valida la suma antes de aplicar la plantilla a un evento).';

create index evaluation_criteria_template_idx on public.evaluation_criteria (template_id, sort_order);

select app.apply_table_conventions('public.evaluation_criteria');


create table public.event_evaluation_setup (
  id                 uuid primary key default gen_random_uuid(),
  sourcing_event_id  uuid not null references public.sourcing_events (id) on delete cascade,

  template_id        uuid references public.evaluation_templates (id) on delete set null,
  template_name_snapshot text not null,
  criteria_snapshot  jsonb not null,

  applied_at         timestamptz not null default now(),
  applied_by         uuid references public.profiles (id) on delete set null,
  updated_at         timestamptz not null default now(),

  constraint event_evaluation_setup_unique unique (sourcing_event_id)
);

comment on table public.event_evaluation_setup is
  'Snapshot de la plantilla aplicada a UN evento (fase 8.2) — mismo criterio que match_runs.weights_snapshot (0041): un cambio posterior a evaluation_templates/evaluation_criteria no altera por sí solo un proceso ya configurado. criteria_snapshot es un array jsonb de {id, dimension, name, weight} congelado al aplicar. A diferencia de match_runs, esta fila SÍ es mutable (una sola por evento, con updated_at) porque re-aplicar/ajustar el setup antes de que exista una evaluación real es una corrección legítima, no una nueva corrida histórica — services/evaluations.py bloquea el re-setup una vez que existe una evaluación SUBMITTED.';

create index event_evaluation_setup_event_idx on public.event_evaluation_setup (sourcing_event_id);

create trigger trg_event_evaluation_setup_set_updated_at
  before update on public.event_evaluation_setup
  for each row execute function app.set_updated_at();
