"""Recálculo de completitud de perfil.

app.compute_completion_pct() (0027) es una función SQL pura — este módulo
solo la invoca y persiste el resultado en organizations.completion_pct,
dentro de la MISMA transacción que la mutación que motivó el recálculo (para
que quede atómico: si la mutación se revierte, el completion_pct calculado
sobre datos ya-no-vigentes nunca se escribe).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import search as search_repo


async def recompute_completion_pct(session: AsyncSession, organization_id: UUID) -> int:
    # SessionLocal se configura con autoflush=False (app/db/session.py) — a
    # propósito, en todo el proyecto. Eso significa que un cambio hecho vía
    # ORM (ej. offering.status = "ACTIVE") NO se ve todavía desde SQL crudo
    # ejecutado en la misma sesión hasta que algo lo flushee explícitamente.
    # Sin este flush, compute_completion_pct() lee el estado ANTERIOR a la
    # mutación que motivó el recálculo — el propio bug que reveló esto: un
    # offering recién publicado seguía sin sumar su peso a completion_pct
    # porque el UPDATE de status todavía no había salido hacia Postgres.
    await session.flush()
    result = await session.execute(
        text(
            "update public.organizations "
            "set completion_pct = app.compute_completion_pct(:org_id) "
            "where id = :org_id "
            "returning completion_pct"
        ),
        {"org_id": str(organization_id)},
    )
    completion_pct = int(result.scalar_one())
    # Solo actualiza el número de ranking en el read model de búsqueda — no
    # dispara un reindexado completo, ver repositories/search.py.
    await search_repo.update_completion_pct_for_org(
        session, organization_id, completion_pct
    )
    return completion_pct
