"""VOID en sourcing_event_status — "Desierta" (fase 10)

Revision ID: 0089
Revises: 0088

El esquema vive en ../sql/0089_fase10_sourcing_event_status_void.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0089"
down_revision = "0088"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0089_fase10_sourcing_event_status_void.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
