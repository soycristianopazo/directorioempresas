-- ============================================================================
-- 0047 · Cotizaciones (fase 7.5)
-- ----------------------------------------------------------------------------
-- Fase 7.5 del roadmap. Ver docs/02-MODELO-DATOS.md §D9, docs/01-ARQUITECTURA.md §G.1/§G.3.
--
-- quotations es el CONTENEDOR — sin montos, sin datos comerciales. Cada fila
-- lleva su propio supplier_organization_id: es la pieza que hace posible
-- Patrón E en RLS (0049) — una policy que compara la columna DE LA FILA, no
-- un permiso contra una organización fija de la tabla. Es la primera tabla
-- de este proyecto donde varias organizaciones compiten por filas de la
-- misma tabla padre sin verse entre sí.
--
-- quotation_revisions es append-only de verdad (revoke update, delete) — cada
-- envío es una fila nueva, nunca se corrige una ya enviada. is_current es
-- documental (se fija una sola vez al insertar); el puntero vivo y mutable es
-- quotations.current_revision_id, actualizado por el service en la misma
-- transacción del INSERT — mismo patrón _transition()-style que
-- accreditation.py, aplicado acá para resolver la tensión entre "append-only"
-- y "necesita un puntero a la vigente".
--
-- round_type tiene UN SOLO valor usable hoy ('INITIAL'). CLARIFICATION/
-- COUNTER/BAFO pertenecen a negotiation_rounds (fase 8.5, no existe esa
-- tabla) — se agregan con ALTER TYPE ... ADD VALUE cuando lleguen, mismo
-- criterio ya escrito en 0040_sourcing_events.sql para sourcing_event_status.
-- La policy de INSERT (0049) además fuerza round_type='INITIAL' en código,
-- esto solo evita que el propio tipo declare estados que ninguna ruta puede
-- producir todavía.
--
-- current_revision_id y quotation_revisions.quotation_id se referencian
-- mutuamente — la FK de current_revision_id se agrega con ALTER TABLE
-- después de crear quotation_revisions, no en el create table de quotations.
-- ============================================================================

create type app.quotation_status as enum ('DRAFT', 'SUBMITTED', 'WITHDRAWN', 'DISQUALIFIED');
create type app.quotation_round_type as enum ('INITIAL');

create table public.quotations (
  id                        uuid primary key default gen_random_uuid(),
  sourcing_event_id         uuid not null references public.sourcing_events (id) on delete cascade,
  supplier_organization_id  uuid not null references public.organizations (id) on delete cascade,

  status                    app.quotation_status not null default 'DRAFT',
  current_revision_id       uuid,
  first_submitted_at        timestamptz,

  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),
  created_by                uuid references public.profiles (id) on delete set null,
  updated_by                uuid references public.profiles (id) on delete set null,

  constraint quotations_unique unique (sourcing_event_id, supplier_organization_id)
);

comment on table public.quotations is
  'Contenedor de la oferta de un proveedor en un evento (§D9). Sin montos — esos viven en quotation_revisions. current_revision_id apunta a la última ronda enviada; es la única fuente de verdad de "cuál es la vigente", nunca quotation_revisions.is_current (documental, ver comentario de esa tabla).';

create index quotations_event_idx on public.quotations (sourcing_event_id);
create index quotations_org_idx on public.quotations (supplier_organization_id);

select app.apply_table_conventions('public.quotations');


create table public.quotation_revisions (
  id                  uuid primary key default gen_random_uuid(),
  quotation_id        uuid not null references public.quotations (id) on delete cascade,

  round_number        int not null,
  round_type          app.quotation_round_type not null default 'INITIAL',
  is_current          boolean not null default true,

  submitted_at        timestamptz not null default now(),
  submitted_by        uuid references public.profiles (id) on delete set null,
  valid_until         date,

  currency_code       char(3) not null references public.currencies (code),
  fx_rate_snapshot     numeric,
  subtotal             numeric,
  tax_amount            numeric,
  total_amount           numeric not null,
  total_amount_base       numeric,

  payment_terms          text,
  delivery_days           int,
  warranty_terms           text,
  exclusions                text,
  notes                     text,

  constraint quotation_revisions_unique unique (quotation_id, round_number),
  constraint quotation_revisions_amounts check (total_amount >= 0)
);

