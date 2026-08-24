"""Esquemas de certificaciones, referencias de clientes y casos de éxito."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CertificationTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    issuing_body: str | None
    requires_scope: bool
    requires_expiry: bool


class CreateCertificationRequest(BaseModel):
    certification_type_id: UUID
    certificate_number: str | None = Field(default=None, max_length=200)
    scope: str | None = Field(default=None, max_length=500)
    issued_by: str | None = Field(default=None, max_length=200)
    issued_at: date | None = None
    valid_until: date | None = None


class CertificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    certification_type_id: UUID
    certificate_number: str | None
    scope: str | None
    issued_by: str | None
    issued_at: date | None
    valid_until: date | None
    verification_status: str


class CreateClientReferenceRequest(BaseModel):
    client_organization_id: UUID | None = None
    client_name: str | None = Field(default=None, max_length=200)
    industry_id: UUID | None = None
    since: date | None = None
    is_public: bool = False


class ClientReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_organization_id: UUID | None
    client_name: str | None
    industry_id: UUID | None
    since: date | None
    is_public: bool
    is_verified: bool


class CreateCaseStudyRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    client_reference_id: UUID | None = None
    industry_id: UUID | None = None
    admin_division_id: UUID | None = None
    started_on: date | None = None
    ended_on: date | None = None
    duration_months: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=5000)
    results: str | None = Field(default=None, max_length=2000)
    reference_contact_id: UUID | None = None
    is_public: bool = False


class UpdateCaseStudyRequest(CreateCaseStudyRequest):
    pass


class CaseStudyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    client_reference_id: UUID | None
    industry_id: UUID | None
    admin_division_id: UUID | None
    started_on: date | None
    ended_on: date | None
    duration_months: int | None
    description: str | None
    results: str | None
    reference_contact_id: UUID | None
    is_public: bool
    verification_status: str


class SetCaseStudyTaxonomyRequest(BaseModel):
    node_ids: list[UUID] = Field(default_factory=list)


class CaseStudyMediaOut(BaseModel):
    id: UUID
    caption: str | None = None
    url: str


class CreatedOut(BaseModel):
    id: UUID
