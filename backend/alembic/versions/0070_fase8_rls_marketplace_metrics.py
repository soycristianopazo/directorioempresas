"""RLS de analítica agregada (fase 8.9)

Revision ID: 0070
Revises: 0069

El esquema vive en ../sql/0070_fase8_rls_marketplace_metrics.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0070_fase8_rls_marketplace_metrics.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
