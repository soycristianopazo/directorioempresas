"""Conversión de montos a la moneda base — utilidad interna para quotations
(fase 7).

Es un helper puro: recibe una sesión ya abierta (de una transacción con la
identidad ya fijada por RLS, o de sistema) y no abre la suya propia. No es un
punto de entrada independiente como los demás services de este proyecto
(nada de session_for_user aquí) — otro service la llama dentro de su propia
transacción, así que la sesión y el permiso de esa transacción ya están
resueltos por quien llama.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import fx as fx_repo


class FxRateNotFoundError(Exception):
    pass


async def to_base_amount(
    session: AsyncSession,
    *,
    amount: float,
    currency_code: str,
    on_date: date,
    base_currency_code: str,
) -> tuple[float, float]:
    """Devuelve (amount_base, fx_rate_used).

    Si currency_code == base_currency_code, rate=1 sin consultar fx_rates. Si
    no hay tasa disponible para el par, lanza FxRateNotFoundError.
    """
    if currency_code == base_currency_code:
        return amount, 1.0

    rate = await fx_repo.get_latest_rate(
        session, from_code=currency_code, to_code=base_currency_code, on_date=on_date
    )
    if rate is None:
        raise FxRateNotFoundError(
            f"No hay tasa de cambio disponible para {currency_code}->{base_currency_code}"
            f" en o antes de {on_date.isoformat()}"
        )
    return amount * rate, rate
