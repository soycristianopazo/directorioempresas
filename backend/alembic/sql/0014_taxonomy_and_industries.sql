-- ============================================================================
-- 0014 · Taxonomía de oferta e industrias (diseño dual-eje)
-- ----------------------------------------------------------------------------
-- Fase 2.3 y 2.4 del roadmap. Ver docs/01-ARQUITECTURA.md §D.2 y
-- docs/02-MODELO-DATOS.md §D2.
--
-- DISEÑO DUAL-EJE — por qué taxonomy_nodes e industries son dos árboles
-- independientes y no uno anidado dentro del otro:
--
--   taxonomy_nodes = QUÉ se vende (Transporte → Personas → A faena → Bus)
--   industries     = A QUIÉN se le vende (Minería → Cobre → Plantas concentradoras)
--
-- Un solo árbol con la industria como raíz («Minería → Transporte → …») obliga
-- a duplicar cada rama de oferta bajo cada industria que la consume: el mismo
-- bus aparecería bajo Minería→Transporte, Construcción→Transporte,
-- Retail→Transporte… El proveedor se clasificaría N veces y el matching
-- fragmenta la oferta en vez de consolidarla. Con dos ejes ortogonales, la
-- rama de transporte existe una sola vez y la experiencia por industria se
-- declara aparte (organization_industries, fase 3) — permitiendo la señal de
-- matching que un solo árbol no puede expresar: "vende exactamente esto Y
-- tiene experiencia comprobada en esta industria".
-- ============================================================================

create type app.taxonomy_node_type as enum (
  'CATEGORY',
  'SUBCATEGORY',
  'SPECIALTY',
  'SERVICE',
  'PRODUCT'
);

-- Propuesta razonable, no viene de un documento fuente confirmado en el
-- repo. Ampliable sin downtime vía ALTER TYPE ... ADD VALUE si hace falta
-- otro nivel — pero achicar o renombrar valores ya sembrados sí es costoso,
-- así que si el negocio tiene una escala de riesgo distinta, ajustar ANTES
-- de que accreditation_programs.applies_to_risk_level (fase 5) dependa de
-- este ENUM.
create type app.risk_level as enum ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');


-- ============================================================================
-- Eje 1: taxonomy_nodes — qué se vende
-- ============================================================================

create table public.taxonomy_nodes (
  id            uuid primary key default gen_random_uuid(),
  parent_id     uuid references public.taxonomy_nodes (id) on delete restrict,

  slug          text not null,
  level         smallint not null,
  node_type     app.taxonomy_node_type not null,
  path          ltree not null,

  -- Se mantiene por trigger (app.mark_parent_not_leaf, más abajo), no se
  -- setea a mano: refleja si el nodo tiene hijos, no una intención editorial.
  is_leaf       boolean not null default true,
  is_active     boolean not null default true,
  risk_level    app.risk_level,
  sort_order    int not null default 0,

  -- Nombre canónico en español, además de taxonomy_node_translations: evita
  -- un JOIN obligatorio para cualquier listado simple del árbol.
  name          text not null,
  description   text,

  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  constraint taxonomy_nodes_unique_slug unique (parent_id, slug)
);

comment on table public.taxonomy_nodes is
  'Árbol de QUÉ se vende. Ver el comentario de cabecera del archivo sobre el diseño dual-eje. Nunca se borra: solo is_active=false (gobernanza §D.5).';

create index taxonomy_nodes_path_gist_idx on public.taxonomy_nodes using gist (path);
create index taxonomy_nodes_parent_active_idx
  on public.taxonomy_nodes (parent_id) where is_active;

create unique index taxonomy_nodes_root_slug_idx
  on public.taxonomy_nodes (slug)
  where parent_id is null;

select app.apply_table_conventions('public.taxonomy_nodes');

create trigger trg_taxonomy_nodes_path
  before insert or update of parent_id, slug on public.taxonomy_nodes
  for each row execute function app.maintain_hierarchy_path();


