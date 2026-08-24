"""Credenciales, sesiones e identidad de la petición

Revision ID: 0002
Revises: 0001

El esquema vive en ../sql/0002_auth_and_rls.sql. Buena parte de él —policies de RLS,
funciones plpgsql, triggers, particiones, GRANTs, índices parciales— no tiene
representación en la API de Alembic, y embeberlo en op.execute() con cadenas
solo lo haría ilegible. Además así el SQL sigue siendo ejecutable a mano contra
cualquier Postgres y las 42 aserciones pgTAP se conservan intactas.

La ruta se resuelve desde __file__ a propósito: un import entre revisiones
dependería de cómo esté configurado sys.path al invocar Alembic.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0002_auth_and_rls.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
