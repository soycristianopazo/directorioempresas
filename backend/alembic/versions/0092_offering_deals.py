"""Ofertas del catálogo — offering_deals (fase 11)

Revision ID: 0092
Revises: 0091

El esquema vive en ../sql/0092_offering_deals.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0092"
down_revision = "0091"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0092_offering_deals.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
