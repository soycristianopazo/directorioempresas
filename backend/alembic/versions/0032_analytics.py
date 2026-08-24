"""Analítica de búsqueda y visitas

Revision ID: 0032
Revises: 0031

El esquema vive en ../sql/0032_analytics.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0032_analytics.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
