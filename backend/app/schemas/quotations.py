"""Esquemas de cotizaciones (fase 7.5/7.7)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuotationItemIn(BaseModel):
    sourcing_event_item_id: UUID
    quantity: float
    unit_code: str | None = None
    unit_price: float
    discount_pct: float | None = None
    tax_rate: float | None = None
    lead_time_days: int | None = None
    brand: str | None = None
    model: str | None = None
    notes: str | None = None


class QuotationResponseIn(BaseModel):
    sourcing_event_criterion_id: UUID
    complies: bool | None = None
    value_text: str | None = None
    notes: str | None = None


class SubmitRevisionRequest(BaseModel):
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


class RevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    round_number: int
    round_type: str
    submitted_at: datetime
    currency_code: str
    total_amount: float
    total_amount_base: float | None
