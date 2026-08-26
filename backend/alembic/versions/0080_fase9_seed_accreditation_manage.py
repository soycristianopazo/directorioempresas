"""accreditation.manage para BUYER_MANAGER / PROCUREMENT_ANALYST (fase 9.2)

Revision ID: 0080
Revises: 0079

El esquema vive en ../sql/0080_fase9_seed_accreditation_manage.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0080_fase9_seed_accreditation_manage.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
