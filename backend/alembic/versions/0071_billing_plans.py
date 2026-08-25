"""Planes, entitlements, suscripciones y contadores de uso (fase 8.10)

Revision ID: 0071
Revises: 0070

El esquema vive en ../sql/0071_billing_plans.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0071_billing_plans.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
