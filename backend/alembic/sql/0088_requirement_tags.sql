-- ============================================================================
-- 0088 · Hashtags libres por necesidad de compra
-- ----------------------------------------------------------------------------
-- Mismo patrón que offering_tags (0085): tabla hija de requirements,
-- visibilidad/escritura heredadas vía requirement.read/requirement.write
-- (igual que requirement_documents/requirement_locations en 0043_fase6_rls),
-- no vía app.can_view_offering porque la demanda nunca es pública.
-- ============================================================================

create table public.requirement_tags (
  id             uuid primary key default gen_random_uuid(),
  requirement_id uuid not null references public.requirements (id) on delete cascade,
  tag            text not null,
  created_at     timestamptz not null default now(),

  constraint requirement_tags_length check (char_length(tag) between 2 and 30)
);

comment on table public.requirement_tags is
  'Hashtags/palabras clave libres de la necesidad — señal de texto libre para el matching, complementa primary_taxonomy_node_id/industry_id (que son estructurados y controlados).';

create unique index requirement_tags_unique_per_requirement
  on public.requirement_tags (requirement_id, lower(tag));
create index requirement_tags_requirement_idx on public.requirement_tags (requirement_id);

alter table public.requirement_tags enable row level security;

create policy requirement_tags_select on public.requirement_tags
  for select using (
    exists (
      select 1 from public.requirements r
      where r.id = requirement_id and app.has_permission(r.organization_id, 'requirement.read')
    )
  );

create policy requirement_tags_write on public.requirement_tags
  for all
  using (
    exists (
      select 1 from public.requirements r
      where r.id = requirement_id and app.has_permission(r.organization_id, 'requirement.write')
    )
  )
  with check (
    exists (
      select 1 from public.requirements r
      where r.id = requirement_id and app.has_permission(r.organization_id, 'requirement.write')
    )
  );

create policy requirement_tags_system_context on public.requirement_tags
  for all
  using (app.is_system_context()) with check (app.is_system_context());
