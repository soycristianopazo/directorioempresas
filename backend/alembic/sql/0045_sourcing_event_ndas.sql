-- ============================================================================
-- 0045 · NDA del evento y su aceptación (fase 7.2)
-- ----------------------------------------------------------------------------
-- Fase 7.2 del roadmap. Ver docs/02-MODELO-DATOS.md §D8.
--
-- nda_acceptances se arma con tres convenciones de columna ya establecidas en
-- este proyecto, no inventadas: ip_address/user_agent (user_sessions,
-- audit_logs), accepted_at/accepted_by (organization_invitations),
-- checksum_sha256 (organization_document_versions) — el hash prueba QUÉ
-- versión exacta del texto se aceptó, no solo que se aceptó "una" versión.
-- Append-only (revoke update, delete): es un registro de prueba legal, mismo
-- criterio que audit_logs/accreditation_status_history.
-- ============================================================================

create table public.sourcing_event_ndas (
  id                 uuid primary key default gen_random_uuid(),
  sourcing_event_id  uuid not null references public.sourcing_events (id) on delete cascade,

  version            int not null default 1,
  title              text not null,
  body_text          text not null,
  checksum_sha256    text not null,

  created_at         timestamptz not null default now(),
  created_by         uuid references public.profiles (id) on delete set null,

  constraint sourcing_event_ndas_unique unique (sourcing_event_id, version),
  constraint sourcing_event_ndas_version check (version > 0)
);

comment on table public.sourcing_event_ndas is
  'Texto/plantilla de NDA del evento, versionado. checksum_sha256 se calcula sobre body_text al crear la versión — nda_acceptances.checksum_sha256 debe calzar exactamente con el de la versión aceptada.';

create index sourcing_event_ndas_event_idx on public.sourcing_event_ndas (sourcing_event_id);


create table public.nda_acceptances (
  id              uuid primary key default gen_random_uuid(),
  nda_id          uuid not null references public.sourcing_event_ndas (id) on delete cascade,
  organization_id uuid not null references public.organizations (id) on delete cascade,

  accepted_by     uuid references public.profiles (id) on delete set null,
  accepted_at     timestamptz not null default now(),
  ip_address      inet,
  user_agent      text,
  checksum_sha256 text not null,

  constraint nda_acceptances_unique unique (nda_id, organization_id)
);

comment on table public.nda_acceptances is
  'Aceptación registrada: quién, cuándo, IP, hash del texto aceptado (§D8). Append-only — es la prueba legal de aceptación, no se corrige, se vuelve a aceptar una versión nueva del NDA si hace falta.';

create index nda_acceptances_org_idx on public.nda_acceptances (organization_id);

revoke update, delete on public.nda_acceptances from app_user;
