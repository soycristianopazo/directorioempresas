"""Entorno de Alembic.

Dos particularidades de este proyecto:

1. Alembic corre con psycopg2 (síncrono), no con asyncpg. Las migraciones son
   DDL con locks: no ganan nada siendo asíncronas y el modo síncrono evita
   tener que envolver todo en asyncio.

2. La URL de migración NO es la misma que usa la aplicación. Alembic necesita
   el Session Pooler (5432) y el rol `postgres`; la aplicación usa el
   Transaction Pooler (6543) y el rol `app_user`, que a propósito no puede
   hacer DDL. Mezclarlas rompe de una de dos formas: o Alembic falla al no
   poder crear tablas, o la aplicación corre con permisos de superusuario y
   RLS deja de aplicar.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# El paquete `app` vive un nivel por encima de este archivo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.alembic_url)

# autogenerate está deliberadamente desactivado: el esquema se escribe a mano
# en SQL. La detección automática no ve policies de RLS, funciones, triggers ni
# GRANTs, así que generaría revisiones que parecen completas y no lo son.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=settings.alembic_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Cada revisión en su propia transacción: si la 0007 falla, las
            # seis anteriores quedan aplicadas y se puede continuar desde ahí
            # en vez de repetirlo todo.
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
