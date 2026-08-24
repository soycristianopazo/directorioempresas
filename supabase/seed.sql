-- ============================================================================
-- Seed de desarrollo
-- ----------------------------------------------------------------------------
-- Se ejecuta con `supabase db reset`. SOLO datos de prueba.
--
-- Los datos estructurales (permisos, roles de sistema) viven en la migración
-- 0008, no aquí: el sistema no funciona sin ellos y deben existir también en
-- producción.
--
-- El seed de Chile (regiones, comunas, industrias, taxonomía) llega en la
-- fase 2 en supabase/seed/chile/.
-- ============================================================================

-- Contraseña de todos los usuarios de prueba: Password123
do $$
declare
  v_ana   uuid := '11111111-1111-1111-1111-111111111111';
  v_bruno uuid := '22222222-2222-2222-2222-222222222222';
  v_carla uuid := '33333333-3333-3333-3333-333333333333';
  v_admin uuid := '99999999-9999-9999-9999-999999999999';
  v_alfa  uuid;
  v_beta  uuid;
  v_member uuid;
begin
  -- Usuarios
  insert into auth.users (
    id, instance_id, aud, role, email, encrypted_password, email_confirmed_at,
    raw_app_meta_data, raw_user_meta_data, created_at, updated_at
  )
  select
    u.id, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
    u.email, extensions.crypt('Password123', extensions.gen_salt('bf')), now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    jsonb_build_object('first_name', u.first_name, 'last_name', u.last_name),
    now(), now()
  from (values
    (v_ana,   'ana@transportesalfa.cl',  'Ana',   'Rojas'),
    (v_bruno, 'bruno@transportesalfa.cl','Bruno', 'Díaz'),
    (v_carla, 'carla@minerabeta.cl',     'Carla', 'Soto'),
    (v_admin, 'admin@plataforma.cl',     'Admin', 'Plataforma')
  ) as u(id, email, first_name, last_name)
  on conflict (id) do nothing;

  -- Organización proveedora
  insert into public.organizations (
    legal_name, trade_name, slug, country_code, status, visibility,
    short_description, description, founded_year, company_size, employee_count, created_by
  )
  values (
    'Transportes Alfa SpA', 'Transportes Alfa', 'transportes-alfa', 'CL', 'ACTIVE', 'PUBLIC',
    'Transporte de personal para faenas mineras en la Región de Antofagasta.',
    'Operamos flota propia de buses y minibuses con acreditación minera, GPS en línea y conductores con experiencia en faena.',
    2011, 'MEDIUM', 120, v_ana
  )
  on conflict do nothing
  returning id into v_alfa;

  if v_alfa is null then
    select id into v_alfa from public.organizations where slug = 'transportes-alfa';
  end if;

  insert into public.organization_capabilities (organization_id, capability)
  values (v_alfa, 'SUPPLIER'), (v_alfa, 'BUYER')
  on conflict do nothing;

  insert into public.organization_business_roles (organization_id, business_role)
  values (v_alfa, 'CONTRATISTA')
  on conflict do nothing;

  insert into public.organization_legal_identifiers (
    organization_id, identifier_type, country_code, value, value_normalized, is_primary
  )
  values (v_alfa, 'RUT', 'CL', '76.086.428-5', '76086428-5', true)
  on conflict do nothing;

  -- Organización compradora
  insert into public.organizations (
    legal_name, trade_name, slug, country_code, status, visibility, short_description, created_by
  )
  values (
    'Minera Beta S.A.', 'Minera Beta', 'minera-beta', 'CL', 'ACTIVE', 'REGISTERED',
    'Operación minera de cobre en la Región de Antofagasta.', v_carla
  )
  on conflict do nothing
  returning id into v_beta;

  if v_beta is null then
    select id into v_beta from public.organizations where slug = 'minera-beta';
  end if;

  insert into public.organization_capabilities (organization_id, capability)
  values (v_beta, 'BUYER')
  on conflict do nothing;

  insert into public.organization_business_roles (organization_id, business_role)
  values (v_beta, 'MANDANTE')
  on conflict do nothing;

  -- Membresías
  insert into public.organization_members (user_id, organization_id, status)
  values (v_ana, v_alfa, 'ACTIVE')
  on conflict (user_id, organization_id) do nothing
  returning id into v_member;

  if v_member is not null then
    insert into public.member_roles (member_id, role_id)
    select v_member, r.id from public.roles r
    where r.code = 'ORG_OWNER' and r.organization_id is null;
  end if;

  insert into public.organization_members (user_id, organization_id, status)
  values (v_bruno, v_alfa, 'ACTIVE')
  on conflict (user_id, organization_id) do nothing
  returning id into v_member;

  if v_member is not null then
    insert into public.member_roles (member_id, role_id)
    select v_member, r.id from public.roles r
    where r.code = 'SALES' and r.organization_id is null;
  end if;

  insert into public.organization_members (user_id, organization_id, status)
  values (v_carla, v_beta, 'ACTIVE')
  on conflict (user_id, organization_id) do nothing
  returning id into v_member;

  if v_member is not null then
    insert into public.member_roles (member_id, role_id)
    select v_member, r.id from public.roles r
    where r.code = 'ORG_OWNER' and r.organization_id is null;
  end if;

  -- Carla también pertenece a Alfa: valida la pertenencia múltiple (§48).
  insert into public.organization_members (user_id, organization_id, status)
  values (v_carla, v_alfa, 'ACTIVE')
  on conflict (user_id, organization_id) do nothing
  returning id into v_member;

  if v_member is not null then
    insert into public.member_roles (member_id, role_id)
    select v_member, r.id from public.roles r
    where r.code = 'VIEWER' and r.organization_id is null;
  end if;

  -- Administrador de plataforma
  insert into public.platform_admins (user_id, role_id)
  select v_admin, r.id from public.roles r
  where r.code = 'SUPER_ADMIN' and r.organization_id is null
  on conflict do nothing;
end $$;