comment on table public.quotation_revisions is
  'Append-only: una fila por envío (§D9). is_current se fija una vez al insertar y NUNCA se vuelve a tocar (la tabla es revoke update/delete) — es documental. La revisión vigente siempre se determina por quotations.current_revision_id, actualizado en la misma transacción del INSERT.';

create index quotation_revisions_quotation_idx on public.quotation_revisions (quotation_id, round_number desc);

revoke update, delete on public.quotation_revisions from app_user;

alter table public.quotations
  add constraint quotations_current_revision_fk
  foreign key (current_revision_id) references public.quotation_revisions (id);


create table public.quotation_items (
  id                     uuid primary key default gen_random_uuid(),
  quotation_revision_id  uuid not null references public.quotation_revisions (id) on delete cascade,
  sourcing_event_item_id uuid not null references public.sourcing_event_items (id) on delete cascade,

  quantity               numeric not null,
  unit_code              text references public.units_of_measure (code),
  unit_price             numeric not null,
  discount_pct           numeric,
  tax_rate               numeric,
  line_total             numeric not null,
  lead_time_days         int,
  brand                  text,
  model                  text,
  notes                  text,

  constraint quotation_items_unique unique (quotation_revision_id, sourcing_event_item_id),
  constraint quotation_items_amounts check (quantity > 0 and unit_price >= 0 and line_total >= 0)
);

comment on table public.quotation_items is
  'Línea a línea contra sourcing_event_items (§D9). Cuelga de la REVISIÓN, no de la cotización — cada envío es su propio set de líneas, append-only junto con su revisión. sourcing_event_item_id es on delete cascade (igual que sourcing_event_criterion_id en quotation_responses, más abajo): sin eso, borrar un sourcing_event_items desde el lado comprador revienta con FK violation mientras existan cotizaciones del lado proveedor referenciándolo — encontrado en vivo por el teardown de tests/test_quotations.py.';

create index quotation_items_revision_idx on public.quotation_items (quotation_revision_id);

revoke update, delete on public.quotation_items from app_user;


create table public.quotation_responses (
  id                        uuid primary key default gen_random_uuid(),
  quotation_revision_id     uuid not null references public.quotation_revisions (id) on delete cascade,
  sourcing_event_criterion_id uuid not null references public.sourcing_event_criteria (id) on delete cascade,

  complies                  boolean,
  value_text                text,
  notes                     text,

  constraint quotation_responses_unique unique (quotation_revision_id, sourcing_event_criterion_id)
);

comment on table public.quotation_responses is
  'Respuesta del proveedor a cada sourcing_event_criteria de esta revisión — cumple/no cumple/valor declarado (§D9). Alimenta el comparador técnico de fase 8; en fase 7 es solo captura y despliegue informativo.';

create index quotation_responses_revision_idx on public.quotation_responses (quotation_revision_id);

revoke update, delete on public.quotation_responses from app_user;


create table public.quotation_documents (
  id                     uuid primary key default gen_random_uuid(),
  quotation_revision_id  uuid not null references public.quotation_revisions (id) on delete cascade,

  name                   text not null,
  storage_path           text not null,
  checksum_sha256        text not null,

  created_at             timestamptz not null default now(),
  created_by             uuid references public.profiles (id) on delete set null
);

comment on table public.quotation_documents is
  'Anexos de la oferta (§D9) — cuelga de la revisión, igual que quotation_items. Bucket org-documents (mismo bucket de siempre, no los buckets por tipo de contenido de §J que nunca se implementaron), prefijo {organization_id}/quotations/{quotation_id}/{revision_id}/...';

create index quotation_documents_revision_idx on public.quotation_documents (quotation_revision_id);

revoke update, delete on public.quotation_documents from app_user;
