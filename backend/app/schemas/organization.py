"""Esquemas de organización, equipo e invitaciones."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.rut import format_rut, is_valid_rut

Capability = Literal["BUYER", "SUPPLIER"]
Visibility = Literal["PUBLIC", "REGISTERED", "BUYERS_ONLY", "PRIVATE"]
CompanySize = Literal["MICRO", "SMALL", "MEDIUM", "LARGE", "ENTERPRISE"]


class CreateOrganizationRequest(BaseModel):
    legal_name: str = Field(min_length=2, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    rut: str = Field(min_length=1)
    capabilities: list[Capability] = Field(min_length=1)
    country_code: str = Field(default="CL", min_length=2, max_length=2)

    @field_validator("rut")
    @classmethod
    def rut_must_be_valid(cls, value: str) -> str:
        if not is_valid_rut(value):
            raise ValueError("El RUT no es válido")
        return format_rut(value)


class UpdateOrganizationRequest(BaseModel):
    legal_name: str = Field(min_length=2, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    short_description: str | None = Field(default=None, max_length=280)
    description: str | None = Field(default=None, max_length=5000)
    value_proposition: str | None = Field(default=None, max_length=1000)
    website_url: str | None = None
    linkedin_url: str | None = None
    general_email: EmailStr | None = None
    general_phone: str | None = Field(default=None, max_length=32)
    founded_year: int | None = None
    company_size: CompanySize | None = None
    employee_count: int | None = Field(default=None, ge=0)
    visibility: Visibility


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legal_name: str
    trade_name: str | None
    slug: str
    status: str
    visibility: str
    short_description: str | None
    description: str | None
    value_proposition: str | None
    website_url: str | None
    linkedin_url: str | None
    general_email: str | None
    general_phone: str | None
    founded_year: int | None
    company_size: str | None
    employee_count: int | None
    completion_pct: int
    capabilities: list[str]
    primary_identifier: str | None = None


class SwitchOrganizationRequest(BaseModel):
    organization_id: UUID


class InviteMemberRequest(BaseModel):
    organization_id: UUID
    email: EmailStr
    role_code: str = Field(min_length=1)


class TeamRoleOut(BaseModel):
    id: UUID
    code: str
    name: str


class TeamMemberOut(BaseModel):
    member_id: UUID
    user_id: UUID
    status: str
    joined_at: datetime
    full_name: str | None
    email: str | None
    roles: list[TeamRoleOut]


class PendingInvitationOut(BaseModel):
    id: UUID
    email: str
    expires_at: datetime
    created_at: datetime
    role: TeamRoleOut


class InvitationResult(BaseModel):
    invitation_id: UUID
    accept_url: str


class ChangeMemberRolesRequest(BaseModel):
    organization_id: UUID
    role_codes: list[str] = Field(min_length=1)
