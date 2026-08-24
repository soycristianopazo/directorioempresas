-- ============================================================================
-- 0007 · Funciones helper de RLS
-- ----------------------------------------------------------------------------
-- Fase 1.4. Ver docs/01-ARQUITECTURA.md §I.2.
--
-- Tres propiedades obligatorias en toda función usada dentro de una policy:
--
--  1. SECURITY DEFINER  → rompe la recursión. Sin esto, una policy sobre
--     organization_members que consulta organization_members entra en bucle.
--
--  2. STABLE            → el planner la evalúa una vez por sentencia en vez de
--     una vez por fila. En tablas grandes la diferencia son dos órdenes de
--     magnitud.
--
--  3. set search_path = ''  → impide el secuestro por schema. Con SECURITY
--     DEFINER, un search_path abierto es una escalada de privilegios.
--
-- Y dentro de las policies: SIEMPRE app.current_user_id(), nunca auth.uid() a
-- secas. El subselect se convierte en InitPlan y se evalúa una sola vez.
-- ============================================================================

-- ─── Identidad ──────────────────────────────────────────────────────────────
--
-- app.current_user_id() NO se redefine aquí. Ya la define la migración 0002
-- (backend/alembic/sql/0002_auth_and_rls.sql), leyendo la variable de sesión
-- con current_setting('app.current_user_id', true).
--
-- Este archivo es un port automático del rls_helpers.sql original de Supabase,
-- que SÍ tenía aquí un wrapper legítimo (`select auth.uid();`, porque en aquel
-- diseño auth.uid() vivía en el schema auth de Supabase). El script de port
-- reemplazó todo `auth.uid()` por `app.current_user_id()` en bloque — y ese
-- reemplazo, aplicado a ESTA definición en particular, convirtió el wrapper
-- en una función que se llama a sí misma:
--
--   select app.current_user_id();   -- dentro del cuerpo de app.current_user_id()
--
-- `create or replace function` no protesta por una función que se referencia
-- a sí misma — es SQL válido — así que esto no falló al aplicar la migración.
-- Falló en producción, en el primer INSERT/SELECT real que la invocara:
-- "StatementTooComplexError: stack depth limit exceeded". Se reprodujo incluso
-- conectado como `postgres` (superusuario, que bypassa RLS por completo), lo
-- que en su momento descartó erróneamente cualquier hipótesis relacionada con
-- RLS/FORCE/pooler — la única pista real era leer pg_get_functiondef() y
-- comparar contra la fuente, que es como se encontró esto.
--
-- Moraleja para el próximo port en bloque de este tipo: un find/replace de
-- `auth.uid()` → `app.current_user_id()` es correcto en CUALQUIER llamada
-- DESDE OTRA función, pero es exactamente incorrecto dentro de la definición
-- del wrapper que reemplaza a auth.uid() en sí — ese caso necesita revisión
-- manual, no reemplazo ciego.


-- ─── Plataforma ─────────────────────────────────────────────────────────────

create or replace function app.is_platform_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.platform_admins pa
    join public.roles r on r.id = pa.role_id
    where pa.user_id = app.current_user_id()
      and pa.revoked_at is null
      and r.code in ('SUPER_ADMIN', 'PLATFORM_ADMIN')
  );
$$;


create or replace function app.has_platform_role(p_role_code text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.platform_admins pa
    join public.roles r on r.id = pa.role_id
    where pa.user_id = app.current_user_id()
      and pa.revoked_at is null
      and (r.code = p_role_code or r.code = 'SUPER_ADMIN')
  );
$$;

comment on function app.has_platform_role(text) is
  'SUPER_ADMIN satisface cualquier rol de plataforma.';


-- ─── Membresía ──────────────────────────────────────────────────────────────

create or replace function app.is_member_of(p_organization_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_members m
    where m.organization_id = p_organization_id
      and m.user_id = app.current_user_id()
      and m.status = 'ACTIVE'
  );
$$;

comment on function app.is_member_of(uuid) is
  'Membresía activa. Es la condición base de casi toda policy del sistema.';


-- Organizaciones del usuario. Para usar como `org_id in (select ...)`
-- cuando hace falta el conjunto completo en vez de una comprobación puntual.
create or replace function app.current_member_orgs()
returns setof uuid
language sql
stable
security definer
set search_path = ''
as $$
  select m.organization_id
  from public.organization_members m
  where m.user_id = app.current_user_id()
    and m.status = 'ACTIVE';
