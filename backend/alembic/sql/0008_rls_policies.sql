-- ============================================================================
-- 0008 · Row Level Security — dominio D0 (identidad y multitenancy)
-- ----------------------------------------------------------------------------
-- Fase 1.5. Ver docs/01-ARQUITECTURA.md §I.3.
--
-- Deny by default: RLS activo en el 100% de las tablas. Sin policy, nadie pasa.
-- Toda comprobación usa los helpers SECURITY DEFINER de 0007 para evitar
-- recursión y permitir caching del planner.
--
-- Ya no hay cláusulas `TO anon` / `TO authenticated`: sin PostgREST la
-- aplicación conecta siempre con el mismo rol (app_user) y la diferencia entre
-- visitante y usuario la marca que app.current_user_id() devuelva NULL o no.
-- El bypass de los jobs se concede aparte, en la migración 0010.
-- ============================================================================

alter table public.profiles                      enable row level security;
alter table public.organizations                 enable row level security;
alter table public.organization_capabilities     enable row level security;
alter table public.organization_business_roles   enable row level security;
alter table public.organization_legal_identifiers enable row level security;
alter table public.permissions                   enable row level security;
alter table public.roles                         enable row level security;
alter table public.role_permissions              enable row level security;
alter table public.organization_members          enable row level security;
alter table public.member_roles                  enable row level security;
alter table public.platform_admins               enable row level security;
alter table public.organization_invitations      enable row level security;
alter table public.audit_logs                    enable row level security;
alter table public.domain_events                 enable row level security;


-- ============================================================================
-- profiles
-- ============================================================================

-- Cada quien ve su propio perfil.
create policy profiles_select_own
  on public.profiles for select
  using (id = app.current_user_id());

-- Y el de las personas con las que comparte alguna organización.
-- Sin esto no se puede pintar la página de equipo.
create policy profiles_select_colleagues
  on public.profiles for select
  using (
    exists (
      select 1
      from public.organization_members mine
      join public.organization_members theirs
        on theirs.organization_id = mine.organization_id
      where mine.user_id = app.current_user_id()
        and mine.status = 'ACTIVE'
        and theirs.user_id = public.profiles.id
        and theirs.status = 'ACTIVE'
    )
  );

create policy profiles_select_platform_admin
  on public.profiles for select
  using (app.is_platform_admin());

-- Solo el propio usuario edita su perfil. Nadie más, ni su ORG_ADMIN.
create policy profiles_update_own
  on public.profiles for update
  using (id = app.current_user_id())
  with check (id = app.current_user_id());

-- Sin policy de INSERT: los perfiles los crea el trigger on_auth_user_created.
-- Sin policy de DELETE: se borran en cascada al borrar public.users.


-- ============================================================================
-- organizations
-- ============================================================================

create policy organizations_select_member
  on public.organizations for select
  using (app.is_member_of(id));

-- Perfil público: visible para cualquiera, incluso sin sesión.
-- Es lo que hace indexable /proveedores/[slug].
create policy organizations_select_public
  on public.organizations for select
  using (
    deleted_at is null
    and status = 'ACTIVE'
    and visibility = 'PUBLIC'
  );

create policy organizations_select_registered
  on public.organizations for select
  using (
    deleted_at is null
    and status = 'ACTIVE'
    and visibility in ('REGISTERED', 'BUYERS_ONLY')
    and app.can_view_with_visibility(id, visibility)
  );

create policy organizations_select_platform_admin
  on public.organizations for select
  using (app.is_platform_admin());

-- Sin policy de INSERT: crear una organización pasa por
-- public.create_organization(), que además crea al owner en la misma
-- transacción. Un INSERT directo dejaría una organización sin miembros,
-- invisible para todos e imposible de recuperar.

create policy organizations_update_member
  on public.organizations for update
  using (app.has_permission(id, 'organization.update'))
  with check (app.has_permission(id, 'organization.update'));

-- Sin policy de DELETE: el borrado es lógico (deleted_at) vía UPDATE.


-- ============================================================================
-- organization_capabilities · organization_business_roles
-- ============================================================================

