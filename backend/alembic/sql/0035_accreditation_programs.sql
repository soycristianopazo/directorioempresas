-- ============================================================================
-- 0035 · Programas de acreditación y exigencias
-- ----------------------------------------------------------------------------
-- Fase 5.3 del roadmap. Ver docs/01-ARQUITECTURA.md §F.2②/F.3 y
-- docs/02-MODELO-DATOS.md §D6.
--
-- La acreditación es una relación (organización, programa), nunca un campo
-- organizations.accreditation_status — un proveedor puede estar acreditado
-- para servicios TI y no para trabajos eléctricos de alto riesgo. Este
-- archivo define las EXIGENCIAS (qué pide un programa); 0036 define el
-- ESTADO de una organización frente a esas exigencias.
--
-- accreditation_status_transitions es DATA, no código — permite auditar y
-- ajustar el flujo sin deploy (docs/01-ARQUITECTURA.md §F.3).
-- ============================================================================

create type app.accreditation_owner_scope as enum ('PLATFORM', 'ORGANIZATION');

create type app.accreditation_requirement_kind as enum (
  'DOCUMENT', 'CERTIFICATION', 'ATTRIBUTE', 'DECLARATION', 'FORM'
);

create type app.accreditation_enrollment_status as enum (
  'INCOMPLETE', 'PENDING_DOCUMENTS', 'UNDER_REVIEW', 'ACCREDITED',
  'OBSERVED', 'SUSPENDED', 'REJECTED', 'EXPIRED'
);

create type app.accreditation_fulfillment_status as enum (
  'PENDING', 'SUBMITTED', 'UNDER_REVIEW', 'OBSERVED', 'APPROVED', 'REJECTED', 'EXPIRED'
);


create table public.accreditation_programs (
  id                          uuid primary key default gen_random_uuid(),
  code                        text not null unique,
  name                        text not null,
  description                 text,

  owner_scope                 app.accreditation_owner_scope not null default 'PLATFORM',
  owner_organization_id       uuid references public.organizations (id) on delete cascade,

  applies_to_taxonomy_node_id uuid references public.taxonomy_nodes (id),
  applies_to_industry_id      uuid references public.industries (id),
  applies_to_risk_level       app.risk_level,
  country_code                char(2) references public.countries (code),

  validity_months             integer not null default 12,
  is_active                   boolean not null default true,

  created_at                  timestamptz not null default now(),
  updated_at                  timestamptz not null default now(),

  constraint accreditation_programs_owner check (
    (owner_scope = 'PLATFORM' and owner_organization_id is null)
    or (owner_scope = 'ORGANIZATION' and owner_organization_id is not null)
  )
);

comment on table public.accreditation_programs is
  'Programa de exigencias. owner_scope=PLATFORM: programa base de la plataforma. owner_scope=ORGANIZATION: programa propio de un comprador (el modelo lo soporta; la UI de autoría queda para una fase posterior — ver el plan de fase 5).';

create index accreditation_programs_owner_org_idx
  on public.accreditation_programs (owner_organization_id) where owner_organization_id is not null;

select app.apply_table_conventions('public.accreditation_programs');


create table public.requirement_groups (
  id          uuid primary key default gen_random_uuid(),
  program_id  uuid not null references public.accreditation_programs (id) on delete cascade,
  name        text not null,
  weight      numeric not null default 1,
  sort_order  integer not null default 0,

  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.requirement_groups is
  'Secciones del programa (Tributario, Legal, SSO, Financiero, …). weight es informativo para la vista por sección — el % global de completitud lo determina el weight de cada accreditation_requirements, no este.';

create index requirement_groups_program_idx on public.requirement_groups (program_id, sort_order);

select app.apply_table_conventions('public.requirement_groups');


create table public.accreditation_requirements (
  id                       uuid primary key default gen_random_uuid(),
  program_id               uuid not null references public.accreditation_programs (id) on delete cascade,
  group_id                 uuid not null references public.requirement_groups (id) on delete cascade,

  requirement_kind         app.accreditation_requirement_kind not null,
  document_type_id         uuid references public.document_types (id),
  certification_type_id    uuid references public.certification_types (id),
  attribute_definition_id  uuid references public.attribute_definitions (id),

  name                     text not null,
  description              text,
  is_mandatory             boolean not null default true,
  weight                   numeric not null default 1,
  min_validity_days        integer,
  reviewer_role            text not null default 'ACCREDITATION_REVIEWER',
  sort_order               integer not null default 0,

  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),

  constraint accreditation_requirements_reviewer_role check (
    reviewer_role in ('ACCREDITATION_REVIEWER', 'PLATFORM_ADMIN')
  ),
  constraint accreditation_requirements_ref check (
    num_nonnulls(document_type_id, certification_type_id, attribute_definition_id) <= 1
  )
);

comment on table public.accreditation_requirements is
  'Ítem exigido por el programa. La correspondencia exacta requirement_kind↔columna de referencia (DOCUMENT→document_type_id, etc.) la valida el servicio al crear el ítem, no un CHECK — mismo criterio que otras validaciones condicionales por tipo en este proyecto (ver offering_attribute_values).';

