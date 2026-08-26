"""Lectura de datos de referencia. Sin lógica de negocio: pasa parámetros al
repositorio y devuelve los modelos tal cual — estas tablas son catálogos
públicos, no hay reglas de autorización que aplicar más allá de RLS.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_division import AdminDivision
from app.models.reference import (
    Country,
    Currency,
    Language,
    SiiEconomicActivity,
    UnitOfMeasure,
)
from app.repositories import reference as reference_repo


async def list_countries(session: AsyncSession) -> list[Country]:
    return await reference_repo.list_countries(session)


async def list_currencies(session: AsyncSession) -> list[Currency]:
    return await reference_repo.list_currencies(session)


async def list_units_of_measure(session: AsyncSession) -> list[UnitOfMeasure]:
    return await reference_repo.list_units_of_measure(session)


async def list_languages(session: AsyncSession) -> list[Language]:
    return await reference_repo.list_languages(session)


async def list_admin_divisions(
    session: AsyncSession, *, country_code: str, parent_id: UUID | None
) -> list[AdminDivision]:
    return await reference_repo.list_admin_divisions(
        session, country_code=country_code, parent_id=parent_id
    )


async def search_sii_economic_activities(
    session: AsyncSession, *, q: str, limit: int = 30
) -> list[SiiEconomicActivity]:
    return await reference_repo.search_sii_economic_activities(
        session, q=q, limit=limit
    )
