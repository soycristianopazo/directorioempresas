"""Acceso a datos de fx_rates: tasas de conversión de moneda (fase 7)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_latest_rate(
    session: AsyncSession, *, from_code: str, to_code: str, on_date: date
) -> float | None:
    """Tasa más reciente con valid_on <= on_date. None si no hay ninguna."""
    result = await session.execute(
        text(
            "select rate from public.fx_rates "
            "where from_code = :from_code and to_code = :to_code "
            "and valid_on <= :on_date "
            "order by valid_on desc limit 1"
        ),
        {"from_code": from_code, "to_code": to_code, "on_date": on_date},
    )
    row = result.first()
    return float(row[0]) if row is not None else None
