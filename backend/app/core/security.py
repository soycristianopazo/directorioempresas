"""Hashing de contraseñas y JWT.

Dos primitivas separadas y sin estado compartido entre ellas: el hash de
contraseña vive solo en `public.users.password_hash` y nunca sale de la base;
el JWT es lo único que el cliente ve, y no contiene el hash ni ningún dato
sensible — solo el id de usuario y una expiración corta.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt_sha256 en vez de bcrypt a secas: bcrypt puro trunca el input a 72
# bytes en silencio. Una contraseña larga con caracteres multibyte podría
# superar ese límite sin que nadie lo note, y dos contraseñas distintas que
# compartan el mismo prefijo de 72 bytes producirían el mismo hash. El
# prehash SHA-256 de passlib elimina el límite sin cambiar el costo de bcrypt.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password, rounds=settings.bcrypt_rounds)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


# ─────────────────────────────────────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────────────────────────────────────
#
# El access token es de corta vida (15 min) y va en el header Authorization.
# El refresh token NO es un JWT: es un valor aleatorio opaco cuyo hash se
# guarda en user_sessions (ver services/auth.py). Que el access token expire
# rápido limita el daño de un XSS que lo robe; que el refresh no sea un JWT
# significa que revocarlo es un DELETE, no esperar a que expire por su cuenta.


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> UUID:
    """Devuelve el user_id del token, o lanza InvalidTokenError.

    No distingue "expirado" de "manipulado" de "malformado": el llamador
    siempre debe reaccionar igual (pedir un token nuevo), así que exponer la
    causa exacta solo ayudaría a alguien intentando falsificar uno.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("Tipo de token incorrecto")
        return UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise InvalidTokenError("Token inválido o expirado") from exc
