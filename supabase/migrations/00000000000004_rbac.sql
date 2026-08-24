-- ============================================================================
-- 0004 · Membresía, roles y permisos (RBAC)
-- ----------------------------------------------------------------------------
-- Fase 1.3. Ver docs/01-ARQUITECTURA.md §E.
--
-- REGLAS:
--  · Una persona pertenece a N organizaciones  → organization_members
--  · Un miembro tiene N roles                  → member_roles
--  · Nunca se chequea el nombre del rol en el código: se chequea el PERMISO.
--    Eso permite roles custom por empresa sin tocar una línea de TypeScript.
-- ============================================================================

-- ─── Permisos atómicos ──────────────────────────────────────────────────────

create table public.permissions (
  code        text primary key,
  resource    text not null,
  action      text not null,
  description text not null,
  scope       app.role_scope not null default 'ORGANIZATION',

  constraint permissions_code_format check (code ~ '^[a-z_]+\.[a-z_]+$')
);

comment on table public.permissions is
  'Permisos atómicos con formato recurso.acción. Fuente de verdad de la autorización.';


-- ─── Roles ──────────────────────────────────────────────────────────────────

create table public.roles (
  id              uuid primary key default gen_random_uuid(),
  code            text not null,
  name            text not null,
  description     text,
  scope           app.role_scope not null,

  -- NULL = rol de sistema, disponible para todas las organizaciones.
  -- No NULL = rol a medida de esa organización (evolución a permisos granulares
  -- sin refactor, §E.2 de la arquitectura).
  organization_id uuid references public.organizations (id) on delete cascade,

  is_system       boolean not null default false,
  -- Rol que recibe automáticamente quien crea la organización.
  is_default_owner boolean not null default false,
  sort_order      smallint not null default 0,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint roles_code_format check (code ~ '^[A-Z][A-Z0-9_]*$'),
  -- Un rol de sistema no puede pertenecer a una organización, y viceversa.
  constraint roles_system_has_no_org check (
    (is_system and organization_id is null) or (not is_system)
  )
);

comment on table public.roles is
  'Roles de plataforma y de organización. organization_id no nulo = rol custom de esa empresa.';

-- Los roles de sistema tienen código único global.
create unique index roles_system_code_key
  on public.roles (code)
  where organization_id is null;

-- Los roles custom son únicos dentro de su organización.
create unique index roles_org_code_key
  on public.roles (organization_id, code)
  where organization_id is not null;

create index roles_org_idx on public.roles (organization_id);

select app.apply_table_conventions('public.roles');


-- ─── Rol → permisos ─────────────────────────────────────────────────────────

create table public.role_permissions (
  role_id         uuid not null references public.roles (id) on delete cascade,
  permission_code text not null references public.permissions (code) on delete cascade,
  granted_at      timestamptz not null default now(),

  primary key (role_id, permission_code)
);

create index role_permissions_permission_idx
  on public.role_permissions (permission_code);


-- ─── Membresía persona ↔ organización ───────────────────────────────────────

create table public.organization_members (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles (id) on delete cascade,
  organization_id uuid not null references public.organizations (id) on delete cascade,

  status          app.member_status not null default 'ACTIVE',

  -- Límite de aprobación para la cadena DoA de adjudicaciones (mejora N.9).
  -- NULL = no puede aprobar montos. Se usa en la fase 8.
  approval_limit_amount numeric(18, 4),
  approval_limit_currency char(3),

  invited_by      uuid references public.profiles (id) on delete set null,
  invited_at      timestamptz,
  joined_at       timestamptz not null default now(),
  removed_at      timestamptz,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint org_members_unique unique (user_id, organization_id),
  constraint org_members_approval_limit check (
    approval_limit_amount is null or approval_limit_amount >= 0
  ),
  constraint org_members_removed_consistency check (
    (status = 'REMOVED') = (removed_at is not null)
  )
);

comment on table public.organization_members is
  'Pertenencia persona↔empresa. Una persona puede pertenecer a N organizaciones (§48 del brief).';

