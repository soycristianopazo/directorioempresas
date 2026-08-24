-- ============================================================================
-- 0022 · Catálogo de oferta comercial — supplier_offerings (el núcleo)
-- ----------------------------------------------------------------------------
-- Fase 3.3 del roadmap. Ver docs/02-MODELO-DATOS.md §D4.
--
-- La unidad atómica de venta. Se clasifica contra AMBOS ejes de fase 2
-- (taxonomy_nodes: qué es; industries: para quién) y contra el territorio
-- (admin_divisions) donde se presta — no reutiliza organization_territories
-- directamente porque la cobertura puede variar offering por offering (un
-- transportista puede arrendar buses en todo Chile pero solo operar
-- mantención en la Región Metropolitana).
-- ============================================================================

create type app.offering_type as enum (
  'PRODUCT', 'SERVICE', 'RENTAL', 'SOFTWARE', 'TRAINING', 'CONSULTING'
);

create type app.offering_status as enum ('DRAFT', 'ACTIVE', 'PAUSED', 'ARCHIVED');

create type app.offering_availability_status as enum (
  'AVAILABLE', 'LIMITED', 'ON_REQUEST', 'UNAVAILABLE'
);

create type app.offering_coverage_type as enum ('OPERATIONAL', 'COMMERCIAL', 'MOBILIZABLE');

create type app.offering_price_type as enum ('FIXED', 'FROM', 'RANGE', 'ON_REQUEST');


create table public.supplier_offerings (
  id                  uuid primary key default gen_random_uuid(),
  organization_id     uuid not null references public.organizations (id) on delete cascade,

  offering_type       app.offering_type not null,
  name                text not null,
  slug                text not null,

  short_description   text,
  full_description    text,
  specifications       text,
  applications        text,
  brand               text,
  model                text,

  lead_time_days      int,
  moq                 int,
  monthly_capacity    numeric,
  capacity_unit_code  text references public.units_of_measure (code),
  warranty_months     int,
  has_after_sales     boolean not null default false,

  availability_status app.offering_availability_status not null default 'AVAILABLE',
  visibility           app.visibility_level not null default 'PUBLIC',
  status               app.offering_status not null default 'DRAFT',
  published_at         timestamptz,

  created_at           timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  created_by            uuid references public.profiles (id) on delete set null,
  updated_by            uuid references public.profiles (id) on delete set null,
  deleted_at             timestamptz,

  constraint supplier_offerings_unique_slug unique (organization_id, slug),
  constraint supplier_offerings_lead_time check (lead_time_days is null or lead_time_days >= 0),
  constraint supplier_offerings_moq check (moq is null or moq > 0),
  constraint supplier_offerings_warranty check (warranty_months is null or warranty_months >= 0)
);

comment on table public.supplier_offerings is
  'La unidad atómica de venta: un producto/servicio/arriendo/software/capacitación/consultoría. status DRAFT no aparece en ningún listado público, aunque visibility sea PUBLIC.';

create index supplier_offerings_org_idx on public.supplier_offerings (organization_id) where deleted_at is null;
create index supplier_offerings_status_idx on public.supplier_offerings (status) where deleted_at is null;

select app.apply_table_conventions('public.supplier_offerings');


create table public.offering_taxonomy_nodes (
  offering_id  uuid not null references public.supplier_offerings (id) on delete cascade,
  node_id      uuid not null references public.taxonomy_nodes (id),
  is_primary   boolean not null default false,

  primary key (offering_id, node_id)
);

comment on table public.offering_taxonomy_nodes is
  'Un offering puede colgar de N nodos de taxonomía; uno es is_primary.';

create unique index offering_taxonomy_nodes_one_primary_idx
  on public.offering_taxonomy_nodes (offering_id)
  where is_primary;

create index offering_taxonomy_nodes_node_idx on public.offering_taxonomy_nodes (node_id);


create table public.offering_industries (
  offering_id  uuid not null references public.supplier_offerings (id) on delete cascade,
  industry_id  uuid not null references public.industries (id),

  primary key (offering_id, industry_id)
);

comment on table public.offering_industries is
  'Industrias objetivo del offering — no necesariamente las mismas que organization_industries.';

create index offering_industries_industry_idx on public.offering_industries (industry_id);


create table public.offering_territories (
  id                 uuid primary key default gen_random_uuid(),
  offering_id        uuid not null references public.supplier_offerings (id) on delete cascade,
  admin_division_id  uuid not null references public.admin_divisions (id),

  coverage_type      app.offering_coverage_type not null default 'OPERATIONAL',
  mobilization_days  int,
  has_local_base     boolean not null default false,

  constraint offering_territories_unique unique (offering_id, admin_division_id),
  constraint offering_territories_mobilization check (mobilization_days is null or mobilization_days >= 0)
);

comment on table public.offering_territories is
  'Dónde se presta ESE offering en particular. coverage_type distingue base operativa de simple alcance comercial.';

create index offering_territories_offering_idx on public.offering_territories (offering_id);


create table public.offering_pricing (
  id             uuid primary key default gen_random_uuid(),
  offering_id    uuid not null references public.supplier_offerings (id) on delete cascade,

  price_type     app.offering_price_type not null default 'ON_REQUEST',
  amount_min     numeric(18, 4),
  amount_max     numeric(18, 4),
  currency_code  char(3) references public.currencies (code),
  unit_code      text references public.units_of_measure (code),
  valid_until    date,
  is_public      boolean not null default false,

  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),

  constraint offering_pricing_amounts check (
    amount_min is null or amount_max is null or amount_min <= amount_max
  ),
  constraint offering_pricing_fixed_needs_amount check (
    price_type not in ('FIXED', 'FROM') or amount_min is not null
  ),
  constraint offering_pricing_range_needs_amounts check (
    price_type <> 'RANGE' or (amount_min is not null and amount_max is not null)
  )
);

comment on table public.offering_pricing is
  'Precio referencial opcional. is_public controla si se muestra en el perfil público o solo a compradores autenticados.';

create index offering_pricing_offering_idx on public.offering_pricing (offering_id);

select app.apply_table_conventions('public.offering_pricing');
