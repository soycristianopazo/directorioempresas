"""Router de descubrimiento público: /api/discover/*. Búsqueda y perfil de
organización en JSON, para la SPA de comprador (/buscar, /comparar) — la
misma lógica que sirve las páginas Jinja2 públicas (app/api/public.py), acá
expuesta como API para consumo desde React. Sesión pública: RLS decide qué
es visible, no hay chequeo de permiso adicional en Python.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import PublicSession
from app.schemas.search import (
    BadgeSummaryOut,
    FacetItemOut,
    FacetsOut,
    PublicOfferingSummaryOut,
    PublicOrganizationOut,
    SearchResponseOut,
    SearchResultOut,
)
from app.services import search as search_service

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("/search", response_model=SearchResponseOut)
async def search(
    session: PublicSession,
    q: str | None = None,
    taxonomy_node_ids: list[UUID] = Query(default_factory=list),
    industry_ids: list[UUID] = Query(default_factory=list),
    admin_division_ids: list[UUID] = Query(default_factory=list),
    offering_type: str | None = None,
    availability_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> SearchResponseOut:
    result = await search_service.search_offerings(
        session,
        query=q,
        taxonomy_node_ids=taxonomy_node_ids or None,
        industry_ids=industry_ids or None,
        admin_division_ids=admin_division_ids or None,
        offering_type=offering_type,
        availability_status=availability_status,
        page=page,
        page_size=page_size,
    )
    return SearchResponseOut(
        results=[SearchResultOut(**r) for r in result["results"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        facets=FacetsOut(
            taxonomy_nodes=[
                FacetItemOut(**f) for f in result["facets"]["taxonomy_nodes"]
            ],
            industries=[FacetItemOut(**f) for f in result["facets"]["industries"]],
            admin_divisions=[
                FacetItemOut(**f) for f in result["facets"]["admin_divisions"]
            ],
        ),
    )


@router.get("/organizations/{slug}", response_model=PublicOrganizationOut)
async def get_organization(session: PublicSession, slug: str) -> PublicOrganizationOut:
    profile = await search_service.get_public_organization(session, slug)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada"
        )

    org = profile["organization"]
    logo = next((m for m in profile["media"] if m["media_type"] == "LOGO"), None)

    offerings = []
    for item in profile["offerings"]:
        offering = item["offering"]
        media = item["media"]
        pricing = item["pricing"]
        offerings.append(
            PublicOfferingSummaryOut(
                id=offering.id,
                name=offering.name,
                slug=offering.slug,
                short_description=offering.short_description,
                offering_type=offering.offering_type,
                primary_category=(
                    item["primary_node"]["name"] if item["primary_node"] else None
                ),
                price_type=pricing.price_type if pricing else None,
                amount_min=pricing.amount_min if pricing else None,
                amount_max=pricing.amount_max if pricing else None,
                currency_code=pricing.currency_code if pricing else None,
                photo_url=media[0]["url"] if media else None,
            )
        )

    cert_types = profile["certification_types"]
    return PublicOrganizationOut(
        id=org.id,
        legal_name=org.legal_name,
        trade_name=org.trade_name,
        slug=org.slug,
        short_description=org.short_description,
        description=org.description,
        website_url=org.website_url,
        completion_pct=org.completion_pct,
        logo_url=logo["url"] if logo else None,
        industries=[i["name"] for i in profile["industries"]],
        territories=[t["name"] for t in profile["territories"]],
        offerings=offerings,
        certifications=[
            cert_types[c.certification_type_id].name
            for c in profile["certifications"]
            if c.certification_type_id in cert_types
        ],
        badges=[BadgeSummaryOut(**b) for b in profile["badges"]],
    )
