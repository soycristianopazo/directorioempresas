-- ============================================================================
-- 0034 · Repositorio único de evidencia documental
-- ----------------------------------------------------------------------------
-- Fase 5.1/5.2 del roadmap. Ver docs/01-ARQUITECTURA.md §F.2① y
-- docs/02-MODELO-DATOS.md §D5.
--
-- "El F30 se sube una vez y sirve para los 14 programas." organization_documents
-- es UN documento lógico por (organización, tipo) — organization_document_versions
-- es el archivo concreto, append-only: nunca se edita una versión ya subida,
-- se sube una nueva y el servicio marca la anterior SUPERSEDED.
--
-- document_version_id se agrega acá a organization_certifications (columna
-- nueva, no una tabla de documentos liviana aparte) — exactamente como
-- anunciaba el comentario de cabecera de 0025_certifications.sql.
-- ============================================================================

create type app.document_category as enum (
  'LEGAL', 'TRIBUTARIO', 'LABORAL', 'FINANCIERO', 'SSO', 'SEGUROS'
);

create type app.document_version_status as enum (
  'ACTIVE', 'SUPERSEDED', 'REVOKED'
);

create table public.document_types (
  id                    uuid primary key default gen_random_uuid(),
  code                  text not null unique,
  name                  text not null,
  country_code          char(2) references public.countries (code),
  category              app.document_category not null,
  requires_expiry       boolean not null default true,
  default_validity_days integer,
  is_sensitive          boolean not null default false,
  is_active             boolean not null default true,

  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

comment on table public.document_types is
  'Catálogo de tipos documentales (F30, F30-1, carpeta tributaria, vigencia de sociedad, …). Administrado por platform.manage_taxonomy — mismo criterio que certification_types.';

select app.apply_table_conventions('public.document_types');


create table public.organization_documents (
  id               uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references public.organizations (id) on delete cascade,
  document_type_id uuid not null references public.document_types (id),

  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),

  constraint organization_documents_unique unique (organization_id, document_type_id)
);

comment on table public.organization_documents is
  'Repositorio único: un documento lógico por empresa y tipo. Se sube una vez y se reutiliza en todos los programas de acreditación — nunca un documento por programa.';

create index organization_documents_org_idx on public.organization_documents (organization_id);

select app.apply_table_conventions('public.organization_documents');


create table public.organization_document_versions (
  id             uuid primary key default gen_random_uuid(),
  document_id    uuid not null references public.organization_documents (id) on delete cascade,

  storage_path   text not null,
  checksum_sha256 text not null,
  issued_at      date,
  valid_from     date,
  valid_until    date,
  status         app.document_version_status not null default 'ACTIVE',

  created_at     timestamptz not null default now(),
  uploaded_by    uuid references public.profiles (id) on delete set null,

  constraint organization_document_versions_dates check (
    valid_from is null or valid_until is null or valid_from <= valid_until
  )
);

comment on table public.organization_document_versions is
  'Versión concreta con archivo — append-only: storage_path/checksum/fechas nunca se editan tras crearse, una versión nueva reemplaza (status=SUPERSEDED en la anterior, decidido por el servicio, no un trigger).';

create index organization_document_versions_document_idx
  on public.organization_document_versions (document_id, created_at desc);

create index organization_document_versions_valid_until_idx
  on public.organization_document_versions (valid_until)
  where status = 'ACTIVE';


alter table public.organization_certifications
  add column document_version_id uuid references public.organization_document_versions (id) on delete set null;

comment on column public.organization_certifications.document_version_id is
  'Evidencia opcional del repositorio único — sigue siendo autodeclarada sin esta columna (fase 3), la referencia es lo que fase 5 agrega para adjuntar respaldo real.';


-- Seed: tipos documentales del mercado chileno más exigidos en procurement
-- industrial/minero. Propuesta razonable, ajustable — no viene de un
-- catálogo oficial único.
insert into public.document_types (code, name, country_code, category, requires_expiry, default_validity_days, is_sensitive) values
  ('F30',                 'F30 — Certificado de cumplimiento de obligaciones laborales y previsionales', 'CL', 'LABORAL',    true,  30,  false),
  ('F30_1',                'F30-1 — Certificado de cumplimiento de obligaciones laborales (por obra/faena)', 'CL', 'LABORAL', true, 30,  false),
  ('CARPETA_TRIBUTARIA',   'Carpeta tributaria electrónica (SII)',       'CL', 'TRIBUTARIO', true,  30,  true),
  ('VIGENCIA_SOCIEDAD',    'Certificado de vigencia de la sociedad',     'CL', 'LEGAL',      true,  90,  false),
  ('RUT_SII',              'Cédula RUT / verificación SII',              'CL', 'TRIBUTARIO', false, null, true),
  ('POLIZA_RC',            'Póliza de responsabilidad civil',            'CL', 'SEGUROS',    true,  365, false),
  ('REGLAMENTO_INTERNO',   'Reglamento interno de orden, higiene y seguridad', 'CL', 'SSO',   false, null, false),
  ('CERT_ACCIDENTABILIDAD','Certificado de tasa de accidentabilidad (mutualidad)', 'CL', 'SSO', true, 365, false),
  ('BALANCE_FINANCIERO',   'Balance / estados financieros',              'CL', 'FINANCIERO', true,  365, true)
on conflict (code) do nothing;
