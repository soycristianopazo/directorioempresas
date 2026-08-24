-- ============================================================================
-- 001 · RLS del dominio de identidad y multitenancy
-- ----------------------------------------------------------------------------
-- Punto de control 1 del roadmap: demostrar que la organización B no ve datos
-- de la A, con seis identidades distintas.
--
-- Ejecutar con:  npm run db:test
-- ============================================================================

begin;

create extension if not exists pgtap with schema extensions;
\i supabase/tests/helpers.sql

select plan(34);


-- ─── Preparación ────────────────────────────────────────────────────────────
select tests.clear_authentication();

-- Seis identidades:
--   ana    → dueña de Alfa
--   bruno  → miembro de Alfa sin permisos de gestión (VIEWER)
--   carla  → dueña de Beta (organización ajena)
--   diego  → miembro de Alfa Y de Beta (pertenencia múltiple, §48)
--   elena  → usuaria sin organización
--   admin  → SUPER_ADMIN de plataforma
select tests.create_user('ana@alfa.cl',   '11111111-1111-1111-1111-111111111111');
select tests.create_user('bruno@alfa.cl', '22222222-2222-2222-2222-222222222222');
select tests.create_user('carla@beta.cl', '33333333-3333-3333-3333-333333333333');
select tests.create_user('diego@mix.cl',  '44444444-4444-4444-4444-444444444444');
select tests.create_user('elena@sola.cl', '55555555-5555-5555-5555-555555555555');
select tests.create_user('admin@plat.cl', '66666666-6666-6666-6666-666666666666');


-- ─── El trigger de alta crea el perfil ──────────────────────────────────────
select is(
  (select count(*) from public.profiles
   where id in ('11111111-1111-1111-1111-111111111111',
                '55555555-5555-5555-5555-555555555555')),
  2::bigint,
  'on_auth_user_created crea el profile automáticamente'
);

select is(
  (select first_name from public.profiles where id = '11111111-1111-1111-1111-111111111111'),
  'ana',
  'el profile toma first_name desde raw_user_meta_data'
);


-- ─── Validación de RUT en la base, no solo en el frontend ───────────────────
select ok(app.is_valid_rut('76.086.428-5'),  'RUT válido con puntos y guion');
select ok(app.is_valid_rut('760864285'),     'RUT válido sin formato');
select ok(not app.is_valid_rut('76.086.428-9'), 'RUT con dígito verificador incorrecto se rechaza');
select ok(not app.is_valid_rut('abc'),       'RUT no numérico se rechaza');
select is(app.normalize_rut('76.086.428-5'), '76086428-5', 'normalize_rut deja el formato canónico');


-- ─── Creación de organizaciones vía RPC ─────────────────────────────────────
select tests.authenticate_as('11111111-1111-1111-1111-111111111111');

select lives_ok(
  $$ select public.create_organization('Transportes Alfa SpA', 'Alfa', '76.086.428-5',
                                       array['SUPPLIER','BUYER']::app.organization_capability[]) $$,
  'ana puede crear una organización'
);

select tests.clear_authentication();
create temporary table t_ids as
  select id as alfa_id from public.organizations where legal_name = 'Transportes Alfa SpA';

select is(
  (select count(*) from public.organization_members m
   join t_ids t on t.alfa_id = m.organization_id
   where m.user_id = '11111111-1111-1111-1111-111111111111' and m.status = 'ACTIVE'),
  1::bigint,
  'create_organization deja al creador como miembro activo'
);

select is(
  (select count(*) from public.member_roles mr
   join public.organization_members m on m.id = mr.member_id
   join public.roles r on r.id = mr.role_id
   join t_ids t on t.alfa_id = m.organization_id
   where m.user_id = '11111111-1111-1111-1111-111111111111' and r.code = 'ORG_OWNER'),
  1::bigint,
  'create_organization asigna el rol ORG_OWNER'
);

select is(
  (select slug from public.organizations o join t_ids t on t.alfa_id = o.id),
  'alfa',
  'el slug se deriva del nombre comercial'
);

