"""Eliminación de la auditoría forense (audit_logs)

Revision ID: 0011
Revises: 0010

El esquema vive en ../sql/0011_drop_audit_logs.sql. Se retira audit_logs y sus
particiones mensuales (DROP CASCADE) junto con las funciones que solo la
servían. Forward-only: no hay downgrade porque la tabla no llegó a usarse.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0011_drop_audit_logs.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: audit_logs se retira de forma definitiva. Para "
        "reintroducirla, restaurar la migración 0006."
    )
