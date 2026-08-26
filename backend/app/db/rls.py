"""Contexto de identidad para Row Level Security.

Esta es la pieza que hace que RLS funcione sobre FastAPI. Sin ella, el backend
abre la conexión con un rol fijo, Postgres no sabe quién pregunta, y todas las
policies del sistema quedan decorativas.

El contrato es simple y no admite excepciones:

    Ninguna consulta a una tabla de dominio ocurre fuera de una sesión
    obtenida por una de las dependencias de este módulo.

Si aparece un ``SessionLocal()`` suelto en un router, es un agujero en el
aislamiento multiempresa, no un atajo.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal

_T = TypeVar("_T")

# ─────────────────────────────────────────────────────────────────────────────
# SET LOCAL, nunca SET
# ─────────────────────────────────────────────────────────────────────────────
#
# `SET LOCAL` vive dentro de la transacción y muere con ella. `SET` a secas
# persiste en la conexión.
#
# Con un pooler en modo transaction las conexiones se reciclan entre clientes.
# Un `SET` dejaría la identidad del usuario A pegada a la conexión, y la
# siguiente petición —de otra empresa— la heredaría. Es una fuga de datos
# entre organizaciones silenciosa, intermitente y prácticamente imposible de
# reproducir en desarrollo.
#
# El parámetro se pasa como bind, no interpolado: `set_config()` acepta
# argumentos, `SET LOCAL` no. Concatenar el uuid en el SQL sería inyección
# aunque venga de un JWT ya validado.

_SET_USER = text("select set_config('app.current_user_id', :user_id, true)")
_SET_SYSTEM = text("select set_config('app.system_context', :flag, true)")


@asynccontextmanager
async def session_for_user(user_id: UUID | None) -> AsyncIterator[AsyncSession]:
    """Sesión con la identidad fijada para toda la transacción.

    ``user_id`` nulo es legítimo: es el visitante anónimo del perfil público.
    Las policies distinguen ese caso y solo dejan ver lo marcado como PUBLIC.
    """
    async with SessionLocal() as session:
        async with session.begin():
            await session.execute(
                _SET_USER, {"user_id": str(user_id) if user_id else ""}
            )
            yield session


@asynccontextmanager
async def session_for_system() -> AsyncIterator[AsyncSession]:
    """Sesión que omite RLS. Solo para jobs y workers.

    Usos legítimos, y solo estos:
      · registro de usuarios (todavía no hay identidad)
      · canje de tokens de invitación
      · recálculo de scores, vencimientos, procesado del outbox
      · backoffice de plataforma, con auditoría explícita

    Nunca en una ruta que reciba entrada de usuario sin autorizar antes. El
    bypass queda declarado en el código y es rastreable con un grep, que es
    exactamente lo que no ocurre cuando el backend se conecta como `postgres`.
    """
    async with SessionLocal() as session:
        async with session.begin():
            await session.execute(_SET_SYSTEM, {"flag": "on"})
            yield session


# ─────────────────────────────────────────────────────────────────────────────
# Dependencias de FastAPI
# ─────────────────────────────────────────────────────────────────────────────
#
# La dependencia que combina "usuario del JWT" + "sesión con esa identidad"
# vive en app.api.deps, no aquí, y por una razón concreta: necesita depender
# explícitamente de app.api.deps.get_current_user_id para que FastAPI resuelva
# el usuario ANTES de abrir la sesión. Leer `request.state.user_id` sin esa
# relación de dependencia explícita no lo garantiza — FastAPI no promete un
# orden entre dependencias hermanas que no dependen unas de otras — y en un
# fallo silencioso eso se traduce en una sesión con `app.current_user_id`
# vacío, es decir, tratando a un usuario autenticado como anónimo.
#
# Poner esa función aquí también crearía un import circular: este módulo la
# necesitaría depender de app.api.deps, y app.api.deps ya depende de este
# módulo para las funciones de más abajo.


async def gather_for_user(
    user_id: UUID | None, *reads: Callable[[AsyncSession], Awaitable[_T]]
) -> list[_T]:
    """Corre lecturas independientes en paralelo, cada una en su propia
    conexión del pool con la misma identidad RLS ya fijada.

    Solo para lecturas que no dependen entre sí: la base remota (Supabase,
    Oregon) impone ~200-300ms de latencia por round trip, así que una función
    que hoy encadena varios `await` secuenciales paga esa latencia una vez
    por cada uno. Una `AsyncSession` no admite ejecuciones concurrentes sobre
    sí misma — de ahí que cada lectura abra la suya, no que se repartan una
    sesión compartida — por lo que cada rama ve su propia foto de datos ya
    commiteados, no las escrituras sin commitear de otra rama ni de quien
    llama. Nunca uses esto para mezclar una escritura con lecturas que deben
    verla dentro de la misma transacción.
    """

    async def _run(read: Callable[[AsyncSession], Awaitable[_T]]) -> _T:
        async with session_for_user(user_id) as session:
            return await read(session)

    return list(await asyncio.gather(*(_run(read) for read in reads)))


async def get_public_session() -> AsyncIterator[AsyncSession]:
    """Sesión explícitamente anónima, para el sitio público.

    Existe como dependencia propia para que una ruta pública no pueda heredar
    por accidente la identidad de un token que llegara de más.
    """
    async with session_for_user(None) as session:
        yield session


async def get_system_session() -> AsyncIterator[AsyncSession]:
    """Sesión de sistema. Ver la advertencia de ``session_for_system``."""
    async with session_for_system() as session:
        yield session
