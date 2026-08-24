-- ============================================================================
-- 0039 · Demanda — requirements (la necesidad, §18)
-- ----------------------------------------------------------------------------
-- Fase 6.1 del roadmap. Ver docs/02-MODELO-DATOS.md §D8.
--
-- `requirements` es la necesidad tal como la declara el comprador, antes de
-- convertirse en un proceso formal (`sourcing_events`, 0040). Nunca es
-- pública — a diferencia de la oferta, la demanda de un comprador es
-- información privada de su organización (RLS en 0043).
-- ============================================================================

create type app.requirement_status as enum ('DRAFT', 'CONVERTED', 'ARCHIVED');
create type app.requirement_source as enum ('FORM', 'FREE_TEXT', 'DISCOVERY');

create table public.requirements (
  id                        uuid primary key default gen_random_uuid(),
  organization_id           uuid not null references public.organizations (id) on delete cascade,

  name                      text not null,
  description               text,
  primary_taxonomy_node_id  uuid references public.taxonomy_nodes (id),
  industry_id               uuid references public.industries (id),

  needed_from               date,
  needed_until              date,
  duration_months           int,
  estimated_budget          numeric,
  currency_code             char(3) references public.currencies (code),
  commercial_terms          text,
  payment_terms             text,

  status                    app.requirement_status not null default 'DRAFT',
  source                    app.requirement_source not null default 'FORM',
  raw_input_text            text,

  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),
  created_by                uuid references public.profiles (id) on delete set null,
  updated_by                uuid references public.profiles (id) on delete set null,

  constraint requirements_dates check (
    needed_from is null or needed_until is null or needed_from <= needed_until
  ),
  constraint requirements_duration check (duration_months is null or duration_months > 0)
);

comment on table public.requirements is
  'La necesidad de compra tal como la declara el comprador (§18) — previa a un sourcing_event formal. source=DISCOVERY marca las creadas desde "RFQ desde búsqueda" (§42); raw_input_text queda para la estructuración por IA en V2 (§H.9), no se usa en esta fase.';

create index requirements_org_idx on public.requirements (organization_id);
create index requirements_status_idx on public.requirements (organization_id, status);

select app.apply_table_conventions('public.requirements');


create table public.requirement_items (
  id             uuid primary key default gen_random_uuid(),
  requirement_id uuid not null references public.requirements (id) on delete cascade,

  description    text not null,
  quantity       numeric not null,
  unit_code      text references public.units_of_measure (code),
  specifications text,
  sort_order     int not null default 0,

  constraint requirement_items_quantity check (quantity > 0)
);

comment on table public.requirement_items is 'Líneas de la necesidad.';

create index requirement_items_requirement_idx on public.requirement_items (requirement_id);


create table public.requirement_locations (
  id                uuid primary key default gen_random_uuid(),
  requirement_id    uuid not null references public.requirements (id) on delete cascade,
  admin_division_id uuid not null references public.admin_divisions (id),

  constraint requirement_locations_unique unique (requirement_id, admin_division_id)
);

comment on table public.requirement_locations is 'Dónde se ejecuta la necesidad.';


create table public.requirement_documents (
  id             uuid primary key default gen_random_uuid(),
  requirement_id uuid not null references public.requirements (id) on delete cascade,

  name           text not null,
  storage_path   text not null,

  created_at     timestamptz not null default now(),
  created_by     uuid references public.profiles (id) on delete set null
);

comment on table public.requirement_documents is
  'Adjuntos de la necesidad (planos, especificaciones). Bucket org-documents, siempre privado — nunca is_public: a diferencia de offering_documents, esto es demanda del comprador, no material de venta.';

create index requirement_documents_requirement_idx on public.requirement_documents (requirement_id);
