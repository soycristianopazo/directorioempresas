"""Fix: conversations.created_by_organization_id sin cascada (fase 7, bug real)

Revision ID: 0075
Revises: 0074

El esquema vive en ../sql/0075_fix_conversations_org_fk_cascade.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent / "sql" / "0075_fix_conversations_org_fk_cascade.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
