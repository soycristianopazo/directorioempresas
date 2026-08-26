-- ============================================================================
-- 0082 · Catálogo de giros SII (código de actividad económica)
-- ----------------------------------------------------------------------------
-- Catálogo público de referencia, mismo criterio que countries/currencies/
-- units_of_measure (backend/app/models/reference.py) — sin auth para leerlo.
--
-- vat_affected/tax_category tienen un tercer valor 'G' además de SI/NO y 1/2:
-- el propio SII lo usa para actividades donde el contribuyente elige entre
-- opciones disponibles (ver circular de reclasificación 2023) — no es un
-- placeholder ni un error de datos, así que se modela como tal en el enum en
-- vez de forzar un booleano.
-- ============================================================================

create type app.sii_vat_status as enum ('SI', 'NO', 'G');
create type app.sii_tax_category as enum ('1', '2', 'G');

create table public.sii_economic_activities (
  code         text primary key,
  description  text not null,
  sector       text not null,
  subgroup     text,
  vat_affected app.sii_vat_status not null,
  tax_category app.sii_tax_category not null,
  is_active    boolean not null default true,

  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  constraint sii_economic_activities_code_format check (code ~ '^[0-9]{6}$')
);

comment on table public.sii_economic_activities is
  'Códigos de actividad económica (giro) del SII vigentes, 6 dígitos — catálogo público de referencia. Seed en 0083, extraído verbatim de sii.cl (674 filas, 21 sectores).';

create index sii_economic_activities_sector_idx on public.sii_economic_activities (sector);

alter table public.sii_economic_activities enable row level security;

create policy sii_economic_activities_select on public.sii_economic_activities
  for select using (true);

create policy sii_economic_activities_system_context on public.sii_economic_activities
  for all
  using (app.is_system_context())
  with check (app.is_system_context());
