-- ============================================================================
-- 0072 · RLS de planes y facturación (fase 8.10)
-- ----------------------------------------------------------------------------
-- plans/plan_entitlements: catálogo público de lectura para cualquier
-- usuario autenticado (sin dato sensible) — sin INSERT/UPDATE para app_user,
-- solo is_system_context() (semilla de 0073 / administración futura).
-- subscriptions/usage_counters: SELECT is_member_of; sin INSERT/UPDATE para
-- app_user — se gestionan por services/entitlements.py en
-- session_for_system(), sin flujo de autoservicio de cambio de plan en V1.
-- billing_events: mismo patrón que domain_events, solo sistema escribe, el
-- comprador puede leer los propios.
-- ============================================================================

alter table public.plans enable row level security;

create policy plans_select
  on public.plans for select
  using (app.current_user_id() is not null);

create policy plans_system_context
  on public.plans for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.plan_entitlements enable row level security;

create policy plan_entitlements_select
  on public.plan_entitlements for select
  using (app.current_user_id() is not null);

create policy plan_entitlements_system_context
  on public.plan_entitlements for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.subscriptions enable row level security;

create policy subscriptions_select
  on public.subscriptions for select
  using (app.is_member_of(organization_id));

create policy subscriptions_system_context
  on public.subscriptions for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.usage_counters enable row level security;

create policy usage_counters_select
  on public.usage_counters for select
  using (app.is_member_of(organization_id));

create policy usage_counters_system_context
  on public.usage_counters for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.billing_events enable row level security;

create policy billing_events_select
  on public.billing_events for select
  using (app.is_member_of(organization_id));

create policy billing_events_system_context
  on public.billing_events for all
  using (app.is_system_context()) with check (app.is_system_context());
