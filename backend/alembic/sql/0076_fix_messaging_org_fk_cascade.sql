-- ============================================================================
-- 0076 · Fix: más FK de mensajería sin cascada hacia organizations (fase 7, bug real)
-- ----------------------------------------------------------------------------
-- Continuación de 0075: wipe_existing() (seed.py) seguía sin poder borrar
-- una organización de prueba con una conversación real encima, ahora por
-- conversations.organization_id (el contexto tipado, nullable) y
-- messages.sender_organization_id (nullable) — mismas dos columnas de
-- 0050_conversations.sql que quedaron sin `on delete cascade` cuando se
-- escribió esa migración, mismo motivo que created_by_organization_id.
-- ============================================================================

alter table public.conversations
  drop constraint conversations_organization_id_fkey;

alter table public.conversations
  add constraint conversations_organization_id_fkey
  foreign key (organization_id) references public.organizations (id)
  on delete cascade;

alter table public.messages
  drop constraint messages_sender_organization_id_fkey;

alter table public.messages
  add constraint messages_sender_organization_id_fkey
  foreign key (sender_organization_id) references public.organizations (id)
  on delete cascade;