create index accreditation_requirements_program_idx on public.accreditation_requirements (program_id, sort_order);
create index accreditation_requirements_group_idx on public.accreditation_requirements (group_id);

select app.apply_table_conventions('public.accreditation_requirements');


create table public.accreditation_status_transitions (
  from_status  app.accreditation_enrollment_status not null,
  to_status    app.accreditation_enrollment_status not null,
  label        text not null,
  requires_reviewer boolean not null default false,

  primary key (from_status, to_status)
);

comment on table public.accreditation_status_transitions is
  'Transiciones válidas de accreditation_enrollments.status, como datos — permite auditar y ajustar el flujo sin deploy (docs/01-ARQUITECTURA.md §F.3). services/accreditation.py consulta esta tabla antes de cualquier cambio de estado.';


-- Seed: transiciones de la máquina de estados de F.3.
insert into public.accreditation_status_transitions (from_status, to_status, label, requires_reviewer) values
  ('INCOMPLETE',        'PENDING_DOCUMENTS', 'Postular',                    false),
  ('PENDING_DOCUMENTS',  'UNDER_REVIEW',      'Enviar a revisión',          false),
  ('UNDER_REVIEW',       'ACCREDITED',        'Aprobar acreditación',       true),
  ('UNDER_REVIEW',       'OBSERVED',          'Observar',                   true),
  ('UNDER_REVIEW',       'REJECTED',          'Rechazar',                   true),
  ('OBSERVED',           'PENDING_DOCUMENTS', 'Responder observación',      false),
  ('OBSERVED',           'UNDER_REVIEW',      'Reenviar a revisión',        false),
  ('OBSERVED',           'REJECTED',          'Rechazar',                   true),
  ('ACCREDITED',         'SUSPENDED',         'Suspender',                  true),
  ('ACCREDITED',         'EXPIRED',           'Vencer',                     false),
  ('SUSPENDED',          'UNDER_REVIEW',      'Reactivar revisión',         true),
  ('EXPIRED',            'PENDING_DOCUMENTS', 'Renovar',                    false)
on conflict (from_status, to_status) do nothing;


-- Seed: un programa base con secciones y exigencias reales — el punto de
-- control literal del roadmap ("seed del programa base").
insert into public.accreditation_programs (code, name, description, owner_scope, country_code, validity_months)
values (
  'ACREDITACION_BASE',
  'Acreditación Base — Proveedores',
  'Requisitos mínimos para operar como proveedor acreditado en la plataforma: cumplimiento tributario, vigencia legal, seguridad y salud ocupacional.',
  'PLATFORM', 'CL', 12
)
on conflict (code) do nothing;

do $$
declare
  v_program_id uuid;
  v_group_tributario uuid;
  v_group_legal uuid;
  v_group_sso uuid;
  v_group_financiero uuid;
begin
  select id into v_program_id from public.accreditation_programs where code = 'ACREDITACION_BASE';

  insert into public.requirement_groups (program_id, name, weight, sort_order)
  values (v_program_id, 'Tributario', 30, 1)
  returning id into v_group_tributario;

  insert into public.requirement_groups (program_id, name, weight, sort_order)
  values (v_program_id, 'Legal', 25, 2)
  returning id into v_group_legal;

  insert into public.requirement_groups (program_id, name, weight, sort_order)
  values (v_program_id, 'Seguridad y salud ocupacional', 25, 3)
  returning id into v_group_sso;

  insert into public.requirement_groups (program_id, name, weight, sort_order)
  values (v_program_id, 'Financiero', 20, 4)
  returning id into v_group_financiero;

  insert into public.accreditation_requirements
    (program_id, group_id, requirement_kind, document_type_id, name, is_mandatory, weight, min_validity_days, sort_order)
  values
    (v_program_id, v_group_tributario, 'DOCUMENT',
     (select id from public.document_types where code = 'F30'),
     'F30 vigente', true, 15, 30, 1),
    (v_program_id, v_group_tributario, 'DOCUMENT',
     (select id from public.document_types where code = 'CARPETA_TRIBUTARIA'),
     'Carpeta tributaria electrónica', true, 15, 30, 2),
    (v_program_id, v_group_legal, 'DOCUMENT',
     (select id from public.document_types where code = 'VIGENCIA_SOCIEDAD'),
     'Vigencia de la sociedad', true, 25, 90, 1),
    (v_program_id, v_group_sso, 'DOCUMENT',
     (select id from public.document_types where code = 'REGLAMENTO_INTERNO'),
     'Reglamento interno de orden, higiene y seguridad', true, 10, null, 1),
    (v_program_id, v_group_sso, 'DOCUMENT',
     (select id from public.document_types where code = 'CERT_ACCIDENTABILIDAD'),
     'Tasa de accidentabilidad', true, 15, 365, 2),
    (v_program_id, v_group_financiero, 'DOCUMENT',
     (select id from public.document_types where code = 'BALANCE_FINANCIERO'),
     'Balance / estados financieros', false, 20, 365, 1);
end $$;
