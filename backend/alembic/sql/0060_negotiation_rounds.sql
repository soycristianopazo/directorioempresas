-- ============================================================================
-- 0060 · Rondas de negociación (fase 8.5)
-- ----------------------------------------------------------------------------
-- round_type se restringe por CHECK a ('COUNTER','BAFO') — CLARIFICATION
-- (agregado al enum en 0059) queda deliberadamente fuera de esta tabla.
--
-- Razón: una aclaración no cambia el monto, no genera quotation_revision, y
-- no necesita "participantes que deben responder antes de un deadline con
-- una revisión" — es exactamente el modelo que ya existe (conversations/
-- messages de fase 7, services/messaging.py), scopeado al evento. Modelar
-- CLARIFICATION como una fila de negotiation_rounds cuyo
-- responded_quotation_revision_id nunca se llena sería una columna que
-- miente por diseño. Una aclaración se abre como una conversation (o
-- mensaje en la ya existente) con subject "Ronda de aclaraciones" — cero
-- tablas nuevas, reutiliza fase 7 tal cual.
--
-- negotiation_round_participants.responded_quotation_revision_id es el
-- puente hacia services/quotations.py::submit_revision(round_type=...): al
-- responder, el proveedor envía una quotation_revision normal (mismo flujo
-- de siempre) y el service marca esta fila con el id resultante.
-- ============================================================================

create table public.negotiation_rounds (
  id                     uuid primary key default gen_random_uuid(),
  sourcing_event_id      uuid not null references public.sourcing_events (id) on delete cascade,

  round_type             app.quotation_round_type not null,
  instructions           text,
  target_reduction_pct   numeric,
  deadline               timestamptz,

  opened_at              timestamptz not null default now(),
  opened_by              uuid references public.profiles (id) on delete set null,
  closed_at              timestamptz,
  closed_by              uuid references public.profiles (id) on delete set null,

  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  constraint negotiation_rounds_round_type check (round_type in ('COUNTER', 'BAFO'))
);

comment on table public.negotiation_rounds is
  'Ronda de recontraoferta/BAFO abierta por el comprador (fase 8.5). CLARIFICATION queda fuera a propósito — ver el encabezado de este archivo.';

create index negotiation_rounds_event_idx on public.negotiation_rounds (sourcing_event_id);

select app.apply_table_conventions('public.negotiation_rounds');


create table public.negotiation_round_participants (
  id                              uuid primary key default gen_random_uuid(),
  negotiation_round_id            uuid not null references public.negotiation_rounds (id) on delete cascade,
  supplier_organization_id        uuid not null references public.organizations (id) on delete cascade,

  responded_quotation_revision_id uuid references public.quotation_revisions (id) on delete set null,
  responded_at                    timestamptz,

  created_at                      timestamptz not null default now(),
  updated_at                      timestamptz not null default now(),

  constraint negotiation_round_participants_unique unique (negotiation_round_id, supplier_organization_id)
);

comment on table public.negotiation_round_participants is
  'Proveedores invitados a una ronda y su respuesta (fase 8.5). responded_quotation_revision_id queda NULL hasta que el proveedor envía su contraoferta vía services/quotations.py::submit_revision(round_type=...), que llama a mark_responded() en la misma transacción.';

create index negotiation_round_participants_round_idx on public.negotiation_round_participants (negotiation_round_id);
create index negotiation_round_participants_org_idx on public.negotiation_round_participants (supplier_organization_id);

select app.apply_table_conventions('public.negotiation_round_participants');
