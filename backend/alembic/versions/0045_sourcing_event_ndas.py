"""NDA del evento y su aceptación (fase 7.2)

Revision ID: 0045
Revises: 0044

El esquema vive en ../sql/0045_sourcing_event_ndas.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0045_sourcing_event_ndas.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
