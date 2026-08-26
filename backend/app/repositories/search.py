"""Motor de búsqueda: reindexado de supplier_search_index y consultas
facetadas. Casi todo por SQL crudo — es exactamente el tipo de trabajo
(agregación, tsvector, arrays, jsonb) para el que el ORM no aporta nada.

Gotcha heredado de fase 2 (documentado en extenso en
0012_admin_divisions.sql): `app_user` no tiene `extensions` en su
search_path, así que `unaccent()` va siempre calificado `extensions.unaccent(...)`.
"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_REINDEX_OFFERING_SQL = text(
    """
    with agg as (
      select
        so.id as offering_id,
        so.organization_id,
        so.name,
        so.short_description,
        so.full_description,
        so.specifications,
        so.applications,
        so.offering_type,
        so.availability_status,
        so.status as offering_status,
        so.visibility as offering_visibility,
        so.deleted_at as offering_deleted_at,
        o.legal_name,
        o.trade_name,
        o.status as org_status,
        o.visibility as org_visibility,
        o.completion_pct,
        op.price_type
      from public.supplier_offerings so
      join public.organizations o on o.id = so.organization_id
      left join public.offering_pricing op on op.offering_id = so.id
      where so.id = :offering_id
    ),
    nodes as (
      select
        otn.offering_id,
        coalesce(array_agg(distinct otn.node_id), '{}') as node_ids,
        coalesce(string_agg(distinct tn.name, ' '), '') as node_names,
        coalesce(string_agg(distinct tns.synonym, ' '), '') as synonyms
      from public.offering_taxonomy_nodes otn
      join public.taxonomy_nodes tn on tn.id = otn.node_id
      left join public.taxonomy_node_synonyms tns on tns.node_id = tn.id
      where otn.offering_id = :offering_id
      group by otn.offering_id
    ),
    industries as (
      select
        oi.offering_id,
        coalesce(array_agg(distinct oi.industry_id), '{}') as industry_ids,
        coalesce(string_agg(distinct i.name, ' '), '') as industry_names
      from public.offering_industries oi
      join public.industries i on i.id = oi.industry_id
      where oi.offering_id = :offering_id
      group by oi.offering_id
    ),
    territories as (
      select
        ot.offering_id,
        coalesce(array_agg(distinct ot.admin_division_id), '{}') as division_ids
      from public.offering_territories ot
      where ot.offering_id = :offering_id
      group by ot.offering_id
    ),
    attrs as (
      select
        v.offering_id,
        coalesce(
          jsonb_object_agg(ad.code, av.attr_value) filter (where ad.is_filterable),
          '{}'::jsonb
        ) as attributes
      from public.offering_attribute_values v
      join public.attribute_definitions ad on ad.id = v.attribute_definition_id
      left join public.attribute_options opt on opt.id = v.option_id
      left join lateral (
        select array_agg(ao.value) as values
        from public.offering_attribute_option_values oaov
        join public.attribute_options ao on ao.id = oaov.option_id
        where oaov.offering_attribute_value_id = v.id
      ) multi on true
      cross join lateral (
        select case ad.data_type
          when 'TEXT' then to_jsonb(v.value_text)
          when 'NUMBER' then to_jsonb(v.value_number)
          when 'BOOLEAN' then to_jsonb(v.value_boolean)
          when 'DATE' then to_jsonb(v.value_date)
          when 'SELECT' then to_jsonb(opt.value)
          when 'MULTISELECT' then to_jsonb(multi.values)
          else 'null'::jsonb
        end as attr_value
      ) av
      where v.offering_id = :offering_id
      group by v.offering_id
    )
    insert into public.supplier_search_index (
      offering_id, organization_id, search_vector,
      taxonomy_node_ids, industry_ids, admin_division_ids, attributes,
      offering_type, availability_status, price_type, is_public, is_matchable,
      completion_pct, updated_at
    )
    select
      agg.offering_id,
      agg.organization_id,
      setweight(to_tsvector('spanish', extensions.unaccent(coalesce(agg.name, ''))), 'A')
      || setweight(
           to_tsvector('spanish', extensions.unaccent(
             coalesce(agg.short_description, '') || ' ' ||
             coalesce(nodes.node_names, '') || ' ' ||
             coalesce(nodes.synonyms, '') || ' ' ||
             coalesce(industries.industry_names, '')
           )),
           'B'
         )
      || setweight(
           to_tsvector('spanish', extensions.unaccent(
             coalesce(agg.full_description, '') || ' ' ||
             coalesce(agg.specifications, '') || ' ' ||
             coalesce(agg.applications, '')
           )),
           'C'
         )
      || setweight(
           to_tsvector('spanish', extensions.unaccent(coalesce(agg.trade_name, agg.legal_name, ''))),
           'D'
         ) as search_vector,
      coalesce(nodes.node_ids, '{}'),
      coalesce(industries.industry_ids, '{}'),
      coalesce(territories.division_ids, '{}'),
      coalesce(attrs.attributes, '{}'::jsonb),
      agg.offering_type,
      agg.availability_status,
      agg.price_type,
      (
        agg.offering_status = 'ACTIVE' and agg.offering_deleted_at is null
        and agg.offering_visibility = 'PUBLIC'
        and agg.org_status = 'ACTIVE' and agg.org_visibility = 'PUBLIC'
      ),
      (
        agg.offering_status = 'ACTIVE' and agg.offering_deleted_at is null
        and agg.offering_visibility in ('PUBLIC', 'REGISTERED', 'BUYERS_ONLY')
        and agg.org_status = 'ACTIVE' and agg.org_visibility in ('PUBLIC', 'REGISTERED', 'BUYERS_ONLY')
      ),
      agg.completion_pct,
      now()
    from agg
    left join nodes on nodes.offering_id = agg.offering_id
    left join industries on industries.offering_id = agg.offering_id
    left join territories on territories.offering_id = agg.offering_id
    left join attrs on attrs.offering_id = agg.offering_id
    on conflict (offering_id) do update set
      organization_id = excluded.organization_id,
      search_vector = excluded.search_vector,
      taxonomy_node_ids = excluded.taxonomy_node_ids,
      industry_ids = excluded.industry_ids,
      admin_division_ids = excluded.admin_division_ids,
      attributes = excluded.attributes,
      offering_type = excluded.offering_type,
      availability_status = excluded.availability_status,
      price_type = excluded.price_type,
      is_public = excluded.is_public,
      is_matchable = excluded.is_matchable,
      completion_pct = excluded.completion_pct,
      updated_at = excluded.updated_at
    """
)


async def reindex_offering(session: AsyncSession, offering_id: UUID) -> None:
    await session.execute(_REINDEX_OFFERING_SQL, {"offering_id": str(offering_id)})


async def reindex_org_offerings(session: AsyncSession, organization_id: UUID) -> None:
    result = await session.execute(
        text(
            "select id from public.supplier_offerings where organization_id = :org_id"
        ),
        {"org_id": str(organization_id)},
    )
    for row in result:
        await reindex_offering(session, row.id)


async def update_completion_pct_for_org(
    session: AsyncSession, organization_id: UUID, completion_pct: int
) -> None:
    """Actualización liviana: solo el número de ranking, sin recalcular
    tsvector/arrays/atributos — evitar un reindexado completo en cada
    recompute_completion_pct(), que corre mucho más seguido que un cambio
    real de contenido buscable."""
    await session.execute(
        text(
            "update public.supplier_search_index "
            "set completion_pct = :pct, updated_at = now() "
            "where organization_id = :org_id"
        ),
        {"pct": completion_pct, "org_id": str(organization_id)},
    )


async def all_offering_ids(session: AsyncSession) -> list[UUID]:
    """Para el script de reconciliación completa (reindex_search.py)."""
    result = await session.execute(text("select id from public.supplier_offerings"))
    return [row.id for row in result]


def _build_filters(
    *,
    query: str | None,
    taxonomy_node_ids: list[UUID] | None,
    industry_ids: list[UUID] | None,
    admin_division_ids: list[UUID] | None,
    offering_type: str | None,
    availability_status: str | None,
) -> tuple[list[str], dict[str, object]]:
    conditions = ["si.is_public"]
    params: dict[str, object] = {}

    if query:
        conditions.append(
            "si.search_vector @@ websearch_to_tsquery('spanish', extensions.unaccent(:q))"
        )
        params["q"] = query
    if taxonomy_node_ids:
        conditions.append("si.taxonomy_node_ids && cast(:node_ids as uuid[])")
        params["node_ids"] = [str(x) for x in taxonomy_node_ids]
    if industry_ids:
        conditions.append("si.industry_ids && cast(:industry_ids as uuid[])")
        params["industry_ids"] = [str(x) for x in industry_ids]
    if admin_division_ids:
        conditions.append("si.admin_division_ids && cast(:division_ids as uuid[])")
        params["division_ids"] = [str(x) for x in admin_division_ids]
    if offering_type:
        conditions.append("si.offering_type = :offering_type")
        params["offering_type"] = offering_type
    if availability_status:
        conditions.append("si.availability_status = :availability_status")
        params["availability_status"] = availability_status

    return conditions, params


async def search_offerings(
    session: AsyncSession,
    *,
    query: str | None = None,
    taxonomy_node_ids: list[UUID] | None = None,
    industry_ids: list[UUID] | None = None,
    admin_division_ids: list[UUID] | None = None,
    offering_type: str | None = None,
    availability_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    conditions, params = _build_filters(
        query=query,
        taxonomy_node_ids=taxonomy_node_ids,
        industry_ids=industry_ids,
        admin_division_ids=admin_division_ids,
        offering_type=offering_type,
        availability_status=availability_status,
    )
    where_clause = " and ".join(conditions)

    rank_expr = (
        "ts_rank(si.search_vector, websearch_to_tsquery('spanish', extensions.unaccent(:q)))"
        if query
        else "0"
    )

    # count(*) y la página de resultados iban en 2 consultas secuenciales —
    # con la latencia de red hacia la base remota (~0.6-0.9s por round trip
    # medido en vivo, ver hallazgo de la página /discover) eso duplicaba el
    # costo de red por nada. count(*) over() trae el total en la MISMA fila
    # que cada resultado, un solo round trip. Si la página no trae filas
    # (offset más allá del total, o 0 resultados) no hay de dónde leer el
    # total — pero en ese caso el total real de esta misma búsqueda es 0.
    params["limit"] = page_size
    params["offset"] = max(page - 1, 0) * page_size
    result = await session.execute(
        text(
            f"""
            select
              si.offering_id, si.organization_id,
              so.name as offering_name, so.slug as offering_slug,
              so.short_description, so.offering_type, so.availability_status,
              o.legal_name, o.trade_name, o.slug as organization_slug,
              si.completion_pct,
              op.price_type, op.amount_min, op.amount_max, op.currency_code,
              op.unit_code, op.is_public as pricing_is_public,
              comuna.name as comuna, coalesce(acc.is_accredited, false) as is_accredited,
              img.storage_path as image_path,
              deal.deal_price, deal.original_price as deal_original_price,
              deal.currency_code as deal_currency_code,
              deal.stock_quantity as deal_stock_quantity,
              deal.stock_remaining as deal_stock_remaining,
              deal.expires_at as deal_expires_at,
              count(*) over() as total_count,
              {rank_expr} as rank
            from public.supplier_search_index si
            join public.supplier_offerings so on so.id = si.offering_id
            join public.organizations o on o.id = si.organization_id
            left join public.offering_pricing op on op.offering_id = si.offering_id
            left join lateral (
              select om.storage_path
              from public.offering_media om
              where om.offering_id = si.offering_id
              order by om.sort_order
              limit 1
            ) img on true
            left join lateral (
              select od.deal_price, od.original_price, od.currency_code,
                     od.stock_quantity, od.stock_remaining, od.expires_at
              from public.offering_deals od
              where od.offering_id = si.offering_id
                and od.cancelled_at is null
                and (od.expires_at is null or od.expires_at > now())
                and (od.stock_quantity is null or od.stock_remaining > 0)
              order by od.created_at desc
              limit 1
            ) deal on true
            left join lateral (
              select ol.admin_division_id
              from public.organization_locations ol
              where ol.organization_id = o.id and ol.is_active
              order by ol.is_headquarters desc, ol.created_at
              limit 1
            ) hq_loc on true
            left join lateral (
              with recursive ancestors as (
                select id, parent_id, level_name, name
                from public.admin_divisions where id = hq_loc.admin_division_id
                union all
                select ad.id, ad.parent_id, ad.level_name, ad.name
                from public.admin_divisions ad
                join ancestors a on ad.id = a.parent_id
              )
              select name from ancestors where level_name = 'COMUNA' limit 1
            ) comuna on true
            left join lateral (
              select exists (
                select 1 from public.organization_badges ob
                join public.badge_definitions bd on bd.id = ob.badge_id
                where ob.organization_id = o.id
                  and ob.revoked_at is null
                  and bd.code = 'ACREDITADO_BASE'
              ) as is_accredited
            ) acc on true
            where {where_clause}
            order by rank desc, si.completion_pct desc, si.updated_at desc
            limit :limit offset :offset
            """
        ),
        params,
    )
    rows = [dict(row._mapping) for row in result]
    total = rows[0]["total_count"] if rows else 0
    for row in rows:
        del row["total_count"]
    return rows, total


async def facet_counts(
    session: AsyncSession,
    *,
    query: str | None = None,
    taxonomy_node_ids: list[UUID] | None = None,
    industry_ids: list[UUID] | None = None,
    admin_division_ids: list[UUID] | None = None,
    offering_type: str | None = None,
    availability_status: str | None = None,
) -> dict[str, list[dict]]:
    """Conteos sobre el mismo conjunto filtrado — simplificación consciente:
    no excluye la propia dimensión al contarla (ver plan de fase 4)."""
    conditions, params = _build_filters(
        query=query,
        taxonomy_node_ids=taxonomy_node_ids,
        industry_ids=industry_ids,
        admin_division_ids=admin_division_ids,
        offering_type=offering_type,
        availability_status=availability_status,
    )
    where_clause = " and ".join(conditions)

    # Un solo round trip para las 3 dimensiones (antes: 3 consultas
    # secuenciales) — con latencia de red no trivial hacia la base, cada
    # round trip evitado importa tanto como el plan de la consulta misma.
    result = await session.execute(
        text(
            f"""
            select 'taxonomy_nodes' as dimension, node.name as label, node.id as value, count(*) as count
            from public.supplier_search_index si
            join public.taxonomy_nodes node on node.id = any(si.taxonomy_node_ids)
            where {where_clause}
            group by node.name, node.id
            union all
            select 'industries', node.name, node.id, count(*)
            from public.supplier_search_index si
            join public.industries node on node.id = any(si.industry_ids)
            where {where_clause}
            group by node.name, node.id
            union all
            select 'admin_divisions', node.name, node.id, count(*)
            from public.supplier_search_index si
            join public.admin_divisions node on node.id = any(si.admin_division_ids)
            where {where_clause}
            group by node.name, node.id
            """
        ),
        params,
    )
    facets: dict[str, list[dict]] = {
        "taxonomy_nodes": [],
        "industries": [],
        "admin_divisions": [],
    }
    for row in result:
        r = row._mapping
        facets[r["dimension"]].append(
            {"label": r["label"], "value": r["value"], "count": r["count"]}
        )
    for key in facets:
        facets[key].sort(key=lambda f: f["count"], reverse=True)
        facets[key] = facets[key][:20]
    return facets


# ─── Analítica ──────────────────────────────────────────────────────────────
# Escrita siempre en sesión de sistema (session_for_system): el visitante
# anónimo que dispara estos inserts no tiene permiso propio para escribir —
# ver services/search.py.


async def log_search(
    session: AsyncSession,
    *,
    query_text: str | None,
    filters: dict,
    result_count: int,
    searching_organization_id: UUID | None,
) -> None:
    await session.execute(
        text(
            "insert into public.search_logs "
            "(query_text, filters, result_count, searching_organization_id) "
            "values (:query_text, cast(:filters as jsonb), :result_count, :org_id)"
        ),
        {
            "query_text": (query_text or "")[:500] or None,
            "filters": json.dumps(filters),
            "result_count": result_count,
            "org_id": (
                str(searching_organization_id) if searching_organization_id else None
            ),
        },
    )


async def record_impressions(
    session: AsyncSession, offerings: list[tuple[UUID, UUID]]
) -> None:
    """`offerings`: pares (offering_id, organization_id) mostrados en una
    página de resultados. Incrementa el agregado del día vía upsert — un
    solo round trip con unnest() en vez de un insert por fila (antes: hasta
    page_size round trips secuenciales, el costo dominante de una búsqueda
    con latencia de red no trivial hacia la base)."""
    if not offerings:
        return
    offering_ids = [str(offering_id) for offering_id, _ in offerings]
    organization_ids = [str(organization_id) for _, organization_id in offerings]
    await session.execute(
        text(
            "insert into public.search_impressions "
            "(day, organization_id, offering_id, impression_count) "
            "select current_date, org_id, offering_id, 1 "
            "from unnest(cast(:org_ids as uuid[]), cast(:offering_ids as uuid[])) "
            "as pairs(org_id, offering_id) "
            "on conflict (day, organization_id, offering_id) "
            "do update set impression_count = search_impressions.impression_count + 1"
        ),
        {"org_ids": organization_ids, "offering_ids": offering_ids},
    )


async def _seen_today(
    session: AsyncSession, table: str, id_column: str, id_value: UUID, visitor_hash: str
) -> bool:
    result = await session.execute(
        text(
            f"select exists(select 1 from public.{table} "
            f"where {id_column} = :id_value and visitor_hash = :visitor_hash "
            "and created_at >= current_date)"
        ),
        {"id_value": str(id_value), "visitor_hash": visitor_hash},
    )
    return bool(result.scalar_one())


async def record_profile_view(
    session: AsyncSession,
    *,
    organization_id: UUID,
    viewer_organization_id: UUID | None,
    source: str | None,
    visitor_hash: str | None,
) -> None:
    is_unique = True
    if visitor_hash:
        is_unique = not await _seen_today(
            session, "profile_views", "organization_id", organization_id, visitor_hash
        )
    await session.execute(
        text(
            "insert into public.profile_views "
            "(organization_id, viewer_organization_id, source, visitor_hash, is_unique) "
            "values (:org_id, :viewer_org_id, :source, :visitor_hash, :is_unique)"
        ),
        {
            "org_id": str(organization_id),
            "viewer_org_id": (
                str(viewer_organization_id) if viewer_organization_id else None
            ),
            "source": (source or "")[:200] or None,
            "visitor_hash": visitor_hash,
            "is_unique": is_unique,
        },
    )


async def record_offering_views(
    session: AsyncSession,
    *,
    offering_ids: list[UUID],
    organization_id: UUID,
    viewer_organization_id: UUID | None,
    visitor_hash: str | None,
) -> None:
    """Antes: un `_seen_today` + un insert POR offering — para el catálogo de
    un proveedor, hasta 2×N round trips secuenciales contra la base remota,
    disparados en background por cada visita a la ficha (app/api/public.py).
    Ahora: 1 select batch para saber qué offerings ya vio este visitante hoy
    + 1 insert multi-fila (executemany) — 2 round trips sin importar N."""
    if not offering_ids:
        return
    # str(...), no uuid.UUID, para comparar contra asyncpg: SQL crudo sobre
    # una columna uuid devuelve el tipo propio de asyncpg, no uuid.UUID (ver
    # comentario de run_matching en services/matching.py) — normalizar a str
    # de los dos lados es lo único que garantiza que el `in` de abajo compare
    # lo mismo.
    seen_ids: set[str] = set()
    if visitor_hash:
        result = await session.execute(
            text(
                "select offering_id from public.offering_views "
                "where offering_id = any(cast(:ids as uuid[])) "
                "and visitor_hash = :visitor_hash and created_at >= current_date"
            ),
            {
                "ids": [str(i) for i in offering_ids],
                "visitor_hash": visitor_hash,
            },
        )
        seen_ids = {str(row.offering_id) for row in result}

    rows = [
        {
            "offering_id": str(offering_id),
            "org_id": str(organization_id),
            "viewer_org_id": (
                str(viewer_organization_id) if viewer_organization_id else None
            ),
            "visitor_hash": visitor_hash,
            "is_unique": str(offering_id) not in seen_ids,
        }
        for offering_id in offering_ids
    ]
    await session.execute(
        text(
            "insert into public.offering_views "
            "(offering_id, organization_id, viewer_organization_id, visitor_hash, is_unique) "
            "values (:offering_id, :org_id, :viewer_org_id, :visitor_hash, :is_unique)"
        ),
        rows,
    )
