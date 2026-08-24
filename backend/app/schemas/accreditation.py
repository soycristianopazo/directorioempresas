"""Esquemas de programas, postulación y revisión de acreditación."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EnrollmentStatus = Literal[
    "INCOMPLETE",
    "PENDING_DOCUMENTS",
    "UNDER_REVIEW",
    "ACCREDITED",
    "OBSERVED",
    "SUSPENDED",
    "REJECTED",
    "EXPIRED",
]
FulfillmentStatus = Literal[
    "PENDING",
    "SUBMITTED",
    "UNDER_REVIEW",
    "OBSERVED",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
]
FulfillmentDecision = Literal["APPROVED", "OBSERVED", "REJECTED"]
EnrollmentDecision = Literal["ACCREDITED", "OBSERVED", "REJECTED"]


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    owner_scope: str
    validity_months: int
    is_active: bool


class RequirementGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    weight: float
    sort_order: int


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    requirement_kind: str
    name: str
    description: str | None
    is_mandatory: bool
    weight: float
    sort_order: int


class ProgramDetailOut(BaseModel):
    program: ProgramOut
    groups: list[RequirementGroupOut]
    requirements: list[RequirementOut]


class EnrollRequest(BaseModel):
    program_id: UUID


class EnrollmentOut(BaseModel):
    id: UUID
    program_id: UUID
    program_code: str
    program_name: str
    status: EnrollmentStatus
    completion_pct: int
    valid_from: date | None
    valid_until: date | None
    submitted_at: datetime | None
    decided_at: datetime | None


class FulfillmentOut(BaseModel):
    id: UUID
    requirement_id: UUID
    document_version_id: UUID | None
    certification_id: UUID | None
    declared_value: str | None
    status: FulfillmentStatus
    reviewer_id: UUID | None
    reviewed_at: datetime | None
    observation: str | None
    expires_at: date | None
    requirement_name: str
    requirement_kind: str
    is_mandatory: bool
    weight: float
    group_id: UUID
    group_name: str


class SectionProgressOut(BaseModel):
    group_id: UUID
    completion_pct: int
    name: str
    weight: float
    sort_order: int


class StatusHistoryOut(BaseModel):
    id: UUID
    from_status: str | None
    to_status: str
    actor_id: UUID | None
    reason: str | None
    created_at: datetime


class EnrollmentDetailOut(BaseModel):
    enrollment: EnrollmentOut
    fulfillments: list[FulfillmentOut]
    sections: list[SectionProgressOut]
    history: list[StatusHistoryOut]


class SubmitEvidenceRequest(BaseModel):
    requirement_id: UUID
    document_version_id: UUID | None = None
    certification_id: UUID | None = None
    declared_value: str | None = Field(default=None, max_length=2000)


class ReviewQueueItemOut(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    program_id: UUID
    program_code: str
    program_name: str
    status: EnrollmentStatus
    completion_pct: int
    submitted_at: datetime | None
    created_at: datetime


class ReviewFulfillmentRequest(BaseModel):
    decision: FulfillmentDecision
    observation: str | None = Field(default=None, max_length=2000)


class DecideEnrollmentRequest(BaseModel):
    decision: EnrollmentDecision
    reason: str | None = Field(default=None, max_length=2000)


class CreatedOut(BaseModel):
    id: UUID


class CreateProgramRequest(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    validity_months: int = Field(default=12, gt=0)


class CreateRequirementGroupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    weight: float = Field(default=1, gt=0)
    sort_order: int = 0


class CreateRequirementRequest(BaseModel):
    group_id: UUID
    requirement_kind: Literal[
        "DOCUMENT", "CERTIFICATION", "ATTRIBUTE", "DECLARATION", "FORM"
    ]
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_mandatory: bool = True
    weight: float = Field(default=1, gt=0)
    document_type_id: UUID | None = None
    certification_type_id: UUID | None = None
    attribute_definition_id: UUID | None = None
    sort_order: int = 0
