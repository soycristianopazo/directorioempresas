"""Esquemas de la necesidad de compra (fase 6.1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RequirementStatus = Literal["DRAFT", "CONVERTED", "ARCHIVED"]
RequirementSource = Literal["FORM", "FREE_TEXT", "DISCOVERY"]


class CreatedOut(BaseModel):
    id: UUID


class CreateRequirementRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    primary_taxonomy_node_id: UUID | None = None
    industry_id: UUID | None = None
    needed_from: date | None = None
    needed_until: date | None = None
    duration_months: int | None = Field(default=None, gt=0)
    estimated_budget: float | None = None
    currency_code: str | None = None
    commercial_terms: str | None = None
    payment_terms: str | None = None
    source: RequirementSource = "FORM"
    raw_input_text: str | None = None


class UpdateRequirementRequest(CreateRequirementRequest):
    pass


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    primary_taxonomy_node_id: UUID | None
    industry_id: UUID | None
    needed_from: date | None
    needed_until: date | None
    duration_months: int | None
    estimated_budget: float | None
    currency_code: str | None
    status: RequirementStatus
    source: RequirementSource
    created_at: datetime


class AddRequirementItemRequest(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    quantity: float = Field(gt=0)
    unit_code: str | None = None
    specifications: str | None = None
    sort_order: int = 0


class RequirementItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    quantity: float
    unit_code: str | None
    specifications: str | None
    sort_order: int


class RequirementLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admin_division_id: UUID
    name: str


class SetRequirementTagsRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)


class RequirementDocumentOut(BaseModel):
    id: UUID
    name: str
    url: str | None
    created_at: datetime | None = None


class UploadRequirementDocumentResponse(BaseModel):
    id: UUID
    name: str
    url: str | None


class RequirementDetailOut(BaseModel):
    requirement: RequirementOut
    items: list[RequirementItemOut]
    locations: list[RequirementLocationOut]
    documents: list[RequirementDocumentOut]
    tags: list[str]
