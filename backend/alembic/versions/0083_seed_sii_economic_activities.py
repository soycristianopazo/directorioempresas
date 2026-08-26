"""Seed de giros SII (674 códigos)

Revision ID: 0083
Revises: 0082

El esquema vive en ../sql/0083_seed_sii_economic_activities.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0083_seed_sii_economic_activities.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
