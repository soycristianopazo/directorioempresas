-- ============================================================================
-- 0003 · Organizaciones
-- ----------------------------------------------------------------------------
-- Fase 1.2. La empresa: comprador, proveedor o ambos.
--
-- REGLA (§4 del brief, §E.1 de la arquitectura): una organización NO tiene un
-- "tipo". Tiene capacidades (organization_capabilities) y roles declarativos de
-- negocio (organization_business_roles). Una contratista es comprador Y
-- proveedor a la vez, y eso es lo normal.
-- ============================================================================

create table public.organizations (
  id                uuid primary key default gen_random_uuid(),

  -- Identificación
  legal_name        text not null,
  trade_name        text,
  slug              text not null,
  country_code      char(2) not null default 'CL',

  -- Perfil corporativo
  founded_year      smallint,
  company_size      app.company_size,
  employee_count    integer,
  revenue_band      app.revenue_band not null default 'UNDISCLOSED',
  legal_form        text,

  short_description text,
  description       text,
  value_proposition text,
  website_url       text,
  linkedin_url      text,
  general_email     extensions.citext,
  general_phone     text,

  -- Estado y visibilidad
  status            app.organization_status not null default 'DRAFT',
  visibility        app.visibility_level not null default 'PRIVATE',

  -- Confianza y procedencia (mejora N.6: perfiles pre-cargados + reclamo)
  is_claimed        boolean not null default true,
  data_source       text not null default 'SELF_REGISTERED',
  verified_at       timestamptz,
  verified_by       uuid references public.profiles (id) on delete set null,

  -- Completitud del perfil (0..100). Materializada por el motor de la fase 3.
  completion_pct    smallint not null default 0,

  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  created_by        uuid references public.profiles (id) on delete set null,
  updated_by        uuid references public.profiles (id) on delete set null,
  deleted_at        timestamptz,

  constraint organizations_legal_name_len  check (length(trim(legal_name)) between 2 and 200),
  constraint organizations_slug_format     check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  constraint organizations_slug_len        check (length(slug) between 2 and 100),
  constraint organizations_founded_year    check (founded_year is null
                                                  or founded_year between 1800 and 2100),
  constraint organizations_employee_count  check (employee_count is null or employee_count >= 0),
  constraint organizations_completion_pct  check (completion_pct between 0 and 100),
  constraint organizations_website_url     check (website_url is null
                                                  or website_url ~* '^https?://.+'),
  constraint organizations_data_source     check (data_source in
                                                  ('SELF_REGISTERED', 'IMPORTED', 'SEEDED')),
  -- Un perfil no reclamado no puede estar activo ni ser público:
  -- nadie ha confirmado que los datos sean correctos.
  constraint organizations_unclaimed_not_active check (
    is_claimed or status = 'DRAFT'
  )
);

comment on table public.organizations is
  'La empresa. Sin "tipo": ver organization_capabilities y organization_business_roles.';
comment on column public.organizations.is_claimed is
  'false = perfil pre-cargado desde fuente pública, aún no reclamado por la empresa (mejora N.6).';
comment on column public.organizations.completion_pct is
  'Completitud del perfil 0..100. Materializada; no editable a mano.';

-- Slug único entre organizaciones vivas. Índice parcial: si una se borra
-- (soft delete), su slug vuelve a estar disponible.
create unique index organizations_slug_key
  on public.organizations (slug)
  where deleted_at is null;

create index organizations_status_idx
  on public.organizations (status)
  where deleted_at is null;

create index organizations_visibility_idx
  on public.organizations (visibility)
  where deleted_at is null and status = 'ACTIVE';

create index organizations_country_idx
  on public.organizations (country_code)
  where deleted_at is null;

create index organizations_unclaimed_idx
  on public.organizations (created_at desc)
  where deleted_at is null and is_claimed = false;

-- Búsqueda aproximada por nombre para el autocompletado del backoffice.
-- La búsqueda de proveedores real vive en supplier_search_index (fase 4).
create index organizations_trade_name_trgm_idx
  on public.organizations using gin (trade_name extensions.gin_trgm_ops);
