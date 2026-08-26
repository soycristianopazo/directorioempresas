"""Fix: accreditation.manage no autorizaba escribir accreditation_programs (fase 9.2)

Revision ID: 0081
Revises: 0080

El esquema vive en ../sql/0081_fix_accreditation_program_write_permission.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0081_fix_accreditation_program_write_permission.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
