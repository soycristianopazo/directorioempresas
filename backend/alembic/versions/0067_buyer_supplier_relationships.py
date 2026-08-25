"""Vendor List / AVL — buyer_supplier_relationships (fase 8.8)

Revision ID: 0067
Revises: 0066

El esquema vive en ../sql/0067_buyer_supplier_relationships.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0067_buyer_supplier_relationships.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
