-- ============================================================================
-- 0092 · Ofertas del catálogo (fase 11) — offering_deals
-- ----------------------------------------------------------------------------
-- Una oferta liga un producto/servicio YA publicado en el catálogo
-- (supplier_offerings) a un precio rebajado y a UNO de dos límites: stock
-- (se agota) o fecha límite (cuenta regresiva) — nunca ambos, nunca ninguno,
-- de ahí el check constraint. No hay estado persistido ("ACTIVE"/"EXPIRED"):
-- si está vigente se deriva en el momento de leer (mismo criterio que la
-- app ya usa para el vencimiento de sourcing_events — evitar un estado que
-- pueda quedar desincronizado sin un corredor de tareas programadas que lo
-- corrija, algo que este backend no tiene). `stock_remaining` sí se
-- persiste porque es un contador real que el proveedor edita a mano
-- (no hay checkout/compra en la plataforma — el proveedor descuenta cuando
-- vende por fuera).
-- ============================================================================

create table public.offering_deals (
  id                 uuid primary key default gen_random_uuid(),
  offering_id        uuid not null references public.supplier_offerings(id) on delete cascade,

  deal_price         numeric(18,4) not null check (deal_price > 0),
  original_price     numeric(18,4),
  currency_code      char(3) not null references public.currencies(code),
  unit_code          text references public.units_of_measure(code),

  stock_quantity     int check (stock_quantity is null or stock_quantity > 0),
  stock_remaining    int check (stock_remaining is null or stock_remaining >= 0),
  expires_at         timestamptz,

  cancelled_at       timestamptz,

  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  created_by         uuid references public.profiles(id) on delete set null,

  constraint offering_deals_exactly_one_limit check (
    (stock_quantity is not null) <> (expires_at is not null)
  ),
  constraint offering_deals_stock_consistency check (
    stock_quantity is null or stock_remaining is null or stock_remaining <= stock_quantity
  )
);

comment on table public.offering_deals is
  'Ofertas por tiempo o stock limitado sobre un producto/servicio del catálogo (fase 11). Exactamente uno de stock_quantity/expires_at está poblado. Sin estado persistido: vigencia = cancelled_at is null and (expires_at is null or expires_at > now()) and (stock_quantity is null or stock_remaining > 0).';

create index offering_deals_offering_idx on public.offering_deals (offering_id);

-- Solo una oferta VIGENTE por publicación a la vez — se valida en Python
-- antes del insert (mismo criterio que slug_exists en offerings_service),
-- no con un índice único parcial: la vigencia depende de now() y de
-- stock_remaining > 0, ninguno expresable en un índice parcial estable.

-- Mismo patrón que offering_media/offering_taxonomy_nodes (0029): visibilidad
-- pública vía app.can_view_offering(), escritura vía offering.write, más el
-- bypass de contexto de sistema.
alter table public.offering_deals enable row level security;

create policy offering_deals_select on public.offering_deals
  for select using (app.can_view_offering(offering_id));

create policy offering_deals_write on public.offering_deals
  for all using (
    exists (
      select 1 from public.supplier_offerings so
      where so.id = offering_id and app.has_permission(so.organization_id, 'offering.write')
    )
  )
  with check (
    exists (
      select 1 from public.supplier_offerings so
      where so.id = offering_id and app.has_permission(so.organization_id, 'offering.write')
    )
  );

create policy offering_deals_system_context on public.offering_deals
  for all using (app.is_system_context()) with check (app.is_system_context());

grant select, insert, update on public.offering_deals to app_user;
