-- ============================================================================
-- 0015 · Seed de taxonomía e industrias
-- ----------------------------------------------------------------------------
-- Fase 2.3 (seed) y 2.5 (seed) del roadmap.
--
-- Los nodos de nivel 2 y 3 referencian a su padre por `path` (ltree), no por
-- slug: el slug solo es único DENTRO de un padre (unique(parent_id, slug)),
-- así que dos categorías distintas podrían compartir un slug de hijo (p.ej.
-- "preventiva" aparece bajo mantención.mecánica Y mantención.eléctrica). El
-- path completo, en cambio, identifica un nodo sin ambigüedad porque cada
-- nodo tiene exactamente un path.
--
-- PROPUESTA RAZONADA, NO CONFIRMADA CONTRA UN DOCUMENTO FUENTE: la lista de
-- ~28 categorías raíz y las industrias no vienen de un brief externo presente
-- en este repo — se construyeron a partir de las 8 categorías que SÍ nombra
-- explícitamente docs/04-ROADMAP.md, más un set plausible de categorías B2B
-- industriales chilenas. Ajustable sin costo (los nodos nunca se borran de
-- verdad, pero renombrar/reordenar antes de tener datos reales de
-- proveedores es gratis).
-- ============================================================================


-- ============================================================================
-- Industrias (eje: a quién se le vende)
-- ============================================================================

insert into public.industries (slug, name, sort_order) values
  ('mineria',                'Minería',                    1),
  ('construccion',           'Construcción',                2),
  ('retail',                 'Retail',                       3),
  ('energia-y-utilities',    'Energía y utilities',          4),
  ('salud',                  'Salud',                        5),
  ('manufactura',            'Manufactura',                  6),
  ('agroindustria',          'Agroindustria',                7),
  ('transporte-y-logistica', 'Transporte y logística',       8),
  ('sector-publico',         'Sector público',                9),
  ('educacion',              'Educación',                    10);

insert into public.industries (parent_id, slug, name, sort_order)
select id, v.slug, v.name, v.sort_order
from public.industries, (values
  ('cobre',                     'Cobre',                     1),
  ('litio',                     'Litio',                     2),
  ('oro-y-plata',                'Oro y plata',               3),
  ('plantas-concentradoras',     'Plantas concentradoras',    4),
  ('fundiciones',                'Fundiciones',               5),
  ('puertos-y-logistica-minera', 'Puertos y logística minera',6)
) as v(slug, name, sort_order)
where public.industries.path = 'mineria'::ltree;

insert into public.industry_translations (industry_id, language_code, name)
select id, 'es-CL', name from public.industries;


-- ============================================================================
-- Taxonomía (eje: qué se vende) — 28 categorías raíz
-- ============================================================================

insert into public.taxonomy_nodes (slug, node_type, name, risk_level, sort_order) values
  ('transporte',                       'CATEGORY', 'Transporte',                          'MEDIUM',   1),
  ('mantencion',                       'CATEGORY', 'Mantención',                          'MEDIUM',   2),
  ('servicios-electricos',             'CATEGORY', 'Servicios eléctricos',                'HIGH',     3),
  ('arriendo-de-maquinaria',           'CATEGORY', 'Arriendo de maquinaria y equipos',    null,       4),
  ('epp',                              'CATEGORY', 'Elementos de protección personal',    null,       5),
  ('ingenieria',                       'CATEGORY', 'Ingeniería',                          null,       6),
  ('tecnologia-de-la-informacion',     'CATEGORY', 'Tecnología de la información',        null,       7),
  ('alimentacion-y-campamentos',       'CATEGORY', 'Alimentación y campamentos',          null,       8),
  ('construccion',                     'CATEGORY', 'Construcción y obras civiles',        'MEDIUM',   9),
  ('insumos-industriales',             'CATEGORY', 'Insumos y materiales industriales',   null,       10),
  ('repuestos-y-partes',               'CATEGORY', 'Repuestos y partes',                  null,       11),
  ('combustibles-y-lubricantes',       'CATEGORY', 'Combustibles y lubricantes',          'HIGH',     12),
  ('aseo-industrial',                  'CATEGORY', 'Aseo e higiene industrial',           null,       13),
  ('seguridad-y-vigilancia',           'CATEGORY', 'Seguridad y vigilancia',              null,       14),
  ('telecomunicaciones',               'CATEGORY', 'Telecomunicaciones',                  null,       15),
  ('logistica-y-bodegaje',             'CATEGORY', 'Logística y bodegaje',                null,       16),
  ('servicios-ambientales',            'CATEGORY', 'Servicios ambientales',               null,       17),
  ('laboratorios-y-ensayos',           'CATEGORY', 'Laboratorios y ensayos',              null,       18),
  ('capacitacion',                     'CATEGORY', 'Capacitación (OTEC)',                 null,       19),
  ('consultoria',                      'CATEGORY', 'Consultoría y asesorías',             null,       20),
  ('servicios-legales-y-contables',    'CATEGORY', 'Servicios legales y contables',       null,       21),
  ('maquinaria-pesada',                'CATEGORY', 'Maquinaria pesada (venta)',           null,       22),
  ('izaje-y-elevacion',                'CATEGORY', 'Equipos de izaje y elevación',        'HIGH',     23),
  ('ferreteria-industrial',            'CATEGORY', 'Ferretería industrial',               null,       24),
  ('explosivos-y-tronadura',           'CATEGORY', 'Explosivos y tronadura',              'CRITICAL', 25),
  ('perforacion-y-sondaje',            'CATEGORY', 'Perforación y sondaje',               'HIGH',     26),
  ('automatizacion-e-instrumentacion', 'CATEGORY', 'Automatización e instrumentación',    null,       27),
  ('recursos-humanos-y-dotacion',      'CATEGORY', 'Recursos humanos y dotación',         null,       28);


