-- ============================================================================
-- 0067 · Vendor List / AVL — buyer_supplier_relationships (fase 8.8)
-- ----------------------------------------------------------------------------
-- Genuinamente distinta de supplier_lists/supplier_list_items (fase 4,
-- 0031): esas son listas simples guardadas/favoritas, sin ciclo de vida ni
-- semántica de relación. buyer_supplier_relationships tiene un status real
-- (POTENTIAL/IN_EVALUATION/APPROVED/CONDITIONAL/SUSPENDED/BLOCKED) que
-- alimenta directamente accreditation_fit y el filtro de Recall (Etapa 1)
-- del motor de matching — ver el TODO explícito en
-- services/matching.py::compute_accreditation_fit() (0041/fase 6), que esta
-- fase cierra.
-- ============================================================================

create type app.avl_status as enum (
  'POTENTIAL', 'IN_EVALUATION', 'APPROVED', 'CONDITIONAL', 'SUSPENDED', 'BLOCKED'
);

create table public.buyer_supplier_relationships (
  id                        uuid primary key default gen_random_uuid(),
  buyer_organization_id     uuid not null references public.organizations (id) on delete cascade,
  supplier_organization_id  uuid not null references public.organizations (id) on delete cascade,

  status                    app.avl_status not null default 'POTENTIAL',
  status_changed_at         timestamptz not null default now(),
  status_changed_by         uuid references public.profiles (id) on delete set null,

  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),
  created_by                uuid references public.profiles (id) on delete set null,

  constraint buyer_supplier_relationships_unique unique (buyer_organization_id, supplier_organization_id),
  constraint buyer_supplier_relationships_distinct check (buyer_organization_id <> supplier_organization_id)
);

comment on table public.buyer_supplier_relationships is
  'Relación comprador→proveedor con ciclo de vida real (fase 8.8, AVL). Alimenta accreditation_fit (BLOCKED excluye en Recall antes de llegar a scoring; APPROVED da el máximo fit) — services/matching.py.';

create index buyer_supplier_relationships_buyer_idx on public.buyer_supplier_relationships (buyer_organization_id);
create index buyer_supplier_relationships_supplier_idx on public.buyer_supplier_relationships (supplier_organization_id);

select app.apply_table_conventions('public.buyer_supplier_relationships');


create table public.buyer_supplier_notes (
  id             uuid primary key default gen_random_uuid(),
  relationship_id uuid not null references public.buyer_supplier_relationships (id) on delete cascade,

  body           text not null,

  created_at     timestamptz not null default now(),
  created_by     uuid references public.profiles (id) on delete set null
);

comment on table public.buyer_supplier_notes is
  'Notas privadas del comprador sobre la relación (fase 8.8) — nunca visibles al proveedor, ni siquiera de solo lectura (ver 0068).';

create index buyer_supplier_notes_relationship_idx on public.buyer_supplier_notes (relationship_id);

revoke update, delete on public.buyer_supplier_notes from app_user;
