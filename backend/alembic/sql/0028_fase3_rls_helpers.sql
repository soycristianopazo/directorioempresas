-- ============================================================================
-- 0028 · Helpers de RLS para perfil extendido y catálogo de oferta
-- ----------------------------------------------------------------------------
-- Fase 3.6 del roadmap.
--
-- Las tablas de esta fase son mayormente sub-recursos de una organización o
-- de un offering: en vez de repetir el JOIN a organizations/supplier_offerings
-- y la lógica de visibilidad en cada una de las ~20 tablas nuevas, dos
-- helpers concentran esa lógica una sola vez — mismo criterio que ya usa
-- app.has_permission()/app.can_view_with_visibility() para el resto del
-- sistema.
-- ============================================================================

-- ¿Puede el usuario actual VER esta organización? Combina las cuatro
-- policies de SELECT que ya tiene la propia tabla organizations
-- (organizations_select_member/_public/_registered/_platform_admin, 0008)
-- en una sola expresión reutilizable para las tablas hijas.
create or replace function app.can_view_organization(p_organization_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organizations o
    where o.id = p_organization_id
      and o.deleted_at is null
      and (
        (o.status = 'ACTIVE' and app.can_view_with_visibility(o.id, o.visibility))
        or app.is_member_of(o.id)
        or app.is_platform_admin()
      )
  );
$$;

comment on function app.can_view_organization(uuid) is
  'Visibilidad efectiva de una organización — mismo criterio que las 4 policies de SELECT de organizations, reutilizado por las tablas de perfil/catálogo.';


-- ¿Puede el usuario actual VER este offering? Público si está ACTIVE, su
-- visibility resuelve, y la organización dueña también es visible; o si el
-- usuario tiene offering.read en esa organización (ve sus propios
-- borradores); o si es platform admin.
create or replace function app.can_view_offering(p_offering_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.supplier_offerings so
    where so.id = p_offering_id
      and so.deleted_at is null
      and (
        (
          so.status = 'ACTIVE'
          and app.can_view_with_visibility(so.organization_id, so.visibility)
          and app.can_view_organization(so.organization_id)
        )
        or app.has_permission(so.organization_id, 'offering.read')
        or app.is_platform_admin()
      )
  );
$$;

comment on function app.can_view_offering(uuid) is
  'Visibilidad efectiva de un offering: público si está publicado y la organización es visible; miembro con offering.read ve también sus borradores.';

grant execute on function app.can_view_organization(uuid) to app_user;
grant execute on function app.can_view_offering(uuid) to app_user;
