-- ============================================================================
-- 0084 · Giros SII registrados por la organización
-- ----------------------------------------------------------------------------
-- Mismo patrón que organization_industries (0021/0029): tabla puente
-- organización↔catálogo público, visibilidad heredada de
-- app.can_view_organization, escritura con organization.update.
-- ============================================================================

create table public.organization_economic_activities (
  organization_id uuid not null references public.organizations (id) on delete cascade,
  sii_code        text not null references public.sii_economic_activities (code),
  is_primary      boolean not null default false,
  created_at      timestamptz not null default now(),

  primary key (organization_id, sii_code)
);

comment on table public.organization_economic_activities is
  'Giros SII que la organización declara tener registrados con el SII — a nivel de organización (el SII registra por RUT, no por producto). Ver organization_industries para el mismo patrón aplicado a industrias.';

create index organization_economic_activities_org_idx
  on public.organization_economic_activities (organization_id);

alter table public.organization_economic_activities enable row level security;

create policy organization_economic_activities_select
  on public.organization_economic_activities
  for select using (app.can_view_organization(organization_id));

create policy organization_economic_activities_write
  on public.organization_economic_activities
  for all
  using (app.has_permission(organization_id, 'organization.update'))
  with check (app.has_permission(organization_id, 'organization.update'));

create policy organization_economic_activities_system_context
  on public.organization_economic_activities
  for all
  using (app.is_system_context())
  with check (app.is_system_context());
