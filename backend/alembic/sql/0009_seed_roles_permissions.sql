-- ============================================================================
-- 0009 · Catálogo de permisos y roles de sistema
-- ----------------------------------------------------------------------------
-- Fase 1.3 (datos estructurales, no seed de desarrollo).
--
-- Va en una migración y no en seed.sql porque las policies de RLS dependen de
-- que estos códigos existan. Sin ORG_OWNER no se puede crear una organización.
--
-- Se incluyen permisos de fases futuras para que el catálogo sea estable y los
-- roles no haya que reescribirlos en cada fase. Un permiso sin funcionalidad
-- detrás no hace daño; un rol al que hay que añadirle permisos a mano en
-- producción, sí.
-- ============================================================================

insert into public.permissions (code, resource, action, description, scope) values
  -- Organización
  ('organization.read',        'organization', 'read',    'Ver los datos de la organización', 'ORGANIZATION'),
  ('organization.update',      'organization', 'update',  'Editar el perfil de la organización', 'ORGANIZATION'),
  ('organization.delete',      'organization', 'delete',  'Archivar la organización', 'ORGANIZATION'),
  ('organization.billing',     'organization', 'billing', 'Gestionar plan y facturación', 'ORGANIZATION'),

  -- Equipo
  ('member.read',              'member',       'read',    'Ver el equipo', 'ORGANIZATION'),
  ('member.manage',            'member',       'manage',  'Invitar, editar y remover miembros', 'ORGANIZATION'),
  ('role.manage',              'role',         'manage',  'Crear y editar roles a medida', 'ORGANIZATION'),

  -- Auditoría
  ('audit.read',               'audit',        'read',    'Ver la bitácora de auditoría', 'ORGANIZATION'),

  -- Catálogo de oferta (fase 3)
  ('offering.read',            'offering',     'read',    'Ver el catálogo propio', 'ORGANIZATION'),
  ('offering.write',           'offering',     'write',   'Crear y editar productos y servicios', 'ORGANIZATION'),
  ('offering.publish',         'offering',     'publish', 'Publicar o despublicar del catálogo', 'ORGANIZATION'),
  ('offering.delete',          'offering',     'delete',  'Eliminar elementos del catálogo', 'ORGANIZATION'),

  -- Documentos y credenciales (fase 5)
  ('document.read',            'document',     'read',    'Ver documentos de la organización', 'ORGANIZATION'),
  ('document.write',           'document',     'write',   'Subir y versionar documentos', 'ORGANIZATION'),
  ('document.delete',          'document',     'delete',  'Eliminar documentos', 'ORGANIZATION'),
  ('accreditation.submit',     'accreditation','submit',  'Postular y responder observaciones', 'ORGANIZATION'),
  ('accreditation.manage',     'accreditation','manage',  'Administrar programas propios de acreditación', 'ORGANIZATION'),

  -- Demanda y sourcing (fases 6-7)
  ('requirement.read',         'requirement',  'read',    'Ver requerimientos', 'ORGANIZATION'),
  ('requirement.write',        'requirement',  'write',   'Crear y editar requerimientos', 'ORGANIZATION'),
  ('sourcing_event.read',      'sourcing_event','read',   'Ver procesos de sourcing', 'ORGANIZATION'),
  ('sourcing_event.create',    'sourcing_event','create', 'Crear procesos de sourcing', 'ORGANIZATION'),
  ('sourcing_event.publish',   'sourcing_event','publish','Publicar e invitar proveedores', 'ORGANIZATION'),
  ('sourcing_event.cancel',    'sourcing_event','cancel', 'Cancelar o declarar desierto un proceso', 'ORGANIZATION'),
  ('sourcing_event.open_bids', 'sourcing_event','open_bids','Abrir ofertas selladas', 'ORGANIZATION'),

  -- Cotizaciones (fase 7)
  ('quotation.read',           'quotation',    'read',    'Ver cotizaciones recibidas', 'ORGANIZATION'),
  ('quotation.write',          'quotation',    'write',   'Preparar cotizaciones', 'ORGANIZATION'),
  ('quotation.submit',         'quotation',    'submit',  'Enviar cotizaciones', 'ORGANIZATION'),

  -- Evaluación y adjudicación (fase 8)
  ('evaluation.read',          'evaluation',   'read',    'Ver evaluaciones', 'ORGANIZATION'),
  ('evaluation.perform',       'evaluation',   'perform', 'Evaluar ofertas asignadas', 'ORGANIZATION'),
  ('evaluation.manage',        'evaluation',   'manage',  'Configurar plantillas y comités', 'ORGANIZATION'),
  ('negotiation.manage',       'negotiation',  'manage',  'Abrir rondas de negociación y BAFO', 'ORGANIZATION'),
  ('award.create',             'award',        'create',  'Proponer adjudicación', 'ORGANIZATION'),
  ('award.approve',            'award',        'approve', 'Aprobar adjudicación según su límite', 'ORGANIZATION'),

  -- Contratos y desempeño (V2)
  ('contract.read',            'contract',     'read',    'Ver contratos', 'ORGANIZATION'),
  ('contract.manage',          'contract',     'manage',  'Administrar contratos, hitos y SLA', 'ORGANIZATION'),
  ('performance.review',       'performance',  'review',  'Evaluar desempeño de proveedores', 'ORGANIZATION'),

  -- Relación con proveedores
  ('vendor_list.read',         'vendor_list',  'read',    'Ver la lista de proveedores aprobados', 'ORGANIZATION'),
  ('vendor_list.manage',       'vendor_list',  'manage',  'Administrar la vendor list y sus estados', 'ORGANIZATION'),

  -- Comunicación y analítica
  ('message.send',             'message',      'send',    'Enviar mensajes en nombre de la organización', 'ORGANIZATION'),
  ('analytics.read',           'analytics',    'read',    'Ver dashboards y reportes', 'ORGANIZATION'),

  -- Plataforma
  ('platform.manage_taxonomy', 'platform',     'manage_taxonomy',   'Administrar taxonomía, industrias y atributos', 'PLATFORM'),
  ('platform.review_accreditation','platform', 'review_accreditation','Revisar y validar acreditaciones', 'PLATFORM'),
  ('platform.moderate',        'platform',     'moderate',          'Moderar contenido y denuncias', 'PLATFORM'),
  ('platform.manage_plans',    'platform',     'manage_plans',      'Administrar planes y suscripciones', 'PLATFORM'),
  ('platform.impersonate',     'platform',     'impersonate',       'Impersonar usuarios (auditado)', 'PLATFORM')
