-- ============================================================================
-- Helpers para las pruebas pgTAP
-- ----------------------------------------------------------------------------
-- Se cargan con \i desde cada archivo .test.sql.
--
-- La clave de probar RLS es suplantar identidades correctamente: hay que
-- cambiar de rol (authenticated / anon) Y de claims JWT. Cambiar solo el rol
-- deja auth.uid() en null y las pruebas pasan por el motivo equivocado.
--
-- DOS SUTILEZAS QUE CUESTAN UNA TARDE SI NO SE SABEN
-- ---------------------------------------------------------------------------
-- 1. `authenticate_as` NO puede ser SECURITY DEFINER. PostgreSQL guarda y
--    restaura el rol al salir de una función SECURITY DEFINER, así que el
--    `set role` se desharía justo al retornar. Por eso la lectura de
--    auth.users (que `authenticated` no puede hacer) se delega a
--    `tests.get_email`, que sí es SECURITY DEFINER.
--
-- 2. Una vez que la sesión pasa a rol `authenticated`, deja de tener USAGE
--    sobre el schema `tests`. Sin los GRANT del final, la segunda llamada a
--    un helper falla con "permission denied for schema tests".
-- ============================================================================

create schema if not exists tests;
grant usage on schema tests to anon, authenticated, service_role;


-- Crea un usuario en auth.users (el trigger crea el profile).
create or replace function tests.create_user(p_email text, p_id uuid default gen_random_uuid())
returns uuid
language plpgsql
security definer
set search_path = ''
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


-- Lectura de auth.users para los helpers. SECURITY DEFINER porque el rol
-- `authenticated` no tiene acceso a esa tabla.
create or replace function tests.get_email(p_user_id uuid)
returns text
language sql
security definer
set search_path = ''
as $$
  select u.email::text from auth.users u where u.id = p_user_id;
$$;


-- Actúa como un usuario autenticado concreto.
-- Sin SECURITY DEFINER a propósito: ver nota 1 de la cabecera.
create or replace function tests.authenticate_as(p_user_id uuid)
returns void
language plpgsql
as $$
declare
  v_email text := tests.get_email(p_user_id);
begin
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
-- Funciona porque session_user sigue siendo postgres: SET ROLE se autoriza
-- contra el usuario de sesión, no contra el rol actual.
create or replace function tests.clear_authentication()
returns void
language plpgsql
as $$
begin
  perform set_config('role', 'postgres', true);
  perform set_config('request.jwt.claims', null, true);
end;
$$;


-- Ver nota 2 de la cabecera: sin esto, el primer cambio de rol deja
-- inutilizables al resto de los helpers.
grant execute on all functions in schema tests to anon, authenticated, service_role;
