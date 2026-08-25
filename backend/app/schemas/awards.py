"""Esquemas de adjudicación: propuesta de award, decisión de aprobación y
políticas de aprobación (fase 8.6/8.7)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AwardItemIn(BaseModel):
    sourcing_event_item_id: UUID
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class ProposeAwardRequest(BaseModel):
    awarded_organization_id: UUID
    quotation_revision_id: UUID
    justification: str | None = None
    items: list[AwardItemIn]


class DecideApprovalRequest(BaseModel):
    decision: str
    comment: str | None = None


class ApprovalPolicyIn(BaseModel):
    step_order: int
    required_role_code: str
    min_amount: float = 0
    max_amount: float | None = None
