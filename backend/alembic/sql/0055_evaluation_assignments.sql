-- ============================================================================
-- 0055 · Comité de evaluación, evaluaciones y puntajes (fase 8.3/8.4)
-- ----------------------------------------------------------------------------
-- Fase 8.3/8.4 del roadmap. Ver docs/05-MEJORAS-PROPUESTAS.md N.11.
--
-- evaluation_assignments es solo declarativa: guarda QUIÉN evalúa QUÉ
-- dimensión y si puede ver montos (can_view_commercial) — la fila en sí NO
-- otorga acceso a ningún dato de cotización, eso lo deciden las funciones
-- SECURITY DEFINER de 0057. can_view_commercial es booleano por asignación,
-- no derivable del rol EVALUATOR (un organization_member puede tener varios
-- roles a la vez vía la PK compuesta de member_roles, así que "tiene rol
-- EVALUATOR" no basta para saber qué puede ver).
--
-- evaluations/evaluation_scores son mutables mientras status='DRAFT'
-- (el evaluador corrige antes de enviar) y quedan congeladas al pasar a
-- 'SUBMITTED' — services/evaluations.py lo aplica (mismo criterio de
-- "mutable hasta enviar, después append-only de facto" que
-- quotations.status antes de first_submitted_at).
-- ============================================================================

create type app.evaluation_status as enum ('DRAFT', 'SUBMITTED');

create table public.evaluation_assignments (
  id                       uuid primary key default gen_random_uuid(),
  sourcing_event_id        uuid not null references public.sourcing_events (id) on delete cascade,
  organization_member_id   uuid not null references public.organization_members (id) on delete cascade,

  dimension                app.evaluation_dimension not null,
  can_view_commercial      boolean not null default false,

  assigned_at              timestamptz not null default now(),
  assigned_by              uuid references public.profiles (id) on delete set null,

  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),

  constraint evaluation_assignments_unique unique (sourcing_event_id, organization_member_id, dimension)
);

comment on table public.evaluation_assignments is
  'Comité de evaluación de un evento (fase 8.3). Declara quién evalúa qué dimensión y si puede ver montos — el acceso real a datos de cotización lo dan las funciones app.list_quotation_*_for_*_evaluation (0057), nunca esta fila directamente.';

create index evaluation_assignments_event_idx on public.evaluation_assignments (sourcing_event_id);
create index evaluation_assignments_member_idx on public.evaluation_assignments (organization_member_id);

select app.apply_table_conventions('public.evaluation_assignments');


create table public.evaluations (
  id                       uuid primary key default gen_random_uuid(),
  sourcing_event_id        uuid not null references public.sourcing_events (id) on delete cascade,
  quotation_id             uuid not null references public.quotations (id) on delete cascade,
  organization_member_id   uuid not null references public.organization_members (id) on delete cascade,

  status                   app.evaluation_status not null default 'DRAFT',
  overall_comment          text,
  submitted_at             timestamptz,

  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),

  constraint evaluations_unique unique (quotation_id, organization_member_id)
);

comment on table public.evaluations is
  'Una evaluación = un evaluador × una cotización (fase 8.4). sourcing_event_id está denormalizado desde quotation_id para que las policies de RLS y el comparador no necesiten un join extra — se fija una vez al crear y nunca diverge (ambos apuntan al mismo evento por construcción del service).';

create index evaluations_event_idx on public.evaluations (sourcing_event_id);
create index evaluations_quotation_idx on public.evaluations (quotation_id);
create index evaluations_member_idx on public.evaluations (organization_member_id);

select app.apply_table_conventions('public.evaluations');


create table public.evaluation_scores (
  id                     uuid primary key default gen_random_uuid(),
  evaluation_id          uuid not null references public.evaluations (id) on delete cascade,
  evaluation_criterion_id uuid not null references public.evaluation_criteria (id) on delete cascade,

  score                  numeric not null,
  comment                text,
  evidence_document_id   uuid references public.quotation_documents (id) on delete set null,

  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  constraint evaluation_scores_unique unique (evaluation_id, evaluation_criterion_id),
  constraint evaluation_scores_range check (score >= 0 and score <= 100)
);

comment on table public.evaluation_scores is
  'Puntaje del evaluador para un criterio de la plantilla aplicada (fase 8.4), escala 0-100. evidence_document_id referencia un adjunto de la propia cotización (mismo bucket org-documents ya existente) como respaldo, opcional.';

create index evaluation_scores_evaluation_idx on public.evaluation_scores (evaluation_id);

select app.apply_table_conventions('public.evaluation_scores');
