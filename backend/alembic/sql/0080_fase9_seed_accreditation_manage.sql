-- ============================================================================
-- 0080 · accreditation.manage para BUYER_MANAGER / PROCUREMENT_ANALYST (fase 9.2)
-- ----------------------------------------------------------------------------
-- accreditation.manage está sembrado desde 0009_seed_roles_permissions.sql
-- pero sin rol asignado — ORG_OWNER ya lo tenía gratis vía su comodín '*'.
-- Fase 9 lo activa para el perfil que hoy administra vendor tooling propio
-- (vendor_list.manage): significa, de forma unificada, administrar programas
-- propios de acreditación (crear/editar programa, secciones, exigencias,
-- equivalencias) Y revisar/decidir enrollments de esos programas — ver
-- app.is_own_program_reviewer() en 0079.
-- ============================================================================

with mapping (role_code, permission_code) as (
  values
    ('BUYER_MANAGER', 'accreditation.manage'),
    ('PROCUREMENT_ANALYST', 'accreditation.manage')
)
insert into public.role_permissions (role_id, permission_code)
select r.id, p.code
from mapping m
join public.roles r
  on r.code = m.role_code
 and r.organization_id is null
join public.permissions p
  on p.code = m.permission_code
on conflict (role_id, permission_code) do nothing;
