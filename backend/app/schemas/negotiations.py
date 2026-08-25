"""Esquemas de rondas de negociación (fase 8.5)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.quotations import QuotationItemIn, QuotationResponseIn


class OpenRoundRequest(BaseModel):
    round_type: str
    participant_supplier_organization_ids: list[UUID]
    deadline: datetime | None = None
    target_reduction_pct: float | None = None
    instructions: str | None = None


class SubmitCounterRequest(BaseModel):
    """Mismos campos que SubmitRevisionRequest (schemas/quotations.py), con
    negotiation_round_id agregado. Reutiliza QuotationItemIn/QuotationResponseIn
    en vez de duplicarlos — misma forma exacta, no hay razón para bifurcar."""

    negotiation_round_id: UUID
    currency_code: str
    valid_until: date | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    total_amount: float
    payment_terms: str | None = None
    delivery_days: int | None = None
    warranty_terms: str | None = None
    exclusions: str | None = None
    notes: str | None = None
    items: list[QuotationItemIn]
    responses: list[QuotationResponseIn] = []
