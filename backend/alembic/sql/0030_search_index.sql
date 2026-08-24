-- ============================================================================
-- 0030 · Read model de búsqueda — supplier_search_index
-- ----------------------------------------------------------------------------
-- Fase 4.1 del roadmap. Ver docs/02-MODELO-DATOS.md §203/§656 y el plan de
-- fase 4 (docs/04-ROADMAP.md).
--
-- Una fila por oferta, desnormalizada a propósito: consultar en vivo el
-- modelo normalizado con los JOINs a taxonomía/industrias/territorio/
-- atributos no escala para búsqueda facetada en OLTP.
--
-- Se refresca desde Python (services/search.py::reindex_offering), NO por
-- trigger — mismo criterio ya usado en el resto del proyecto para desviarse
-- del diseño original RPC-heavy (ver docs/DATABASE.md, "Capa de aplicación").
--
-- `is_public` va precalculado: refleja exactamente lo que
-- app.can_view_with_visibility() resuelve como visible para un visitante SIN
-- sesión (offering.status=ACTIVE, offering.visibility=PUBLIC,
-- organización.status=ACTIVE, organización.visibility=PUBLIC). La búsqueda
-- pública (/discover, anónima) filtra por esta columna directamente — no
-- indexa todavía visibilidad graduada (REGISTERED/BUYERS_ONLY) según quién
-- busca; ver la nota de alcance en el plan de fase 4.
--
-- Sin columnas de scoring/acreditación: is_accredited y supplier_score son
-- conceptos de fase 5 y fase 6 respectivamente, que todavía no existen. El
-- orden por defecto usa ts_rank + completion_pct (proxy de calidad honesto
-- con lo que hoy se puede medir), no columnas placeholder sin sentido.
-- ============================================================================

create table public.supplier_search_index (
  offering_id         uuid primary key references public.supplier_offerings (id) on delete cascade,
  organization_id     uuid not null references public.organizations (id) on delete cascade,

  search_vector       tsvector not null,

  taxonomy_node_ids   uuid[] not null default '{}',
  industry_ids        uuid[] not null default '{}',
  admin_division_ids  uuid[] not null default '{}',

  -- Proyección derivada de offering_attribute_values (solo atributos
  -- is_filterable=true), para filtrado facetado en una sola pasada. La
  -- verdad son las filas tipadas de offering_attribute_values; esto es una
  -- copia de lectura, reconciliada por backend/scripts/reindex_search.py.
  attributes          jsonb not null default '{}'::jsonb,

  offering_type       text not null,
  availability_status text not null,
  price_type          text,

  is_public           boolean not null default false,
  completion_pct      smallint not null default 0,

  updated_at          timestamptz not null default now()
);

comment on table public.supplier_search_index is
  'Read model desnormalizado de búsqueda, 1 fila por oferta. Refrescado por services/search.py::reindex_offering(), no por trigger. Ver docs/02-MODELO-DATOS.md §203.';

comment on column public.supplier_search_index.is_public is
  'Precalculado = visible para un visitante anónimo (offering+org ACTIVE y visibility=PUBLIC). No cubre visibilidad graduada (REGISTERED/BUYERS_ONLY) — fuera de alcance de esta pasada.';

create index supplier_search_index_vector_idx
  on public.supplier_search_index using gin (search_vector);

create index supplier_search_index_taxonomy_idx
  on public.supplier_search_index using gin (taxonomy_node_ids);

create index supplier_search_index_industry_idx
  on public.supplier_search_index using gin (industry_ids);

create index supplier_search_index_division_idx
  on public.supplier_search_index using gin (admin_division_ids);

create index supplier_search_index_attributes_idx
  on public.supplier_search_index using gin (attributes jsonb_path_ops);

create index supplier_search_index_public_idx
  on public.supplier_search_index (is_public, updated_at desc);
