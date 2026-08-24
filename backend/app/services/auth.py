"""Registro, login, refresco y cierre de sesión.

Contrato con el frontend (src/lib/api.js y src/context/AuthContext.jsx):

  · El access token viaja en el body de la respuesta y el cliente lo guarda en
    memoria/localStorage. Vive 15 minutos.
  · El refresh token viaja en una cookie httpOnly (`refresh_token`, scoped a
    /api/auth) que el cliente nunca lee ni envía a mano — el navegador la
    adjunta solo en peticiones a /api/auth/*.
  · Cada refresh ROTA el token: se emite uno nuevo y el anterior queda
    marcado `replaced_by_id`. Reutilizar uno ya rotado es la señal de un
    token robado — revoca la cadena completa en vez de solo el intento.

Login y registro corren en contexto de sistema (`session_for_system`) porque
todavía no existe una identidad autenticada con la que RLS pueda trabajar: es
exactamente el caso legítimo para el que existe ese bypass, declarado y
rastreable, en vez de conectar como `postgres`.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.rls import session_for_system, session_for_user
from app.models.rbac import PlatformAdmin
from app.repositories import organizations as orgs_repo
from app.repositories import users as users_repo


class AuthError(Exception):
    """Error de negocio de autenticación. El router lo traduce a HTTP 401."""


REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"
MAX_FAILED_LOGINS = 8
LOCKOUT_MINUTES = 15


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


@dataclass
class AuthResult:
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime
    user_id: UUID


async def _issue_session(
    user_id: UUID, *, user_agent: str | None, ip_address: str | None
) -> AuthResult:
    refresh_token = _generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)

    async with session_for_system() as db:
        await users_repo.create_session(
            db,
            user_id=user_id,
            refresh_token_hash=_hash_token(refresh_token),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    return AuthResult(
        access_token=create_access_token(user_id),
        refresh_token=refresh_token,
        refresh_expires_at=expires_at,
        user_id=user_id,
    )


async def register(
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthResult:
    async with session_for_system() as db:
        existing = await users_repo.get_by_email(db, email)
        if existing is not None:
            # Mismo mensaje que credenciales inválidas más abajo: no confirmar
            # si un correo existe es una decisión deliberada de privacidad.
            raise AuthError("No se pudo crear la cuenta")

        user = await users_repo.create_user_with_profile(
            db,
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
        )
        user_id = user.id

    return await _issue_session(user_id, user_agent=user_agent, ip_address=ip_address)


async def login(
    *,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthResult:
    async with session_for_system() as db:
        user = await users_repo.get_by_email(db, email)

        if user is None:
            # Se ejecuta un verify_password igual, con un hash de relleno, para
            # que el tiempo de respuesta no delate si el correo existe o no.
            verify_password(password, "$2b$12$" + "x" * 53)
            raise AuthError("Correo o contraseña incorrectos")

        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise AuthError("Cuenta bloqueada temporalmente por intentos fallidos")

        if not verify_password(password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= MAX_FAILED_LOGINS:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=LOCKOUT_MINUTES
                )
            raise AuthError("Correo o contraseña incorrectos")

        if not user.is_active:
            raise AuthError("Cuenta desactivada")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)
        user_id = user.id

    return await _issue_session(user_id, user_agent=user_agent, ip_address=ip_address)


async def refresh(
    *,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthResult:
    token_hash = _hash_token(refresh_token)

    async with session_for_system() as db:
        record = await users_repo.get_session_by_token_hash(db, token_hash)

        if record is None:
            raise AuthError("Sesión no encontrada")

        if record.revoked_at is not None:
            # Un token ya rotado que vuelve a presentarse es la firma de un
            # robo: alguien más además del legítimo lo está usando. Se corta
            # toda la cadena de sesiones del usuario, no solo este intento.
            await users_repo.revoke_all_sessions_for_user(db, record.user_id)
            raise AuthError("Sesión revocada. Por seguridad, inicia sesión nuevamente.")

        if record.expires_at < datetime.now(UTC):
            raise AuthError("Sesión expirada")

        user_id = record.user_id
        old_session_id = record.id

    result = await _issue_session(user_id, user_agent=user_agent, ip_address=ip_address)

    async with session_for_system() as db:
        new_record = await users_repo.get_session_by_token_hash(
            db, _hash_token(result.refresh_token)
        )
        await users_repo.revoke_session(
            db, old_session_id, replaced_by_id=new_record.id if new_record else None
        )

    return result


async def logout(*, refresh_token: str) -> None:
    token_hash = _hash_token(refresh_token)
    async with session_for_system() as db:
        record = await users_repo.get_session_by_token_hash(db, token_hash)
        if record is not None and record.revoked_at is None:
            await users_repo.revoke_session(db, record.id)


@dataclass
class MeResult:
    user_id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    full_name: str | None
    locale: str
    last_org_id: UUID | None
    memberships: list[orgs_repo.MembershipRow]
    is_platform_admin: bool


async def get_me(user_id: UUID) -> MeResult:
    """Corre con la identidad real del usuario (no system context): así se
    ejercita exactamente el mismo camino de RLS que usará el resto de la app,
    y v_my_organizations solo puede devolver lo que ESE usuario ve.
    """
    async with session_for_user(user_id) as db:
        user = await users_repo.get_by_id(db, user_id)
        profile = await users_repo.get_profile(db, user_id)
        memberships = await orgs_repo.list_my_memberships(db)

        result = await db.execute(
            select(PlatformAdmin.user_id).where(
                PlatformAdmin.user_id == user_id, PlatformAdmin.revoked_at.is_(None)
            )
        )
        is_admin = result.scalar_one_or_none() is not None

    if user is None or profile is None:
        raise AuthError("Usuario no encontrado")

    return MeResult(
        user_id=user_id,
        email=str(user.email),
        first_name=profile.first_name,
        last_name=profile.last_name,
        full_name=profile.full_name,
        locale=profile.locale,
        last_org_id=profile.last_org_id,
        memberships=memberships,
        is_platform_admin=is_admin,
    )
