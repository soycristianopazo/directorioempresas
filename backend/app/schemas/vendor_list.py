"""Esquemas de Vendor List / AVL (fase 8.8)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SetRelationshipStatusRequest(BaseModel):
    supplier_organization_id: UUID
    status: str


class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    buyer_organization_id: UUID
    supplier_organization_id: UUID
    status: str
    status_changed_at: datetime
    status_changed_by: UUID | None


class AddNoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    relationship_id: UUID
    body: str
    created_at: datetime
    created_by: UUID | None


class CreatedOut(BaseModel):
    id: UUID
