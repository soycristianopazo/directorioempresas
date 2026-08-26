"""Giros SII registrados por la organización

Revision ID: 0084
Revises: 0083

El esquema vive en ../sql/0084_organization_economic_activities.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0084"
down_revision = "0083"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0084_organization_economic_activities.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
