"""Motor y sesiones de base de datos.

Configurado para el Transaction Pooler de Supabase, que es pgBouncer en modo
transaction. Ese modo impone restricciones que rompen asyncpg si no se
desactivan explícitamente, y los síntomas son confusos: funciona en desarrollo
y falla de forma intermitente en producción bajo concurrencia.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Por qué cada parámetro
# ─────────────────────────────────────────────────────────────────────────────
#
# statement_cache_size=0
#   asyncpg cachea sentencias preparadas por conexión. pgBouncer en modo
#   transaction reparte una misma conexión física entre clientes distintos, así
#   que la sentencia preparada que asyncpg cree tener puede no existir en la
#   conexión que le toque. Produce "prepared statement _asyncpg_stmt_x does not
#   exist" de forma esporádica y solo bajo carga.
#
# prepared_statement_cache_size=0
#   Lo mismo, pero en la capa del dialecto de SQLAlchemy. Hay que desactivar
#   las dos: desactivar solo una deja el problema a medias.
#
# prepared_statement_name_func
#   Nombres únicos por sentencia. Cinturón y tirantes: si algo terminara
#   preparando pese a la caché desactivada, al menos no colisiona entre
#   clientes que comparten conexión.
#
# pool_pre_ping=False
#   El pooler ya entrega conexiones vivas. Un ping por checkout es un
#   round-trip extra por petición sin ganancia real.
#
# pool_recycle=1800
#   Por debajo del timeout del pooler, para reciclar antes de que él corte.

# Los tres van juntos dentro de connect_args. El adaptador de asyncpg que usa
# SQLAlchemy recibe un único diccionario de argumentos de conexión: separa
# `prepared_statement_cache_size` y `prepared_statement_name_func` de ese
# mismo diccionario antes de reenviar el resto a asyncpg.connect() — no son
# kwargs de create_async_engine(). Pasarlos ahí en vez de en connect_args
# revienta en el arranque con "Invalid argument(s)": lo que sigue es lo
# verificado contra la fuente del dialecto, no una suposición.
engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_size=10,
    max_overflow=5,
    pool_recycle=1800,
    pool_pre_ping=False,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        "server_settings": {
            "application_name": settings.app_name,
            # jit desactivado: con consultas OLTP cortas el tiempo de
            # compilación supera al de ejecución.
            "jit": "off",
        },
    },
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_raw_session() -> AsyncIterator[AsyncSession]:
    """Sesión SIN contexto de identidad.

    Solo para el arranque de la aplicación y comprobaciones de salud. Las
    peticiones de usuario deben usar las dependencias de ``app.db.rls``, que
    fijan la identidad antes de tocar una sola tabla.
    """
    async with SessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    """Cierra el pool. Se invoca en el shutdown de FastAPI."""
    await engine.dispose()
