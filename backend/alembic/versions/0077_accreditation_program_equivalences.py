"""Homologación cruzada de programas de acreditación (fase 9.1)

Revision ID: 0077
Revises: 0076

El esquema vive en ../sql/0077_accreditation_program_equivalences.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0077_accreditation_program_equivalences.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
