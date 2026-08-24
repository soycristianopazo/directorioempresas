"""Esquemas de notificaciones in-app y preferencias (fase 7.9)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

NotificationPriority = Literal["LOW", "NORMAL", "HIGH"]
NotificationChannel = Literal["IN_APP", "EMAIL"]


class NotificationOut(BaseModel):
    id: UUID
    type: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: UUID | None
    action_url: str | None
    priority: NotificationPriority
    read_at: datetime | None
    created_at: datetime


class NotificationPreferenceOut(BaseModel):
    id: UUID
    channel: NotificationChannel
    event_type: str
    enabled: bool


class SetPreferenceRequest(BaseModel):
    channel: NotificationChannel
    event_type: str
    enabled: bool
