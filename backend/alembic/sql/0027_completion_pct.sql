-- ============================================================================
-- 0027 · Motor de completitud de perfil
-- ----------------------------------------------------------------------------
-- Fase 3.5 del roadmap.
--
-- Se implementa como una función SQL pura, no como triggers repartidos en
-- ocho tablas: mantener un trigger de recálculo en cada tabla que afecta la
-- completitud (locations, contacts, media, industries, territories,
-- offerings, certifications, case_studies) es frágil — agregar una tabla
-- nueva que afecte completitud significa acordarse de agregarle el trigger
-- también, y ese "acordarse" es exactamente el tipo de acoplamiento a
-- distancia que este proyecto evita en otros lados (ver 0009: los permisos
-- de fases futuras se siembran de antemano en vez de tener que tocar código
-- viejo cuando llega la fase). En cambio: una función pura, invocada por el
-- servicio de aplicación al final de cada mutación relevante (ver
-- backend/app/services/completion.py) — el mismo patrón que usa el resto de
-- la capa de servicio para "hacer algo después de mutar dentro de la misma
-- transacción".
-- ============================================================================

create or replace function app.compute_completion_pct(p_organization_id uuid)
returns smallint
language sql
stable
as $$
  select (
    -- Perfil básico: 20
    (case when exists (
      select 1 from public.organizations o
      where o.id = p_organization_id
        and o.short_description is not null
        and o.description is not null
        and o.value_proposition is not null
    ) then 20 else 0 end)
    -- Al menos una ubicación: 10
    + (case when exists (
        select 1 from public.organization_locations l
        where l.organization_id = p_organization_id and l.is_active
      ) then 10 else 0 end)
    -- Al menos un contacto: 10
    + (case when exists (
        select 1 from public.organization_contacts c
        where c.organization_id = p_organization_id and c.is_active
      ) then 10 else 0 end)
    -- Logo: 10
    + (case when exists (
        select 1 from public.organization_media m
        where m.organization_id = p_organization_id and m.media_type = 'LOGO'
      ) then 10 else 0 end)
    -- Al menos una industria: 10
    + (case when exists (
        select 1 from public.organization_industries oi
        where oi.organization_id = p_organization_id
      ) then 10 else 0 end)
    -- Al menos un territorio: 10
    + (case when exists (
        select 1 from public.organization_territories ot
        where ot.organization_id = p_organization_id
      ) then 10 else 0 end)
    -- Al menos una oferta publicada: 20 (el paso más importante para un proveedor)
    + (case when exists (
        select 1 from public.supplier_offerings so
        where so.organization_id = p_organization_id
          and so.status = 'ACTIVE'
          and so.deleted_at is null
      ) then 20 else 0 end)
    -- Al menos una certificación o caso de éxito: 10
    + (case when exists (
        select 1 from public.organization_certifications oc where oc.organization_id = p_organization_id
        union all
        select 1 from public.case_studies cs where cs.organization_id = p_organization_id
      ) then 10 else 0 end)
  )::smallint;
$$;

comment on function app.compute_completion_pct(uuid) is
  'Completitud de perfil (0-100), ponderada por sección. Se invoca desde el servicio de aplicación tras cada mutación relevante — ver services/completion.py.';

grant execute on function app.compute_completion_pct(uuid) to app_user;
