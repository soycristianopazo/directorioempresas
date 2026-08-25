"""Nuevos valores de sourcing_event_status (fase 8.7)

Revision ID: 0064
Revises: 0063

El esquema vive en ../sql/0064_sourcing_event_status_awarded_closed.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0064_sourcing_event_status_awarded_closed.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
