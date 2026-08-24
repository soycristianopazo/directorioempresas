-- ============================================================================
-- 0040 · Demanda — sourcing_events (el proceso) y sourcing_event_criteria
-- ----------------------------------------------------------------------------
-- Fase 6.2/6.3 del roadmap. Ver docs/02-MODELO-DATOS.md §D8.
--
-- Alcance acotado a propósito: esta migración cubre el evento y su
-- estructura (lotes, ítems, hitos, documentos, criterios MUST/NICE) — lo
-- necesario para correr el motor de matching (0041). `sourcing_event_status`
-- solo tiene DRAFT/PUBLISHED/CANCELLED porque invitar, cotizar y adjudicar
-- son fase 7/8 (sourcing_event_invitations, quotations, awards no existen
-- todavía); el enum se extiende hacia adelante cuando esas fases lleguen,
-- no se inventan estados que nada puede alcanzar hoy.
-- ============================================================================

create type app.sourcing_event_type as enum ('RFI', 'RFQ', 'RFP', 'QUICK_BUY', 'DIRECT_AWARD');
create type app.sourcing_bid_mode as enum ('OPEN', 'SEALED');
create type app.sourcing_event_status as enum ('DRAFT', 'PUBLISHED', 'CANCELLED');

create table public.sourcing_events (
  id                              uuid primary key default gen_random_uuid(),
  organization_id                 uuid not null references public.organizations (id) on delete cascade,
  requirement_id                  uuid references public.requirements (id),

  event_code                      text not null unique,
  name                            text not null,
  description                     text,
  event_type                      app.sourcing_event_type not null default 'RFQ',
  visibility                      app.visibility_level not null default 'PRIVATE',
  bid_mode                        app.sourcing_bid_mode not null default 'OPEN',
  status                          app.sourcing_event_status not null default 'DRAFT',

  currency_code                   char(3) references public.currencies (code),
  estimated_amount                numeric,

  requires_nda                    boolean not null default false,
  requires_accreditation_program_id uuid references public.accreditation_programs (id),
  max_invitations                 int,

  -- Override parcial de services/matching.py::DEFAULT_WEIGHTS por componente
  -- (§H.4) — null usa los pesos de plataforma. Se congela en
  -- match_runs.weights_snapshot en cada corrida, nunca se lee "en vivo" desde
  -- acá una vez ejecutada.
  matching_weights                jsonb,

  published_at                    timestamptz,
  bid_opened_at                   timestamptz,
  bid_opened_by                   uuid references public.profiles (id) on delete set null,

  created_at                      timestamptz not null default now(),
  updated_at                      timestamptz not null default now(),
  created_by                      uuid references public.profiles (id) on delete set null,
  updated_by                      uuid references public.profiles (id) on delete set null,

  constraint sourcing_events_max_invitations check (max_invitations is null or max_invitations > 0)
);

comment on table public.sourcing_events is
  'El proceso de compra (§20). visibility nunca es información pública general — casi siempre PRIVATE/INVITED_ONLY; a diferencia de organizations/offerings, un sourcing_event es demanda privada de un comprador, no oferta a promocionar.';

create index sourcing_events_org_idx on public.sourcing_events (organization_id);
create index sourcing_events_status_idx on public.sourcing_events (organization_id, status);

select app.apply_table_conventions('public.sourcing_events');


create table public.sourcing_event_lots (
  id                uuid primary key default gen_random_uuid(),
  sourcing_event_id uuid not null references public.sourcing_events (id) on delete cascade,

  name              text not null,
  description       text,
  sort_order        int not null default 0
);

comment on table public.sourcing_event_lots is 'Lotes adjudicables por separado.';

create index sourcing_event_lots_event_idx on public.sourcing_event_lots (sourcing_event_id);


create table public.sourcing_event_items (
  id                 uuid primary key default gen_random_uuid(),
  sourcing_event_id  uuid not null references public.sourcing_events (id) on delete cascade,
  lot_id             uuid references public.sourcing_event_lots (id) on delete set null,
  taxonomy_node_id   uuid references public.taxonomy_nodes (id),

  description        text not null,
  quantity            numeric not null,
  unit_code           text references public.units_of_measure (code),
  is_optional         boolean not null default false,
  sort_order          int not null default 0,

  constraint sourcing_event_items_quantity check (quantity > 0)
);

comment on table public.sourcing_event_items is
  'Líneas a cotizar. La cotización (fase 7) se estructura contra estas filas — capacity_fit del motor de matching (§H.4.8) compara supplier_offerings.monthly_capacity contra la quantity agregada de las líneas del evento.';

create index sourcing_event_items_event_idx on public.sourcing_event_items (sourcing_event_id);


create type app.sourcing_stage_type as enum (
  'PUBLICATION', 'QUESTIONS_DEADLINE', 'BID_DEADLINE', 'BID_OPENING', 'EVALUATION', 'ESTIMATED_AWARD'
);

