-- ============================================================================
-- 0036 · Estado de acreditación por organización
-- ----------------------------------------------------------------------------
-- Fase 5.4 del roadmap. Ver docs/01-ARQUITECTURA.md §F.2③④⑤/§F.4.
--
-- accreditation_enrollments responde "¿está acreditada esta empresa para
-- esto?" — una fila por (organización, programa), nunca un campo suelto en
-- organizations. accreditation_fulfillments es el cumplimiento ítem a ítem.
--
-- completion_pct se recalcula en Python (services/accreditation.py), no por
-- trigger — mismo criterio que recompute_completion_pct/reindex_offering de
-- fases anteriores. accreditation_status_history y accreditation_review_events
-- son append-only de verdad (REVOKE UPDATE, DELETE), mismo criterio que
-- audit_logs/search_logs.
-- ============================================================================

create table public.accreditation_enrollments (
  id             uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  program_id     uuid not null references public.accreditation_programs (id),

  status         app.accreditation_enrollment_status not null default 'INCOMPLETE',
  completion_pct smallint not null default 0,
  score          numeric,

  valid_from     date,
  valid_until    date,
  submitted_at   timestamptz,
  decided_at     timestamptz,
  decided_by     uuid references public.profiles (id) on delete set null,

  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),

  constraint accreditation_enrollments_unique unique (organization_id, program_id),
  constraint accreditation_enrollments_completion_range check (completion_pct between 0 and 100)
);

comment on table public.accreditation_enrollments is
  'Estado de una organización frente a un programa. "¿Está acreditada esta empresa para esto?" — la respuesta vive acá, nunca en un campo de organizations.';

create index accreditation_enrollments_org_idx on public.accreditation_enrollments (organization_id);
create index accreditation_enrollments_program_idx on public.accreditation_enrollments (program_id, status);

select app.apply_table_conventions('public.accreditation_enrollments');


create table public.accreditation_fulfillments (
  id                 uuid primary key default gen_random_uuid(),
  enrollment_id      uuid not null references public.accreditation_enrollments (id) on delete cascade,
  requirement_id     uuid not null references public.accreditation_requirements (id),

  document_version_id uuid references public.organization_document_versions (id),
  certification_id     uuid references public.organization_certifications (id),
  declared_value        text,

  status         app.accreditation_fulfillment_status not null default 'PENDING',
  reviewer_id    uuid references public.profiles (id) on delete set null,
  reviewed_at    timestamptz,
  observation    text,
  expires_at     date,

  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),

  constraint accreditation_fulfillments_unique unique (enrollment_id, requirement_id)
);

comment on table public.accreditation_fulfillments is
  'Cumplimiento ítem a ítem. Evidencia por FK (document_version_id / certification_id) o declared_value libre para DECLARATION/FORM. expires_at se copia de la evidencia al adjuntarla — la vigencia efectiva ("¿sigue vigente hoy?") siempre se evalúa en la consulta (expires_at >= current_date), no depende de un job que la marque EXPIRED.';

create index accreditation_fulfillments_enrollment_idx on public.accreditation_fulfillments (enrollment_id);
create index accreditation_fulfillments_expires_idx on public.accreditation_fulfillments (expires_at) where status = 'APPROVED';

select app.apply_table_conventions('public.accreditation_fulfillments');


create table public.accreditation_section_progress (
  enrollment_id  uuid not null references public.accreditation_enrollments (id) on delete cascade,
  group_id       uuid not null references public.requirement_groups (id) on delete cascade,
  completion_pct smallint not null default 0,
  updated_at     timestamptz not null default now(),

  primary key (enrollment_id, group_id),
  constraint accreditation_section_progress_range check (completion_pct between 0 and 100)
);

comment on table public.accreditation_section_progress is
  'Materializado por services/accreditation.py::recompute_enrollment_completion(), no por trigger. Es lo que se pinta en pantalla por sección (Tributario/Legal/SSO/Financiero) — docs/01-ARQUITECTURA.md §F.4 lo llama "la vista del §11 del brief".';


create table public.accreditation_status_history (
  id             uuid primary key default gen_random_uuid(),
  enrollment_id  uuid not null references public.accreditation_enrollments (id) on delete cascade,
  from_status    app.accreditation_enrollment_status,
  to_status      app.accreditation_enrollment_status not null,
  actor_id       uuid references public.profiles (id) on delete set null,
  reason         text,
  created_at     timestamptz not null default now()
);

comment on table public.accreditation_status_history is
  'Append-only: cada cambio de estado con actor, motivo y timestamp. actor_id nulo = transición automática (ej. vencimiento).';

create index accreditation_status_history_enrollment_idx
  on public.accreditation_status_history (enrollment_id, created_at desc);

revoke update, delete on public.accreditation_status_history from app_user;


create table public.accreditation_review_events (
  id             uuid primary key default gen_random_uuid(),
  fulfillment_id uuid not null references public.accreditation_fulfillments (id) on delete cascade,
  actor_id       uuid references public.profiles (id) on delete set null,
  message        text not null,
  created_at     timestamptz not null default now()
);

comment on table public.accreditation_review_events is
  'Bitácora de revisión de un ítem: observaciones del revisor, solicitudes de subsanación, respuestas del proveedor — todo en la misma línea de tiempo, append-only.';

create index accreditation_review_events_fulfillment_idx
  on public.accreditation_review_events (fulfillment_id, created_at);

revoke update, delete on public.accreditation_review_events from app_user;
