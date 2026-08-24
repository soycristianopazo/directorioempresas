"""supplier_search_index gana is_matchable (Recall de matching)

Revision ID: 0042
Revises: 0041

El esquema vive en ../sql/0042_search_index_matchable.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0042_search_index_matchable.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
