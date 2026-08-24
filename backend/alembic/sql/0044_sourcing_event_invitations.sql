-- ============================================================================
-- 0044 · Invitaciones a proveedores (fase 7.1)
-- ----------------------------------------------------------------------------
-- Fase 7.1 del roadmap. Ver docs/02-MODELO-DATOS.md §D8, docs/01-ARQUITECTURA.md §G.1.
--
-- Máquina de 11 estados, tomada del propio diseño (§G.1): INVITED → VIEWED →
-- NDA_ACCEPTED → INTERESTED → PARTICIPATING → QUOTED, más DECLINED/
-- NO_RESPONSE/WITHDRAWN/DISQUALIFIED/EXPIRED. Los estados posteriores a QUOTED
-- del diagrama original (SHORTLISTED/NEGOTIATING/AWARDED/NOT_AWARDED)
-- dependen de evaluación y adjudicación — fase 8, no existe esa
-- infraestructura todavía — mismo criterio ya escrito en
-- 0040_sourcing_events.sql para sourcing_event_status: el enum se extiende
-- hacia adelante cuando esas fases lleguen, no se inventan estados que nada
-- puede alcanzar hoy.
--
-- app.sourcing_invitation_status es un tipo NUEVO — no reutiliza
-- app.invitation_status (0005_rbac.sql), que es para invitaciones de
-- miembros de equipo, un concepto no relacionado.
--
-- Transición-como-dato + validador + service, mismo patrón que
-- accreditation_status_transitions/is_valid_transition()/_transition()
-- (0035/0036_accreditation*.sql, services/accreditation.py).
-- ============================================================================

create type app.sourcing_invitation_status as enum (
  'INVITED', 'VIEWED', 'NDA_ACCEPTED', 'INTERESTED', 'PARTICIPATING', 'QUOTED',
  'DECLINED', 'NO_RESPONSE', 'WITHDRAWN', 'DISQUALIFIED', 'EXPIRED'
);
create type app.sourcing_invitation_source as enum ('MATCH', 'MANUAL', 'LIST', 'PUBLIC_APPLY');

create table public.sourcing_event_invitations (
  id                        uuid primary key default gen_random_uuid(),
  sourcing_event_id         uuid not null references public.sourcing_events (id) on delete cascade,
  supplier_organization_id  uuid not null references public.organizations (id) on delete cascade,

  status                    app.sourcing_invitation_status not null default 'INVITED',
  source                    app.sourcing_invitation_source not null default 'MANUAL',
  match_score_snapshot      numeric,

  invited_at                timestamptz not null default now(),
  viewed_at                 timestamptz,
  responded_at              timestamptz,
  decline_reason_code       text,

  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),
  created_by                uuid references public.profiles (id) on delete set null,
  updated_by                uuid references public.profiles (id) on delete set null,

  constraint sourcing_event_invitations_unique unique (sourcing_event_id, supplier_organization_id)
);

comment on table public.sourcing_event_invitations is
  'Participación de un proveedor en un sourcing_event (§20/§G.1). match_score_snapshot congela el score de matching al momento de invitar (fase 6), si source=MATCH — no se recalcula después.';

create index sourcing_event_invitations_event_idx on public.sourcing_event_invitations (sourcing_event_id);
create index sourcing_event_invitations_org_idx on public.sourcing_event_invitations (supplier_organization_id);

select app.apply_table_conventions('public.sourcing_event_invitations');


create table public.sourcing_event_invitation_transitions (
  from_status  app.sourcing_invitation_status not null,
  to_status    app.sourcing_invitation_status not null,
  label        text not null,

  primary key (from_status, to_status)
);

comment on table public.sourcing_event_invitation_transitions is
  'Transiciones válidas de sourcing_event_invitations.status, como datos — mismo criterio que accreditation_status_transitions. services/invitations.py consulta esta tabla antes de cualquier cambio de estado.';

