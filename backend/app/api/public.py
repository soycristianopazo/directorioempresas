"""Páginas públicas indexables: /discover, /proveedores/{slug},
/sitemap.xml, /robots.txt. Fuera del prefijo /api a propósito (ver
docstring de app/main.py) — HTML servido por Jinja2, no JSON, para que un
crawler (o un usuario sin JS) vea contenido real en la respuesta inicial.

Llaman directo a services/search.py, sin pasar por HTTP — ver el plan de
fase 4 sobre por qué (evitar una llamada de la app a sí misma).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.api.deps import PublicSession
from app.services import search as search_service

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


def _money(value: float | str | None) -> str:
    """1234.5000 (numeric de Postgres, vía asyncpg) -> "1.235" — sin
    decimales, separador de miles latino. Los montos de este dominio son
    montos de negocio (CLP, UF), no requieren precisión decimal visible."""
    if value is None:
        return ""
    return f"{float(value):,.0f}".replace(",", ".")


templates.env.filters["money"] = _money

OFFERING_TYPE_LABELS = {
    "PRODUCT": "Producto",
    "SERVICE": "Servicio",
    "RENTAL": "Arriendo",
    "SOFTWARE": "Software",
    "TRAINING": "Capacitación",
    "CONSULTING": "Consultoría",
}
AVAILABILITY_LABELS = {
    "AVAILABLE": "Disponible",
    "LIMITED": "Disponibilidad limitada",
    "ON_REQUEST": "Bajo pedido",
    "UNAVAILABLE": "No disponible",
}

_VISITOR_COOKIE = "visitor_id"
_VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _visitor_hash(request: Request) -> str:
    return request.cookies.get(_VISITOR_COOKIE) or str(uuid4())


def _set_visitor_cookie(
    response: Response, request: Request, visitor_hash: str
) -> None:
    if _VISITOR_COOKIE not in request.cookies:
        response.set_cookie(
            _VISITOR_COOKIE,
            visitor_hash,
            max_age=_VISITOR_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
        )


@router.get("/discover", response_class=HTMLResponse)
async def discover_page(
    request: Request,
    session: PublicSession,
    q: str | None = None,
    category: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    page: int = 1,
) -> HTMLResponse:
    page_size = 20
    node_ids = [UUID(category)] if category else None
    industry_ids = [UUID(industry)] if industry else None
    division_ids = [UUID(region)] if region else None

    result = await search_service.search_offerings(
        session,
        query=q,
        taxonomy_node_ids=node_ids,
        industry_ids=industry_ids,
        admin_division_ids=division_ids,
        page=max(page, 1),
        page_size=page_size,
    )

    def build_url(**overrides: str | int | None) -> str:
        params: dict[str, str | int | None] = {
            "q": q,
            "category": category,
            "industry": industry,
            "region": region,
        }
        params.update(overrides)
        clean = {k: v for k, v in params.items() if v}
        return "/discover" + (f"?{urlencode(clean)}" if clean else "")

    active_filters = []
    if category:
        label = next(
            (
                f["label"]
                for f in result["facets"]["taxonomy_nodes"]
                if str(f["value"]) == category
            ),
            "Categoría",
        )
        active_filters.append({"label": label, "remove_url": build_url(category=None)})
    if industry:
        label = next(
            (
                f["label"]
                for f in result["facets"]["industries"]
                if str(f["value"]) == industry
            ),
            "Industria",
        )
        active_filters.append({"label": label, "remove_url": build_url(industry=None)})
    if region:
        label = next(
            (
                f["label"]
                for f in result["facets"]["admin_divisions"]
                if str(f["value"]) == region
            ),
            "Región",
        )
        active_filters.append({"label": label, "remove_url": build_url(region=None)})

    facets = {
        "taxonomy_nodes": [
            {
                "label": f["label"],
                "count": f["count"],
                "active": str(f["value"]) == category,
                "url": build_url(
                    category=None if str(f["value"]) == category else str(f["value"])
                ),
            }
            for f in result["facets"]["taxonomy_nodes"]
        ],
        "industries": [
            {
                "label": f["label"],
                "count": f["count"],
                "active": str(f["value"]) == industry,
                "url": build_url(
                    industry=None if str(f["value"]) == industry else str(f["value"])
                ),
            }
            for f in result["facets"]["industries"]
        ],
        "admin_divisions": [
            {
                "label": f["label"],
                "count": f["count"],
                "active": str(f["value"]) == region,
                "url": build_url(
                    region=None if str(f["value"]) == region else str(f["value"])
                ),
            }
            for f in result["facets"]["admin_divisions"]
        ],
    }

    return templates.TemplateResponse(
        request,
        "discover.html",
        {
            "q": q,
            "category": category,
            "industry": industry,
            "region": region,
            "page": page,
            "page_size": page_size,
            "total": result["total"],
            "results": result["results"],
            "facets": facets,
            "active_filters": active_filters,
            "offering_type_labels": OFFERING_TYPE_LABELS,
            "availability_labels": AVAILABILITY_LABELS,
            "prev_url": build_url(page=page - 1) if page > 1 else None,
            "next_url": build_url(page=page + 1),
            "current_year": datetime.now(timezone.utc).year,
        },
    )


@router.get("/proveedores/{slug}", response_class=HTMLResponse)
async def provider_profile_page(
    request: Request, session: PublicSession, slug: str
) -> HTMLResponse:
    profile = await search_service.get_public_organization(session, slug)
    if profile is None:
        return HTMLResponse(
            "<!doctype html><html lang=es-CL><head><meta charset=utf-8>"
            "<title>Proveedor no encontrado · Directorio de Empresas</title>"
            "<link rel=stylesheet href=/static/css/public.css></head><body>"
            "<div class=container style='padding:4rem 0'>"
            "<h1>No encontramos este proveedor</h1>"
            "<p><a class='btn btn-primary' href=/discover>Volver a la búsqueda</a></p>"
            "</div></body></html>",
            status_code=404,
        )

    org = profile["organization"]
    logo = next((m for m in profile["media"] if m["media_type"] == "LOGO"), None)

    response = templates.TemplateResponse(
        request,
        "provider_profile.html",
        {
            "org": org,
            "logo_url": logo["url"] if logo else None,
            "industries": [i["name"] for i in profile["industries"]],
            "territories": [t["name"] for t in profile["territories"]],
            "offerings": profile["offerings"],
            "certifications": [
                profile["certification_types"][c.certification_type_id].name
                for c in profile["certifications"]
                if c.certification_type_id in profile["certification_types"]
            ],
            "case_studies": profile["case_studies"],
            "public_contacts": profile["contacts"],
            "current_year": datetime.now(timezone.utc).year,
        },
    )

    visitor_hash = _visitor_hash(request)
    _set_visitor_cookie(response, request, visitor_hash)
    await search_service.record_profile_view(
        organization_id=org.id,
        viewer_organization_id=None,
        source=request.query_params.get("ref"),
        visitor_hash=visitor_hash,
    )
    offering_ids = [item["offering"].id for item in profile["offerings"]]
    await search_service.record_offering_views(
        offering_ids=offering_ids,
        organization_id=org.id,
        viewer_organization_id=None,
        visitor_hash=visitor_hash,
    )
    return response


@router.get("/sitemap.xml", response_class=Response)
async def sitemap(request: Request, session: PublicSession) -> Response:
    result = await search_service.search_offerings(
        session, page=1, page_size=1000, log=False
    )
    base = str(request.base_url).rstrip("/")
    slugs = sorted({r["organization_slug"] for r in result["results"]})

    urls = [f"{base}/discover"]
    urls.extend(f"{base}/proveedores/{slug}" for slug in slugs)

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
        + "</urlset>"
    )
    return Response(content=body, media_type="application/xml")


@router.get("/robots.txt", response_class=Response)
async def robots(request: Request) -> Response:
    base = str(request.base_url).rstrip("/")
    body = f"User-agent: *\nAllow: /discover\nAllow: /proveedores/\nDisallow: /api/\nSitemap: {base}/sitemap.xml\n"
    return Response(content=body, media_type="text/plain")
