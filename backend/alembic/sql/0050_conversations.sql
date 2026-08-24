-- ============================================================================
-- 0050 · Mensajería (fase 7.8)
-- ----------------------------------------------------------------------------
-- Fase 7.8 del roadmap. Ver docs/02-MODELO-DATOS.md §D11.
--
-- Decisión de diseño (plan de fase 7): actualizaciones en vivo por POLLING,
-- no Supabase Realtime — confirmado que el frontend real de este proyecto
-- (frontend/) no tiene ninguna referencia a Supabase (sin anon key, sin
-- supabase-js) y que docs/RLS.md/docs/DATABASE.md ya documentan el abandono
-- de GoTrue/PostgREST por la misma razón (identidad propia vía
-- SET LOCAL, no auth.uid()). El frontend hace polling a
-- GET .../messages?after=<cursor> — esta migración no necesita nada especial
-- para eso, es una tabla y un índice por fecha, como cualquier otra.
--
-- context_type con FKs reales nullable (nunca un id polimórfico sin FK) —
-- mismo criterio que sourcing_event_criteria/accreditation_requirements. Se
-- omite CONTRACT del enum: no existe tabla contracts todavía (V2) — mismo
-- criterio de extender el enum hacia adelante cuando la tabla exista, no
-- antes (0040_sourcing_events.sql).
--
-- created_by_organization_id (no está en docs/02-MODELO-DATOS.md, es una
-- adición de este plan): sin ella la policy de INSERT no tiene nada propio
-- que verificar más que "algún participante" — que todavía no existe en el
-- momento de crear la fila. Se usa solo para el chequeo de creación; quién
-- puede LEER/escribir después lo decide conversation_participants.
-- ============================================================================

create type app.conversation_context_type as enum (
  'ORGANIZATION', 'OFFERING', 'REQUIREMENT', 'SOURCING_EVENT', 'QUOTATION'
);

create table public.conversations (
  id                        uuid primary key default gen_random_uuid(),
  context_type              app.conversation_context_type not null,

  organization_id           uuid references public.organizations (id),
  offering_id               uuid references public.supplier_offerings (id),
  requirement_id            uuid references public.requirements (id),
  sourcing_event_id         uuid references public.sourcing_events (id),
  quotation_id              uuid references public.quotations (id),

  created_by_organization_id uuid not null references public.organizations (id),

  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),
  created_by                uuid references public.profiles (id) on delete set null,
  updated_by                uuid references public.profiles (id) on delete set null,

  constraint conversations_context_ref check (
    (context_type = 'ORGANIZATION'   and organization_id is not null)
    or (context_type = 'OFFERING'       and offering_id is not null)
    or (context_type = 'REQUIREMENT'       and requirement_id is not null)
    or (context_type = 'SOURCING_EVENT'       and sourcing_event_id is not null)
    or (context_type = 'QUOTATION'               and quotation_id is not null)
  )
);

comment on table public.conversations is
  'Hilo con contexto tipado (§D11) — FK real por tipo, nunca polimórfico ciego. created_by_organization_id es quién abrió el hilo, usado solo por la policy de creación.';

create index conversations_sourcing_event_idx on public.conversations (sourcing_event_id) where sourcing_event_id is not null;
create index conversations_quotation_idx on public.conversations (quotation_id) where quotation_id is not null;

select app.apply_table_conventions('public.conversations');


create table public.conversation_participants (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  organization_id uuid not null references public.organizations (id) on delete cascade,

  added_at        timestamptz not null default now(),
  last_read_at    timestamptz,
  is_muted        boolean not null default false,

  constraint conversation_participants_unique unique (conversation_id, organization_id)
);

comment on table public.conversation_participants is
  'Organización participante del hilo (§D11). last_read_at es un cursor de conveniencia para "no leídos"; message_reads (append-only) es el registro granular por mensaje.';

create index conversation_participants_org_idx on public.conversation_participants (organization_id);


create table public.messages (
  id                     uuid primary key default gen_random_uuid(),
  conversation_id        uuid not null references public.conversations (id) on delete cascade,
  sender_id              uuid references public.profiles (id) on delete set null,
  sender_organization_id uuid references public.organizations (id),

  body                   text not null,
  is_system              boolean not null default false,

  created_at             timestamptz not null default now(),
  edited_at              timestamptz,
  deleted_at             timestamptz
);

comment on table public.messages is
  'Mensaje (§D11). sender_organization_id nulo + is_system=true = mensaje del sistema (ej. "invitación aceptada"), no de una organización.';

create index messages_conversation_idx on public.messages (conversation_id, created_at);


create table public.message_attachments (
  id           uuid primary key default gen_random_uuid(),
  message_id   uuid not null references public.messages (id) on delete cascade,

  name            text not null,
  storage_path    text not null,
  checksum_sha256 text not null,

  created_at      timestamptz not null default now()
);

comment on table public.message_attachments is 'Adjuntos con metadatos y checksum (§D11).';

create index message_attachments_message_idx on public.message_attachments (message_id);


create table public.message_reads (
  message_id  uuid not null references public.messages (id) on delete cascade,
  reader_id   uuid not null references public.profiles (id) on delete cascade,
  read_at     timestamptz not null default now(),

  primary key (message_id, reader_id)
);

comment on table public.message_reads is 'Lecturas por participante (§D11), append-only por naturaleza (una lectura no se deshace).';