-- Pone is_leaf=false en el padre cuando se inserta un hijo. No hace falta la
-- operación inversa (restaurar is_leaf=true si se "eliminara" el único hijo):
-- los nodos nunca se borran de verdad, solo is_active=false, así que un padre
-- que alguna vez tuvo un hijo se queda is_leaf=false para siempre — que es
-- correcto: la clasificación histórica de cualquier oferta que apuntara a ese
-- hijo debe seguir siendo válida.
create or replace function app.mark_parent_not_leaf()
returns trigger
language plpgsql
as $$
begin
  if new.parent_id is not null then
    update public.taxonomy_nodes
       set is_leaf = false
     where id = new.parent_id
       and is_leaf = true;
  end if;
  return new;
end;
$$;

create trigger trg_taxonomy_nodes_mark_parent
  after insert on public.taxonomy_nodes
  for each row execute function app.mark_parent_not_leaf();


create table public.taxonomy_node_translations (
  node_id       uuid not null references public.taxonomy_nodes (id) on delete cascade,
  language_code text not null references public.languages (code),
  name          text not null,
  description   text,

  primary key (node_id, language_code)
);

comment on table public.taxonomy_node_translations is
  'i18n de taxonomy_nodes. name/description en taxonomy_nodes son el canónico es-CL.';


create table public.taxonomy_node_synonyms (
  id            uuid primary key default gen_random_uuid(),
  node_id       uuid not null references public.taxonomy_nodes (id) on delete cascade,
  synonym       text not null,
  language_code text not null references public.languages (code) default 'es-CL',
  created_at    timestamptz not null default now()
);

comment on table public.taxonomy_node_synonyms is
  'Sinónimos y jerga de negocio ("camión pluma"↔"camión grúa"). Alimenta el FTS de fase 4 — no se construye el FTS todavía, solo se deja la tabla lista.';

-- gin_trgm_ops (pg_trgm, ya habilitada en 0001): búsqueda aproximada de
-- sinónimos cuando fase 4 construya el FTS.
create index taxonomy_node_synonyms_trgm_idx
  on public.taxonomy_node_synonyms using gin (synonym gin_trgm_ops);


create table public.taxonomy_external_mappings (
  id             uuid primary key default gen_random_uuid(),
  node_id        uuid not null references public.taxonomy_nodes (id) on delete cascade,
  standard       text not null,
  external_code  text not null,
  external_label text,
  created_at     timestamptz not null default now(),

  constraint taxonomy_external_mappings_standard check (standard in ('UNSPSC', 'CPC', 'NACE')),
  constraint taxonomy_external_mappings_unique unique (node_id, standard, external_code)
);

comment on table public.taxonomy_external_mappings is
  'Interoperabilidad con estándares externos (UNSPSC/CPC/NACE) para ERPs de clientes enterprise.';


-- ============================================================================
-- Eje 2: industries — a quién se le vende
-- ----------------------------------------------------------------------------
-- Árbol independiente y ortogonal a taxonomy_nodes. NO anidado dentro de él.
-- ============================================================================

create table public.industries (
  id          uuid primary key default gen_random_uuid(),
  parent_id   uuid references public.industries (id) on delete restrict,

  slug        text not null,
  level       smallint not null,
  path        ltree not null,
  is_active   boolean not null default true,
  sort_order  int not null default 0,
  name        text not null,

  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),

  constraint industries_unique_slug unique (parent_id, slug)
);

comment on table public.industries is
  'Árbol de A QUIÉN se le vende. Independiente de taxonomy_nodes — ver el comentario de cabecera del archivo.';

create index industries_path_gist_idx on public.industries using gist (path);

create unique index industries_root_slug_idx
  on public.industries (slug)
  where parent_id is null;

select app.apply_table_conventions('public.industries');

create trigger trg_industries_path
  before insert or update of parent_id, slug on public.industries
  for each row execute function app.maintain_hierarchy_path();


create table public.industry_translations (
  industry_id   uuid not null references public.industries (id) on delete cascade,
  language_code text not null references public.languages (code),
  name          text not null,
  description   text,

  primary key (industry_id, language_code)
);

comment on table public.industry_translations is
  'i18n de industries. name en industries es el canónico es-CL.';