-- ============================================================================
-- Profundidad (2-3 niveles) en las 8 categorías prioritarias del roadmap
-- ============================================================================

-- ─── Transporte ──────────────────────────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('personas', 'Transporte de personas', 1),
  ('carga',    'Transporte de carga',    2)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'transporte'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SPECIALTY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('transporte.personas', 'faena',  'Traslado a faena',      1),
  ('transporte.personas', 'urbano', 'Traslado urbano',        2),
  ('transporte.carga',    'general', 'Carga general',         1),
  ('transporte.carga',    'especializada', 'Carga especializada', 2)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;

-- ─── Mantención ──────────────────────────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('mecanica', 'Mantención mecánica',   1),
  ('electrica', 'Mantención eléctrica', 2)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'mantencion'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SPECIALTY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('mantencion.mecanica',  'preventiva', 'Preventiva', 1),
  ('mantencion.mecanica',  'correctiva', 'Correctiva', 2),
  ('mantencion.electrica', 'preventiva', 'Preventiva', 1),
  ('mantencion.electrica', 'correctiva', 'Correctiva', 2)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;

-- ─── Servicios eléctricos ────────────────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('baja-tension', 'Baja tensión', 1),
  ('alta-tension', 'Alta tensión', 2)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'servicios_electricos'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SPECIALTY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('servicios_electricos.baja_tension', 'instalaciones',  'Instalaciones',  1),
  ('servicios_electricos.baja_tension', 'mantenimiento',  'Mantenimiento',  2),
  ('servicios_electricos.alta_tension', 'instalaciones',  'Instalaciones',  1),
  ('servicios_electricos.alta_tension', 'mantenimiento',  'Mantenimiento',  2)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;

-- ─── Arriendo de maquinaria y equipos ────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('movimiento-de-tierra',  'Movimiento de tierra',  1),
  ('izaje',                 'Izaje',                 2),
  ('generacion-electrica',  'Generación eléctrica',  3)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'arriendo_de_maquinaria'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SPECIALTY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('arriendo_de_maquinaria.movimiento_de_tierra', 'excavadoras',          'Excavadoras',           1),
  ('arriendo_de_maquinaria.movimiento_de_tierra', 'cargadores-frontales', 'Cargadores frontales',  2),
  ('arriendo_de_maquinaria.izaje',                'gruas-moviles',        'Grúas móviles',         1),
  ('arriendo_de_maquinaria.izaje',                'gruas-horquilla',      'Grúas horquilla',       2),
  ('arriendo_de_maquinaria.generacion_electrica', 'generadores-diesel',   'Generadores diésel',    1)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;

-- ─── EPP ─────────────────────────────────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('proteccion-cabeza',        'Protección de cabeza',        1),
  ('proteccion-respiratoria',  'Protección respiratoria',     2),
  ('proteccion-caidas',        'Protección contra caídas',    3)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'epp'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'PRODUCT', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('epp.proteccion_cabeza',       'cascos',              'Cascos',                1),
  ('epp.proteccion_cabeza',       'proteccion-auditiva', 'Protección auditiva',   2),
  ('epp.proteccion_respiratoria', 'respiradores',        'Respiradores',          1),
  ('epp.proteccion_respiratoria', 'filtros',             'Filtros',               2),
  ('epp.proteccion_caidas',       'arneses',             'Arneses',               1),
  ('epp.proteccion_caidas',       'lineas-de-vida',      'Líneas de vida',        2)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;

