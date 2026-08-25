"""Semilla de planes (fase 8.10)

Revision ID: 0073
Revises: 0072

El esquema vive en ../sql/0073_billing_seed_plans.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0073_billing_seed_plans.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
