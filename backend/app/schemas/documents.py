"""Esquemas del repositorio de evidencia documental."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DocumentCategory = Literal[
    "LEGAL", "TRIBUTARIO", "LABORAL", "FINANCIERO", "SSO", "SEGUROS"
]
DocumentVersionStatus = Literal["ACTIVE", "SUPERSEDED", "REVOKED"]


class DocumentTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    category: str
    requires_expiry: bool
    default_validity_days: int | None
    is_sensitive: bool


class OrganizationDocumentOut(BaseModel):
    id: UUID
    document_type_id: UUID
    code: str
    name: str
    category: str
    requires_expiry: bool
    is_sensitive: bool
    active_version_id: UUID | None
    valid_until: date | None
    issued_at: date | None
    version_status: str | None


class DocumentVersionOut(BaseModel):
    id: UUID
    status: str
    issued_at: date | None
    valid_from: date | None
    valid_until: date | None
    url: str | None


class UploadVersionResponse(BaseModel):
    id: UUID
    url: str | None
    valid_until: date | None