create policy org_capabilities_select
  on public.organization_capabilities for select
  using (
    app.is_member_of(organization_id)
    or app.is_platform_admin()
    or exists (
      select 1 from public.organizations o
      where o.id = organization_id
        and o.deleted_at is null
        and o.status = 'ACTIVE'
        and o.visibility = 'PUBLIC'
    )
  );

create policy org_capabilities_write
  on public.organization_capabilities for all
  using (app.has_permission(organization_id, 'organization.update'))
  with check (app.has_permission(organization_id, 'organization.update'));


create policy org_business_roles_select
  on public.organization_business_roles for select
  using (
    app.is_member_of(organization_id)
    or app.is_platform_admin()
    or exists (
      select 1 from public.organizations o
      where o.id = organization_id
        and o.deleted_at is null
        and o.status = 'ACTIVE'
        and o.visibility = 'PUBLIC'
    )
  );

create policy org_business_roles_write
  on public.organization_business_roles for all
  using (app.has_permission(organization_id, 'organization.update'))
  with check (app.has_permission(organization_id, 'organization.update'));


-- ============================================================================
-- organization_legal_identifiers
-- ----------------------------------------------------------------------------
-- El RUT NO es público. Se expone a miembros y a compradores autenticados
-- (que legítimamente necesitan identificar a la contraparte), nunca a anon:
-- publicarlo abierto invita al scraping masivo de la base de proveedores.
-- ============================================================================

create policy org_legal_identifiers_select
  on public.organization_legal_identifiers for select
  using (
    app.is_member_of(organization_id)
    or app.is_platform_admin()
    or (
      app.viewer_has_capability('BUYER')
      and exists (
        select 1 from public.organizations o
        where o.id = organization_id
          and o.deleted_at is null
          and o.status = 'ACTIVE'
          and o.visibility in ('PUBLIC', 'REGISTERED', 'BUYERS_ONLY')
      )
    )
  );

create policy org_legal_identifiers_write
  on public.organization_legal_identifiers for all
  using (app.has_permission(organization_id, 'organization.update'))
  with check (app.has_permission(organization_id, 'organization.update'));


-- ============================================================================
-- permissions · roles · role_permissions
-- ----------------------------------------------------------------------------
-- Catálogo. Lectura para autenticados; escritura solo plataforma (o el
-- ORG_ADMIN sobre los roles custom de su propia organización).
-- ============================================================================

create policy permissions_select
  on public.permissions for select
  using (true);

create policy permissions_write_platform
  on public.permissions for all
  using (app.has_platform_role('SUPER_ADMIN'))
  with check (app.has_platform_role('SUPER_ADMIN'));


create policy roles_select_system
  on public.roles for select
  using (organization_id is null);

create policy roles_select_own_org
  on public.roles for select
  using (organization_id is not null and app.is_member_of(organization_id));

create policy roles_write_platform
  on public.roles for all
  using (app.has_platform_role('SUPER_ADMIN'))
  with check (app.has_platform_role('SUPER_ADMIN'));

-- Roles a medida de una organización: los administra su propio ORG_ADMIN.
create policy roles_write_own_org
  on public.roles for all
  using (
    organization_id is not null
    and not is_system
    and app.has_permission(organization_id, 'role.manage')
  )
  with check (
    organization_id is not null
    and not is_system
    and app.has_permission(organization_id, 'role.manage')
  );


create policy role_permissions_select
  on public.role_permissions for select
  using (
    exists (
      select 1 from public.roles r
      where r.id = role_id
        and (r.organization_id is null or app.is_member_of(r.organization_id))
    )
  );

create policy role_permissions_write_platform
  on public.role_permissions for all
  using (app.has_platform_role('SUPER_ADMIN'))
  with check (app.has_platform_role('SUPER_ADMIN'));

create policy role_permissions_write_own_org
  on public.role_permissions for all
  using (
    exists (
      select 1 from public.roles r
      where r.id = role_id
        and r.organization_id is not null
        and not r.is_system
        and app.has_permission(r.organization_id, 'role.manage')
    )
  )
  with check (
    exists (
      select 1 from public.roles r
      where r.id = role_id
        and r.organization_id is not null
        and not r.is_system
        and app.has_permission(r.organization_id, 'role.manage')
    )
  );


