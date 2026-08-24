"""Dependencias de autenticación de FastAPI.

Esta es la pieza que conecta el JWT del header con la identidad que
`app.db.rls` fija en la base con SET LOCAL. El orden importa: `get_db_session`
declara una dependencia EXPLÍCITA sobre `get_current_user_id`, para que
FastAPI garantice resolver el usuario antes de abrir la sesión. Leer un valor
puesto por una dependencia hermana sin esa relación explícita no lo garantiza,
y el fallo sería silencioso: una sesión con `app.current_user_id` vacío trata
a un usuario autenticado como anónimo.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidTokenError, decode_access_token
from app.db.rls import get_public_session, get_system_session, session_for_user

# auto_error=False: sin esto, un request sin header Authorization aborta con
# 403 antes de que el código de la ruta pueda decidir si el acceso anónimo es
# válido (como en el perfil público de una organización).
_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UUID | None:
    """Resuelve el usuario del token, si lo hay. No exige que exista."""
    if credentials is None:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except InvalidTokenError:
        return None


async def require_user_id(
    user_id: Annotated[UUID | None, Depends(get_current_user_id)]
) -> UUID:
    """Exige un token válido. Para las rutas que no admiten acceso anónimo."""
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def get_db_session(
    user_id: Annotated[UUID | None, Depends(get_current_user_id)],
) -> AsyncIterator[AsyncSession]:
    """Sesión con la identidad del token ya fijada vía SET LOCAL.

    `user_id` puede ser None (visitante sin token): la sesión sigue siendo
    válida, solo que app.current_user_id() devolverá NULL y las policies
    dejarán ver únicamente lo marcado como PUBLIC.
    """
    async with session_for_user(user_id) as session:
        yield session


async def get_authenticated_session(
    user_id: Annotated[UUID, Depends(require_user_id)],
) -> AsyncIterator[AsyncSession]:
    """Como get_db_session, pero exige que haya sesión. Para rutas privadas."""
    async with session_for_user(user_id) as session:
        yield session


# Alias con nombres explícitos para usar directamente en las rutas.
CurrentUserId = Annotated[UUID, Depends(require_user_id)]
OptionalUserId = Annotated[UUID | None, Depends(get_current_user_id)]
DbSession = Annotated[AsyncSession, Depends(get_authenticated_session)]
AnySession = Annotated[AsyncSession, Depends(get_db_session)]
PublicSession = Annotated[AsyncSession, Depends(get_public_session)]
SystemSession = Annotated[AsyncSession, Depends(get_system_session)]
