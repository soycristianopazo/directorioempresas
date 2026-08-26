-- ============================================================================
-- 0085 · Hashtags por producto/servicio del catálogo
-- ----------------------------------------------------------------------------
-- Mismo patrón que offering_taxonomy_nodes/offering_industries (0022/0029):
-- tabla hija de supplier_offerings, visibilidad/escritura heredadas del
-- offering vía app.can_view_offering / offering.write.
-- ============================================================================

create table public.offering_tags (
  id          uuid primary key default gen_random_uuid(),
  offering_id uuid not null references public.supplier_offerings (id) on delete cascade,
  tag         text not null,
  created_at  timestamptz not null default now(),

  constraint offering_tags_length check (char_length(tag) between 2 and 30)
);

comment on table public.offering_tags is
  'Hashtags libres por producto/servicio — búsqueda/matching fino dentro del catálogo, complementa short_description. Sin categoría/validación contra un catálogo controlado, a diferencia de offering_taxonomy_nodes.';

create unique index offering_tags_unique_per_offering
  on public.offering_tags (offering_id, lower(tag));
create index offering_tags_offering_idx on public.offering_tags (offering_id);

alter table public.offering_tags enable row level security;

create policy offering_tags_select on public.offering_tags
  for select using (app.can_view_offering(offering_id));

create policy offering_tags_write on public.offering_tags
  for all
  using (
    exists (
      select 1 from public.supplier_offerings so
      where so.id = offering_id and app.has_permission(so.organization_id, 'offering.write')
    )
  )
  with check (
    exists (
      select 1 from public.supplier_offerings so
      where so.id = offering_id and app.has_permission(so.organization_id, 'offering.write')
    )
  );

create policy offering_tags_system_context on public.offering_tags
  for all
  using (app.is_system_context())
  with check (app.is_system_context());
