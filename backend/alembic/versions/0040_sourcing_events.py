"""Demanda — sourcing_events, lotes/ítems/hitos/documentos, criterios MUST/NICE

Revision ID: 0040
Revises: 0039

El esquema vive en ../sql/0040_sourcing_events.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0040_sourcing_events.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