select is(
  (select value from public.organization_legal_identifiers li
   join t_ids t on t.alfa_id = li.organization_id),
  '76086428-5',
  'el RUT se normaliza al guardarse'
);


-- Beta, de carla
select tests.authenticate_as('33333333-3333-3333-3333-333333333333');
select public.create_organization('Beta Minería Ltda', 'Beta', '77.777.777-7',
                                  array['BUYER']::app.organization_capability[]);
select tests.clear_authentication();

create temporary table t_beta as
  select id as beta_id from public.organizations where legal_name = 'Beta Minería Ltda';


-- Bruno entra a Alfa como VIEWER; diego entra a Alfa y a Beta.
insert into public.organization_members (user_id, organization_id, status)
select '22222222-2222-2222-2222-222222222222', alfa_id, 'ACTIVE' from t_ids;

insert into public.member_roles (member_id, role_id)
select m.id, r.id
from public.organization_members m
cross join public.roles r
join t_ids t on t.alfa_id = m.organization_id
where m.user_id = '22222222-2222-2222-2222-222222222222'
  and r.code = 'VIEWER' and r.organization_id is null;

insert into public.organization_members (user_id, organization_id, status)
select '44444444-4444-4444-4444-444444444444', alfa_id, 'ACTIVE' from t_ids;
insert into public.organization_members (user_id, organization_id, status)
select '44444444-4444-4444-4444-444444444444', beta_id, 'ACTIVE' from t_beta;

-- admin como SUPER_ADMIN de plataforma
insert into public.platform_admins (user_id, role_id)
select '66666666-6666-6666-6666-666666666666', r.id
from public.roles r where r.code = 'SUPER_ADMIN' and r.organization_id is null;


-- ============================================================================
-- AISLAMIENTO: el núcleo del punto de control 1
-- ============================================================================

-- ── carla (organización ajena) ──────────────────────────────────────────────
select tests.authenticate_as('33333333-3333-3333-3333-333333333333');

select is(
  (select count(*) from public.organizations o join t_ids t on t.alfa_id = o.id),
  0::bigint,
  'AISLAMIENTO · carla NO ve la organización Alfa (está en DRAFT/PRIVATE)'
);

select is(
  (select count(*) from public.organization_members m join t_ids t on t.alfa_id = m.organization_id),
  0::bigint,
  'AISLAMIENTO · carla NO ve los miembros de Alfa'
);

select is(
  (select count(*) from public.organization_legal_identifiers li
   join t_ids t on t.alfa_id = li.organization_id),
  0::bigint,
  'AISLAMIENTO · carla NO ve el RUT de Alfa (organización no activa)'
);

select is(
  (select count(*) from public.profiles where id = '11111111-1111-1111-1111-111111111111'),
  0::bigint,
  'AISLAMIENTO · carla NO ve el perfil de ana (no comparten organización)'
);

select ok(
  not app.is_member_of((select alfa_id from t_ids)),
  'AISLAMIENTO · is_member_of devuelve false para carla en Alfa'
);

select ok(
  not app.has_permission((select alfa_id from t_ids), 'organization.update'),
  'AISLAMIENTO · carla no tiene permisos sobre Alfa'
);


-- ── ana (dueña de Alfa) ─────────────────────────────────────────────────────
select tests.authenticate_as('11111111-1111-1111-1111-111111111111');

select is(
  (select count(*) from public.organizations o join t_ids t on t.alfa_id = o.id),
  1::bigint,
  'ana ve su organización'
);

select is(
  (select count(*) from public.organizations o join t_beta t on t.beta_id = o.id),
  0::bigint,
  'ana NO ve la organización de carla'
);

select ok(
  app.has_permission((select alfa_id from t_ids), 'organization.update'),
  'ORG_OWNER tiene organization.update'
);

select ok(
  app.has_permission((select alfa_id from t_ids), 'member.manage'),
  'ORG_OWNER tiene member.manage'
);

select is(
  (select count(*) from public.profiles where id = '22222222-2222-2222-2222-222222222222'),
  1::bigint,
  'ana ve el perfil de bruno porque comparten organización'
);


-- ── bruno (miembro sin permisos de gestión) ─────────────────────────────────
select tests.authenticate_as('22222222-2222-2222-2222-222222222222');

