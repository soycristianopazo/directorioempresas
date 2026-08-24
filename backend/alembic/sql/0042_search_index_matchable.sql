-- ============================================================================
-- 0042 · supplier_search_index gana is_matchable (fase 6 — Recall del motor)
-- ----------------------------------------------------------------------------
-- 0030_search_index.sql ya está aplicada (fase 4) — no se edita, se agrega
-- una columna hacia adelante. Su propio comentario ("is_public... no cubre
-- visibilidad graduada... fuera de alcance de esta pasada") ya anticipaba
-- exactamente este momento.
--
-- La Etapa 1 (Recall) del motor de matching corre para un COMPRADOR
-- AUTENTICADO, no para un visitante anónimo — is_public (PUBLIC only) no
-- alcanza. app.can_view_with_visibility() ya resuelve REGISTERED→cualquier
-- usuario logueado y BUYERS_ONLY→cualquier organización con capacidad
-- BUYER (que es exactamente quien corre un sourcing_event); INVITED_ONLY y
-- PRIVATE siguen sin ser matcheables por Recall — esos requieren invitación
-- explícita (fase 7), no descubrimiento.
-- ============================================================================

alter table public.supplier_search_index
  add column is_matchable boolean not null default false;

comment on column public.supplier_search_index.is_matchable is
  'Precalculado = visible para cualquier comprador autenticado (offering+org ACTIVE, visibility PUBLIC/REGISTERED/BUYERS_ONLY). Superconjunto de is_public — úsalo para Recall de matching, no is_public.';

-- Backfill: misma condición base que is_public (ACTIVE + no borrado, ambos
-- lados), pero con visibility relajada a los tres niveles que resuelven
-- true para cualquier comprador logueado.
update public.supplier_search_index si
set is_matchable = (
  so.status = 'ACTIVE' and so.deleted_at is null
  and so.visibility in ('PUBLIC', 'REGISTERED', 'BUYERS_ONLY')
  and o.status = 'ACTIVE'
  and o.visibility in ('PUBLIC', 'REGISTERED', 'BUYERS_ONLY')
)
from public.supplier_offerings so
join public.organizations o on o.id = so.organization_id
where so.id = si.offering_id;

create index supplier_search_index_matchable_idx
  on public.supplier_search_index (is_matchable)
  where is_matchable;
