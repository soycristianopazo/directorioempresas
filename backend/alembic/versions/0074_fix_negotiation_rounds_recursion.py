"""Fix: recursión infinita en RLS de negociación (fase 8.5)

Revision ID: 0074
Revises: 0073

El esquema vive en ../sql/0074_fix_negotiation_rounds_recursion.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0074_fix_negotiation_rounds_recursion.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
