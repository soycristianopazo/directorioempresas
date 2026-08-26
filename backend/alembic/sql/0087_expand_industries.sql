-- ============================================================================
-- 0087 · Ampliación del árbol de industrias (a quién se le vende)
-- ----------------------------------------------------------------------------
-- El seed original (0015) cubría 10 categorías raíz — el propio archivo lo
-- marca como "propuesta razonada, no confirmada contra un documento fuente...
-- ajustable sin costo". Feedback de usuario: la lista quedaba corta frente a
-- los sectores económicos relevantes en Chile. Se agregan 14 categorías raíz
-- más y subcategorías para Construcción/Energía/Retail/Transporte (Minería
-- ya las tenía desde 0015) — mismo patrón: insert de raíces, luego insert de
-- hijos por path ltree del padre.
-- ============================================================================

insert into public.industries (slug, name, sort_order) values
  ('silvicultura-y-forestal',   'Silvicultura y forestal',    11),
  ('pesca-y-acuicultura',       'Pesca y acuicultura',        12),
  ('petroleo-y-gas',            'Petróleo y gas',             13),
  ('telecomunicaciones',        'Telecomunicaciones',         14),
  ('tecnologia-y-software',     'Tecnología y software',      15),
  ('financiero-y-seguros',      'Financiero y seguros',       16),
  ('inmobiliario',              'Inmobiliario',                17),
  ('turismo-y-hoteleria',       'Turismo y hotelería',        18),
  ('alimentos-y-bebidas',       'Alimentos y bebidas',        19),
  ('automotriz',                'Automotriz',                  20),
  ('servicios-profesionales',   'Servicios profesionales',    21),
  ('farmaceutica',              'Farmacéutica',                22),
  ('defensa-y-seguridad',       'Defensa y seguridad',        23),
  ('medios-y-entretenimiento',  'Medios y entretenimiento',   24)
on conflict (slug) where parent_id is null do nothing;

insert into public.industries (parent_id, slug, name, sort_order)
select id, v.slug, v.name, v.sort_order
from public.industries, (values
  ('edificacion-habitacional',      'Edificación habitacional',       1),
  ('obras-civiles-e-infraestructura','Obras civiles e infraestructura',2),
  ('infraestructura-vial',           'Infraestructura vial',           3)
) as v(slug, name, sort_order)
where public.industries.path = 'construccion'::ltree
on conflict (parent_id, slug) do nothing;

insert into public.industries (parent_id, slug, name, sort_order)
select id, v.slug, v.name, v.sort_order
from public.industries, (values
  ('generacion-electrica',      'Generación eléctrica',        1),
  ('transmision-y-distribucion','Transmisión y distribución',  2),
  ('energias-renovables',       'Energías renovables (ERNC)',  3),
  ('agua-y-saneamiento',        'Agua y saneamiento',          4)
) as v(slug, name, sort_order)
where public.industries.path = 'energia_y_utilities'::ltree
on conflict (parent_id, slug) do nothing;

insert into public.industries (parent_id, slug, name, sort_order)
select id, v.slug, v.name, v.sort_order
from public.industries, (values
  ('supermercados',           'Supermercados',            1),
  ('tiendas-por-departamento','Tiendas por departamento', 2),
  ('comercio-electronico',    'Comercio electrónico',     3)
) as v(slug, name, sort_order)
where public.industries.path = 'retail'::ltree
on conflict (parent_id, slug) do nothing;

insert into public.industries (parent_id, slug, name, sort_order)
select id, v.slug, v.name, v.sort_order
from public.industries, (values
  ('transporte-de-carga-terrestre',  'Transporte de carga terrestre',  1),
  ('transporte-maritimo-y-portuario','Transporte marítimo y portuario',2),
  ('almacenaje-y-bodegaje',          'Almacenaje y bodegaje',          3)
) as v(slug, name, sort_order)
where public.industries.path = 'transporte_y_logistica'::ltree
on conflict (parent_id, slug) do nothing;

insert into public.industry_translations (industry_id, language_code, name)
select id, 'es-CL', name
from public.industries
where id not in (select industry_id from public.industry_translations);