$$;


-- ─── Permisos ───────────────────────────────────────────────────────────────
-- Esta es la función que el código debe usar. Nunca comparar por nombre de rol:
-- `has_permission(org, 'sourcing_event.award')`, no `role = 'BUYER_MANAGER'`.

create or replace function app.has_permission(p_organization_id uuid, p_permission text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select
    -- Los admin de plataforma tienen paso libre; toda lectura sensible
    -- suya queda registrada en audit_logs por la capa de aplicación.
    app.is_platform_admin()
    or exists (
      select 1
      from public.organization_members m
      join public.member_roles mr    on mr.member_id = m.id
      join public.role_permissions rp on rp.role_id = mr.role_id
      where m.organization_id = p_organization_id
        and m.user_id = app.current_user_id()
        and m.status = 'ACTIVE'
        and rp.permission_code = p_permission
    );
$$;

comment on function app.has_permission(uuid, text) is
  'Permiso efectivo del usuario en una organización, vía sus roles.';


-- Todos los permisos efectivos del usuario en una organización.
-- La UI la usa una vez por sesión en vez de N llamadas a has_permission.
create or replace function app.effective_permissions(p_organization_id uuid)
returns setof text
language sql
stable
security definer
set search_path = ''
as $$
  select distinct rp.permission_code
  from public.organization_members m
  join public.member_roles mr     on mr.member_id = m.id
  join public.role_permissions rp on rp.role_id = mr.role_id
  where m.organization_id = p_organization_id
    and m.user_id = app.current_user_id()
    and m.status = 'ACTIVE'
  union
  select p.code
  from public.permissions p
  where app.is_platform_admin();
$$;


-- ─── Capacidades ────────────────────────────────────────────────────────────

create or replace function app.org_has_capability(
  p_organization_id uuid,
  p_capability app.organization_capability
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_capabilities c
    where c.organization_id = p_organization_id
      and c.capability = p_capability
  );
$$;


-- ¿Alguna de las organizaciones del usuario tiene esta capacidad?
-- Base del nivel de visibilidad BUYERS_ONLY.
create or replace function app.viewer_has_capability(
  p_capability app.organization_capability
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_members m
    join public.organization_capabilities c on c.organization_id = m.organization_id
    where m.user_id = app.current_user_id()
      and m.status = 'ACTIVE'
      and c.capability = p_capability
  );
$$;


-- ─── Visibilidad graduada ───────────────────────────────────────────────────
-- Implementa el Patrón C de §I.3: PUBLIC / REGISTERED / BUYERS_ONLY /
-- INVITED_ONLY / PRIVATE.
--
-- INVITED_ONLY devuelve false por ahora: la noción de "invitación vigente"
-- depende de sourcing_event_invitations, que se crea en la fase 7. Se
-- completará entonces. Devolver false es el fallo seguro.

create or replace function app.can_view_with_visibility(
  p_organization_id uuid,
  p_visibility app.visibility_level
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select case p_visibility
    when 'PUBLIC'       then true
    when 'REGISTERED'   then app.current_user_id() is not null
    when 'BUYERS_ONLY'  then app.viewer_has_capability('BUYER')
    when 'INVITED_ONLY' then false
    when 'PRIVATE'      then false
    else false
  end
  or app.is_member_of(p_organization_id)
  or app.is_platform_admin();
$$;

comment on function app.can_view_with_visibility(uuid, app.visibility_level) is
  'Visibilidad graduada (§57, §86). El miembro y el admin de plataforma siempre ven.';


-- ─── Permisos de ejecución ──────────────────────────────────────────────────
-- El rol de la aplicación necesita ejecutarlas porque las policies las
-- invocan en su nombre. Nadie más las necesita.

grant execute on function
  app.current_user_id(),
  app.is_platform_admin(),
  app.has_platform_role(text),
  app.is_member_of(uuid),
  app.current_member_orgs(),
  app.has_permission(uuid, text),
  app.effective_permissions(uuid),
  app.org_has_capability(uuid, app.organization_capability),
  app.viewer_has_capability(app.organization_capability),
  app.can_view_with_visibility(uuid, app.visibility_level)
to app_user;
