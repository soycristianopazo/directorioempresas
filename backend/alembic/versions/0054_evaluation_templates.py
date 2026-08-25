"""Plantillas y criterios de evaluación (fase 8.1/8.2)

Revision ID: 0054
Revises: 0053

El esquema vive en ../sql/0054_evaluation_templates.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0054_evaluation_templates.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
