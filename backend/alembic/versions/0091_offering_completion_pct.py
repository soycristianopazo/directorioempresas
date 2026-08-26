"""Completitud por publicación del catálogo (supplier_offerings.completion_pct)

Revision ID: 0091
Revises: 0090

El esquema vive en ../sql/0091_offering_completion_pct.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0091"
down_revision = "0090"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0091_offering_completion_pct.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