select is(
  (select count(*) from public.organizations o join t_ids t on t.alfa_id = o.id),
  1::bigint,
  'bruno ve la organización a la que pertenece'
);

select ok(
  app.has_permission((select alfa_id from t_ids), 'organization.read'),
  'VIEWER tiene organization.read'
);

select ok(
  not app.has_permission((select alfa_id from t_ids), 'organization.update'),
  'PERMISOS · VIEWER NO puede editar la organización'
);

select ok(
  not app.has_permission((select alfa_id from t_ids), 'member.manage'),
  'PERMISOS · VIEWER NO puede administrar miembros'
);

select throws_ok(
  $$ update public.organizations set legal_name = 'Secuestrada'
     where id = (select alfa_id from t_ids) $$,
  null,
  null,
  'PERMISOS · el UPDATE de un VIEWER no modifica ninguna fila'
);


-- ── diego (pertenencia múltiple, §48) ───────────────────────────────────────
select tests.authenticate_as('44444444-4444-4444-4444-444444444444');

select is(
  (select count(*) from public.organization_members
   where user_id = '44444444-4444-4444-4444-444444444444' and status = 'ACTIVE'),
  2::bigint,
  'MULTIEMPRESA · diego pertenece a dos organizaciones simultáneamente'
);

select is(
  (select count(*) from public.v_my_organizations),
  2::bigint,
  'MULTIEMPRESA · v_my_organizations devuelve ambas'
);

select lives_ok(
  $$ select public.switch_organization((select beta_id from t_beta)) $$,
  'MULTIEMPRESA · diego puede cambiar a Beta'
);


-- ── elena (sin organización) ────────────────────────────────────────────────
select tests.authenticate_as('55555555-5555-5555-5555-555555555555');

select is(
  (select count(*) from public.organizations),
  0::bigint,
  'AISLAMIENTO · elena no ve ninguna organización'
);

select is(
  (select count(*) from public.v_my_organizations),
  0::bigint,
  'elena no tiene organizaciones'
);

select throws_ok(
  $$ select public.switch_organization((select alfa_id from t_ids)) $$,
  'P0001',
  'No pertenece a esa organización',
  'switch_organization rechaza una organización ajena'
);


-- ── anónimo ─────────────────────────────────────────────────────────────────
select tests.authenticate_as_anon();

select is(
  (select count(*) from public.organizations),
  0::bigint,
  'AISLAMIENTO · anónimo no ve organizaciones no públicas'
);

select is(
  (select count(*) from public.organization_legal_identifiers),
  0::bigint,
  'PRIVACIDAD · anónimo nunca ve RUTs (anti-scraping)'
);


-- ── Perfil público: visible para anónimo cuando corresponde ─────────────────
select tests.clear_authentication();
update public.organizations
  set status = 'ACTIVE', visibility = 'PUBLIC'
  where id = (select alfa_id from t_ids);

select tests.authenticate_as_anon();

select is(
  (select count(*) from public.organizations o join t_ids t on t.alfa_id = o.id),
  1::bigint,
  'VISIBILIDAD · anónimo SÍ ve una organización ACTIVE + PUBLIC'
);

select is(
  (select count(*) from public.organization_legal_identifiers li
   join t_ids t on t.alfa_id = li.organization_id),
  0::bigint,
  'VISIBILIDAD · el RUT sigue oculto aunque el perfil sea público'
);


-- ── admin de plataforma ─────────────────────────────────────────────────────
select tests.authenticate_as('66666666-6666-6666-6666-666666666666');

select ok(app.is_platform_admin(), 'admin es reconocido como platform admin');

select is(
  (select count(*) from public.organizations),
  2::bigint,
  'el admin de plataforma ve todas las organizaciones'
);


-- ── Inmutabilidad de la auditoría ───────────────────────────────────────────
select tests.clear_authentication();

select throws_ok(
  $$ update public.audit_logs set action = 'manipulado' where true $$,
  null,
  null,
  'AUDITORÍA · audit_logs no admite UPDATE ni siquiera como superusuario'
);


select * from finish();
rollback;