-- ============================================================================
-- organization_members
-- ============================================================================

-- Cada quien ve sus propias membresías: es lo que alimenta el selector de
-- organización activa.
create policy org_members_select_own
  on public.organization_members for select
  using (user_id = app.current_user_id());

-- Y ve al resto del equipo de sus organizaciones.
create policy org_members_select_team
  on public.organization_members for select
  using (app.is_member_of(organization_id));

create policy org_members_select_platform_admin
  on public.organization_members for select
  using (app.is_platform_admin());

-- Sin INSERT directo: entrar a una organización pasa por
-- create_organization() o accept_invitation(). Si un usuario pudiera
-- insertarse a sí mismo en organization_members, el aislamiento multiempresa
-- entero se cae. Esta es la policy más importante del archivo.

create policy org_members_update
  on public.organization_members for update
  using (app.has_permission(organization_id, 'member.manage'))
  with check (app.has_permission(organization_id, 'member.manage'));

create policy org_members_delete
  on public.organization_members for delete
  using (app.has_permission(organization_id, 'member.manage'));


-- ============================================================================
-- member_roles
-- ============================================================================

create policy member_roles_select
  on public.member_roles for select
  using (
    exists (
      select 1 from public.organization_members m
      where m.id = member_id
        and (m.user_id = app.current_user_id() or app.is_member_of(m.organization_id))
    )
  );

create policy member_roles_write
  on public.member_roles for all
  using (
    exists (
      select 1 from public.organization_members m
      where m.id = member_id
        and app.has_permission(m.organization_id, 'member.manage')
    )
  )
  with check (
    exists (
      select 1 from public.organization_members m
      where m.id = member_id
        and app.has_permission(m.organization_id, 'member.manage')
    )
  );


-- ============================================================================
-- platform_admins
-- ----------------------------------------------------------------------------
-- Solo SUPER_ADMIN. Nadie más necesita saber quiénes son los administradores.
-- ============================================================================

create policy platform_admins_select_own
  on public.platform_admins for select
  using (user_id = app.current_user_id());

create policy platform_admins_all_super
  on public.platform_admins for all
  using (app.has_platform_role('SUPER_ADMIN'))
  with check (app.has_platform_role('SUPER_ADMIN'));


-- ============================================================================
-- organization_invitations
-- ----------------------------------------------------------------------------
-- El invitado NO consulta esta tabla: canjea el token vía
-- accept_invitation(), que corre como SECURITY DEFINER. Así el token nunca
-- se compara desde el cliente y la tabla no queda expuesta a enumeración.
-- ============================================================================

create policy org_invitations_select_team
  on public.organization_invitations for select
  using (app.has_permission(organization_id, 'member.manage'));

create policy org_invitations_insert
  on public.organization_invitations for insert
  with check (
    app.has_permission(organization_id, 'member.manage')
    and invited_by = app.current_user_id()
  );

create policy org_invitations_update
  on public.organization_invitations for update
  using (app.has_permission(organization_id, 'member.manage'))
  with check (app.has_permission(organization_id, 'member.manage'));

create policy org_invitations_delete
  on public.organization_invitations for delete
  using (app.has_permission(organization_id, 'member.manage'));


-- ============================================================================
-- audit_logs
-- ----------------------------------------------------------------------------
-- Lectura para quien tenga audit.read en la organización. Escritura solo vía
-- app.write_audit() (SECURITY DEFINER): sin policy de INSERT, nadie puede
-- fabricar registros de auditoría desde el cliente.
-- ============================================================================

create policy audit_logs_select_org
  on public.audit_logs for select
  using (
    organization_id is not null
    and app.has_permission(organization_id, 'audit.read')
  );

create policy audit_logs_select_platform
  on public.audit_logs for select
  using (app.is_platform_admin());


-- ============================================================================
-- domain_events
-- ----------------------------------------------------------------------------
-- RLS activo y CERO policies: es un outbox interno. Solo service_role (que
-- salta RLS) lo consume desde los workers. Ningún usuario debe verlo: el
-- payload puede contener datos de varias organizaciones.
-- ============================================================================

revoke all on public.domain_events from anon, authenticated;