on conflict (code) do update
  set resource    = excluded.resource,
      action      = excluded.action,
      description = excluded.description,
      scope       = excluded.scope;


-- ============================================================================
-- Roles de sistema
-- ============================================================================

insert into public.roles (code, name, description, scope, is_system, is_default_owner, sort_order) values
  -- Plataforma
  ('SUPER_ADMIN',            'Super administrador',      'Control total de la plataforma, incluida impersonación auditada', 'PLATFORM', true, false, 1),
  ('PLATFORM_ADMIN',         'Administrador plataforma', 'Backoffice, taxonomía, moderación y planes',                      'PLATFORM', true, false, 2),
  ('ACCREDITATION_REVIEWER', 'Revisor de acreditación',  'Revisa y valida la documentación de acreditación',                'PLATFORM', true, false, 3),
  ('SUPPORT_AGENT',          'Soporte',                  'Lectura de soporte, sin acceso a datos comerciales sensibles',    'PLATFORM', true, false, 4),

  -- Organización
  ('ORG_OWNER',           'Dueño de la cuenta',       'Control total de la organización, incluida facturación', 'ORGANIZATION', true, true,  10),
  ('ORG_ADMIN',           'Administrador',            'Equipo, perfil y configuración',                          'ORGANIZATION', true, false, 11),
  ('BUYER_MANAGER',       'Jefe de abastecimiento',   'Gestiona procesos y adjudica dentro de su límite',        'ORGANIZATION', true, false, 12),
  ('BUYER',               'Comprador',                'Crea requerimientos y procesos, sin adjudicar',           'ORGANIZATION', true, false, 13),
  ('PROCUREMENT_ANALYST', 'Analista de abastecimiento','Analítica, vendor list y comparación de ofertas',        'ORGANIZATION', true, false, 14),
  ('CONTRACT_MANAGER',    'Administrador de contrato','Contratos, SLA y evaluación de desempeño',                'ORGANIZATION', true, false, 15),
  ('EVALUATOR',           'Evaluador',                'Evalúa únicamente las ofertas que se le asignan',         'ORGANIZATION', true, false, 16),
  ('SUPPLIER_ADMIN',      'Administrador proveedor',  'Perfil, catálogo y acreditación',                         'ORGANIZATION', true, false, 17),
  ('SALES',               'Ventas',                   'Oportunidades, cotizaciones y mensajería',                'ORGANIZATION', true, false, 18),
  ('VIEWER',              'Solo lectura',             'Consulta sin capacidad de modificar',                     'ORGANIZATION', true, false, 19)
