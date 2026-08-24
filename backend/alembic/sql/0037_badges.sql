-- ============================================================================
-- 0037 · Badges de confianza
-- ----------------------------------------------------------------------------
-- Fase 5.9 del roadmap. Ver docs/01-ARQUITECTURA.md §F.6.
--
-- Las reglas son DATOS (rule_expression jsonb), evaluadas por un evaluador
-- determinístico en services/badges.py — nunca badges hardcodeados en
-- Python, nunca badges comprables (is_sponsored siempre false para los de
-- confianza, sembrado explícito por fila, no un default silencioso).
-- ============================================================================

create table public.badge_definitions (
  id              uuid primary key default gen_random_uuid(),
  code            text not null unique,
  name            text not null,
  description     text,
  icon            text,
  rule_expression jsonb not null,
  is_automatic    boolean not null default true,
  validity_days   integer,
  is_sponsored    boolean not null default false,
  is_active       boolean not null default true,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.badge_definitions is
  'rule_expression: {"all": [{"fact": "...", "op": "=|>=|...", "value": ...}]} — evaluado por services/badges.py::evaluate_badges_for_org(), nunca en código. Facts reconocidos en esta fase: accreditation.<program_code>.status, documents.expired_count. supplier_score.total (fase 6) queda como fact válido pero no resoluble todavía.';

select app.apply_table_conventions('public.badge_definitions');


create table public.organization_badges (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  badge_id        uuid not null references public.badge_definitions (id),

  granted_at      timestamptz not null default now(),
  expires_at      timestamptz,
  evidence        jsonb not null default '{}'::jsonb,
  granted_by      uuid references public.profiles (id) on delete set null,
  revoked_at      timestamptz,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.organization_badges is
  'Badge otorgado. granted_by nulo = otorgado automáticamente por el evaluador. Lectura pública (es la señal de confianza que se muestra en /proveedores/{slug}) — nunca la otorga el cliente directo, siempre services/badges.py tras una decisión de revisor.';

create index organization_badges_org_idx on public.organization_badges (organization_id) where revoked_at is null;

-- Como mucho un otorgamiento ACTIVO (no revocado) por (organización, badge)
-- a la vez — evita duplicados si el evaluador corre más de una vez.
create unique index organization_badges_active_unique
  on public.organization_badges (organization_id, badge_id)
  where revoked_at is null;

select app.apply_table_conventions('public.organization_badges');


-- Seed: badges automáticos de esta fase.
insert into public.badge_definitions (code, name, description, icon, rule_expression, is_automatic, validity_days) values
  (
    'ACREDITADO_BASE',
    'Proveedor Acreditado',
    'Completó y aprobó la Acreditación Base de la plataforma.',
    'shield-check',
    '{"all": [{"fact": "accreditation.ACREDITACION_BASE.status", "op": "=", "value": "ACCREDITED"}]}'::jsonb,
    true, 365
  ),
  (
    'DOCUMENTACION_AL_DIA',
    'Documentación al día',
    'Ningún documento del repositorio de evidencia está vencido.',
    'file-check',
    '{"all": [{"fact": "documents.expired_count", "op": "=", "value": 0}]}'::jsonb,
    true, null
  ),
  (
    'CONFIANZA_PLATAFORMA',
    'Confianza de la plataforma',
    'Acreditado y con toda su documentación vigente.',
    'badge-check',
    '{"all": [
        {"fact": "accreditation.ACREDITACION_BASE.status", "op": "=", "value": "ACCREDITED"},
        {"fact": "documents.expired_count", "op": "=", "value": 0}
      ]}'::jsonb,
    true, 180
  )
on conflict (code) do nothing;
