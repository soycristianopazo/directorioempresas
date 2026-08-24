-- ============================================================================
-- 0010 · Endurecimiento: rol de aplicación, permisos y FORCE RLS
-- ----------------------------------------------------------------------------
-- ÚLTIMA migración a propósito: recorre todas las tablas del esquema, así que
-- solo tiene sentido cuando ya existen todas.
-- ============================================================================

-- ============================================================================
-- Rol de aplicación
-- ----------------------------------------------------------------------------
-- El backend NO se conecta como `postgres`. Se conecta como `app_user`, que:
--   · no es dueño de ninguna tabla  → está sujeto a RLS
--   · no tiene BYPASSRLS
--   · no puede hacer DDL            → una inyección no altera el esquema
--
-- Las migraciones sí corren como `postgres` (Alembic, conexión aparte en
-- modo sesión por el puerto 5432).
-- ============================================================================

-- El rol app_user se crea en la migración 0001: hay tablas que ya le
-- revocan permisos antes de llegar aquí.

grant usage on schema public to app_user;
grant usage on schema app to app_user;

grant select, insert, update, delete on all tables in schema public to app_user;
grant usage, select on all sequences in schema public to app_user;
grant execute on all functions in schema app to app_user;
grant execute on all functions in schema public to app_user;

-- Que las tablas futuras hereden los mismos permisos sin acordarse de darlos.
alter default privileges in schema public
  grant select, insert, update, delete on tables to app_user;
alter default privileges in schema public
  grant usage, select on sequences to app_user;
alter default privileges in schema app
  grant execute on functions to app_user;

-- Excepciones: tablas que la aplicación nunca debe modificar.
revoke insert, update, delete on public.audit_logs from app_user;
revoke all on public.permissions from app_user;
grant select on public.permissions to app_user;


-- ============================================================================
-- FORCE ROW LEVEL SECURITY
-- ----------------------------------------------------------------------------
-- Sin esto, cualquier conexión con el rol dueño omite las policies. Es la
-- línea que separa "RLS configurado" de "RLS aplicado".
-- ============================================================================

do $$
declare
  r record;
begin
  for r in
    select c.relname
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind in ('r', 'p')
      and not c.relispartition
  loop
    execute format('alter table public.%I enable row level security', r.relname);
    execute format('alter table public.%I force row level security', r.relname);
  end loop;
end $$;




-- ============================================================================
-- Bypass de sistema
-- ----------------------------------------------------------------------------
-- Los jobs y el registro de usuarios necesitan operar sin identidad. En vez de
-- conectarse como `postgres` —que saltaría RLS siempre y en silencio— cada
-- tabla recibe una policy permisiva que solo se cumple cuando la transacción
-- declaró explícitamente `app.system_context = on`.
--
-- Postgres combina policies permisivas con OR, así que esto no debilita las
-- demás: añade una vía adicional que la aplicación tiene que pedir a
-- propósito, y que se ve con un grep de `session_for_system`.
-- ============================================================================

do $$
declare
  r record;
begin
  for r in
    select c.relname
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind in ('r', 'p')
      and not c.relispartition
      -- audit_logs queda fuera: es inmutable incluso para el contexto de
      -- sistema. La escritura pasa por app.write_audit(), que es
      -- SECURITY DEFINER y por tanto no está sujeta a estas policies.
      and c.relname <> 'audit_logs'
      and not exists (
        select 1 from pg_policies p
        where p.schemaname = 'public'
          and p.tablename = c.relname
          and p.policyname = c.relname || '_system_context'
      )
  loop
    execute format(
      'create policy %I on public.%I for all using (app.is_system_context()) '
      'with check (app.is_system_context())',
      r.relname || '_system_context', r.relname
    );
  end loop;
end $$;


-- ============================================================================
-- Vista de organizaciones del usuario
-- ----------------------------------------------------------------------------
-- security_invoker = true: la vista respeta las policies de quien consulta.
-- Sin esa opción correría con los privilegios de su dueño y sería un agujero
-- silencioso que rodea todas las policies de las tablas subyacentes.
-- ============================================================================

create or replace view public.v_my_organizations
with (security_invoker = true)
as
select
  o.id,
  o.legal_name,
  o.trade_name,
  o.slug,
  o.status,
  o.visibility,
  o.completion_pct,
  m.id                as member_id,
  m.status            as member_status,
  m.joined_at,
  coalesce(
    array_agg(distinct r.code) filter (where r.code is not null),
    array[]::text[]
  )                   as role_codes,
  coalesce(
    array_agg(distinct c.capability::text) filter (where c.capability is not null),
    array[]::text[]
  )                   as capabilities
from public.organizations o
join public.organization_members m
  on m.organization_id = o.id
 and m.user_id = app.current_user_id()
 and m.status = 'ACTIVE'
left join public.member_roles mr on mr.member_id = m.id
left join public.roles r         on r.id = mr.role_id
left join public.organization_capabilities c on c.organization_id = o.id
where o.deleted_at is null
group by o.id, m.id;

grant select on public.v_my_organizations to app_user;
