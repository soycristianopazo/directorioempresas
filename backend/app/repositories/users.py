"""Acceso a datos de usuarios, perfiles, sesiones y tokens."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Profile, User, UserSession, UserToken


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_profile(session: AsyncSession, user_id: UUID) -> Profile | None:
    result = await session.execute(select(Profile).where(Profile.id == user_id))
    return result.scalar_one_or_none()


async def create_user_with_profile(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    first_name: str,
    last_name: str,
) -> User:
    user = User(email=email, password_hash=password_hash)
    session.add(user)
    await session.flush()  # necesitamos user.id antes de crear el profile

    profile = Profile(id=user.id, first_name=first_name, last_name=last_name)
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    user.profile = profile
    return user


async def create_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    refresh_token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> UserSession:
    record = UserSession(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    session.add(record)
    await session.flush()
    return record


async def get_session_by_token_hash(
    session: AsyncSession, token_hash: str
) -> UserSession | None:
    result = await session.execute(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def revoke_session(
    session: AsyncSession, session_id: UUID, replaced_by_id: UUID | None = None
) -> None:
    record = await session.get(UserSession, session_id)
    if record is not None:
        record.revoked_at = datetime.now(record.issued_at.tzinfo)
        record.replaced_by_id = replaced_by_id


async def revoke_all_sessions_for_user(session: AsyncSession, user_id: UUID) -> None:
    result = await session.execute(
        select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        )
    )
    for record in result.scalars():
        record.revoked_at = datetime.now(record.issued_at.tzinfo)


async def create_verification_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    purpose: str,
    token_hash: str,
    expires_at: datetime,
) -> UserToken:
    record = UserToken(
        user_id=user_id, purpose=purpose, token_hash=token_hash, expires_at=expires_at
    )
    session.add(record)
    await session.flush()
    return record