create index org_members_user_idx
  on public.organization_members (user_id)
  where status = 'ACTIVE';

create index org_members_org_idx
  on public.organization_members (organization_id)
  where status = 'ACTIVE';

select app.apply_table_conventions('public.organization_members');


-- ─── Miembro → N roles ──────────────────────────────────────────────────────

create table public.member_roles (
  member_id   uuid not null references public.organization_members (id) on delete cascade,
  role_id     uuid not null references public.roles (id) on delete cascade,
  assigned_at timestamptz not null default now(),
  assigned_by uuid references public.profiles (id) on delete set null,

  primary key (member_id, role_id)
);

comment on table public.member_roles is
  'Un miembro puede tener varios roles (ej. BUYER_MANAGER + CONTRACT_MANAGER).';

create index member_roles_role_idx on public.member_roles (role_id);


-- Un rol de organización solo puede asignarse a miembros de ESA organización.
-- Sin esto, un ORG_ADMIN podría asignar un rol custom de otra empresa.
create or replace function app.check_member_role_org_match()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_role_org   uuid;
  v_member_org uuid;
  v_role_scope app.role_scope;
begin
  select r.organization_id, r.scope into v_role_org, v_role_scope
  from public.roles r where r.id = new.role_id;

  select m.organization_id into v_member_org
  from public.organization_members m where m.id = new.member_id;

  if v_role_scope = 'PLATFORM' then
    -- Los roles de plataforma no se asignan por membresía de organización.
    raise exception 'Un rol de plataforma no puede asignarse vía member_roles'
      using errcode = 'check_violation';
  end if;

  if v_role_org is not null and v_role_org <> v_member_org then
    raise exception 'El rol pertenece a otra organización'
      using errcode = 'check_violation';
  end if;

  return new;
end;
$$;

create trigger trg_member_roles_org_match
  before insert or update on public.member_roles
  for each row execute function app.check_member_role_org_match();


-- ─── Roles de plataforma (separados de la membresía de empresa) ─────────────

create table public.platform_admins (
  user_id     uuid not null references public.profiles (id) on delete cascade,
  role_id     uuid not null references public.roles (id) on delete cascade,
  granted_at  timestamptz not null default now(),
  granted_by  uuid references public.profiles (id) on delete set null,
  revoked_at  timestamptz,

  primary key (user_id, role_id)
);

comment on table public.platform_admins is
  'Roles de plataforma (SUPER_ADMIN, PLATFORM_ADMIN, ACCREDITATION_REVIEWER, SUPPORT_AGENT).';

create index platform_admins_active_idx
  on public.platform_admins (user_id)
  where revoked_at is null;


-- ─── Invitaciones al equipo ─────────────────────────────────────────────────

create table public.organization_invitations (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  email           extensions.citext not null,
  role_id         uuid not null references public.roles (id) on delete restrict,

  -- Se guarda solo el hash del token. Si se filtra la tabla, los tokens
  -- pendientes siguen sin ser utilizables.
  token_hash      text not null,
  status          app.invitation_status not null default 'PENDING',

  invited_by      uuid not null references public.profiles (id) on delete cascade,
  expires_at      timestamptz not null,
  accepted_at     timestamptz,
  accepted_by     uuid references public.profiles (id) on delete set null,
  revoked_at      timestamptz,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint org_invitations_email_format check (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  constraint org_invitations_expires_future check (expires_at > created_at)
);

comment on table public.organization_invitations is
  'Invitaciones por email. Se almacena el hash del token, nunca el token.';

create unique index org_invitations_token_key
  on public.organization_invitations (token_hash);

-- Una sola invitación pendiente por email y organización.
create unique index org_invitations_pending_key
  on public.organization_invitations (organization_id, email)
  where status = 'PENDING';

create index org_invitations_email_idx
  on public.organization_invitations (email)
  where status = 'PENDING';

select app.apply_table_conventions('public.organization_invitations');
