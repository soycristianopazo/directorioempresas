-- ============================================================================
-- 0001 · Extensiones, esquemas y convenciones transversales
-- ----------------------------------------------------------------------------
-- Fase 0.4 del roadmap. Todo lo que el resto de migraciones da por sentado.
-- Ver docs/01-ARQUITECTURA.md §A.5
-- ============================================================================

-- ─── Extensiones ────────────────────────────────────────────────────────────
create extension if not exists "pgcrypto"  with schema extensions;  -- gen_random_uuid
create extension if not exists "ltree"     with schema extensions;  -- jerarquías (fase 2)
create extension if not exists "pg_trgm"   with schema extensions;  -- búsqueda aproximada
create extension if not exists "unaccent"  with schema extensions;  -- FTS en español
create extension if not exists "citext"    with schema extensions;  -- emails case-insensitive

-- ─── Esquemas ───────────────────────────────────────────────────────────────
-- `app` concentra las funciones internas (helpers de RLS, triggers, utilidades).
-- No se expone por PostgREST: nada aquí es invocable desde el cliente.
create schema if not exists app;

revoke all on schema app from public, anon, authenticated;
grant usage on schema app to authenticated, service_role;

comment on schema app is
  'Funciones internas: helpers de RLS, triggers y utilidades. No expuesto vía API.';


-- ============================================================================
-- ENUMs raíz
-- ----------------------------------------------------------------------------
-- Criterio (docs/01-ARQUITECTURA.md §A.5): ENUM solo para conjuntos cerrados
-- del núcleo. Todo lo que el negocio pueda ampliar sin deploy va en catálogo.
-- ============================================================================

-- Visibilidad graduada de recursos (§57, §86 del brief).
create type app.visibility_level as enum (
  'PUBLIC',        -- cualquiera, incluso anónimo. Indexable.
  'REGISTERED',    -- cualquier usuario autenticado
  'BUYERS_ONLY',   -- solo organizaciones con capacidad BUYER
  'INVITED_ONLY',  -- solo con invitación vigente
  'PRIVATE'        -- solo la organización dueña
);

-- Capacidades de sistema de una organización (§4). NO son roles de negocio.
create type app.organization_capability as enum (
  'BUYER',
  'SUPPLIER',
  'PLATFORM_ADMIN'
);

-- Roles declarativos de negocio. No afectan permisos: filtran y presentan.
create type app.organization_business_role as enum (
  'MANDANTE',
  'CONTRATISTA',
  'SUBCONTRATISTA',
  'FABRICANTE',
  'DISTRIBUIDOR',
  'REPRESENTANTE',
  'CONSULTORA',
  'OTEC',
  'SERVICIOS_PROFESIONALES'
);

create type app.organization_status as enum (
  'DRAFT',       -- creada, onboarding sin terminar
  'ACTIVE',
  'SUSPENDED',   -- moderación
  'ARCHIVED'
);

create type app.member_status as enum (
  'INVITED',
  'ACTIVE',
  'SUSPENDED',
  'REMOVED'
);

create type app.role_scope as enum (
  'PLATFORM',
  'ORGANIZATION'
);

create type app.invitation_status as enum (
  'PENDING',
  'ACCEPTED',
  'EXPIRED',
  'REVOKED'
);

create type app.company_size as enum (
  'MICRO',     -- 1-9
  'SMALL',     -- 10-49
  'MEDIUM',    -- 50-199
  'LARGE',     -- 200-999
  'ENTERPRISE' -- 1000+
);

create type app.revenue_band as enum (
  'UNDER_2400_UF',
  'UF_2400_25000',
  'UF_25000_100000',
  'UF_100000_1000000',
  'OVER_1000000_UF',
  'UNDISCLOSED'
);

create type app.contact_type as enum (
  'GENERAL',
  'COMERCIAL',
  'VENTAS',
  'GERENCIA',
  'OPERACIONES',
  'ABASTECIMIENTO',
  'CONTRATOS',
  'FINANZAS',
  'RRHH',
  'HSE',
  'ADMINISTRADOR_CONTRATO',
  'SOPORTE_TECNICO'
);

create type app.location_type as enum (
  'HEADQUARTERS',
  'BRANCH',
  'OPERATIONAL_BASE',
  'WAREHOUSE',
  'PLANT',
  'OFFICE'
);


-- ============================================================================
-- Utilidades de trigger
-- ============================================================================

-- Mantiene updated_at. Se aplica a toda tabla de dominio con escritura.
create or replace function app.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

comment on function app.set_updated_at() is
  'Trigger BEFORE UPDATE: refresca updated_at.';


-- Mantiene updated_by con el usuario de la petición, si lo hay.
--
-- Un job corre sin identidad: en ese caso preserva el valor anterior en vez de
-- ponerlo a NULL, para no borrar el rastro de quién editó por última vez.
--
-- app.current_user_id() se define en la migración 0002. plpgsql resuelve los
-- nombres en tiempo de ejecución, así que referenciarla aquí es válido.
create or replace function app.set_updated_by()
returns trigger
language plpgsql
as $$
declare
  v_user_id uuid := app.current_user_id();
begin
  if v_user_id is not null then
    new.updated_by := v_user_id;
  end if;
  return new;
end;
$$;


