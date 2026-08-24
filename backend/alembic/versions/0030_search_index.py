"""Read model de búsqueda — supplier_search_index

Revision ID: 0030
Revises: 0029

El esquema vive en ../sql/0030_search_index.sql — ver ese archivo para el
porqué del diseño (read model refrescado desde Python, no por trigger).
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0030_search_index.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
