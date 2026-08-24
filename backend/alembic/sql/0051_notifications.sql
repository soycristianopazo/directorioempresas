-- ============================================================================
-- 0051 · Notificaciones (fase 7.9)
-- ----------------------------------------------------------------------------
-- Fase 7.9 del roadmap. Ver docs/02-MODELO-DATOS.md §D11.
--
-- Sin domain_events: esa tabla existe desde fase 0/1 pero no tiene ningún
-- productor ni consumidor en todo el código (confirmado por exploración) —
-- construir el mecanismo de outbox completo para un solo caso de uso es la
-- abstracción prematura que este proyecto evita. services/invitations.py,
-- services/qa.py y services/quotations.py escriben directo a notifications
-- en el momento del evento de negocio, vía un bloque session_for_system()
-- corto (la fila es para OTRO usuario, no el actor de la transacción —
-- ver docs/RLS.md, lista de usos legítimos de contexto de sistema).
--
-- Canal email queda completamente stub en notification_deliveries — misma
-- desviación ya aceptada en fase 5.10 (falta decidir proveedor externo).
-- Solo el canal IN_APP es funcional en esta fase.
--
-- entity_type/entity_id sin FK tipada (a diferencia de conversations, que sí
-- usa FKs reales): una notificación sigue teniendo sentido aunque la entidad
-- referenciada ya no exista (el usuario ve "tu cotización fue evaluada" aun
-- si el evento se archivó después) — es exactamente el mismo criterio que ya
-- usa domain_events.aggregate_type/aggregate_id para el mismo problema.
-- ============================================================================

create type app.notification_priority as enum ('LOW', 'NORMAL', 'HIGH');
create type app.notification_channel as enum ('IN_APP', 'EMAIL');
create type app.notification_delivery_status as enum ('PENDING', 'SENT', 'FAILED');

create table public.notifications (
  id            uuid primary key default gen_random_uuid(),
  recipient_id  uuid not null references public.profiles (id) on delete cascade,

  type          text not null,
  title         text not null,
  body          text,
  entity_type   text,
  entity_id     uuid,
  action_url    text,
  priority      app.notification_priority not null default 'NORMAL',

  read_at       timestamptz,
  created_at    timestamptz not null default now()
);

comment on table public.notifications is
  'Notificación in-app (§D11). Escrita directo por el service que dispara el evento de negocio (invitación enviada, pregunta respondida, cotización recibida, ofertas abiertas) — sin domain_events de por medio en esta fase.';

create index notifications_recipient_idx on public.notifications (recipient_id, created_at desc);
create index notifications_recipient_unread_idx on public.notifications (recipient_id) where read_at is null;


create table public.notification_preferences (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.profiles (id) on delete cascade,

  channel    app.notification_channel not null,
  event_type text not null,
  enabled    boolean not null default true,

  constraint notification_preferences_unique unique (user_id, channel, event_type)
);

comment on table public.notification_preferences is 'Preferencias por tipo de evento y canal (§D11), autoservicio del usuario.';


create table public.notification_deliveries (
  id                 uuid primary key default gen_random_uuid(),
  notification_id    uuid not null references public.notifications (id) on delete cascade,

  channel              app.notification_channel not null,
  status               app.notification_delivery_status not null default 'PENDING',
  provider_message_id  text,
  attempted_at         timestamptz,
  sent_at              timestamptz,
  error                text
);

comment on table public.notification_deliveries is
  'Envío por canal (§D11). Preparado para push/WhatsApp sin cambiar el modelo — solo IN_APP tiene un consumidor real hoy; EMAIL queda stub hasta decidir proveedor externo (misma desviación de fase 5.10).';

create index notification_deliveries_notification_idx on public.notification_deliveries (notification_id);
