"""Secuencia real para sourcing_events.event_code (bug de fase 6, fix en fase 7)

Revision ID: 0053
Revises: 0052

El esquema vive en ../sql/0053_sourcing_event_code_seq.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0053_sourcing_event_code_seq.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