-- ─── Ingeniería ──────────────────────────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('civil',     'Ingeniería civil',     1),
  ('electrica', 'Ingeniería eléctrica', 2),
  ('procesos',  'Ingeniería de procesos', 3)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'ingenieria'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SPECIALTY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('ingenieria.civil',     'estructural',        'Estructural',          1),
  ('ingenieria.civil',     'geotecnica',         'Geotécnica',           2),
  ('ingenieria.electrica', 'proyectos-bt-at',    'Proyectos BT/AT',      1),
  ('ingenieria.electrica', 'automatizacion',     'Automatización',       2),
  ('ingenieria.procesos',  'diseno-de-plantas',  'Diseño de plantas',    1),
  ('ingenieria.procesos',  'optimizacion',       'Optimización',         2)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;

-- ─── Tecnología de la información ────────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('software',        'Software',        1),
  ('infraestructura', 'Infraestructura', 2),
  ('ciberseguridad',  'Ciberseguridad',  3)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'tecnologia_de_la_informacion'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SPECIALTY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('tecnologia_de_la_informacion.software',        'erp',                  'ERP',                       1),
  ('tecnologia_de_la_informacion.software',        'desarrollo-a-medida',  'Desarrollo a medida',       2),
  ('tecnologia_de_la_informacion.infraestructura', 'cloud',                'Cloud',                     1),
  ('tecnologia_de_la_informacion.infraestructura', 'redes-y-conectividad', 'Redes y conectividad',      2),
  ('tecnologia_de_la_informacion.ciberseguridad',  'soc',                  'SOC',                       1),
  ('tecnologia_de_la_informacion.ciberseguridad',  'auditoria-de-seguridad','Auditoría de seguridad',   2)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;

-- ─── Alimentación y campamentos ──────────────────────────────────────────
insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SUBCATEGORY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('casino-industrial', 'Casino industrial', 1),
  ('campamentos',       'Campamentos',       2),
  ('catering-eventos',  'Catering de eventos', 3)
) as v(slug, name, sort_order)
where public.taxonomy_nodes.path = 'alimentacion_y_campamentos'::ltree;

insert into public.taxonomy_nodes (parent_id, slug, node_type, name, sort_order)
select id, v.slug, 'SPECIALTY', v.name, v.sort_order
from public.taxonomy_nodes, (values
  ('alimentacion_y_campamentos.casino_industrial', 'concesion-de-casino',  'Concesión de casino',   1),
  ('alimentacion_y_campamentos.casino_industrial', 'catering-diario',      'Catering diario',       2),
  ('alimentacion_y_campamentos.campamentos',       'instalacion',          'Instalación de campamentos', 1),
  ('alimentacion_y_campamentos.campamentos',       'habilitacion',         'Habilitación',          2),
  ('alimentacion_y_campamentos.catering_eventos',  'eventos-corporativos', 'Eventos corporativos',  1)
) as v(parent_path, slug, name, sort_order)
where public.taxonomy_nodes.path = v.parent_path::ltree;


-- ============================================================================
-- Traducciones es-CL — se copian del nombre canónico ya sembrado
-- ============================================================================

insert into public.taxonomy_node_translations (node_id, language_code, name, description)
select id, 'es-CL', name, description from public.taxonomy_nodes;


-- ============================================================================
-- Sinónimos de ejemplo (docs/02-MODELO-DATOS.md: "colación"↔"alimentación",
-- "camión pluma"↔"camión grúa")
-- ============================================================================

insert into public.taxonomy_node_synonyms (node_id, synonym)
select id, 'colación' from public.taxonomy_nodes where path = 'alimentacion_y_campamentos'::ltree
union all
select id, 'camión pluma' from public.taxonomy_nodes where path = 'arriendo_de_maquinaria.izaje.gruas_moviles'::ltree
union all
select id, 'camión grúa' from public.taxonomy_nodes where path = 'arriendo_de_maquinaria.izaje.gruas_moviles'::ltree
union all
select id, 'buses de acercamiento' from public.taxonomy_nodes where path = 'transporte.personas.faena'::ltree;
