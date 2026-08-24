-- ============================================================================
-- 0032 · Analítica de búsqueda y visitas
-- ----------------------------------------------------------------------------
-- Fase 4.7 del roadmap. Ver docs/02-MODELO-DATOS.md §204-207.
--
-- Cuatro tablas de solo-escritura-por-el-sistema (nunca por el cliente
-- directo): el visitante anónimo que dispara estos inserts no tiene permiso
-- propio para escribir nada — el sistema registra en su nombre, mismo
-- criterio que domain_events (0010_hardening.sql). Los agregados se leen por
-- endpoints propios, nunca por SELECT directo del cliente.
--
-- search_logs / profile_views / offering_views son de solo inserción — se
-- revoca UPDATE/DELETE, igual que audit_logs. search_impressions es la
-- excepción: es un agregado diario que se incrementa con
-- INSERT ... ON CONFLICT DO UPDATE, así que sí necesita UPDATE.
-- ============================================================================

create table public.search_logs (
  id                        uuid primary key default gen_random_uuid(),
  query_text                text,
  filters                   jsonb not null default '{}'::jsonb,
  result_count              integer not null,
  searching_organization_id uuid references public.organizations (id) on delete set null,
  created_at                timestamptz not null default now(),

  constraint search_logs_query_length check (char_length(coalesce(query_text, '')) <= 500)
);

comment on table public.search_logs is
  'Cada búsqueda en /discover o /api/discover/search: texto, filtros, nº de resultados. Base de "categorías más demandadas" y detección de gaps de oferta.';

create index search_logs_created_idx on public.search_logs (created_at desc);

revoke update, delete on public.search_logs from app_user;


create table public.search_impressions (
  id               uuid primary key default gen_random_uuid(),
  day              date not null default current_date,
  organization_id  uuid not null references public.organizations (id) on delete cascade,
  offering_id      uuid not null references public.supplier_offerings (id) on delete cascade,
  impression_count integer not null default 0,

  constraint search_impressions_unique unique (day, organization_id, offering_id)
);

comment on table public.search_impressions is
  'Apariciones agregadas por día de una oferta en resultados de búsqueda ("apareciste en 120 búsquedas"). Se incrementa con upsert, no una fila por impresión.';

create index search_impressions_org_idx on public.search_impressions (organization_id, day desc);


create table public.profile_views (
  id                       uuid primary key default gen_random_uuid(),
  organization_id          uuid not null references public.organizations (id) on delete cascade,
  viewer_organization_id   uuid references public.organizations (id) on delete set null,
  source                   text,
  visitor_hash             text,
  is_unique                boolean not null default true,
  created_at               timestamptz not null default now()
);

comment on table public.profile_views is
  'Visitas a /proveedores/{slug}. visitor_hash: identificador anónimo (cookie), usado solo para calcular is_unique por día — no es PII identificable.';

create index profile_views_org_idx on public.profile_views (organization_id, created_at desc);

revoke update, delete on public.profile_views from app_user;


create table public.offering_views (
  id                       uuid primary key default gen_random_uuid(),
  offering_id              uuid not null references public.supplier_offerings (id) on delete cascade,
  organization_id          uuid not null references public.organizations (id) on delete cascade,
  viewer_organization_id   uuid references public.organizations (id) on delete set null,
  visitor_hash             text,
  is_unique                boolean not null default true,
  created_at               timestamptz not null default now()
);

comment on table public.offering_views is
  'Visitas a una oferta específica dentro del perfil público. En esta pasada, "mostrada" cuenta como "vista" — no hay tracking de scroll/viewport todavía.';

create index offering_views_offering_idx on public.offering_views (offering_id, created_at desc);

revoke update, delete on public.offering_views from app_user;
