"""Ampliación del árbol de industrias

Revision ID: 0087
Revises: 0086

El esquema vive en ../sql/0087_expand_industries.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0087"
down_revision = "0086"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0087_expand_industries.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
