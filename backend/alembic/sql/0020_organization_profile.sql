-- ============================================================================
-- 0020 · Perfil extendido de organización
-- ----------------------------------------------------------------------------
-- Fase 3.1 del roadmap. Ver docs/02-MODELO-DATOS.md §D0 (estas tablas se
-- documentaron junto a identidad, pero su construcción se difirió a fase 3).
--
-- `app.location_type` y `app.contact_type` ya existen desde 0001_foundation.sql
-- — se declararon ahí a propósito, junto al resto de ENUMs raíz, aunque las
-- tablas que los usan recién se crean aquí.
-- ============================================================================

create table public.organization_locations (
  id                uuid primary key default gen_random_uuid(),
  organization_id   uuid not null references public.organizations (id) on delete cascade,

  location_type     app.location_type not null default 'OFFICE',
  is_headquarters   boolean not null default false,

  address_line      text not null,
  admin_division_id uuid references public.admin_divisions (id),
  lat               numeric(9, 6),
  lng               numeric(9, 6),

  is_active         boolean not null default true,

  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  created_by        uuid references public.profiles (id) on delete set null,
  updated_by        uuid references public.profiles (id) on delete set null
);

comment on table public.organization_locations is
  'Casa matriz, sucursales, bases operacionales. is_headquarters marca una sola fila por organización (ver índice único parcial).';

-- Como máximo una casa matriz por organización — no lo puede expresar un
-- CHECK de fila, hace falta un índice único parcial.
create unique index organization_locations_one_hq_idx
  on public.organization_locations (organization_id)
  where is_headquarters and is_active;

create index organization_locations_org_idx on public.organization_locations (organization_id) where is_active;

select app.apply_table_conventions('public.organization_locations');


create table public.organization_contacts (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,

  full_name       text not null,
  job_title       text,
  contact_type    app.contact_type not null default 'GENERAL',

  email           extensions.citext,
  phone           text,
  whatsapp        text,
  linkedin_url    text,

  is_public       boolean not null default false,
  is_primary      boolean not null default false,
  is_active       boolean not null default true,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  created_by      uuid references public.profiles (id) on delete set null,
  updated_by      uuid references public.profiles (id) on delete set null,

  constraint organization_contacts_has_channel check (
    email is not null or phone is not null or whatsapp is not null
  )
);

comment on table public.organization_contacts is
  'Directorio de contactos (§6 del brief). is_public controla si aparece en el perfil público, no solo al equipo.';

create index organization_contacts_org_idx on public.organization_contacts (organization_id) where is_active;

select app.apply_table_conventions('public.organization_contacts');


create table public.organization_media (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,

  media_type      text not null,
  storage_path    text not null,
  alt_text        text,
  sort_order      int not null default 0,

  created_at      timestamptz not null default now(),
  created_by      uuid references public.profiles (id) on delete set null,

  constraint organization_media_type check (media_type in ('LOGO', 'BANNER', 'GALLERY', 'VIDEO'))
);

comment on table public.organization_media is
  'Logo, banner, galería, video corporativo. storage_path es relativo al bucket org-media (Supabase Storage) — ver backend/app/core/storage.py.';

-- Un solo logo y un solo banner activos por organización.
create unique index organization_media_one_logo_idx
  on public.organization_media (organization_id)
  where media_type = 'LOGO';
create unique index organization_media_one_banner_idx
  on public.organization_media (organization_id)
  where media_type = 'BANNER';

create index organization_media_org_idx on public.organization_media (organization_id);


create table public.organization_settings (
  organization_id      uuid primary key references public.organizations (id) on delete cascade,

  base_currency_code   char(3) references public.currencies (code) default 'CLP',
  preferred_language   text references public.languages (code) default 'es-CL',
  notify_new_message   boolean not null default true,
  notify_new_requirement boolean not null default true,

  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

comment on table public.organization_settings is
  'Preferencias 1:1 con organizations. Fila creada junto con la organización (ver services/organizations.py).';

select app.apply_table_conventions('public.organization_settings');