-- Impide modificar columnas inmutables (created_at, created_by, y las PK).
create or replace function app.prevent_immutable_change()
returns trigger
language plpgsql
as $$
begin
  if new.created_at is distinct from old.created_at then
    raise exception 'created_at es inmutable (tabla %)', tg_table_name
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;


-- Atajo para aplicar las convenciones estándar a una tabla.
-- Se invoca al final de cada migración que crea tablas de dominio.
create or replace function app.apply_table_conventions(p_table regclass)
returns void
language plpgsql
as $$
declare
  v_name text := p_table::text;
  v_short text := split_part(v_name, '.', 2);
begin
  if v_short = '' then
    v_short := v_name;
  end if;

  execute format(
    'create trigger trg_%s_set_updated_at
       before update on %s
       for each row execute function app.set_updated_at()',
    v_short, v_name
  );

  execute format(
    'create trigger trg_%s_immutable
       before update on %s
       for each row execute function app.prevent_immutable_change()',
    v_short, v_name
  );
end;
$$;

comment on function app.apply_table_conventions(regclass) is
  'Aplica los triggers estándar (updated_at + inmutabilidad de created_at) a una tabla.';


-- ============================================================================
-- Utilidades generales
-- ============================================================================

-- Slug URL-safe a partir de texto libre.
--
-- Usa translate() y NO extensions.unaccent(): unaccent es STABLE (depende del
-- diccionario cargado), así que una función que lo invoque no puede declararse
-- IMMUTABLE con honestidad. Como este slug se usa en índices únicos y columnas
-- generadas, necesita ser realmente inmutable. El translate cubre el set
-- latino-1 que aparece en razones sociales chilenas y latinoamericanas.
create or replace function app.slugify(p_text text)
returns text
language sql
immutable
strict
parallel safe
as $$
  select trim(both '-' from
    regexp_replace(
      lower(translate(
        p_text,
        'áàäâãÁÀÄÂÃéèëêÉÈËÊíìïîÍÌÏÎóòöôõÓÒÖÔÕúùüûÚÙÜÛñÑçÇ',
        'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUnNcC'
      )),
      '[^a-z0-9]+', '-', 'g'
    )
  );
$$;

comment on function app.slugify(text) is
  'Slug URL-safe. IMMUTABLE: apta para índices y columnas generadas.';


-- Validación de RUT chileno (módulo 11). Acepta con o sin puntos/guion.
-- Se usa como CHECK en organization_legal_identifiers.
create or replace function app.is_valid_rut(p_rut text)
returns boolean
language plpgsql
immutable
parallel safe
as $$
declare
  v_clean  text;
  v_body   text;
  v_dv     text;
  v_sum    int := 0;
  v_mult   int := 2;
  v_i      int;
  v_rest   int;
  v_expect text;
begin
  if p_rut is null then
    return false;
  end if;

  v_clean := upper(regexp_replace(p_rut, '[^0-9kK]', '', 'g'));

  if length(v_clean) < 2 or length(v_clean) > 9 then
    return false;
  end if;

  v_body := left(v_clean, length(v_clean) - 1);
  v_dv   := right(v_clean, 1);

  if v_body !~ '^[0-9]+$' then
    return false;
  end if;

  for v_i in reverse length(v_body)..1 loop
    v_sum  := v_sum + (substr(v_body, v_i, 1))::int * v_mult;
    v_mult := case when v_mult = 7 then 2 else v_mult + 1 end;
  end loop;

  v_rest := 11 - (v_sum % 11);
  v_expect := case v_rest
                when 11 then '0'
                when 10 then 'K'
                else v_rest::text
              end;

  return v_dv = v_expect;
end;
$$;

comment on function app.is_valid_rut(text) is
  'Valida un RUT chileno por módulo 11. Acepta formato con o sin puntos y guion.';


-- Normaliza un RUT a formato canónico sin puntos y con guion: 76543210-K
create or replace function app.normalize_rut(p_rut text)
returns text
language sql
immutable
parallel safe
as $$
  select case
    when p_rut is null then null
    when length(c.clean) < 2 then c.clean
    else left(c.clean, length(c.clean) - 1) || '-' || right(c.clean, 1)
  end
  from (select upper(regexp_replace(p_rut, '[^0-9kK]', '', 'g')) as clean) as c;
$$;

comment on function app.normalize_rut(text) is
  'Normaliza un RUT al formato canónico 76543210-K.';


-- ============================================================================
-- Rol de la aplicación
-- ----------------------------------------------------------------------------
-- Se crea aquí, no en el endurecimiento final, porque varias migraciones
-- intermedias le revocan permisos sobre tablas concretas y necesitan que ya
-- exista.
--
-- Los privilegios se otorgan en 0010, cuando todas las tablas están creadas.
-- Aquí solo se declara la identidad:
--
--   nologin    · no se conecta directamente; la aplicación asume este rol
--   noinherit  · no hereda privilegios de los roles a los que pertenezca
--
-- Lo que NO tiene, y es lo importante: BYPASSRLS, y la propiedad de ninguna
-- tabla. Un rol dueño de las tablas omitiría las policies aunque estuvieran
-- activas.
-- ============================================================================

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'app_user') then
    create role app_user nologin noinherit;
  end if;
end $$;
