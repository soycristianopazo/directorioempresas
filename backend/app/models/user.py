"""public.users, user_sessions, user_tokens, profiles."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Computed, ForeignKey, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, INET, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    email_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)


class UserSession(Base):
    """Refresh tokens. Se guarda solo el hash — ver services/auth.py."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(INET)

    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_sessions.id", ondelete="SET NULL")
    )


class UserToken(Base):
    """Tokens de un solo uso: verificación de correo, reset de contraseña."""

    __tablename__ = "user_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    # full_name es GENERATED ALWAYS AS ... STORED en la base. Computed() no
    # solo lo documenta: es lo que hace que SQLAlchemy excluya la columna del
    # INSERT/UPDATE. Sin esto, el ORM manda `full_name = NULL` en cada INSERT
    # (incluso sin asignarlo explícitamente, porque es un mapped_column común)
    # y Postgres lo rechaza — "cannot insert a non-DEFAULT value into column
    # full_name" — porque ninguna sentencia puede escribir en una columna
    # generada, ni siquiera con NULL. La expresión que sigue es solo
    # documentación: como los modelos nunca corren create_all(), no se
    # reejecuta como DDL.
    full_name: Mapped[str | None] = mapped_column(
        Text,
        Computed(
            "nullif(trim(coalesce(first_name, '') || ' ' || coalesce(last_name, '')), '')",
            persisted=True,
        ),
    )
    avatar_url: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    job_title: Mapped[str | None] = mapped_column(Text)

    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default="es-CL")
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="America/Santiago"
    )
    last_org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    onboarded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_active_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="profile")
