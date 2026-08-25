-- ============================================================================
-- 0073 · Semilla de planes (fase 8.10)
-- ----------------------------------------------------------------------------
-- Migración de DATOS, no de esquema — mismo criterio que la semilla
-- ACREDITACION_BASE (0035): el catálogo de planes es estructural (las
-- policies/entitlements dependen de que existan), no un dato de desarrollo,
-- así que va en una migración y no en backend/seed.py. No toca
-- `subscriptions`: esas se asignan en seed.py, porque dependen de
-- `organizations` ya sembradas por la app (con IDs generados en tiempo de
-- ejecución), no por SQL puro.
-- ============================================================================

insert into public.plans (code, name, description, monthly_price, currency_code, sort_order) values
  ('FREE',       'Gratuito',   'Para empezar a explorar la plataforma',            0,      'CLP', 1),
  ('PRO',        'Pro',        'Para equipos de abastecimiento en operación activa', 490000, 'CLP', 2),
  ('ENTERPRISE', 'Enterprise', 'Sin límites, para organizaciones grandes',          null,   null,  3)
on conflict (code) do nothing;

insert into public.plan_entitlements (plan_id, feature_code, is_unlimited, limit_value, limit_period)
select p.id, e.feature_code, e.is_unlimited, e.limit_value, e.limit_period
from public.plans p
join (values
  ('FREE',       'requirement.create',    false, 3,    'MONTH'),
  ('FREE',       'sourcing_event.create', false, 1,    'MONTH'),
  ('FREE',       'team.member',           false, 3,    'TOTAL'),
  ('PRO',        'requirement.create',    false, 50,   'MONTH'),
  ('PRO',        'sourcing_event.create', false, 20,   'MONTH'),
  ('PRO',        'team.member',           false, 15,   'TOTAL'),
  ('ENTERPRISE', 'requirement.create',    true,  null, 'MONTH'),
  ('ENTERPRISE', 'sourcing_event.create', true,  null, 'MONTH'),
  ('ENTERPRISE', 'team.member',           true,  null, 'TOTAL')
) as e(plan_code, feature_code, is_unlimited, limit_value, limit_period)
  on e.plan_code = p.code
on conflict (plan_id, feature_code) do nothing;