create index organizations_legal_name_trgm_idx
  on public.organizations using gin (legal_name extensions.gin_trgm_ops);

select app.apply_table_conventions('public.organizations');

create trigger trg_organizations_set_updated_by
  before update on public.organizations
  for each row execute function app.set_updated_by();


-- ============================================================================
-- Capacidades de sistema
-- ============================================================================

create table public.organization_capabilities (
  organization_id uuid not null references public.organizations (id) on delete cascade,
  capability      app.organization_capability not null,
  enabled_at      timestamptz not null default now(),
  enabled_by      uuid references public.profiles (id) on delete set null,

  primary key (organization_id, capability)
);

comment on table public.organization_capabilities is
  'Capacidades de sistema: BUYER, SUPPLIER, PLATFORM_ADMIN. Afectan permisos y navegación.';

create index organization_capabilities_capability_idx
  on public.organization_capabilities (capability);


-- ============================================================================
-- Roles declarativos de negocio
-- ============================================================================

create table public.organization_business_roles (
  organization_id uuid not null references public.organizations (id) on delete cascade,
  business_role   app.organization_business_role not null,

  primary key (organization_id, business_role)
);

comment on table public.organization_business_roles is
  'Roles declarativos (mandante, contratista, OTEC…). NO afectan permisos: filtran y presentan.';


-- ============================================================================
-- Identificadores tributarios multi-país
-- ----------------------------------------------------------------------------
-- Mejora N.5 aplicada a la identidad fiscal: no un `tax_id text` único, sino
-- N identificadores tipados por país (RUT en CL, RFC en MX, DUNS global…).
-- ============================================================================

create table public.organization_legal_identifiers (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,

  identifier_type text not null,
  country_code    char(2),
  value           text not null,
  value_normalized text not null,

  is_primary      boolean not null default false,
  verified_at     timestamptz,
  verified_by     uuid references public.profiles (id) on delete set null,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint org_legal_id_type check (
    identifier_type in ('RUT', 'RFC', 'CUIT', 'NIT', 'CNPJ', 'VAT', 'EIN', 'DUNS')
  ),
  -- El RUT chileno se valida por módulo 11 en la propia base.
  -- Validar solo en el frontend garantiza basura en la tabla.
  constraint org_legal_id_rut_valid check (
    identifier_type <> 'RUT' or app.is_valid_rut(value)
  )
);

comment on table public.organization_legal_identifiers is
  'Identificadores tributarios multi-país. El RUT se valida por módulo 11 vía CHECK.';

-- Un mismo identificador no puede pertenecer a dos organizaciones vivas.
create unique index org_legal_identifiers_unique
  on public.organization_legal_identifiers (identifier_type, country_code, value_normalized);

create index org_legal_identifiers_org_idx
  on public.organization_legal_identifiers (organization_id);

-- Una sola identificación primaria por organización.
create unique index org_legal_identifiers_one_primary
  on public.organization_legal_identifiers (organization_id)
  where is_primary;

select app.apply_table_conventions('public.organization_legal_identifiers');


-- Normaliza el valor antes de guardar, para que el índice único funcione
-- con independencia de cómo lo escriba el usuario (76.543.210-K / 765432 10k).
create or replace function app.normalize_legal_identifier()
returns trigger
language plpgsql
as $$
begin
  if new.identifier_type = 'RUT' then
    new.value_normalized := app.normalize_rut(new.value);
    new.value := new.value_normalized;
  else
    new.value_normalized := upper(regexp_replace(new.value, '[^A-Za-z0-9]', '', 'g'));
  end if;
  return new;
end;
$$;

create trigger trg_org_legal_identifiers_normalize
  before insert or update of value, identifier_type
  on public.organization_legal_identifiers
  for each row execute function app.normalize_legal_identifier();


-- ============================================================================
-- FK diferida de profiles.last_org_id
-- ----------------------------------------------------------------------------
-- Se define aquí porque en 0002 la tabla organizations aún no existía.
-- ON DELETE SET NULL: borrar una organización no debe romper el perfil.
-- ============================================================================

alter table public.profiles
  add constraint profiles_last_org_id_fkey
  foreign key (last_org_id) references public.organizations (id) on delete set null;

