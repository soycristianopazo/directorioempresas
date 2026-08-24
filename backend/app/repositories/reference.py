"""Acceso a datos de referencia: países, monedas, unidades, idiomas, divisiones
administrativas. Todo lectura — estas tablas no se escriben desde el servicio
de referencia (la escritura de divisiones administrativas es un caso raro,
de plataforma, que no necesita esta fase).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_division import AdminDivision
from app.models.reference import Country, Currency, Language, UnitOfMeasure


async def list_countries(session: AsyncSession) -> list[Country]:
    result = await session.execute(
        select(Country).where(Country.is_active.is_(True)).order_by(Country.name)
    )
    return list(result.scalars())


async def list_currencies(session: AsyncSession) -> list[Currency]:
    result = await session.execute(
        select(Currency).where(Currency.is_active.is_(True)).order_by(Currency.code)
    )
    return list(result.scalars())


async def list_units_of_measure(session: AsyncSession) -> list[UnitOfMeasure]:
    result = await session.execute(
        select(UnitOfMeasure)
        .where(UnitOfMeasure.is_active.is_(True))
        .order_by(UnitOfMeasure.name)
    )
    return list(result.scalars())


async def list_languages(session: AsyncSession) -> list[Language]:
    result = await session.execute(
        select(Language).where(Language.is_active.is_(True)).order_by(Language.name)
    )
    return list(result.scalars())


async def list_admin_divisions(
    session: AsyncSession,
    *,
    country_code: str,
    parent_id: UUID | None = None,
) -> list[AdminDivision]:
    """Hijos directos de `parent_id` (o las 16 regiones si es None).

    Deliberadamente "un nivel por llamada", no el árbol completo: 346 comunas
    de una sola vez es más de lo que cualquier selector en cascada necesita
    pintar a la vez.
    """
    query = select(AdminDivision).where(
        AdminDivision.country_code == country_code,
        AdminDivision.is_active.is_(True),
    )
    if parent_id is None:
        query = query.where(AdminDivision.parent_id.is_(None))
    else:
        query = query.where(AdminDivision.parent_id == parent_id)
    result = await session.execute(query.order_by(AdminDivision.name))
    return list(result.scalars())
