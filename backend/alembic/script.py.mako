"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from __future__ import annotations

from pathlib import Path

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

# El esquema se escribe en ../sql/<revision>_<slug>.sql y se ejecuta desde aquí.
# Ver cualquier revisión existente para el patrón.
SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "${up_revision}_${message.lower().replace(' ', '_')}.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError
