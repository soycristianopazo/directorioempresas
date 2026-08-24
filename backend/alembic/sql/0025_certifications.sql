-- ============================================================================
-- 0025 · Certificaciones
-- ----------------------------------------------------------------------------
-- Fase 3.4 del roadmap. Ver docs/02-MODELO-DATOS.md §D5.
--
-- Alcance acotado a propósito: organization_certifications es autodeclarada
-- en esta fase (certificate_number, fechas, verification_status='UNVERIFIED'
-- por defecto) — SIN evidencia documental todavía. El repositorio de
-- documentos versionados (document_types, organization_documents,
-- organization_document_versions) y la revisión real de un acreditador son
-- Fase 5 (Acreditación); document_version_id se agrega ahí como columna
-- nueva, no se inventa una tabla de documentos liviana aquí para no
-- duplicar ese modelo.
-- ============================================================================

create type app.certification_verification_status as enum (
  'UNVERIFIED', 'PENDING_REVIEW', 'VERIFIED', 'REJECTED', 'EXPIRED'
);

create table public.certification_types (
  id              uuid primary key default gen_random_uuid(),
  code            text not null unique,
  name            text not null,
  issuing_body    text,
  requires_scope  boolean not null default false,
  requires_expiry boolean not null default true,
  is_active       boolean not null default true,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.certification_types is
  'Catálogo de tipos de certificación (ISO 9001/14001/45001, mutualidad, sellos sectoriales). Administrado por platform.manage_taxonomy — mismo permiso que la taxonomía, es un catálogo de plataforma del mismo tipo.';

select app.apply_table_conventions('public.certification_types');


create table public.organization_certifications (
  id                    uuid primary key default gen_random_uuid(),
  organization_id       uuid not null references public.organizations (id) on delete cascade,
  certification_type_id uuid not null references public.certification_types (id),

  certificate_number    text,
  scope                 text,
  issued_by             text,
  issued_at             date,
  valid_until           date,

  verification_status   app.certification_verification_status not null default 'UNVERIFIED',

  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  created_by            uuid references public.profiles (id) on delete set null,

  constraint organization_certifications_dates check (
    issued_at is null or valid_until is null or issued_at <= valid_until
  )
);

comment on table public.organization_certifications is
  'Certificación autodeclarada por la empresa. verification_status queda en UNVERIFIED hasta que exista el flujo de revisión (fase 5) — no se inventa aquí.';

create index organization_certifications_org_idx on public.organization_certifications (organization_id);

select app.apply_table_conventions('public.organization_certifications');


-- Seed de certificaciones comunes en el mercado chileno/industrial.
insert into public.certification_types (code, name, issuing_body, requires_scope, requires_expiry) values
  ('ISO_9001',  'ISO 9001 — Gestión de calidad',       null, true,  true),
  ('ISO_14001', 'ISO 14001 — Gestión ambiental',        null, true,  true),
  ('ISO_45001', 'ISO 45001 — Seguridad y salud ocupacional', null, true, true),
  ('ISO_27001', 'ISO 27001 — Seguridad de la información', null, true, true),
  ('MUTUALIDAD','Adherido a mutualidad de seguridad',   null, false, true),
  ('SELLO_OS10','OS10 — Vigilancia privada',            null, false, true)
on conflict (code) do nothing;
