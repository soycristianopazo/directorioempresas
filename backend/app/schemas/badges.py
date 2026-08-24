"""Esquemas de badges de confianza."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrganizationBadgeOut(BaseModel):
    id: UUID
    badge_id: UUID
    granted_at: datetime
    expires_at: datetime | None
    code: str
    name: str
    description: str | None
    icon: str | None
