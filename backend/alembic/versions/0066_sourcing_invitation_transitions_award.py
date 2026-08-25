"""Transiciones de invitación para evaluación/negociación/adjudicación (fase 8.7)

Revision ID: 0066
Revises: 0065

El esquema vive en ../sql/0066_sourcing_invitation_transitions_award.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0066_sourcing_invitation_transitions_award.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
