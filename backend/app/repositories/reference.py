"""Acceso a datos de referencia: países, monedas, unidades, idiomas, divisiones
administrativas. Todo lectura — estas tablas no se escriben desde el servicio
de referencia (la escritura de divisiones administrativas es un caso raro,
de plataforma, que no necesita esta fase).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_division import AdminDivision
from app.models.reference import (
    Country,
    Currency,
    Language,
    SiiEconomicActivity,
    UnitOfMeasure,
)


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


async def get_admin_division_ancestors(
    session: AsyncSession, division_id: UUID
) -> list[dict]:
    """La división pedida más toda su cadena de padres, raíz primero (en
    Chile: región → provincia → comuna). Sirve para mostrar "Región X,
    Comuna Y" a partir de un único admin_division_id de hoja, sin que el
    caller tenga que conocer cuántos niveles tiene la jerarquía."""
    result = await session.execute(
        text(
            "with recursive ancestors as ("
            "  select id, parent_id, level, level_name, name "
            "  from public.admin_divisions where id = :division_id "
            "  union all "
            "  select ad.id, ad.parent_id, ad.level, ad.level_name, ad.name "
            "  from public.admin_divisions ad "
            "  join ancestors a on ad.id = a.parent_id"
            ") "
            "select level, level_name, name from ancestors order by level"
        ),
        {"division_id": str(division_id)},
    )
    return [dict(row._mapping) for row in result]


async def search_sii_economic_activities(
    session: AsyncSession, *, q: str, limit: int = 30
) -> list[SiiEconomicActivity]:
    """Búsqueda por código (prefijo) o texto libre en la descripción — 674
    filas totales, demasiadas para cargar completas en un selector como se
    hace con industries (taxonomy.py)."""
    pattern = f"%{q}%"
    result = await session.execute(
        select(SiiEconomicActivity)
        .where(
            SiiEconomicActivity.is_active.is_(True),
            or_(
                SiiEconomicActivity.code.ilike(f"{q}%"),
                SiiEconomicActivity.description.ilike(pattern),
            ),
        )
        .order_by(SiiEconomicActivity.code)
        .limit(limit)
    )
    return list(result.scalars())
