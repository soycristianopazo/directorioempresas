"""Punto de entrada de la aplicación.

Todas las rutas de API cuelgan de /api, como espera el frontend
(REACT_APP_BACKEND_URL + /api en src/lib/api.js, proxeado por Craco en
desarrollo). Las páginas públicas indexables (Jinja2, fase 4) viven fuera
de ese prefijo — /discover, /proveedores/{slug}, /sitemap.xml, /robots.txt,
montadas desde app.api.public — para que un crawler o un usuario sin JS
reciba HTML con contenido real en la respuesta inicial.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.public import router as public_router
from app.api.v1.accreditation import programs_router as accreditation_programs_router
from app.api.v1.accreditation import router as accreditation_router
from app.api.v1.admin_accreditation import router as admin_accreditation_router
from app.api.v1.admin_taxonomy import industries_router as admin_industries_router
from app.api.v1.admin_taxonomy import router as admin_taxonomy_router
from app.api.v1.auth import router as auth_router
from app.api.v1.credentials import reference_router as certification_types_router
from app.api.v1.credentials import router as credentials_router
from app.api.v1.discover import router as discover_router
from app.api.v1.documents import router as documents_router
from app.api.v1.documents import types_router as document_types_router
from app.api.v1.matching import router as matching_router
from app.api.v1.offerings import router as offerings_router
from app.api.v1.organization_profile import router as organization_profile_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.reference import router as reference_router
from app.api.v1.requirements import router as requirements_router
from app.api.v1.sourcing import router as sourcing_router
from app.api.v1.supplier_lists import router as supplier_lists_router
from app.api.v1.taxonomy import industries_router as industries_router
from app.api.v1.taxonomy import router as taxonomy_router
from app.api.v1.team import router as team_router
from app.core.config import settings
from app.db.session import dispose_engine

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await dispose_engine()


app = FastAPI(
    title="Directorio de Empresas — API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

# allow_credentials=True es obligatorio: el refresh token viaja en cookie
# httpOnly y el navegador solo la adjunta a peticiones cross-origin si el
# servidor declara explícitamente que las acepta. Con eso activo,
# allow_origins NO puede ser "*" — el navegador lo rechaza — así que se listan
# los orígenes reales desde settings.cors_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(organizations_router, prefix="/api")
app.include_router(team_router, prefix="/api")
app.include_router(reference_router, prefix="/api")
app.include_router(taxonomy_router, prefix="/api")
app.include_router(industries_router, prefix="/api")
app.include_router(admin_taxonomy_router, prefix="/api")
app.include_router(admin_industries_router, prefix="/api")
app.include_router(organization_profile_router, prefix="/api")
app.include_router(offerings_router, prefix="/api")
app.include_router(credentials_router, prefix="/api")
app.include_router(certification_types_router, prefix="/api")
app.include_router(discover_router, prefix="/api")
app.include_router(supplier_lists_router, prefix="/api")
app.include_router(document_types_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(accreditation_programs_router, prefix="/api")
app.include_router(accreditation_router, prefix="/api")
app.include_router(admin_accreditation_router, prefix="/api")
app.include_router(requirements_router, prefix="/api")
app.include_router(sourcing_router, prefix="/api")
app.include_router(matching_router, prefix="/api")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
app.include_router(public_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Nunca devolver el traceback al cliente. Los errores de negocio ya se
    traducen a HTTPException en cada router; si algo más llega hasta aquí es
    un bug, y lo único que el cliente necesita saber es que ocurrió — el
    detalle va al log del servidor, no a la respuesta.
    """
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ocurrió un error inesperado. Intenta nuevamente."},
    )


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
