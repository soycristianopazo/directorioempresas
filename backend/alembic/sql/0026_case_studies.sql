-- ============================================================================
-- 0026 · Referencias de clientes y casos de éxito
-- ----------------------------------------------------------------------------
-- Fase 3.4 del roadmap. Ver docs/02-MODELO-DATOS.md §D5.
-- ============================================================================

create type app.case_study_verification_status as enum ('UNVERIFIED', 'VERIFIED', 'DISPUTED');

create table public.client_references (
  id                     uuid primary key default gen_random_uuid(),
  organization_id        uuid not null references public.organizations (id) on delete cascade,

  -- Si el cliente está en la plataforma, referenciarlo; si no, nombre libre.
  client_organization_id uuid references public.organizations (id) on delete set null,
  client_name            text,

  industry_id            uuid references public.industries (id),
  since                  date,
  is_public              boolean not null default false,
  is_verified            boolean not null default false,

  created_at             timestamptz not null default now(),

  constraint client_references_has_client check (
    client_organization_id is not null or client_name is not null
  )
);

comment on table public.client_references is
  'Clientes declarados por la empresa. client_organization_id cuando el cliente ya está en la plataforma; client_name libre en caso contrario.';

create index client_references_org_idx on public.client_references (organization_id);


create table public.case_studies (
  id                   uuid primary key default gen_random_uuid(),
  organization_id      uuid not null references public.organizations (id) on delete cascade,

  name                 text not null,
  client_reference_id  uuid references public.client_references (id) on delete set null,
  industry_id          uuid references public.industries (id),
  admin_division_id    uuid references public.admin_divisions (id),

  started_on           date,
  ended_on             date,
  duration_months      int,

  description          text,
  results              text,
  reference_contact_id uuid references public.organization_contacts (id) on delete set null,

  is_public            boolean not null default false,
  verification_status  app.case_study_verification_status not null default 'UNVERIFIED',

  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  created_by           uuid references public.profiles (id) on delete set null,

  constraint case_studies_dates check (started_on is null or ended_on is null or started_on <= ended_on),
  constraint case_studies_duration check (duration_months is null or duration_months > 0)
);

comment on table public.case_studies is
  'Proyectos y casos de éxito (§17 del brief). is_public los muestra en el perfil; reference_contact_id permite que un comprador pida referencia directa (con el consentimiento implícito de haberlo cargado).';

create index case_studies_org_idx on public.case_studies (organization_id);

select app.apply_table_conventions('public.case_studies');


create table public.case_study_taxonomy_nodes (
  case_study_id uuid not null references public.case_studies (id) on delete cascade,
  node_id       uuid not null references public.taxonomy_nodes (id),

  primary key (case_study_id, node_id)
);

comment on table public.case_study_taxonomy_nodes is
  'Qué se ejecutó en el caso, clasificado — hace la experiencia matcheable, no solo texto libre.';


create table public.case_study_media (
  id             uuid primary key default gen_random_uuid(),
  case_study_id  uuid not null references public.case_studies (id) on delete cascade,

  storage_path   text not null,
  caption        text,
  sort_order     int not null default 0,

  created_at     timestamptz not null default now(),
  created_by     uuid references public.profiles (id) on delete set null
);

comment on table public.case_study_media is
  'Fotos y evidencias del caso. Bucket org-media (público) — mismo bucket que organization_media/offering_media.';

create index case_study_media_case_study_idx on public.case_study_media (case_study_id);
