-- ============================================================================
-- 0002 · Credenciales e identidad de la petición
-- ----------------------------------------------------------------------------
-- Reemplaza a auth.users de GoTrue y a auth.uid().
--
-- El endurecimiento (rol app_user, grants y FORCE RLS) NO va aquí: necesita
-- que todas las tablas existan, así que vive en la última migración.
--
-- QUÉ CAMBIA RESPECTO AL DISEÑO ORIGINAL Y POR QUÉ
-- ---------------------------------------------------------------------------
-- El diseño original apoyaba RLS en Supabase Auth: GoTrue emitía el JWT,
-- PostgREST lo pasaba a Postgres, y `auth.uid()` leía el claim `sub`.
--
-- Con FastAPI + SQLAlchemy + asyncpg no hay PostgREST: la aplicación abre la
-- conexión con un rol fijo. Eso rompe RLS de dos maneras, y ambas hay que
-- cerrarlas explícitamente:
--
--   1. `auth.uid()` no existe. Se reemplaza por una variable de sesión que la
--      aplicación fija por transacción: `app.current_user_id`.
--
--   2. Conectarse como `postgres` omite RLS por completo. El dueño de una
--      tabla NO está sujeto a sus propias policies salvo que se declare
--      FORCE ROW LEVEL SECURITY. Un backend que conecta como `postgres`
--      contra una base "con RLS habilitado" no tiene ninguna protección:
--      tiene una puerta blindada con la llave puesta.
--
-- La combinación correcta es: rol dedicado sin privilegios de dueño +
-- FORCE RLS en todas las tablas + SET LOCAL por transacción.
--
-- COMPATIBILIDAD CON EL TRANSACTION POOLER
-- ---------------------------------------------------------------------------
-- `SET LOCAL` tiene alcance transaccional, que es exactamente el alcance que
-- pgBouncer garantiza en modo transaction. Al terminar la transacción la
-- variable desaparece con ella, así que una conexión reciclada nunca arrastra
-- la identidad del request anterior. Si se usara `SET` (sin LOCAL) el pooler
-- filtraría identidades entre peticiones: es el bug de seguridad clásico de
-- este patrón.
-- ============================================================================


-- ─── Usuarios (reemplaza auth.users de GoTrue) ──────────────────────────────