insert into public.sourcing_event_invitation_transitions (from_status, to_status, label) values
  ('INVITED',       'VIEWED',        'Ver invitación'),
  ('VIEWED',        'NDA_ACCEPTED',  'Aceptar NDA'),
  ('VIEWED',        'INTERESTED',    'Marcar interés (sin NDA exigido)'),
  ('NDA_ACCEPTED',  'INTERESTED',    'Marcar interés'),
  ('INTERESTED',    'PARTICIPATING', 'Confirmar participación'),
  ('PARTICIPATING', 'QUOTED',        'Cotización enviada'),
  ('QUOTED',        'PARTICIPATING', 'Reabrir tras reenvío de cotización'),
  ('INVITED',       'DECLINED',      'Declinar'),
  ('VIEWED',        'DECLINED',      'Declinar'),
  ('NDA_ACCEPTED',  'DECLINED',      'Declinar'),
  ('INTERESTED',    'DECLINED',      'Declinar'),
  ('PARTICIPATING', 'WITHDRAWN',     'Retirarse'),
  ('QUOTED',        'WITHDRAWN',     'Retirarse'),
  ('INVITED',       'NO_RESPONSE',   'Plazo vencido sin respuesta'),
  ('VIEWED',        'NO_RESPONSE',   'Plazo vencido sin respuesta'),
  ('INVITED',       'EXPIRED',       'Evento cerrado sin respuesta'),
  ('VIEWED',        'EXPIRED',       'Evento cerrado sin respuesta'),
  ('NDA_ACCEPTED',  'EXPIRED',       'Evento cerrado sin respuesta'),
  ('INTERESTED',    'EXPIRED',       'Evento cerrado sin respuesta'),
  ('INVITED',       'DISQUALIFIED',  'Descalificar'),
  ('VIEWED',        'DISQUALIFIED',  'Descalificar'),
  ('NDA_ACCEPTED',  'DISQUALIFIED',  'Descalificar'),
  ('INTERESTED',    'DISQUALIFIED',  'Descalificar'),
  ('PARTICIPATING', 'DISQUALIFIED',  'Descalificar'),
  ('QUOTED',        'DISQUALIFIED',  'Descalificar')
on conflict (from_status, to_status) do nothing;


create table public.invitation_status_history (
  id             uuid primary key default gen_random_uuid(),
  invitation_id  uuid not null references public.sourcing_event_invitations (id) on delete cascade,
  from_status    app.sourcing_invitation_status,
  to_status      app.sourcing_invitation_status not null,
  actor_id       uuid references public.profiles (id) on delete set null,
  reason         text,
  created_at     timestamptz not null default now()
);

comment on table public.invitation_status_history is
  'Append-only: cada transición con actor, motivo y timestamp. Base de la analítica de tasa de respuesta (§D8). actor_id nulo = transición automática (ej. expiración de plazo).';

create index invitation_status_history_invitation_idx
  on public.invitation_status_history (invitation_id, created_at desc);

revoke update, delete on public.invitation_status_history from app_user;


-- ============================================================================
-- app.has_active_sourcing_invitation — cierra un vacío real de fase 6: hoy
-- ningún proveedor invitado puede leer el evento al que fue invitado (0043
-- solo da SELECT al comprador dueño). Se reutiliza en 0048 (visibilidad del
-- evento para el invitado), en el gate ALL_PARTICIPANTS de Q&A (0046/0048), y
-- en la policy de inserción de quotation_revisions (0049).
-- ============================================================================

create or replace function app.has_active_sourcing_invitation(p_sourcing_event_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.sourcing_event_invitations sei
    where sei.sourcing_event_id = p_sourcing_event_id
      and app.is_member_of(sei.supplier_organization_id)
      and sei.status not in ('WITHDRAWN', 'DISQUALIFIED', 'EXPIRED', 'DECLINED', 'NO_RESPONSE')
  );
$$;

grant execute on function app.has_active_sourcing_invitation(uuid) to app_user;

comment on function app.has_active_sourcing_invitation(uuid) is
  '¿El usuario actual pertenece a un proveedor con invitación viva (no retirada/descalificada/expirada/declinada/sin respuesta) en este evento? Base de la visibilidad del proveedor invitado sobre el evento, Q&A y elegibilidad para cotizar.';
