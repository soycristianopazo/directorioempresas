-- ============================================================================
-- 0068 · RLS de Vendor List / AVL (fase 8.8)
-- ----------------------------------------------------------------------------
-- Mismo patrón exacto que supplier_lists/supplier_list_items (0033):
-- vendor_list.read/vendor_list.manage, ya sembrados desde fase 1 y ya
-- reutilizados en fase 4 (el propio comentario de 0033 dice que se
-- sembraron "para esta fase" en referencia a la AVL). Sin policy de
-- proveedor en absoluto, ni siquiera de solo lectura — buyer_supplier_
-- relationships es una herramienta interna del comprador, nunca visible a
-- la organización calificada.
-- ============================================================================

alter table public.buyer_supplier_relationships enable row level security;

create policy buyer_supplier_relationships_select
  on public.buyer_supplier_relationships for select
  using (app.has_permission(buyer_organization_id, 'vendor_list.read'));

create policy buyer_supplier_relationships_write
  on public.buyer_supplier_relationships for all
  using (app.has_permission(buyer_organization_id, 'vendor_list.manage'))
  with check (app.has_permission(buyer_organization_id, 'vendor_list.manage'));

create policy buyer_supplier_relationships_system_context
  on public.buyer_supplier_relationships for all
  using (app.is_system_context()) with check (app.is_system_context());


alter table public.buyer_supplier_notes enable row level security;

create policy buyer_supplier_notes_select
  on public.buyer_supplier_notes for select
  using (
    exists (
      select 1 from public.buyer_supplier_relationships r
      where r.id = relationship_id and app.has_permission(r.buyer_organization_id, 'vendor_list.read')
    )
  );

create policy buyer_supplier_notes_insert
  on public.buyer_supplier_notes for insert
  with check (
    exists (
      select 1 from public.buyer_supplier_relationships r
      where r.id = relationship_id and app.has_permission(r.buyer_organization_id, 'vendor_list.manage')
    )
  );

create policy buyer_supplier_notes_system_context
  on public.buyer_supplier_notes for all
  using (app.is_system_context()) with check (app.is_system_context());
