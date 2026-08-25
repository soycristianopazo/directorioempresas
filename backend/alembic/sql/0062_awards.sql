-- ============================================================================
-- 0062 · Adjudicación: awards, award_items, award_approvals, políticas (fase 8.6)
-- ----------------------------------------------------------------------------
-- Mecanismo de dos capas (plan de fase 8, Decisión 4):
--
-- organization_approval_policies decide CUÁNTOS pasos hacen falta y QUÉ ROL
-- requiere cada uno, según el monto — todas las políticas cuyo rango
-- [min_amount, max_amount) cubre awards.amount_base, ordenadas por
-- step_order, generan cada una su propia fila en award_approvals. Los
-- montos de min_amount/max_amount están en la MISMA moneda base que
-- awards.amount_base (la moneda base del evento, igual que
-- quotation_revisions.total_amount_base) — sin columna de moneda propia
-- para no reintroducir una conversión donde el monto ya llega convertido.
--
-- organization_members.approval_limit_amount (0005_rbac.sql, YA EXISTE)
-- decide QUÉ MIEMBRO CONCRETO, entre los que tienen el rol requerido por un
-- paso, puede efectivamente resolverlo: services/awards.py busca, para cada
-- paso, el miembro con ese required_role_code cuyo approval_limit_amount >=
-- amount_base, desempatando por "el de menor límite suficiente". Si CERO
-- pasos aplican, el award queda APPROVED de inmediato (no se fuerza
-- burocracia donde la organización no la configuró). required_role_code es
-- texto plano, no FK a roles.id: roles.code NO es único globalmente (solo
-- entre roles de sistema, ver 0005) y un award puede necesitar apuntar a un
-- rol de sistema por su código sin acoplarse a una fila concreta.
-- ============================================================================

create type app.award_status as enum ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'PUBLISHED');
create type app.approval_status as enum ('PENDING', 'APPROVED', 'REJECTED');

create table public.organization_approval_policies (
  id                  uuid primary key default gen_random_uuid(),
  organization_id     uuid not null references public.organizations (id) on delete cascade,

  step_order          int not null,
  required_role_code  text not null,
  min_amount          numeric not null default 0,
  max_amount          numeric,

  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  constraint organization_approval_policies_range check (max_amount is null or max_amount > min_amount),
  constraint organization_approval_policies_min check (min_amount >= 0)
);

comment on table public.organization_approval_policies is
  'Cadena de aprobación (DoA) de una organización (fase 8.6). Cada fila es un paso potencial: si amount_base cae en [min_amount, max_amount), ese paso aplica. Varias filas pueden aplicar a la vez (montos altos suman pasos, no solo escalan uno) — services/awards.py las ordena por step_order.';

create index organization_approval_policies_org_idx on public.organization_approval_policies (organization_id, step_order);

select app.apply_table_conventions('public.organization_approval_policies');


create table public.awards (
  id                        uuid primary key default gen_random_uuid(),
  sourcing_event_id         uuid not null references public.sourcing_events (id) on delete cascade,
  awarded_organization_id   uuid not null references public.organizations (id) on delete cascade,
  quotation_revision_id     uuid not null references public.quotation_revisions (id),

  status                    app.award_status not null default 'DRAFT',
  justification             text,

  currency_code             char(3) not null references public.currencies (code),
  amount                    numeric not null,
  amount_base               numeric not null,

  proposed_at               timestamptz not null default now(),
  proposed_by               uuid references public.profiles (id) on delete set null,
  decided_at                timestamptz,
  published_at              timestamptz,
  published_by              uuid references public.profiles (id) on delete set null,

  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),

  constraint awards_amount check (amount >= 0 and amount_base >= 0)
);

comment on table public.awards is
  'Propuesta de adjudicación a un proveedor (fase 8.6), sobre la revisión de cotización elegida. amount_base en la moneda base del evento — mismo criterio que quotation_revisions.total_amount_base, es lo que se compara contra organization_approval_policies.';

create index awards_event_idx on public.awards (sourcing_event_id);
create index awards_org_idx on public.awards (awarded_organization_id);

select app.apply_table_conventions('public.awards');


create table public.award_items (
  id                       uuid primary key default gen_random_uuid(),
  award_id                 uuid not null references public.awards (id) on delete cascade,
  sourcing_event_item_id   uuid not null references public.sourcing_event_items (id) on delete cascade,
  quotation_item_id        uuid references public.quotation_items (id),

  quantity                 numeric not null,
  unit_price               numeric not null,
  line_total               numeric not null,

  created_at               timestamptz not null default now(),

  constraint award_items_amounts check (quantity > 0 and unit_price >= 0 and line_total >= 0)
);

comment on table public.award_items is
  'Línea a línea de lo adjudicado (fase 8.6), copiado de la revisión de cotización elegida al proponer el award — igual que quotation_items congela su cotización, esto congela el award, sin releer la cotización después.';

create index award_items_award_idx on public.award_items (award_id);

revoke update, delete on public.award_items from app_user;


create table public.award_approvals (
  id                     uuid primary key default gen_random_uuid(),
  award_id               uuid not null references public.awards (id) on delete cascade,

  step_order             int not null,
  required_role_code     text not null,
  approver_member_id     uuid not null references public.organization_members (id) on delete cascade,

  status                 app.approval_status not null default 'PENDING',
  decided_at             timestamptz,
  comment                text,

  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  constraint award_approvals_unique unique (award_id, step_order)
);

comment on table public.award_approvals is
  'Un paso resuelto de la cadena de aprobación (fase 8.6). approver_member_id es el organization_member CONCRETO elegido por services/awards.py (el de menor approval_limit_amount que igual alcanza el monto) — nadie más puede decidir este paso, ni siquiera otro miembro con el mismo rol (autoservicio estricto en RLS, 0063).';

create index award_approvals_award_idx on public.award_approvals (award_id);
create index award_approvals_approver_idx on public.award_approvals (approver_member_id);

select app.apply_table_conventions('public.award_approvals');
