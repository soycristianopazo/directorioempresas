"""Punto de entrada de la aplicación.

Todas las rutas de API cuelgan de /api, como espera el frontend
(REACT_APP_BACKEND_URL + /api en src/lib/api.js, proxeado por Craco en
desarrollo). Las páginas públicas indexables (Jinja2) llegan en una fase
posterior y se montarán fuera de este prefijo.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.admin_taxonomy import industries_router as admin_industries_router
from app.api.v1.admin_taxonomy import router as admin_taxonomy_router
from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.reference import router as reference_router
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
