"""RLS de cotizaciones — modo sellado (fase 7.6)

Revision ID: 0049
Revises: 0048

El esquema vive en ../sql/0049_fase7_rls_quotations.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0049_fase7_rls_quotations.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
