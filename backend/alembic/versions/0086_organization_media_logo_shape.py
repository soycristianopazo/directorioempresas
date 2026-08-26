"""Forma del logo (cuadrado / horizontal)

Revision ID: 0086
Revises: 0085

El esquema vive en ../sql/0086_organization_media_logo_shape.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0086_organization_media_logo_shape.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
