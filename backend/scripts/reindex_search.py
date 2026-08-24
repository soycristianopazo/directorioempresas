"""Reconstruye supplier_search_index desde cero, para todas las ofertas.

"Job de reconciliación" de fase 4, pero como script de uso manual — no hay
scheduler/cron en este stack todavía (ver el plan de fase 4 sobre por qué
no se inventa infra de scheduling en esta pasada). Se corre a mano cuando
se sospecha que el índice divergió de las tablas tipadas, o después de un
cambio masivo de datos (ej. un seed nuevo).

Uso:
    cd backend && source .venv/bin/activate && PYTHONPATH=. python scripts/reindex_search.py
"""

from __future__ import annotations

import asyncio

from app.db.rls import session_for_system
from app.repositories import search as search_repo


async def main() -> None:
    async with session_for_system() as db:
        offering_ids = await search_repo.all_offering_ids(db)
        print(f"Reindexando {len(offering_ids)} ofertas…")
        for i, offering_id in enumerate(offering_ids, start=1):
            await search_repo.reindex_offering(db, offering_id)
            if i % 50 == 0:
                print(f"  {i}/{len(offering_ids)}")
    print("✓ Reindexado completo.")


if __name__ == "__main__":
    asyncio.run(main())