create table public.users (
  id                  uuid primary key default gen_random_uuid(),
  email               extensions.citext not null,
  password_hash       text not null,

  email_verified_at   timestamptz,
  last_login_at       timestamptz,

  -- Bloqueo por intentos fallidos. Se gestiona en el servicio de auth.
  failed_login_count  smallint not null default 0,
  locked_until        timestamptz,

  is_active           boolean not null default true,

  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  deleted_at          timestamptz,

  constraint users_email_format check (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  -- bcrypt siempre produce 60 caracteres con prefijo $2a/$2b/$2y.
  constraint users_password_hash_format check (password_hash ~ '^\$2[aby]\$\d{2}\$.{53}$'),
  constraint users_failed_login_count check (failed_login_count >= 0)
);

comment on table public.users is
  'Credenciales. Reemplaza auth.users: la autenticación la maneja FastAPI con PyJWT + bcrypt.';

create unique index users_email_key on public.users (email) where deleted_at is null;
create index users_active_idx on public.users (id) where is_active and deleted_at is null;


-- ─── Sesiones / refresh tokens ──────────────────────────────────────────────
-- El access token es un JWT corto que no se almacena. El refresh sí, porque
-- debe poder revocarse: cerrar sesión en un dispositivo, expulsar a un
-- empleado que se fue, invalidar todo tras un cambio de contraseña.
--
-- Se guarda solo el hash, igual que con los tokens de invitación.

create table public.user_sessions (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references public.users (id) on delete cascade,

  refresh_token_hash  text not null,
  user_agent          text,
  ip_address          inet,

  issued_at           timestamptz not null default now(),
  expires_at          timestamptz not null,
  revoked_at          timestamptz,
  -- Rotación de refresh tokens: al usar uno se emite otro y este apunta al
  -- sucesor. Si alguien reutiliza un token ya rotado es señal de robo y se
  -- revoca la cadena completa.
  replaced_by_id      uuid references public.user_sessions (id) on delete set null,

  constraint user_sessions_expiry check (expires_at > issued_at)
);

create unique index user_sessions_token_key on public.user_sessions (refresh_token_hash);
create index user_sessions_user_idx on public.user_sessions (user_id)
  where revoked_at is null;
create index user_sessions_cleanup_idx on public.user_sessions (expires_at)
  where revoked_at is null;


-- ─── Tokens de un solo uso (verificación de correo, reset de contraseña) ────

create table public.user_tokens (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references public.users (id) on delete cascade,
  purpose       text not null,
  token_hash    text not null,
  expires_at    timestamptz not null,
  consumed_at   timestamptz,
  created_at    timestamptz not null default now(),

  constraint user_tokens_purpose check (purpose in ('EMAIL_VERIFICATION', 'PASSWORD_RESET'))
);

create unique index user_tokens_hash_key on public.user_tokens (token_hash);
create index user_tokens_user_idx on public.user_tokens (user_id, purpose)
  where consumed_at is null;


-- ============================================================================
-- Identidad de la petición
-- ============================================================================

-- Reemplaza a auth.uid().
--
-- `current_setting(..., true)` con missing_ok = true devuelve NULL en vez de
-- lanzar cuando la variable no está fijada. Eso importa: los jobs y las
-- migraciones corren sin identidad, y deben poder hacerlo sin reventar.
--
-- STABLE, no IMMUTABLE: el valor cambia entre transacciones.
create or replace function app.current_user_id()
returns uuid
language sql
stable
security definer
set search_path = ''
as $$
  select nullif(current_setting('app.current_user_id', true), '')::uuid;
$$;

comment on function app.current_user_id() is
  'Identidad de la petición. La fija FastAPI con SET LOCAL al abrir la transacción.';


-- Escotilla de emergencia para jobs y workers.
--
-- Un proceso sin usuario (recálculo de scores, vencimientos, procesado del
-- outbox) necesita saltarse RLS. En vez de conectarse como `postgres` —que lo
-- saltaría todo siempre y en silencio— se declara explícitamente por
-- transacción. Así el bypass es visible en el código y auditable.
create or replace function app.is_system_context()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(current_setting('app.system_context', true), 'off') = 'on';
$$;


-- ============================================================================
-- Policies de las tablas de credenciales
-- ----------------------------------------------------------------------------
-- Deliberadamente restrictivas: el servicio de autenticación es el único que
-- las toca, y lo hace en contexto de sistema. Ninguna petición de usuario
-- tiene motivo para leer un hash de contraseña ni un refresh token.
-- ============================================================================

create policy users_select_self
  on public.users for select
  using (id = app.current_user_id() or app.is_system_context());

create policy users_update_self
  on public.users for update
  using (id = app.current_user_id() or app.is_system_context())
  with check (id = app.current_user_id() or app.is_system_context());

create policy users_system_write
  on public.users for insert
  with check (app.is_system_context());

create policy user_sessions_system
  on public.user_sessions for all
  using (app.is_system_context())
  with check (app.is_system_context());

create policy user_tokens_system
  on public.user_tokens for all
  using (app.is_system_context())
  with check (app.is_system_context());


-- ============================================================================
-- Nota sobre profiles
-- ----------------------------------------------------------------------------
-- `profiles.id` pasa a referenciar public.users(id) en vez de auth.users(id).
-- El trigger `on_auth_user_created` desaparece: el alta de perfil la hace el
-- servicio de registro de FastAPI dentro de la misma transacción que crea el
-- usuario, que es más explícito y testeable que un trigger sobre una tabla de
-- otro sistema.
-- ============================================================================