on conflict (code) where organization_id is null do update
  set name        = excluded.name,
      description = excluded.description,
      sort_order  = excluded.sort_order;


-- ============================================================================
-- Rol → permisos
-- ----------------------------------------------------------------------------
-- Se declara como una tabla de pares y se resuelve por código, para que este
-- bloque sea legible y auditable de un vistazo.
-- ============================================================================

with mapping (role_code, permission_code) as (
  values
    -- ── ORG_OWNER: todos los permisos de organización ──────────────────────
    ('ORG_OWNER', '*'),

    -- ── ORG_ADMIN ──────────────────────────────────────────────────────────
    ('ORG_ADMIN', 'organization.read'),
    ('ORG_ADMIN', 'organization.update'),
    ('ORG_ADMIN', 'member.read'),
    ('ORG_ADMIN', 'member.manage'),
    ('ORG_ADMIN', 'role.manage'),
    ('ORG_ADMIN', 'audit.read'),
    ('ORG_ADMIN', 'document.read'),
    ('ORG_ADMIN', 'document.write'),
    ('ORG_ADMIN', 'analytics.read'),
    ('ORG_ADMIN', 'message.send'),

    -- ── BUYER_MANAGER ──────────────────────────────────────────────────────
    ('BUYER_MANAGER', 'organization.read'),
    ('BUYER_MANAGER', 'member.read'),
    ('BUYER_MANAGER', 'requirement.read'),
    ('BUYER_MANAGER', 'requirement.write'),
    ('BUYER_MANAGER', 'sourcing_event.read'),
    ('BUYER_MANAGER', 'sourcing_event.create'),
    ('BUYER_MANAGER', 'sourcing_event.publish'),
    ('BUYER_MANAGER', 'sourcing_event.cancel'),
    ('BUYER_MANAGER', 'sourcing_event.open_bids'),
    ('BUYER_MANAGER', 'quotation.read'),
    ('BUYER_MANAGER', 'evaluation.read'),
    ('BUYER_MANAGER', 'evaluation.manage'),
    ('BUYER_MANAGER', 'negotiation.manage'),
    ('BUYER_MANAGER', 'award.create'),
    ('BUYER_MANAGER', 'award.approve'),
    ('BUYER_MANAGER', 'vendor_list.read'),
    ('BUYER_MANAGER', 'vendor_list.manage'),
    ('BUYER_MANAGER', 'contract.read'),
    ('BUYER_MANAGER', 'performance.review'),
    ('BUYER_MANAGER', 'analytics.read'),
    ('BUYER_MANAGER', 'message.send'),

    -- ── BUYER: crea procesos, NO adjudica ni abre ofertas selladas ─────────
    ('BUYER', 'organization.read'),
    ('BUYER', 'requirement.read'),
    ('BUYER', 'requirement.write'),
    ('BUYER', 'sourcing_event.read'),
    ('BUYER', 'sourcing_event.create'),
    ('BUYER', 'sourcing_event.publish'),
    ('BUYER', 'quotation.read'),
    ('BUYER', 'evaluation.read'),
    ('BUYER', 'vendor_list.read'),
    ('BUYER', 'analytics.read'),
    ('BUYER', 'message.send'),

    -- ── PROCUREMENT_ANALYST: analiza, no ejecuta ───────────────────────────
    ('PROCUREMENT_ANALYST', 'organization.read'),
    ('PROCUREMENT_ANALYST', 'requirement.read'),
    ('PROCUREMENT_ANALYST', 'sourcing_event.read'),
    ('PROCUREMENT_ANALYST', 'quotation.read'),
    ('PROCUREMENT_ANALYST', 'evaluation.read'),
    ('PROCUREMENT_ANALYST', 'vendor_list.read'),
    ('PROCUREMENT_ANALYST', 'vendor_list.manage'),
    ('PROCUREMENT_ANALYST', 'contract.read'),
    ('PROCUREMENT_ANALYST', 'analytics.read'),

    -- ── CONTRACT_MANAGER ───────────────────────────────────────────────────
    ('CONTRACT_MANAGER', 'organization.read'),
    ('CONTRACT_MANAGER', 'contract.read'),
    ('CONTRACT_MANAGER', 'contract.manage'),
    ('CONTRACT_MANAGER', 'performance.review'),
    ('CONTRACT_MANAGER', 'document.read'),
    ('CONTRACT_MANAGER', 'vendor_list.read'),
    ('CONTRACT_MANAGER', 'analytics.read'),
    ('CONTRACT_MANAGER', 'message.send'),

    -- ── EVALUATOR: solo evalúa lo asignado ─────────────────────────────────
    ('EVALUATOR', 'organization.read'),
    ('EVALUATOR', 'sourcing_event.read'),
    ('EVALUATOR', 'evaluation.read'),
    ('EVALUATOR', 'evaluation.perform'),

    -- ── SUPPLIER_ADMIN ─────────────────────────────────────────────────────
    ('SUPPLIER_ADMIN', 'organization.read'),
    ('SUPPLIER_ADMIN', 'organization.update'),
    ('SUPPLIER_ADMIN', 'member.read'),
    ('SUPPLIER_ADMIN', 'offering.read'),
    ('SUPPLIER_ADMIN', 'offering.write'),
    ('SUPPLIER_ADMIN', 'offering.publish'),
    ('SUPPLIER_ADMIN', 'offering.delete'),
    ('SUPPLIER_ADMIN', 'document.read'),
    ('SUPPLIER_ADMIN', 'document.write'),
    ('SUPPLIER_ADMIN', 'document.delete'),
    ('SUPPLIER_ADMIN', 'accreditation.submit'),
    ('SUPPLIER_ADMIN', 'quotation.read'),
    ('SUPPLIER_ADMIN', 'quotation.write'),
    ('SUPPLIER_ADMIN', 'quotation.submit'),
    ('SUPPLIER_ADMIN', 'analytics.read'),
    ('SUPPLIER_ADMIN', 'message.send'),

    -- ── SALES ──────────────────────────────────────────────────────────────
    ('SALES', 'organization.read'),
    ('SALES', 'offering.read'),
    ('SALES', 'offering.write'),
    ('SALES', 'quotation.read'),
    ('SALES', 'quotation.write'),
    ('SALES', 'quotation.submit'),
    ('SALES', 'analytics.read'),
    ('SALES', 'message.send'),

    -- ── VIEWER ─────────────────────────────────────────────────────────────
    ('VIEWER', 'organization.read'),
    ('VIEWER', 'member.read'),
    ('VIEWER', 'offering.read'),
    ('VIEWER', 'requirement.read'),
    ('VIEWER', 'sourcing_event.read'),
    ('VIEWER', 'vendor_list.read'),
    ('VIEWER', 'contract.read'),

    -- ── Roles de plataforma ────────────────────────────────────────────────
    ('SUPER_ADMIN', '*'),
    ('PLATFORM_ADMIN', 'platform.manage_taxonomy'),
    ('PLATFORM_ADMIN', 'platform.moderate'),
    ('PLATFORM_ADMIN', 'platform.manage_plans'),
    ('PLATFORM_ADMIN', 'platform.review_accreditation'),
    ('ACCREDITATION_REVIEWER', 'platform.review_accreditation'),
    ('SUPPORT_AGENT', 'organization.read')
)
insert into public.role_permissions (role_id, permission_code)
select r.id, p.code
from mapping m
join public.roles r
  on r.code = m.role_code
 and r.organization_id is null
join public.permissions p
  on (m.permission_code = '*' and p.scope = r.scope)
  or  p.code = m.permission_code
on conflict (role_id, permission_code) do nothing;


-- El comodín '*' de ORG_OWNER cubre los permisos de organización.
-- SUPER_ADMIN necesita además todos los de plataforma y viceversa:
-- es el único rol verdaderamente irrestricto.
insert into public.role_permissions (role_id, permission_code)
select r.id, p.code
from public.roles r
cross join public.permissions p
where r.code = 'SUPER_ADMIN' and r.organization_id is null
on conflict (role_id, permission_code) do nothing;
