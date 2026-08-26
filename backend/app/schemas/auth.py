"""Esquemas de entrada/salida del router de autenticación."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_strength(value: str) -> str:
    if not any(c.islower() for c in value):
        raise ValueError("Incluye una minúscula")
    if not any(c.isupper() for c in value):
        raise ValueError("Incluye una mayúscula")
    if not any(c.isdigit() for c in value):
        raise ValueError("Incluye un número")
    return value


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    last_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legal_name: str
    trade_name: str | None
    slug: str
    status: str
    visibility: str
    completion_pct: int
    member_id: UUID
    role_codes: list[str]
    capabilities: list[str]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    full_name: str | None
    locale: str
    last_org_id: UUID | None
    memberships: list[MembershipOut] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(TokenResponse):
    user: UserOut


class MeResponse(BaseModel):
    user: UserOut
    is_platform_admin: bool


class UpdateProfileRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    last_name: str = Field(min_length=2, max_length=80)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class AuditContext(BaseModel):
    """Contexto opcional que el cliente puede reportar para auditoría."""

    ip_address: str | None = None
    user_agent: str | None = None


class SessionInfo(BaseModel):
    id: UUID
    created_at: datetime
    expires_at: datetime
    user_agent: str | None
    is_current: bool
