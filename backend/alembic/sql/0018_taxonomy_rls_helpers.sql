-- ============================================================================
-- 0018 · Helper de RLS: permisos de plataforma sin organización
-- ----------------------------------------------------------------------------
-- Fase 2.8 del roadmap.
--
-- app.has_permission(org, perm) de 0007 resuelve permisos DENTRO de una
-- organización. Las tablas de esta fase (referencia, taxonomía, atributos)
-- son de plataforma, sin organización de por medio, así que necesitan su
-- propio equivalente: app.has_platform_permission(perm), simétrico en forma
-- a has_permission pero resolviendo contra platform_admins + role_permissions
-- directamente.
--
-- Hoy solo PLATFORM_ADMIN y SUPER_ADMIN tienen 'platform.manage_taxonomy'
-- (sembrado en 0009). Si mañana se necesita un rol de plataforma más
-- granular (ej. TAXONOMY_EDITOR), este helper y las policies que lo usan no
-- necesitan tocarse — solo el seed de role_permissions.
-- ============================================================================

create or replace function app.has_platform_permission(p_permission text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select
    app.has_platform_role('SUPER_ADMIN')
    or exists (
      select 1
      from public.platform_admins pa
      join public.role_permissions rp on rp.role_id = pa.role_id
      where pa.user_id = app.current_user_id()
        and pa.revoked_at is null
        and rp.permission_code = p_permission
    );
$$;

comment on function app.has_platform_permission(text) is
  'Permiso efectivo de plataforma (sin organización), vía platform_admins. SUPER_ADMIN siempre pasa.';

grant execute on function app.has_platform_permission(text) to app_user;
