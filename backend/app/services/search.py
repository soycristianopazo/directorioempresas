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

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import public_url
from app.db.rls import session_for_system
from app.repositories import credentials as credentials_repo
from app.repositories import offerings as offerings_repo
from app.repositories import organization_profile as profile_repo
from app.repositories import organizations as organizations_repo
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

    return {
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "facets": facets,
    }


async def get_public_organization(session: AsyncSession, slug: str) -> dict | None:
    """Perfil público completo de una organización. `None` si no existe o
    RLS no la deja ver (organización no ACTIVE+PUBLIC para un visitante sin
    sesión — ver app.can_view_organization)."""
    org = await organizations_repo.get_by_slug(session, slug)
    if org is None:
        return None

    offerings = await offerings_repo.list_offerings(session, org.id, status="ACTIVE")
    offering_summaries = []
    for offering in offerings:
        nodes = await offerings_repo.list_taxonomy_nodes_with_names(
            session, offering.id
        )
        pricing = await offerings_repo.get_pricing(session, offering.id)
        media = await offerings_repo.list_media(session, offering.id)
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

    cert_types = {
        t.id: t for t in await credentials_repo.list_certification_types(session)
    }
    org_media = [
        {
            "media_type": m.media_type,
            "url": public_url(bucket=MEDIA_BUCKET, path=m.storage_path),
        }
        for m in await profile_repo.list_media(session, org.id)
    ]

    return {
        "organization": org,
        "locations": await profile_repo.list_locations(session, org.id),
        "contacts": await profile_repo.list_contacts(session, org.id),
        "media": org_media,
        "industries": await profile_repo.list_industries(session, org.id),
        "territories": await profile_repo.list_territories(session, org.id),
        "offerings": offering_summaries,
        "certifications": await credentials_repo.list_certifications(session, org.id),
        "certification_types": cert_types,
        "client_references": await credentials_repo.list_client_references(
            session, org.id
        ),
        "case_studies": await credentials_repo.list_case_studies(session, org.id),
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
