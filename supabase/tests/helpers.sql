-- ============================================================================
-- Helpers para las pruebas pgTAP
-- ----------------------------------------------------------------------------
-- Se cargan con \i desde cada archivo .test.sql.
--
-- La clave de probar RLS es suplantar identidades correctamente: hay que
-- cambiar de rol (authenticated / anon) Y de claims JWT. Cambiar solo el rol
-- deja auth.uid() en null y las pruebas pasan por el motivo equivocado.
-- ============================================================================

create schema if not exists tests;


-- Crea un usuario en auth.users (el trigger crea el profile).
create or replace function tests.create_user(p_email text, p_id uuid default gen_random_uuid())
returns uuid
language plpgsql
as $$
begin
  insert into auth.users (
    id, instance_id, aud, role, email,
    encrypted_password, email_confirmed_at,
    raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at
  )
  values (
    p_id, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', p_email,
    extensions.crypt('password123', extensions.gen_salt('bf')), now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    jsonb_build_object('first_name', split_part(p_email, '@', 1)),
    now(), now()
  );

  return p_id;
end;
$$;


-- Actúa como un usuario autenticado concreto.
create or replace function tests.authenticate_as(p_user_id uuid)
returns void
language plpgsql
as $$
declare
  v_email text;
begin
  select email into v_email from auth.users where id = p_user_id;

  perform set_config('role', 'authenticated', true);
  perform set_config(
    'request.jwt.claims',
    json_build_object(
      'sub', p_user_id::text,
      'email', v_email,
      'role', 'authenticated',
      'aal', 'aal1'
    )::text,
    true
  );
end;
$$;


-- Actúa como visitante anónimo.
create or replace function tests.authenticate_as_anon()
returns void
language plpgsql
as $$
begin
  perform set_config('role', 'anon', true);
  perform set_config('request.jwt.claims', json_build_object('role', 'anon')::text, true);
end;
$$;


-- Vuelve al rol privilegiado para preparar datos.
create or replace function tests.clear_authentication()
returns void
language plpgsql
as $$
begin
  perform set_config('role', 'postgres', true);
  perform set_config('request.jwt.claims', null, true);
end;
$$;


-- Cuenta filas visibles de una tabla bajo la identidad actual.
-- Es la primitiva de casi toda aserción de RLS: "¿cuántas filas ve X?".
create or replace function tests.count_visible(p_table text, p_where text default 'true')
returns bigint
language plpgsql
as $$
declare
  v_count bigint;
begin
  execute format('select count(*) from %s where %s', p_table, p_where) into v_count;
  return v_count;
end;
$$;
