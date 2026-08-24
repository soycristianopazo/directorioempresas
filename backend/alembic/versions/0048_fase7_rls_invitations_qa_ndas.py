"""RLS de invitaciones, NDA y Q&A + visibilidad del proveedor invitado (fase 7)

Revision ID: 0048
Revises: 0047

El esquema vive en ../sql/0048_fase7_rls_invitations_qa_ndas.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0048_fase7_rls_invitations_qa_ndas.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
