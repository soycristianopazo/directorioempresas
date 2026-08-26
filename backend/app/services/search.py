"""Motor de búsqueda: reindexado (llamado desde otros servicios tras
mutaciones relevantes, en la MISMA transacción — mismo patrón que
services/completion.py) y descubrimiento público (búsqueda + perfil de
organización), consumido tanto por las páginas Jinja2 (app/api/public.py)
como por la API JSON (/api/discover/*, para la SPA de comprador).

Las lecturas públicas no verifican permiso en Python — RLS ya resuelve qué
es visible para un visitante anónimo (o autenticado) directamente en el
SELECT. Estas funciones llaman a los mismos repositorios que usa la API
autenticada, solo que con una sesión pública/de sistema en vez de una con
un usuario dueño de la organización.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import public_url
from app.db.rls import gather_for_user, session_for_system, session_for_user
from app.repositories import credentials as credentials_repo
from app.repositories import offerings as offerings_repo
from app.repositories import organization_profile as profile_repo
from app.repositories import badges as badges_repo
from app.repositories import organizations as organizations_repo
from app.repositories import reference as reference_repo
from app.repositories import search as search_repo

MEDIA_BUCKET = "org-media"

# ─── Reindexado ──────────────────────────────────────────────────────────────
# Llamado desde services/offerings.py, services/organization_profile.py y
# services/completion.py, reusando la MISMA sesión/transacción de la
# mutación que lo dispara — así el reindexado ve los cambios recién hechos
# sin depender de un commit cruzado entre conexiones (mismo cuidado que
# recompute_completion_pct con autoflush=False: si la mutación es solo ORM,
# hace falta un flush() antes de que este SQL crudo la vea).


async def reindex_offering(db: AsyncSession, offering_id: UUID) -> None:
    # SessionLocal corre con autoflush=False en todo el proyecto — sin este
    # flush, una mutación ORM pendiente (offering.status = "ACTIVE", por
    # ejemplo) no es visible todavía para el SQL crudo de abajo. Mismo
    # cuidado exacto que recompute_completion_pct en services/completion.py.
    await db.flush()
    await search_repo.reindex_offering(db, offering_id)


async def reindex_org_offerings(db: AsyncSession, organization_id: UUID) -> None:
    await db.flush()
    await search_repo.reindex_org_offerings(db, organization_id)


# ─── Búsqueda pública ────────────────────────────────────────────────────────


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
    searching_organization_id: UUID | None = None,
    log: bool = True,
    background_tasks: BackgroundTasks | None = None,
) -> dict:
    results, total = await search_repo.search_offerings(
        session,
        query=query,
        taxonomy_node_ids=taxonomy_node_ids,
        industry_ids=industry_ids,
        admin_division_ids=admin_division_ids,
        offering_type=offering_type,
        availability_status=availability_status,
        page=page,
        page_size=page_size,
    )
    for r in results:
        image_path = r.pop("image_path", None)
        r["image_url"] = (
            public_url(bucket=MEDIA_BUCKET, path=image_path) if image_path else None
        )
    facets = await search_repo.facet_counts(
        session,
        query=query,
        taxonomy_node_ids=taxonomy_node_ids,
        industry_ids=industry_ids,
        admin_division_ids=admin_division_ids,
        offering_type=offering_type,
        availability_status=availability_status,
    )

    if log:
        filters = {
            "taxonomy_node_ids": [str(x) for x in (taxonomy_node_ids or [])],
            "industry_ids": [str(x) for x in (industry_ids or [])],
            "admin_division_ids": [str(x) for x in (admin_division_ids or [])],
            "offering_type": offering_type,
            "availability_status": availability_status,
        }
        # Registrar la búsqueda y las impresiones es puro analytics, a nadie
        # que está esperando resultados le importa que termine antes de ver
        # la página — pero antes se hacía `await` acá mismo, sumando 2
        # round trips más a una base remota de ~0.6-0.9s cada uno (medido en
        # vivo) al camino crítico de /discover. Con `background_tasks` (lo
        # pasan las rutas de FastAPI) corre DESPUÉS de responder; sin él
        # (llamadas fuera de un request, tests) cae al await de siempre.
        if background_tasks is not None:
            background_tasks.add_task(
                _log_search_activity,
                query=query,
                filters=filters,
                total=total,
                searching_organization_id=searching_organization_id,
                results=results,
            )
        else:
            await _log_search_activity(
                query=query,
                filters=filters,
                total=total,
                searching_organization_id=searching_organization_id,
                results=results,
            )

    return {
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "facets": facets,
    }


async def _log_search_activity(
    *,
    query: str | None,
    filters: dict,
    total: int,
    searching_organization_id: UUID | None,
    results: list[dict],
) -> None:
    async with session_for_system() as db:
        await search_repo.log_search(
            db,
            query_text=query,
            filters=filters,
            result_count=total,
            searching_organization_id=searching_organization_id,
        )
        offerings = [(r["offering_id"], r["organization_id"]) for r in results]
        if offerings:
            await search_repo.record_impressions(db, offerings)


async def get_public_organization(user_id: UUID | None, slug: str) -> dict | None:
    """Perfil público completo de una organización. `None` si no existe o
    RLS no la deja ver (organización no ACTIVE+PUBLIC para un visitante sin
    sesión — ver app.can_view_organization). `user_id=None` es el visitante
    anónimo; un `user_id` de un miembro de la organización ve el perfil
    aunque todavía no esté publicado (usado por la vista previa del dueño).

    Las ~12 lecturas de acá abajo son independientes entre sí — antes se
    encadenaban en una sola sesión y cada `await` pagaba de nuevo la latencia
    de red hacia la base remota (~200-300ms, ver docstring de
    `gather_for_user`). Correrlas en paralelo, cada una en su propia
    conexión del pool, cambia el costo de "N round trips sumados" a
    "el más lento de los N" — es la razón por la que este perfil tardaba
    varios segundos en cargar."""
    async with session_for_user(user_id) as session:
        org = await organizations_repo.get_by_slug(session, slug)
    if org is None:
        return None

    (
        offerings,
        cert_type_rows,
        media_rows,
        locations,
        contacts,
        industries,
        economic_activities,
        territories,
        certifications,
        client_references,
        case_studies,
        badges,
    ) = await gather_for_user(
        user_id,
        lambda db: offerings_repo.list_offerings(db, org.id, status="ACTIVE"),
        lambda db: credentials_repo.list_certification_types(db),
        lambda db: profile_repo.list_media(db, org.id),
        lambda db: profile_repo.list_locations(db, org.id),
        lambda db: profile_repo.list_contacts(db, org.id),
        lambda db: profile_repo.list_industries(db, org.id),
        lambda db: profile_repo.list_economic_activities(db, org.id),
        lambda db: profile_repo.list_territories(db, org.id),
        lambda db: credentials_repo.list_certifications(db, org.id),
        lambda db: credentials_repo.list_client_references(db, org.id),
        lambda db: credentials_repo.list_case_studies(db, org.id),
        lambda db: badges_repo.list_org_badges(db, org.id),
    )

    # Antes: 3 lecturas POR offering (nodos, precio, media), todas en el
    # mismo gather — para un catálogo de 10 productos, 30 conexiones
    # paralelas contra una base remota de latencia alta. Un proveedor sin
    # media ni pricing configurados igual pagaba esa cuenta completa. Ahora:
    # 3 consultas batch (`= any(:ids)` / `.in_()`), sin importar cuántos
    # productos tenga el catálogo — medido en vivo: la ficha de un proveedor
    # con catálogo bajaba de ~18s a rangos manejables con este cambio.
    offering_ids = [o.id for o in offerings]
    if offering_ids:
        nodes_by_offering, pricing_by_offering, media_by_offering = (
            await gather_for_user(
                user_id,
                lambda db: offerings_repo.list_taxonomy_nodes_with_names_batch(
                    db, offering_ids
                ),
                lambda db: offerings_repo.get_pricing_batch(db, offering_ids),
                lambda db: offerings_repo.list_media_batch(db, offering_ids),
            )
        )
    else:
        nodes_by_offering, pricing_by_offering, media_by_offering = {}, {}, {}

    offering_summaries = []
    for offering in offerings:
        nodes = nodes_by_offering.get(offering.id, [])
        pricing = pricing_by_offering.get(offering.id)
        media = media_by_offering.get(offering.id, [])
        offering_summaries.append(
            {
                "offering": offering,
                "primary_node": next((n for n in nodes if n["is_primary"]), None),
                "pricing": pricing if pricing and pricing.is_public else None,
                "media": [
                    {
                        "url": public_url(bucket=MEDIA_BUCKET, path=m.storage_path),
                        "alt_text": m.alt_text,
                    }
                    for m in media
                ],
            }
        )

    cert_types = {t.id: t for t in cert_type_rows}
    org_media = [
        {
            "media_type": m.media_type,
            "url": public_url(bucket=MEDIA_BUCKET, path=m.storage_path),
            "logo_shape": m.logo_shape,
        }
        for m in media_rows
    ]

    # list_locations ya ordena is_headquarters primero (repositories/
    # organization_profile.py) — si no hay ninguna marcada como casa matriz,
    # la primera ubicación activa es la mejor aproximación disponible. Esta
    # sí depende del resultado de `locations`, así que no puede ir en el
    # gather de arriba — es la única lectura que queda secuencial.
    headquarters = None
    primary_location = next(iter(locations), None)
    if primary_location is not None and primary_location.admin_division_id is not None:
        async with session_for_user(user_id) as session:
            ancestors = await reference_repo.get_admin_division_ancestors(
                session, primary_location.admin_division_id
            )
        headquarters = {
            "region": next(
                (a["name"] for a in ancestors if a["level_name"] == "REGION"), None
            ),
            "comuna": next(
                (a["name"] for a in ancestors if a["level_name"] == "COMUNA"), None
            ),
        }

    return {
        "organization": org,
        "locations": locations,
        "headquarters": headquarters,
        "contacts": contacts,
        "media": org_media,
        "industries": industries,
        "economic_activities": economic_activities,
        "territories": territories,
        "offerings": offering_summaries,
        "certifications": certifications,
        "certification_types": cert_types,
        "client_references": client_references,
        "case_studies": case_studies,
        "badges": badges,
    }


async def record_profile_view(
    *,
    organization_id: UUID,
    viewer_organization_id: UUID | None,
    source: str | None,
    visitor_hash: str | None,
) -> None:
    async with session_for_system() as db:
        await search_repo.record_profile_view(
            db,
            organization_id=organization_id,
            viewer_organization_id=viewer_organization_id,
            source=source,
            visitor_hash=visitor_hash,
        )


async def record_offering_views(
    *,
    offering_ids: list[UUID],
    organization_id: UUID,
    viewer_organization_id: UUID | None,
    visitor_hash: str | None,
) -> None:
    if not offering_ids:
        return
    async with session_for_system() as db:
        await search_repo.record_offering_views(
            db,
            offering_ids=offering_ids,
            organization_id=organization_id,
            viewer_organization_id=viewer_organization_id,
            visitor_hash=visitor_hash,
        )
