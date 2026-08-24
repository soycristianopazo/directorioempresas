-- ============================================================================
-- 0002 · Perfiles de usuario
-- ----------------------------------------------------------------------------
-- Fase 1.1. Espejo 1:1 de auth.users con los datos de la persona.
--
-- REGLA (docs/01-ARQUITECTURA.md §E.1): profiles NO tiene organization_id.
-- Una persona pertenece a N organizaciones vía organization_members.
-- ============================================================================

create table public.profiles (
  id            uuid primary key references auth.users (id) on delete cascade,

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
  'Datos de la persona. 1:1 con auth.users. Sin organization_id: ver organization_members.';
comment on column public.profiles.last_org_id is
  'Sugerencia de UI para preseleccionar organización. Nunca fuente de autorización.';

create index profiles_last_active_idx on public.profiles (last_active_at desc nulls last);

select app.apply_table_conventions('public.profiles');


-- ─── Alta automática desde auth.users ───────────────────────────────────────
-- SECURITY DEFINER porque corre en el contexto del signup, antes de que exista
-- sesión. search_path acotado para evitar secuestro por schema.
create or replace function app.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, first_name, last_name, avatar_url)
  values (
    new.id,
    nullif(new.raw_user_meta_data ->> 'first_name', ''),
    nullif(new.raw_user_meta_data ->> 'last_name', ''),
    nullif(new.raw_user_meta_data ->> 'avatar_url', '')
  )
  on conflict (id) do nothing;

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function app.handle_new_user();


-- ─── Baja: auth.users on delete cascade se encarga del profile ──────────────
-- No se define trigger de borrado: la FK con ON DELETE CASCADE es suficiente
-- y evita una ruta de borrado alternativa que pueda desincronizarse.
