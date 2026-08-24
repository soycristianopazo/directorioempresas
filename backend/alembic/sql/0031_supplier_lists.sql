-- ============================================================================
-- 0031 · Listas de proveedores guardadas (favoritos)
-- ----------------------------------------------------------------------------
-- Fase 4.9 del roadmap. Ver docs/02-MODELO-DATOS.md §117-118.
--
-- Herramienta de comprador: guardar organizaciones proveedoras en listas
-- curadas ("Transportistas Antofagasta", "Proveedores críticos"). El ítem
-- referencia una organización completa, no una oferta puntual — coherente
-- con que el comparador (fase 4.8) también compara organizaciones.
-- ============================================================================

create table public.supplier_lists (
  id                   uuid primary key default gen_random_uuid(),
  organization_id      uuid not null references public.organizations (id) on delete cascade,

  name                 text not null,
  is_shared_with_org   boolean not null default true,

  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  created_by           uuid references public.profiles (id) on delete set null
);

comment on table public.supplier_lists is
  'Listas de proveedores guardadas por una organización compradora. is_shared_with_org=true (default): visible para todo el equipo, no solo quien la creó.';

select app.apply_table_conventions('public.supplier_lists');

create index supplier_lists_organization_idx
  on public.supplier_lists (organization_id);


create table public.supplier_list_items (
  id                       uuid primary key default gen_random_uuid(),
  list_id                  uuid not null references public.supplier_lists (id) on delete cascade,
  target_organization_id   uuid not null references public.organizations (id) on delete cascade,

  note                     text,
  sort_order               integer not null default 0,

  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  created_by               uuid references public.profiles (id) on delete set null,

  constraint supplier_list_items_unique unique (list_id, target_organization_id)
);

comment on table public.supplier_list_items is
  'Organizaciones guardadas dentro de una lista. unique(list_id, target_organization_id): guardar dos veces la misma organización actualiza, no duplica.';

select app.apply_table_conventions('public.supplier_list_items');

create index supplier_list_items_list_idx
  on public.supplier_list_items (list_id, sort_order);
