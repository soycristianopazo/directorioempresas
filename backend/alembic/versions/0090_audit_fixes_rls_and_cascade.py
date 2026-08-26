"""Fixes de auditoría: RLS faltante + FK sin cascada

Revision ID: 0090
Revises: 0089

El esquema vive en ../sql/0090_audit_fixes_rls_and_cascade.sql.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0090"
down_revision = "0089"
branch_labels = None
depends_on = None

SQL_FILE = (
    Path(__file__).resolve().parent.parent
    / "sql"
    / "0090_audit_fixes_rls_and_cascade.sql"
)


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
