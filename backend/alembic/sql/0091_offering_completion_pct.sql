-- ============================================================================
-- 0091 · Motor de completitud de publicaciones del catálogo
-- ----------------------------------------------------------------------------
-- Mismo patrón que 0027_completion_pct.sql (completitud de organización):
-- función SQL pura, invocada por el servicio de aplicación tras cada mutación
-- relevante (ver backend/app/services/offerings.py), en vez de triggers
-- repartidos por cada tabla que afecta la completitud de una oferta.
-- ============================================================================

alter table public.supplier_offerings
  add column completion_pct smallint not null default 0;

create or replace function app.compute_offering_completion_pct(p_offering_id uuid)
returns smallint
language sql
stable
as $$
  select (
    -- Descripción completa: 15
    (case when exists (
      select 1 from public.supplier_offerings so
      where so.id = p_offering_id and so.full_description is not null
    ) then 15 else 0 end)
    -- Al menos una categoría: 20 (lo que más pesa en poder ser encontrado)
    + (case when exists (
        select 1 from public.offering_taxonomy_nodes otn
        where otn.offering_id = p_offering_id
      ) then 20 else 0 end)
    -- Al menos una foto: 20 (confianza visual, el mayor salto de calidad percibida)
    + (case when exists (
        select 1 from public.offering_media om
        where om.offering_id = p_offering_id
      ) then 20 else 0 end)
    -- Precio informado (aunque sea "a solicitud" declarado explícitamente): 15
    + (case when exists (
        select 1 from public.offering_pricing op
        where op.offering_id = p_offering_id
      ) then 15 else 0 end)
    -- Al menos un hashtag: 10
    + (case when exists (
        select 1 from public.offering_tags ot
        where ot.offering_id = p_offering_id
      ) then 10 else 0 end)
    -- Especificaciones o marca/modelo: 10
    + (case when exists (
        select 1 from public.supplier_offerings so
        where so.id = p_offering_id
          and (so.specifications is not null or so.brand is not null or so.model is not null)
      ) then 10 else 0 end)
    -- Al menos una industria declarada: 10
    + (case when exists (
        select 1 from public.offering_industries oi
        where oi.offering_id = p_offering_id
      ) then 10 else 0 end)
  )::smallint;
$$;

comment on function app.compute_offering_completion_pct(uuid) is
  'Completitud de una publicación del catálogo (0-100), ponderada por sección. Se invoca desde services/offerings.py tras cada mutación relevante — mismo patrón que app.compute_completion_pct (0027) a nivel de organización.';

grant execute on function app.compute_offering_completion_pct(uuid) to app_user;

-- Backfill de las ofertas ya existentes.
update public.supplier_offerings
set completion_pct = app.compute_offering_completion_pct(id);
