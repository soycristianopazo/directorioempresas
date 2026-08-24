-- ============================================================================
-- 0021 · Industrias y cobertura territorial a nivel empresa
-- ----------------------------------------------------------------------------
-- Fase 3.2 del roadmap. Conecta el perfil de organización con la taxonomía
-- dual-eje de fase 2 (industries, admin_divisions).
-- ============================================================================

create table public.organization_industries (
  organization_id     uuid not null references public.organizations (id) on delete cascade,
  industry_id         uuid not null references public.industries (id),

  years_experience    smallint,
  is_primary          boolean not null default false,

  created_at          timestamptz not null default now(),

  primary key (organization_id, industry_id),
  constraint organization_industries_years check (years_experience is null or years_experience >= 0)
);

comment on table public.organization_industries is
  'Industrias que atiende la empresa (§D2). years_experience se declara aquí; evidenciarlo con casos de éxito es aparte (case_studies).';

-- Como máximo una industria "principal" por organización — el negocio puede
-- declarar varias industrias pero necesita destacar una para el perfil.
create unique index organization_industries_one_primary_idx
  on public.organization_industries (organization_id)
  where is_primary;


create table public.organization_territories (
  id                  uuid primary key default gen_random_uuid(),
  organization_id     uuid not null references public.organizations (id) on delete cascade,
  admin_division_id   uuid not null references public.admin_divisions (id),

  created_at          timestamptz not null default now(),

  constraint organization_territories_unique unique (organization_id, admin_division_id)
);

comment on table public.organization_territories is
  'Cobertura declarada a nivel empresa, para búsqueda gruesa y perfil. Editable directamente — no se deriva automáticamente de offering_territories en esta fase (queda como mejora futura si diverge demasiado en la práctica).';

create index organization_territories_org_idx on public.organization_territories (organization_id);
