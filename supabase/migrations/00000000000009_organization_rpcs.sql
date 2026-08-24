-- ============================================================================
-- 0009 · Operaciones transaccionales de organización
-- ----------------------------------------------------------------------------
-- Fase 1.7 / 1.8.
--
-- Estas operaciones NO pueden ser un INSERT desde el cliente porque tocan
-- varias tablas que deben quedar coherentes o no quedar. Crear una
-- organización sin su owner produce una entidad huérfana que nadie puede ver
-- ni recuperar. Por eso van como RPC SECURITY DEFINER con validación explícita
-- dentro: el cliente pide la operación, no la compone.
-- ============================================================================

-- ─── Crear organización ─────────────────────────────────────────────────────

create or replace function public.create_organization(
  p_legal_name    text,
  p_trade_name    text default null,
  p_rut           text default null,
  p_capabilities  app.organization_capability[] default array['SUPPLIER']::app.organization_capability[],
  p_country_code  char(2) default 'CL'
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id  uuid := auth.uid();
  v_org_id   uuid;
  v_member_id uuid;
  v_owner_role_id uuid;
  v_slug     text;
  v_base_slug text;
  v_suffix   int := 0;
  v_capability app.organization_capability;
begin
  if v_user_id is null then
    raise exception 'Se requiere sesión iniciada'
      using errcode = 'insufficient_privilege';
  end if;

  if p_legal_name is null or length(trim(p_legal_name)) < 2 then
    raise exception 'La razón social es obligatoria'
      using errcode = 'check_violation';
  end if;

  if p_capabilities is null or cardinality(p_capabilities) = 0 then
    raise exception 'Se requiere al menos una capacidad (BUYER o SUPPLIER)'
      using errcode = 'check_violation';
  end if;

  -- PLATFORM_ADMIN no se puede autoasignar: solo lo otorga un SUPER_ADMIN.
  if 'PLATFORM_ADMIN' = any (p_capabilities) and not app.has_platform_role('SUPER_ADMIN') then
    raise exception 'La capacidad PLATFORM_ADMIN no puede autoasignarse'
      using errcode = 'insufficient_privilege';
  end if;

  if p_rut is not null and not app.is_valid_rut(p_rut) then
    raise exception 'RUT inválido: %', p_rut
      using errcode = 'check_violation';
  end if;

  -- Slug único: se deriva del nombre comercial y se desambigua con sufijo.
  v_base_slug := app.slugify(coalesce(nullif(trim(p_trade_name), ''), p_legal_name));
  if v_base_slug is null or v_base_slug = '' then
    v_base_slug := 'empresa';
  end if;
  v_base_slug := left(v_base_slug, 90);
  v_slug := v_base_slug;

  while exists (
    select 1 from public.organizations o
    where o.slug = v_slug and o.deleted_at is null
  ) loop
    v_suffix := v_suffix + 1;
    v_slug := v_base_slug || '-' || v_suffix::text;
  end loop;

  -- 1 · La organización
  insert into public.organizations (
    legal_name, trade_name, slug, country_code, status, visibility, created_by, updated_by
  )
  values (
    trim(p_legal_name), nullif(trim(p_trade_name), ''), v_slug, p_country_code,
    'DRAFT', 'PRIVATE', v_user_id, v_user_id
  )
  returning id into v_org_id;

  -- 2 · Capacidades
  foreach v_capability in array p_capabilities loop
    insert into public.organization_capabilities (organization_id, capability, enabled_by)
    values (v_org_id, v_capability, v_user_id)
    on conflict do nothing;
  end loop;

  -- 3 · Identificación tributaria
  if p_rut is not null then
    insert into public.organization_legal_identifiers (
      organization_id, identifier_type, country_code, value, value_normalized, is_primary
    )
    values (v_org_id, 'RUT', p_country_code, p_rut, app.normalize_rut(p_rut), true);
  end if;

  -- 4 · El creador como miembro
  insert into public.organization_members (user_id, organization_id, status)
  values (v_user_id, v_org_id, 'ACTIVE')
  returning id into v_member_id;

  -- 5 · Rol de dueño
  select r.id into v_owner_role_id
  from public.roles r
  where r.organization_id is null and r.is_default_owner
  limit 1;

  if v_owner_role_id is null then
    raise exception 'No existe el rol por defecto de dueño (ORG_OWNER)'
      using errcode = 'internal_error';
  end if;

  insert into public.member_roles (member_id, role_id, assigned_by)
  values (v_member_id, v_owner_role_id, v_user_id);

  -- 6 · Preseleccionar en la UI
  update public.profiles set last_org_id = v_org_id where id = v_user_id;

  -- 7 · Rastro
  perform app.write_audit(
    'organization.created', 'organization', v_org_id, v_org_id,
    null, jsonb_build_object('legal_name', p_legal_name, 'slug', v_slug)
  );
  perform app.emit_event(
    'organization.created', 'organization', v_org_id, v_org_id,
    jsonb_build_object('slug', v_slug, 'capabilities', to_jsonb(p_capabilities))
  );

  return v_org_id;
end;
$$;

comment on function public.create_organization is
  'Crea organización + capacidades + RUT + owner en una sola transacción.';

revoke all on function public.create_organization from public, anon;
grant execute on function public.create_organization to authenticated;


-- ─── Aceptar invitación ─────────────────────────────────────────────────────
-- El cliente envía el token en claro; la comparación se hace aquí contra el
-- hash almacenado. El token nunca sale de la base ni se expone vía SELECT.

create or replace function public.accept_invitation(p_token text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id    uuid := auth.uid();
  v_user_email citext;
  v_inv        public.organization_invitations%rowtype;
  v_member_id  uuid;
  v_token_hash text;
begin
  if v_user_id is null then
    raise exception 'Se requiere sesión iniciada'
      using errcode = 'insufficient_privilege';
  end if;

  v_token_hash := encode(extensions.digest(p_token, 'sha256'), 'hex');

  select * into v_inv
  from public.organization_invitations i
  where i.token_hash = v_token_hash
  for update;

  if not found then
    raise exception 'Invitación no encontrada'
      using errcode = 'no_data_found';
  end if;

  if v_inv.status <> 'PENDING' then
    raise exception 'La invitación ya no está vigente (estado: %)', v_inv.status
      using errcode = 'check_violation';
  end if;

  if v_inv.expires_at <= now() then
    update public.organization_invitations
      set status = 'EXPIRED'
      where id = v_inv.id;
    raise exception 'La invitación expiró'
      using errcode = 'check_violation';
  end if;

  -- La invitación es para un email concreto: no es un pase transferible.
  select u.email into v_user_email from auth.users u where u.id = v_user_id;

  if v_user_email is distinct from v_inv.email then
    raise exception 'La invitación fue emitida para otra dirección de correo'
      using errcode = 'insufficient_privilege';
  end if;

  -- Reincorporación: si ya fue miembro y se le removió, se reactiva.
  insert into public.organization_members (user_id, organization_id, status, invited_by, invited_at)
  values (v_user_id, v_inv.organization_id, 'ACTIVE', v_inv.invited_by, v_inv.created_at)
  on conflict (user_id, organization_id) do update
    set status = 'ACTIVE', removed_at = null
  returning id into v_member_id;

  insert into public.member_roles (member_id, role_id, assigned_by)
  values (v_member_id, v_inv.role_id, v_inv.invited_by)
  on conflict do nothing;

  update public.organization_invitations
    set status = 'ACCEPTED', accepted_at = now(), accepted_by = v_user_id
    where id = v_inv.id;

  update public.profiles set last_org_id = v_inv.organization_id where id = v_user_id;

  perform app.write_audit(
    'member.joined', 'organization_member', v_member_id, v_inv.organization_id,
    null, jsonb_build_object('via', 'invitation', 'invitation_id', v_inv.id)
  );
  perform app.emit_event(
    'member.joined', 'organization', v_inv.organization_id, v_inv.organization_id,
    jsonb_build_object('user_id', v_user_id)
  );

  return v_inv.organization_id;
end;
$$;

revoke all on function public.accept_invitation from public, anon;
grant execute on function public.accept_invitation to authenticated;


-- ─── Cambiar organización activa ────────────────────────────────────────────
-- Persiste la preferencia de UI. La autorización real la sigue haciendo RLS
-- en cada consulta: esto es una comodidad, no un control de acceso.

create or replace function public.switch_organization(p_organization_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := auth.uid();
begin
  if v_user_id is null then
    raise exception 'Se requiere sesión iniciada'
      using errcode = 'insufficient_privilege';
  end if;

  if not exists (
    select 1 from public.organization_members m
    where m.user_id = v_user_id
      and m.organization_id = p_organization_id
      and m.status = 'ACTIVE'
  ) then
    raise exception 'No pertenece a esa organización'
      using errcode = 'insufficient_privilege';
  end if;

  update public.profiles
    set last_org_id = p_organization_id, last_active_at = now()
    where id = v_user_id;
end;
$$;

revoke all on function public.switch_organization from public, anon;
grant execute on function public.switch_organization to authenticated;


-- ─── Remover un miembro ─────────────────────────────────────────────────────
-- Con la salvaguarda que siempre falta: no dejar la organización sin dueño.

create or replace function public.remove_member(p_member_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_member public.organization_members%rowtype;
  v_owner_count int;
  v_is_owner boolean;
begin
  select * into v_member
  from public.organization_members m
  where m.id = p_member_id;

  if not found then
    raise exception 'Miembro no encontrado' using errcode = 'no_data_found';
  end if;

  if not app.has_permission(v_member.organization_id, 'member.manage') then
    raise exception 'Sin permiso para administrar miembros'
      using errcode = 'insufficient_privilege';
  end if;

  select exists (
    select 1 from public.member_roles mr
    join public.roles r on r.id = mr.role_id
    where mr.member_id = p_member_id and r.is_default_owner
  ) into v_is_owner;

  if v_is_owner then
    select count(*) into v_owner_count
    from public.organization_members m
    join public.member_roles mr on mr.member_id = m.id
    join public.roles r on r.id = mr.role_id
    where m.organization_id = v_member.organization_id
      and m.status = 'ACTIVE'
      and r.is_default_owner;

    if v_owner_count <= 1 then
      raise exception 'No se puede remover al último dueño de la organización'
        using errcode = 'check_violation';
    end if;
  end if;

  update public.organization_members
    set status = 'REMOVED', removed_at = now()
    where id = p_member_id;

  perform app.write_audit(
    'member.removed', 'organization_member', p_member_id, v_member.organization_id,
    jsonb_build_object('user_id', v_member.user_id), null
  );
end;
$$;

revoke all on function public.remove_member from public, anon;
grant execute on function public.remove_member to authenticated;


-- ============================================================================
-- Vistas de conveniencia
-- ----------------------------------------------------------------------------
-- security_invoker = true: la vista respeta las policies del usuario que
-- consulta. Sin esta opción una vista corre como su dueño y se convierte en
-- un agujero silencioso en RLS.
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
 and m.user_id = (select auth.uid())
 and m.status = 'ACTIVE'
left join public.member_roles mr on mr.member_id = m.id
left join public.roles r         on r.id = mr.role_id
left join public.organization_capabilities c on c.organization_id = o.id
where o.deleted_at is null
group by o.id, m.id;

comment on view public.v_my_organizations is
  'Organizaciones del usuario con sus roles y capacidades. Alimenta el selector de organización.';

grant select on public.v_my_organizations to authenticated;


-- ============================================================================
-- Envoltorios públicos de los helpers de RLS
-- ----------------------------------------------------------------------------
-- El schema `app` no se expone vía PostgREST a propósito. Estas dos funciones
-- son la única superficie que la aplicación necesita consultar, y solo pueden
-- responder sobre el usuario de la sesión: no aceptan un user_id como
-- argumento, así que no sirven para enumerar permisos ajenos.
-- ============================================================================

create or replace function public.my_permissions(p_organization_id uuid)
returns setof text
language sql
stable
security definer
set search_path = ''
as $$
  select app.effective_permissions(p_organization_id);
$$;

comment on function public.my_permissions(uuid) is
  'Permisos efectivos del usuario de la sesión en una organización.';

revoke all on function public.my_permissions from public, anon;
grant execute on function public.my_permissions to authenticated;


create or replace function public.am_i_platform_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select app.is_platform_admin();
$$;

revoke all on function public.am_i_platform_admin from public, anon;
grant execute on function public.am_i_platform_admin to authenticated;
