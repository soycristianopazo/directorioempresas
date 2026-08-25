-- ============================================================================
-- 0075 · Fix: conversations.created_by_organization_id sin cascada (fase 7, bug real)
-- ----------------------------------------------------------------------------
-- Bug real encontrado en vivo corriendo seed.py: wipe_existing() borra las
-- organizaciones de prueba para poder correr el seed repetidas veces, pero
-- conversations.created_by_organization_id (0050_conversations.sql) se
-- declaró `references public.organizations (id)` sin `on delete cascade` —
-- mismo patrón de gotcha ya documentado para quotation_items/
-- quotation_responses en fase 7 (docs/RLS.md, bug #2: "sin on delete
-- cascade hacia sus FK secundarias"), esta vez sobre conversations en vez de
-- quotation_items. Cualquier conversación real creada durante una sesión de
-- verificación en el navegador deja a wipe_existing() incapaz de borrar la
-- organización: "update or delete on table organizations violates foreign
-- key constraint conversations_created_by_organization_id_fkey".
-- ============================================================================

alter table public.conversations
  drop constraint conversations_created_by_organization_id_fkey;

alter table public.conversations
  add constraint conversations_created_by_organization_id_fkey
  foreign key (created_by_organization_id) references public.organizations (id)
  on delete cascade;
