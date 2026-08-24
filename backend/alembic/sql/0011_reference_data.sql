-- ============================================================================
-- 0011 · Datos de referencia: países, monedas, unidades, idiomas
-- ----------------------------------------------------------------------------
-- Fase 2.1 del roadmap. Ver docs/02-MODELO-DATOS.md §D1.
--
-- Catálogos pequeños, de escritura infrecuente y lectura pública: se sembran
-- inline en la propia migración (mismo criterio que 0009 con permisos/roles),
-- no en un CSV aparte como sí hace falta para las 346 comunas de 0013.
-- ============================================================================

-- ─── Países ─────────────────────────────────────────────────────────────────

create table public.countries (
  code                 char(2) primary key,  -- ISO 3166-1 alpha-2
  name                 text not null,
  default_currency_code char(3),
  phone_prefix         text,
  is_active            boolean not null default true,

  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

comment on table public.countries is
  'Catálogo de países (ISO 3166-1 alpha-2). Ampliable sin deploy.';

select app.apply_table_conventions('public.countries');


-- ─── Monedas ────────────────────────────────────────────────────────────────

create table public.currencies (
  code            char(3) primary key,  -- ISO 4217, o UF/UTM como pseudo-código
  name            text not null,
  symbol          text not null,
  decimal_places  smallint not null default 2,
  -- UF y UTM son unidades de reajuste chilenas, no monedas de curso legal.
  -- Se modelan como "moneda" porque los montos de la plataforma (ofertas,
  -- cotizaciones, garantías) se expresan indistintamente en CLP/USD/UF/UTM, y
  -- separar el concepto en otra tabla obligaría a duplicar cada columna de
  -- monto con su propio par "moneda o índice". is_index_unit distingue el
  -- caso sin bifurcar el modelo.
  is_index_unit   boolean not null default false,
  is_active       boolean not null default true,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint currencies_decimal_places check (decimal_places >= 0 and decimal_places <= 6)
);

comment on table public.currencies is
  'Monedas ISO 4217 más UF/UTM (is_index_unit=true). Fuente de verdad de decimal_places para formateo.';

select app.apply_table_conventions('public.currencies');


-- ─── Tipos de cambio ────────────────────────────────────────────────────────
-- Fuera de alcance de esta fase: la ingesta diaria real (Banco Central / SII
-- para UF y UTM, mercado para USD/EUR) es un job que se construye cuando
-- exista un consumidor real de tipos de cambio históricos (cotizaciones
-- multi-moneda, fase 7). Aquí solo se crea la tabla y se siembran 1-2 filas
-- de ejemplo para que no quede vacía en desarrollo.

create table public.fx_rates (
  from_code   char(3) not null references public.currencies (code),
  to_code     char(3) not null references public.currencies (code),
  valid_on    date not null,
  rate        numeric(18, 8) not null,
  source      text,

  created_at  timestamptz not null default now(),

  primary key (from_code, to_code, valid_on),
  constraint fx_rates_positive check (rate > 0),
  constraint fx_rates_distinct_codes check (from_code <> to_code)
);

comment on table public.fx_rates is
  'Tipos de cambio históricos por día. Ingesta automática diaria: fuera de alcance de fase 2.';

create index fx_rates_lookup_idx on public.fx_rates (from_code, to_code, valid_on desc);


-- ─── Unidades de medida ─────────────────────────────────────────────────────

create table public.units_of_measure (
  code            text primary key,
  name            text not null,
  -- Familia libre (LENGTH, TIME, COUNT, MASS, VOLUME, AREA...): agrupa para
  -- UI (ej. no permitir convertir HH a KM), no se usa para lógica de negocio.
  family          text not null,
  -- Factor de conversión a la unidad base de su family, cuando aplica
  -- (ej. TON → KG). NULL para unidades sin conversión definida (GLOBAL, PAX).
  factor_to_base  numeric,
  is_active       boolean not null default true,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.units_of_measure is
  'Unidades de medida para atributos y precios. Ampliable sin deploy.';

select app.apply_table_conventions('public.units_of_measure');


-- ─── Idiomas ────────────────────────────────────────────────────────────────

create table public.languages (
  code        text primary key,  -- BCP 47, ej. es-CL
  name        text not null,
  is_active   boolean not null default true,

  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.languages is
  'Idiomas disponibles para contenido traducible (taxonomía, industrias).';

select app.apply_table_conventions('public.languages');


-- ============================================================================
-- Seed
-- ============================================================================

insert into public.countries (code, name, default_currency_code, phone_prefix) values
  ('CL', 'Chile',      'CLP', '+56'),
  ('PE', 'Perú',       'PEN', '+51'),
  ('AR', 'Argentina',  'ARS', '+54'),
  ('CO', 'Colombia',   'COP', '+57'),
  ('MX', 'México',     'MXN', '+52'),
  ('BR', 'Brasil',     'BRL', '+55'),
  ('US', 'Estados Unidos', 'USD', '+1')
on conflict (code) do nothing;

insert into public.currencies (code, name, symbol, decimal_places, is_index_unit) values
  ('CLP', 'Peso chileno',        '$',    0, false),
  ('USD', 'Dólar estadounidense','US$',  2, false),
  ('EUR', 'Euro',                '€',    2, false),
  ('PEN', 'Sol peruano',         'S/',   2, false),
  ('ARS', 'Peso argentino',      'AR$',  2, false),
  ('COP', 'Peso colombiano',     'CO$',  2, false),
  ('MXN', 'Peso mexicano',       'MX$',  2, false),
  ('BRL', 'Real brasileño',      'R$',   2, false),
  ('UF',  'Unidad de Fomento',   'UF',   4, true),
  ('UTM', 'Unidad Tributaria Mensual', 'UTM', 0, true)
on conflict (code) do nothing;

-- Ejemplo mínimo para que la tabla no quede vacía en desarrollo. NO es una
-- fuente viva: cuando exista el job de ingesta (Banco Central/SII), estas
-- filas de ejemplo quedan como historial, no se borran.
insert into public.fx_rates (from_code, to_code, valid_on, rate, source) values
  ('UF',  'CLP', current_date, 38000.00, 'seed_manual'),
  ('UTM', 'CLP', current_date, 67000.00, 'seed_manual')
on conflict (from_code, to_code, valid_on) do nothing;

insert into public.units_of_measure (code, name, family, factor_to_base) values
  ('UN',     'Unidad',              'COUNT',  1),
  ('HH',     'Hora-hombre',         'TIME',   1),
  ('KM',     'Kilómetro',           'LENGTH', 1),
  ('TON',    'Tonelada',            'MASS',   1000),
  ('KG',     'Kilogramo',           'MASS',   1),
  ('M3',     'Metro cúbico',        'VOLUME', 1),
  ('LT',     'Litro',               'VOLUME', 0.001),
  ('M2',     'Metro cuadrado',      'AREA',   1),
  ('MES',    'Mes',                 'TIME',   null),
  ('GLOBAL', 'Suma alzada',         'OTHER',  null),
  -- PAX (capacidad de pasajeros): la necesita el seed de atributos de la
  -- categoría transporte.personas en 0017_seed_attributes.sql.
  ('PAX',    'Pasajero',            'COUNT',  1)
on conflict (code) do nothing;

insert into public.languages (code, name, is_active) values
  ('es-CL', 'Español (Chile)', true),
  ('en-US', 'English (US)',    false),
  ('pt-BR', 'Português (Brasil)', false)
on conflict (code) do nothing;
