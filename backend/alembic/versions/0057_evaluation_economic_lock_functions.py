"""Bloqueo económico del comité de evaluación (fase 8.3/8.4)

Revision ID: 0057
Revises: 0056

El esquema vive en ../sql/0057_evaluation_economic_lock_functions.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0057_evaluation_economic_lock_functions.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