create table public.sourcing_event_stages (
  id                 uuid primary key default gen_random_uuid(),
  sourcing_event_id  uuid not null references public.sourcing_events (id) on delete cascade,

  stage_type         app.sourcing_stage_type not null,
  scheduled_at        timestamptz,
  completed_at        timestamptz,

  constraint sourcing_event_stages_unique unique (sourcing_event_id, stage_type)
);

comment on table public.sourcing_event_stages is 'Hitos del proceso: publicación, cierre de consultas, cierre de ofertas, apertura, evaluación, adjudicación estimada.';


create table public.sourcing_event_documents (
  id                 uuid primary key default gen_random_uuid(),
  sourcing_event_id  uuid not null references public.sourcing_events (id) on delete cascade,

  name                text not null,
  storage_path        text not null,
  requires_nda         boolean not null default false,

  created_at           timestamptz not null default now(),
  created_by           uuid references public.profiles (id) on delete set null
);

comment on table public.sourcing_event_documents is
  'Bases, planos, anexos. Bucket org-documents, siempre privado — requires_nda marca los que exigirán aceptación de NDA antes de servir la URL firmada (fase 7, sourcing_event_ndas/nda_acceptances no existen todavía).';

create index sourcing_event_documents_event_idx on public.sourcing_event_documents (sourcing_event_id);


-- ============================================================================
-- sourcing_event_criteria — MUST_HAVE / NICE_TO_HAVE (§55, §H.3)
-- ----------------------------------------------------------------------------
-- Siete tipos de criterio, cada uno con su propia columna de referencia
-- tipada — mismo criterio que accreditation_requirements (fase 5): FK reales
-- por tipo + CHECK de coherencia, nunca un id polimórfico sin FK.
-- ============================================================================

create type app.sourcing_criterion_type as enum (
  'ATTRIBUTE', 'CERTIFICATION', 'ACCREDITATION', 'TERRITORY',
  'EXPERIENCE_YEARS', 'INDUSTRY_EXPERIENCE', 'CAPACITY', 'CUSTOM'
);
create type app.criterion_requirement_level as enum ('MUST_HAVE', 'NICE_TO_HAVE');

create table public.sourcing_event_criteria (
  id                 uuid primary key default gen_random_uuid(),
  sourcing_event_id  uuid not null references public.sourcing_events (id) on delete cascade,

  criterion_type     app.sourcing_criterion_type not null,
  requirement_level  app.criterion_requirement_level not null default 'MUST_HAVE',
  -- MUST "blando" (§H.3): nivel MUST_HAVE con is_blocking=false pesa como
  -- advertencia, no descarta al candidato — is_eligible solo lo tumba un
  -- MUST_HAVE con is_blocking=true.
  is_blocking        boolean not null default true,
  weight             numeric not null default 1,
  sort_order         int not null default 0,
  description        text,

  -- ATTRIBUTE — operador validado en Python contra docs/02-MODELO-DATOS.md
  -- §D.4 según el data_type de attribute_definitions, no con un CHECK acá
  -- (el operador válido depende de una tabla que este CHECK no puede leer).
  attribute_definition_id uuid references public.attribute_definitions (id),
  operator                text,
  value_text               text,
  value_number              numeric,
  value_number_max          numeric,
  value_boolean              boolean,
  value_date                 date,
  value_date_max              date,
  value_options                text[],

  -- CERTIFICATION
  certification_type_id     uuid references public.certification_types (id),

  -- ACCREDITATION
  accreditation_program_id  uuid references public.accreditation_programs (id),

  -- TERRITORY
  admin_division_id          uuid references public.admin_divisions (id),
  max_mobilization_days       int,

  -- EXPERIENCE_YEARS (min_years solo) / INDUSTRY_EXPERIENCE (industry_id + min_years)
  industry_id                  uuid references public.industries (id),
  min_years                     int,

  -- CAPACITY
  min_capacity                   numeric,

  created_at                      timestamptz not null default now(),
  updated_at                      timestamptz not null default now(),

  constraint sourcing_event_criteria_reference check (
    (criterion_type = 'ATTRIBUTE' and attribute_definition_id is not null)
    or (criterion_type = 'CERTIFICATION' and certification_type_id is not null)
    or (criterion_type = 'ACCREDITATION' and accreditation_program_id is not null)
    or (criterion_type = 'TERRITORY' and admin_division_id is not null)
    or (criterion_type = 'EXPERIENCE_YEARS' and min_years is not null)
    or (criterion_type = 'INDUSTRY_EXPERIENCE' and industry_id is not null and min_years is not null)
    or (criterion_type = 'CAPACITY' and min_capacity is not null)
    or (criterion_type = 'CUSTOM' and description is not null)
  )
);

comment on table public.sourcing_event_criteria is
  'MUST_HAVE/NICE_TO_HAVE del evento (§55). CUSTOM nunca bloquea — no hay forma de auto-evaluar texto libre, se muestra al revisor humano como nota. Los demás tipos alimentan la Etapa 2 (elegibilidad) y, para NICE_TO_HAVE, la Etapa 3 (attribute_fit) del motor de matching.';

create index sourcing_event_criteria_event_idx on public.sourcing_event_criteria (sourcing_event_id);

select app.apply_table_conventions('public.sourcing_event_criteria');
