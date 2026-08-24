-- ============================================================================
-- 0016 · Atributos dinámicos (EAV tipado) + vista de herencia
-- ----------------------------------------------------------------------------
-- Fase 2.6 del roadmap. Ver docs/02-MODELO-DATOS.md §D3.
--
-- Un atributo se define una vez (attribute_definitions) y se vincula a uno o
-- más nodos de taxonomía (taxonomy_node_attributes). Si is_inherited=true, se
-- aplica también a todos los nodos descendientes — así "vehicle_year" definido
-- en transporte.personas no hay que repetirlo en cada leaf de esa rama. La
-- vista v_effective_node_attributes resuelve esa herencia vía `path`.
-- ============================================================================

create type app.attribute_data_type as enum (
  'TEXT', 'NUMBER', 'BOOLEAN', 'DATE', 'SELECT', 'MULTISELECT', 'RANGE'
);

create type app.attribute_applies_to as enum (
  'OFFERING', 'REQUIREMENT', 'ORGANIZATION'
);


create table public.attribute_definitions (
  id              uuid primary key default gen_random_uuid(),
  code            text not null unique,
  name            text not null,
  data_type       app.attribute_data_type not null,
  unit_code       text references public.units_of_measure (code),
  min_value       numeric,
  max_value       numeric,
  is_filterable   boolean not null default false,
  is_comparable   boolean not null default false,
  help_text       text,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint attribute_definitions_code_format check (code ~ '^[a-z][a-z0-9_]*$'),
  constraint attribute_definitions_range check (
    min_value is null or max_value is null or min_value <= max_value
  )
);

comment on table public.attribute_definitions is
  'Catálogo de atributos dinámicos tipados. unit_code solo tiene sentido para NUMBER/RANGE.';

select app.apply_table_conventions('public.attribute_definitions');


create table public.attribute_options (
  id                      uuid primary key default gen_random_uuid(),
  attribute_definition_id uuid not null references public.attribute_definitions (id) on delete cascade,
  value                   text not null,
  label                   text not null,
  sort_order              int not null default 0,
  is_active               boolean not null default true,

  constraint attribute_options_unique unique (attribute_definition_id, value)
);

comment on table public.attribute_options is
  'Opciones para atributos SELECT/MULTISELECT.';


create table public.taxonomy_node_attributes (
  id                      uuid primary key default gen_random_uuid(),
  node_id                 uuid not null references public.taxonomy_nodes (id) on delete cascade,
  attribute_definition_id uuid not null references public.attribute_definitions (id) on delete restrict,
  applies_to              app.attribute_applies_to not null,
  is_required             boolean not null default false,
  is_inherited            boolean not null default true,
  filter_weight           smallint not null default 0,
  sort_order              int not null default 0,

  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),

  constraint taxonomy_node_attributes_unique
    unique (node_id, attribute_definition_id, applies_to)
);

comment on table public.taxonomy_node_attributes is
  'Vínculo nodo↔atributo. is_inherited=true lo propaga a los descendientes (ver v_effective_node_attributes).';

create index taxonomy_node_attributes_node_idx on public.taxonomy_node_attributes (node_id);
create index taxonomy_node_attributes_def_idx on public.taxonomy_node_attributes (attribute_definition_id);

select app.apply_table_conventions('public.taxonomy_node_attributes');


-- ============================================================================
-- v_effective_node_attributes — resuelve la herencia por path
-- ----------------------------------------------------------------------------
-- Para un nodo dado, devuelve los atributos definidos en él MÁS los heredados
-- de sus ancestros (cuando is_inherited=true en el ancestro). Si el mismo
-- atributo está definido tanto en el propio nodo como en un ancestro, gana la
-- definición más específica (la más cercana al nodo) — igual que cualquier
-- anulación de configuración normal. Esto es lo que hace posible el
-- checkpoint del roadmap: "un admin agrega un atributo a una categoría y el
-- formulario del proveedor se genera solo" para cualquier nodo descendiente,
-- sin tocar cada leaf uno por uno.
--
-- security_invoker = true: la vista respeta las policies de quien consulta
-- (mismo criterio que v_my_organizations en 0010). Sin esto, correría con los
-- privilegios de postgres y sería un agujero silencioso alrededor de RLS.
-- ============================================================================

create or replace view public.v_effective_node_attributes
with (security_invoker = true)
as
select distinct on (n.id, tna.attribute_definition_id, tna.applies_to)
  n.id                         as node_id,
  tna.attribute_definition_id,
  tna.applies_to,
  tna.is_required,
  tna.filter_weight,
  tna.sort_order,
  (tna.node_id = n.id)         as is_direct,
  ancestor.id                  as defined_on_node_id
from public.taxonomy_nodes n
join public.taxonomy_nodes ancestor
  on ancestor.path @> n.path
join public.taxonomy_node_attributes tna
  on tna.node_id = ancestor.id
 and (ancestor.id = n.id or tna.is_inherited)
where n.is_active and ancestor.is_active
order by n.id, tna.attribute_definition_id, tna.applies_to, nlevel(ancestor.path) desc;

comment on view public.v_effective_node_attributes is
  'Atributos efectivos de un nodo, incluidos los heredados de ancestros. La definición más específica (ancestro más cercano) gana sobre la heredada.';

grant select on public.v_effective_node_attributes to app_user;
