"""document_types, organization_documents, organization_document_versions
— repositorio único de evidencia (fase 5.1/5.2).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import CHAR, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

DocumentCategoryEnum = ENUM(
    "LEGAL",
    "TRIBUTARIO",
    "LABORAL",
    "FINANCIERO",
    "SSO",
    "SEGUROS",
    name="document_category",
    schema="app",
    create_type=False,
)
DocumentVersionStatusEnum = ENUM(
    "ACTIVE",
    "SUPERSEDED",
    "REVOKED",
    name="document_version_status",
    schema="app",
    create_type=False,
)


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str | None] = mapped_column(
        CHAR(2), ForeignKey("countries.code")
    )
    category: Mapped[str] = mapped_column(DocumentCategoryEnum, nullable=False)
    requires_expiry: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    default_validity_days: Mapped[int | None] = mapped_column(Integer)
    is_sensitive: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class OrganizationDocument(Base):
    __tablename__ = "organization_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_types.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class OrganizationDocumentVersion(Base):
    __tablename__ = "organization_document_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_documents.id", ondelete="CASCADE")
    )

    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[date | None] = mapped_column()
    valid_from: Mapped[date | None] = mapped_column()
    valid_until: Mapped[date | None] = mapped_column()
    status: Mapped[str] = mapped_column(
        DocumentVersionStatusEnum, nullable=False, server_default="ACTIVE"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
