"""Preguntas y respuestas del evento (fase 7.4)

Revision ID: 0046
Revises: 0045

El esquema vive en ../sql/0046_sourcing_qa.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0046_sourcing_qa.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
