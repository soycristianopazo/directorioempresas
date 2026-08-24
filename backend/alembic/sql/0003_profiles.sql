-- ============================================================================
-- 0002 · Perfiles de usuario
-- ----------------------------------------------------------------------------
-- Fase 1.1. Espejo 1:1 de public.users con los datos de la persona.
--
-- REGLA (docs/01-ARQUITECTURA.md §E.1): profiles NO tiene organization_id.
-- Una persona pertenece a N organizaciones vía organization_members.
-- ============================================================================

create table public.profiles (
  id            uuid primary key references public.users (id) on delete cascade,

  first_name    text,
  last_name     text,
  full_name     text generated always as (
                  nullif(trim(coalesce(first_name, '') || ' ' || coalesce(last_name, '')), '')
                ) stored,
  avatar_url    text,
  phone         text,
  job_title     text,

  locale        text not null default 'es-CL',
  timezone      text not null default 'America/Santiago',

  -- Última organización usada. Sugerencia de UI: se REVALIDA contra la
  -- membresía en cada request. Nunca es fuente de autorización.
  last_org_id   uuid,

  onboarded_at  timestamptz,
  last_active_at timestamptz,

  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  constraint profiles_locale_format check (locale ~ '^[a-z]{2}(-[A-Z]{2})?$'),
  constraint profiles_phone_len     check (phone is null or length(phone) between 6 and 32)
);

comment on table public.profiles is
  'Datos de la persona. 1:1 con public.users. Sin organization_id: ver organization_members.';
comment on column public.profiles.last_org_id is
  'Sugerencia de UI para preseleccionar organización. Nunca fuente de autorización.';

create index profiles_last_active_idx on public.profiles (last_active_at desc nulls last);

select app.apply_table_conventions('public.profiles');


-- ─── Alta del perfil ────────────────────────────────────────────────────────
--
-- En el diseño anterior un trigger sobre auth.users creaba el profile, porque
-- GoTrue insertaba en una tabla de otro sistema y no había otro punto donde
-- engancharse.
--
-- Aquí el registro lo hace el servicio de autenticación de FastAPI, que crea
-- usuario y perfil en la misma transacción. Es más explícito, se puede testear
-- sin levantar Postgres, y los errores de validación salen por donde el resto
-- de los errores de la aplicación en vez de como una excepción de trigger.
--
-- Ver backend/app/services/auth.py
