-- ============================================================================
-- 0071 · Planes, entitlements, suscripciones y contadores de uso (fase 8.10)
-- ----------------------------------------------------------------------------
-- Sin pasarela de pago en V1 (confirmado: sin Stripe/Flow/Transbank en
-- ningún docs/*.md) — "facturación manual" es la desviación V1 aceptada,
-- mismo criterio que jobs/email real quedó fuera en fase 5/7.
-- subscriptions/usage_counters se gestionan por services/entitlements.py
-- corriendo en session_for_system(), nunca por autoservicio del cliente.
-- ============================================================================

create type app.subscription_status as enum ('TRIAL', 'ACTIVE', 'PAST_DUE', 'CANCELLED');

create table public.plans (
  id              uuid primary key default gen_random_uuid(),
  code            text not null unique,
  name            text not null,
  description     text,
  monthly_price   numeric,
  currency_code   char(3) references public.currencies (code),
  is_active       boolean not null default true,
  sort_order      int not null default 0,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.plans is
  'Catálogo de planes (fase 8.10) — FREE/PRO/ENTERPRISE, sembrados en 0073. monthly_price es informativo (sin cobro automático en V1).';

select app.apply_table_conventions('public.plans');


create table public.plan_entitlements (
  id             uuid primary key default gen_random_uuid(),
  plan_id        uuid not null references public.plans (id) on delete cascade,

  feature_code   text not null,
  is_unlimited   boolean not null default false,
  limit_value    int,
  limit_period   text not null default 'MONTH',

  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),

  constraint plan_entitlements_unique unique (plan_id, feature_code),
  constraint plan_entitlements_period check (limit_period in ('MONTH', 'TOTAL')),
  constraint plan_entitlements_limit check (is_unlimited or limit_value is not null)
);

comment on table public.plan_entitlements is
  'Límite de un plan para una feature (fase 8.10) — feature_code es texto libre coordinado con services/entitlements.py (ej. "requirement.create", "sourcing_event.create", "team.member"), no un permission_code de RBAC (son conceptos distintos: RBAC decide SI un usuario puede intentar la acción, entitlements decide si la ORGANIZACIÓN ya se quedó sin cupo). limit_period MONTH resetea vía period_key en usage_counters; TOTAL es un tope de por vida (ej. cantidad de miembros de equipo).';

select app.apply_table_conventions('public.plan_entitlements');


create table public.subscriptions (
  id                     uuid primary key default gen_random_uuid(),
  organization_id        uuid not null references public.organizations (id) on delete cascade,
  plan_id                uuid not null references public.plans (id),

  status                 app.subscription_status not null default 'TRIAL',
  current_period_start   date,
  current_period_end     date,

  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  constraint subscriptions_unique unique (organization_id)
);

comment on table public.subscriptions is
  'Suscripción vigente de una organización (fase 8.10) — una fila por organización, mutable (cambio de plan sobrescribe, no hay historial de suscripciones en V1). Gestionada por services/entitlements.py/billing.py en session_for_system(), sin flujo de autoservicio de cambio de plan.';

create index subscriptions_plan_idx on public.subscriptions (plan_id);

select app.apply_table_conventions('public.subscriptions');


create table public.usage_counters (
  id                uuid primary key default gen_random_uuid(),
  organization_id   uuid not null references public.organizations (id) on delete cascade,

  feature_code      text not null,
  period_key        text not null,
  count             int not null default 0,

  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),

  constraint usage_counters_unique unique (organization_id, feature_code, period_key),
  constraint usage_counters_count check (count >= 0)
);

comment on table public.usage_counters is
  'Contador de uso por organización × feature × periodo (fase 8.10). period_key es "TOTAL" para límites de por vida o "YYYY-MM" para límites mensuales, según plan_entitlements.limit_period. services/entitlements.py hace upsert idempotente (on conflict do update set count = count + 1), mismo criterio de atomicidad que la secuencia de 0053.';

create index usage_counters_org_idx on public.usage_counters (organization_id);

select app.apply_table_conventions('public.usage_counters');


create table public.billing_events (
  id               uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references public.organizations (id) on delete cascade,

  type             text not null,
  payload          jsonb,

  created_at       timestamptz not null default now()
);

comment on table public.billing_events is
  'Bitácora de eventos de facturación (fase 8.10) — mismo patrón que domain_events (0010): solo el sistema escribe, el comprador puede leer los propios.';

create index billing_events_org_idx on public.billing_events (organization_id, created_at desc);

revoke update, delete on public.billing_events from app_user;
