"""Esquemas de invitaciones y NDA (fase 7.1/7.2)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InviteSupplierRequest(BaseModel):
    supplier_organization_id: UUID
    source: str = "MANUAL"
    match_score_snapshot: float | None = None


class DisqualifyRequest(BaseModel):
    reason: str | None = None


class DeclineRequest(BaseModel):
    reason_code: str | None = None


class NdaUpsertRequest(BaseModel):
    title: str
    body_text: str


class NdaOut(BaseModel):
    id: UUID
    version: int
    title: str
    body_text: str


class InvitationHistoryEntryOut(BaseModel):
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


class InvitationDetailOut(BaseModel):
    id: UUID
    sourcing_event_id: UUID
    status: str
    source: str
    invited_at: datetime
    viewed_at: datetime | None
    responded_at: datetime | None
    decline_reason_code: str | None
    history: list[InvitationHistoryEntryOut]
