-- ============================================================================
-- 0017 · Seed de atributos para las 8 categorías prioritarias
-- ----------------------------------------------------------------------------
-- Fase 2.7 del roadmap. Demuestra el checkpoint textual: "un admin crea una
-- categoría con 3 atributos y el formulario del proveedor se genera solo" —
-- vía v_effective_node_attributes (0016), sin tocar cada nodo hoja uno por
-- uno gracias a is_inherited=true.
-- ============================================================================

-- ─── Definiciones ────────────────────────────────────────────────────────

insert into public.attribute_definitions (code, name, data_type, unit_code, min_value, max_value, is_filterable, is_comparable) values
  ('vehicle_year',        'Año del vehículo',              'NUMBER',  null,  1990, 2027, true,  true),
  ('pax_capacity',        'Capacidad de pasajeros',        'NUMBER',  'PAX', 1,    null, true,  true),
  ('has_gps',             'Cuenta con GPS',                'BOOLEAN', null,  null, null, true,  false),

  ('response_time_hours', 'Tiempo de respuesta',           'NUMBER',  'HH',  0,    null, true,  true),
  ('service_type',        'Tipo de servicio',              'SELECT',  null,  null, null, true,  false),

  ('voltage_range',       'Rango de tensión',              'SELECT',  null,  null, null, true,  false),
  ('certified_electrician','Electricista certificado SEC', 'BOOLEAN', null,  null, null, true,  false),

  ('capacity_ton',        'Capacidad',                     'NUMBER',  'TON', 0,    null, true,  true),
  ('fuel_type',           'Tipo de combustible',           'SELECT',  null,  null, null, true,  false),
  ('operator_included',   'Incluye operador',              'BOOLEAN', null,  null, null, true,  false),

  ('certification_standard','Norma de certificación',      'SELECT',  null,  null, null, true,  false),
  ('size_range',           'Rango de tallas',              'TEXT',    null,  null, null, false, false),
  ('is_reusable',           'Reutilizable',                'BOOLEAN', null,  null, null, true,  false),

  ('discipline',            'Disciplina',                  'SELECT',  null,  null, null, true,  false),
  ('has_professional_seal', 'Firma de profesional responsable', 'BOOLEAN', null, null, null, true, false),

  ('deployment',            'Modalidad de despliegue',     'MULTISELECT', null, null, null, true, false),
  ('license_model',         'Modelo de licenciamiento',    'SELECT',  null,  null, null, true,  false),

  ('daily_capacity',        'Capacidad diaria',            'NUMBER',  'UN',  0,    null, true,  true),
  ('has_sanitary_resolution','Resolución sanitaria vigente','BOOLEAN', null, null, null, true,  false)
on conflict (code) do nothing;


-- ─── Opciones (SELECT / MULTISELECT) ─────────────────────────────────────

insert into public.attribute_options (attribute_definition_id, value, label, sort_order)
select ad.id, v.value, v.label, v.sort_order
from public.attribute_definitions ad, (values
  ('service_type', 'PREVENTIVA', 'Preventiva', 1),
  ('service_type', 'CORRECTIVA', 'Correctiva', 2),
  ('service_type', 'AMBAS',      'Ambas',      3),

  ('voltage_range', 'BT', 'Baja tensión', 1),
  ('voltage_range', 'MT', 'Media tensión', 2),
  ('voltage_range', 'AT', 'Alta tensión', 3),

  ('fuel_type', 'DIESEL',    'Diésel',    1),
  ('fuel_type', 'ELECTRICO', 'Eléctrico', 2),
  ('fuel_type', 'GAS',       'Gas',       3),

  ('certification_standard', 'NCh',  'NCh (chilena)', 1),
  ('certification_standard', 'ANSI', 'ANSI',           2),
  ('certification_standard', 'EN',   'EN (europea)',   3),

  ('discipline', 'CIVIL',            'Civil',             1),
  ('discipline', 'ELECTRICA',        'Eléctrica',         2),
  ('discipline', 'PROCESOS',         'Procesos',          3),
  ('discipline', 'MULTIDISCIPLINARIA','Multidisciplinaria',4),

  ('deployment', 'SAAS',        'SaaS',         1),
  ('deployment', 'CLOUD',       'Cloud',        2),
  ('deployment', 'ON_PREMISE',  'On-premise',   3),

  ('license_model', 'SUBSCRIPTION', 'Suscripción',    1),
  ('license_model', 'PERPETUAL',    'Licencia perpetua',2),
  ('license_model', 'USAGE_BASED',  'Por uso',        3)
) as v(code, value, label, sort_order)
where ad.code = v.code
on conflict (attribute_definition_id, value) do nothing;


-- ─── Vínculo a nodos de taxonomía (applies_to=OFFERING, is_inherited=true) ─

insert into public.taxonomy_node_attributes (node_id, attribute_definition_id, applies_to, is_required, is_inherited, sort_order)
select tn.id, ad.id, 'OFFERING', v.is_required, true, v.sort_order
from public.taxonomy_nodes tn, public.attribute_definitions ad, (values
  -- Transporte de personas (subcategoría, no toda la raíz: carga no aplica)
  ('transporte.personas', 'vehicle_year', true,  1),
  ('transporte.personas', 'pax_capacity', true,  2),
  ('transporte.personas', 'has_gps',      false, 3),

  -- Mantención (raíz: aplica a mecánica y eléctrica por igual)
  ('mantencion', 'response_time_hours', true,  1),
  ('mantencion', 'service_type',        true,  2),

  -- Servicios eléctricos (raíz)
  ('servicios_electricos', 'voltage_range',        true, 1),
  ('servicios_electricos', 'certified_electrician', true, 2),

  -- Arriendo de maquinaria y equipos (raíz)
  ('arriendo_de_maquinaria', 'capacity_ton',      true,  1),
  ('arriendo_de_maquinaria', 'fuel_type',         false, 2),
  ('arriendo_de_maquinaria', 'operator_included', false, 3),

  -- EPP (raíz)
  ('epp', 'certification_standard', true,  1),
  ('epp', 'size_range',             false, 2),
  ('epp', 'is_reusable',            false, 3),

  -- Ingeniería (raíz)
  ('ingenieria', 'discipline',            true,  1),
  ('ingenieria', 'has_professional_seal', false, 2),

  -- TI · Software (subcategoría, no toda la raíz: infraestructura/ciberseguridad no aplican)
  ('tecnologia_de_la_informacion.software', 'deployment',     true, 1),
  ('tecnologia_de_la_informacion.software', 'license_model',  true, 2),

  -- Alimentación y campamentos (raíz)
  ('alimentacion_y_campamentos', 'daily_capacity',           true,  1),
  ('alimentacion_y_campamentos', 'has_sanitary_resolution',  false, 2)
) as v(node_path, attribute_code, is_required, sort_order)
where tn.path = v.node_path::ltree
  and ad.code = v.attribute_code
on conflict (node_id, attribute_definition_id, applies_to) do nothing;
