"""RLS del revisor de programa propio (fase 9.3)

Revision ID: 0079
Revises: 0078

El esquema vive en ../sql/0079_fase9_rls_reviewer_own_program.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0079_fase9_rls_reviewer_own_program.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
