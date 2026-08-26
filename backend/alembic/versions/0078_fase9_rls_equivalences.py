"""RLS de homologación cruzada + función compartida de autoría (fase 9.1/9.2)

Revision ID: 0078
Revises: 0077

El esquema vive en ../sql/0078_fase9_rls_equivalences.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0078_fase9_rls_equivalences.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
