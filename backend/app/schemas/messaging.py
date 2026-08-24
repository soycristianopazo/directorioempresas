"""Esquemas de mensajería: conversaciones, mensajes y adjuntos (fase 7.8)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ConversationContextType = Literal[
    "ORGANIZATION", "OFFERING", "REQUIREMENT", "SOURCING_EVENT", "QUOTATION"
]


class GetOrCreateConversationRequest(BaseModel):
    context_type: ConversationContextType
    context_id: UUID
    participant_organization_ids: list[UUID] = Field(default_factory=list)


class ConversationParticipantOut(BaseModel):
    organization_id: UUID
    name: str


class ConversationOut(BaseModel):
    id: UUID
    context_type: ConversationContextType
    organization_id: UUID | None
    offering_id: UUID | None
    requirement_id: UUID | None
    sourcing_event_id: UUID | None
    quotation_id: UUID | None
    created_at: datetime
    updated_at: datetime
    last_read_at: datetime | None
    unread_count: int
    participants: list[ConversationParticipantOut]


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=8000)


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID | None
    sender_organization_id: UUID | None
    body: str
    is_system: bool
    created_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None


class AttachmentOut(BaseModel):
    id: UUID
    url: str | None
