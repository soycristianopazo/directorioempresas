"""Esquemas del proceso de sourcing: sourcing_events y su estructura
(fase 6.2/6.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SourcingEventType = Literal["RFI", "RFQ", "RFP", "QUICK_BUY", "DIRECT_AWARD"]
SourcingBidMode = Literal["OPEN", "SEALED"]
SourcingEventStatus = Literal["DRAFT", "PUBLISHED", "CANCELLED"]
Visibility = Literal["PUBLIC", "REGISTERED", "BUYERS_ONLY", "INVITED_ONLY", "PRIVATE"]
SourcingCriterionType = Literal[
    "ATTRIBUTE",
    "CERTIFICATION",
    "ACCREDITATION",
    "TERRITORY",
    "EXPERIENCE_YEARS",
    "INDUSTRY_EXPERIENCE",
    "CAPACITY",
    "CUSTOM",
]
CriterionRequirementLevel = Literal["MUST_HAVE", "NICE_TO_HAVE"]


class CreatedOut(BaseModel):
    id: UUID


class CreateSourcingEventRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    event_type: SourcingEventType = "RFQ"
    requirement_id: UUID | None = None
    visibility: Visibility = "PRIVATE"
    bid_mode: SourcingBidMode = "OPEN"
    currency_code: str | None = None
    estimated_amount: float | None = None
    requires_nda: bool = False
    requires_accreditation_program_id: UUID | None = None
    max_invitations: int | None = Field(default=None, gt=0)
    matching_weights: dict[str, float] | None = None


class UpdateSourcingEventRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    visibility: Visibility = "PRIVATE"
    bid_mode: SourcingBidMode = "OPEN"
    currency_code: str | None = None
    estimated_amount: float | None = None
    requires_nda: bool = False
    requires_accreditation_program_id: UUID | None = None
    max_invitations: int | None = Field(default=None, gt=0)
    matching_weights: dict[str, float] | None = None


class SourcingEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    requirement_id: UUID | None
    event_code: str
    name: str
    description: str | None
    event_type: SourcingEventType
    visibility: Visibility
    bid_mode: SourcingBidMode
    status: SourcingEventStatus
    currency_code: str | None
    estimated_amount: float | None
    requires_nda: bool
    requires_accreditation_program_id: UUID | None
    max_invitations: int | None
    matching_weights: dict | None
    published_at: datetime | None
    bid_opened_at: datetime | None
    bid_opened_by: UUID | None
    created_at: datetime


class AddLotRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    sort_order: int = 0


class LotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    sort_order: int


class AddItemRequest(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    quantity: float = Field(gt=0)
    unit_code: str | None = None
    taxonomy_node_id: UUID | None = None
    lot_id: UUID | None = None
    is_optional: bool = False
    sort_order: int = 0


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lot_id: UUID | None
    taxonomy_node_id: UUID | None
    description: str
    quantity: float
    unit_code: str | None
    is_optional: bool
    sort_order: int


class UpsertStageRequest(BaseModel):
    stage_type: Literal[
        "PUBLICATION",
        "QUESTIONS_DEADLINE",
        "BID_DEADLINE",
        "BID_OPENING",
        "EVALUATION",
        "ESTIMATED_AWARD",
    ]
    scheduled_at: datetime | None = None


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stage_type: str
    scheduled_at: datetime | None
    completed_at: datetime | None


class CreateCriterionRequest(BaseModel):
    criterion_type: SourcingCriterionType
    requirement_level: CriterionRequirementLevel = "MUST_HAVE"
    is_blocking: bool = True
    weight: float = Field(default=1, gt=0)
    sort_order: int = 0
    description: str | None = None

    attribute_definition_id: UUID | None = None
    operator: str | None = None
    value_text: str | None = None
    value_number: float | None = None
    value_number_max: float | None = None
    value_boolean: bool | None = None
    value_date: str | None = None
    value_date_max: str | None = None
    value_options: list[str] | None = None

    certification_type_id: UUID | None = None
    accreditation_program_id: UUID | None = None
    admin_division_id: UUID | None = None
    max_mobilization_days: int | None = None
    industry_id: UUID | None = None
    min_years: int | None = None
    min_capacity: float | None = None


class CriterionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    criterion_type: SourcingCriterionType
    requirement_level: CriterionRequirementLevel
    is_blocking: bool
    weight: float
    sort_order: int
    description: str | None
    attribute_definition_id: UUID | None
    operator: str | None
    certification_type_id: UUID | None
    accreditation_program_id: UUID | None
    admin_division_id: UUID | None
    industry_id: UUID | None
    min_years: int | None
    min_capacity: float | None


class SourcingEventDetailOut(BaseModel):
    event: SourcingEventOut
    lots: list[LotOut]
    items: list[ItemOut]
    stages: list[StageOut]
    criteria: list[CriterionOut]
