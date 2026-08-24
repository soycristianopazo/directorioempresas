"""Helpers de RLS para perfil extendido y catálogo de oferta

Revision ID: 0028
Revises: 0027

El esquema vive en ../sql/0028_fase3_rls_helpers.sql. Buena parte de él —policies de RLS,
funciones plpgsql, triggers, particiones, GRANTs, índices parciales— no tiene
representación en la API de Alembic, y embeberlo en op.execute() con cadenas
solo lo haría ilegible. Además así el SQL sigue siendo ejecutable a mano contra
cualquier Postgres.

La ruta se resuelve desde __file__ a propósito: un import entre revisiones
dependería de cómo esté configurado sys.path al invocar Alembic.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0028_fase3_rls_helpers.sql"


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade: el esquema aún no llegó a producción, así que el camino "
        "de vuelta es recrear desde cero. Cuando haya datos reales, cada "
        "revisión llevará el suyo."
    )
