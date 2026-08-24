"""Router de datos de referencia: /api/reference/*. Todo lectura, sesión
pública — son catálogos, no hay nada que ocultar ni de un visitante anónimo.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import PublicSession
from app.schemas.reference import (
    AdminDivisionOut,
    CountryOut,
    CurrencyOut,
    LanguageOut,
    UnitOfMeasureOut,
)
from app.services import reference as reference_service

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/countries", response_model=list[CountryOut])
async def list_countries(session: PublicSession) -> list[CountryOut]:
    countries = await reference_service.list_countries(session)
    return [CountryOut.model_validate(c) for c in countries]


@router.get("/currencies", response_model=list[CurrencyOut])
async def list_currencies(session: PublicSession) -> list[CurrencyOut]:
    currencies = await reference_service.list_currencies(session)
    return [CurrencyOut.model_validate(c) for c in currencies]


@router.get("/units-of-measure", response_model=list[UnitOfMeasureOut])
async def list_units_of_measure(session: PublicSession) -> list[UnitOfMeasureOut]:
    units = await reference_service.list_units_of_measure(session)
    return [UnitOfMeasureOut.model_validate(u) for u in units]


@router.get("/languages", response_model=list[LanguageOut])
async def list_languages(session: PublicSession) -> list[LanguageOut]:
    languages = await reference_service.list_languages(session)
    return [LanguageOut.model_validate(lang) for lang in languages]


@router.get("/admin-divisions", response_model=list[AdminDivisionOut])
async def list_admin_divisions(
    session: PublicSession,
    country: str = Query(default="CL", min_length=2, max_length=2),
    parent_id: UUID | None = Query(default=None),
) -> list[AdminDivisionOut]:
    divisions = await reference_service.list_admin_divisions(
        session, country_code=country, parent_id=parent_id
    )
    return [AdminDivisionOut.model_validate(d) for d in divisions]
