"""certification_types, organization_certifications, client_references,
case_studies y relacionadas (D5, alcance acotado a fase 3 — ver el
comentario de cabecera de 0025_certifications.sql sobre qué queda para
fase 5).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CertificationVerificationStatusEnum = ENUM(
    "UNVERIFIED",
    "PENDING_REVIEW",
    "VERIFIED",
    "REJECTED",
    "EXPIRED",
    name="certification_verification_status",
    schema="app",
    create_type=False,
)
CaseStudyVerificationStatusEnum = ENUM(
    "UNVERIFIED",
    "VERIFIED",
    "DISPUTED",
    name="case_study_verification_status",
    schema="app",
    create_type=False,
)


class CertificationType(Base):
    __tablename__ = "certification_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_body: Mapped[str | None] = mapped_column(Text)
    requires_scope: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    requires_expiry: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OrganizationCertification(Base):
    __tablename__ = "organization_certifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    certification_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certification_types.id"), nullable=False
    )

    certificate_number: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    issued_by: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[date | None] = mapped_column()
    valid_until: Mapped[date | None] = mapped_column()

    verification_status: Mapped[str] = mapped_column(
        CertificationVerificationStatusEnum, nullable=False, server_default="UNVERIFIED"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class ClientReference(Base):
    __tablename__ = "client_references"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    client_name: Mapped[str | None] = mapped_column(Text)
    industry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id")
    )
    since: Mapped[date | None] = mapped_column()
    is_public: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    is_verified: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class CaseStudy(Base):
    __tablename__ = "case_studies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    client_reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_references.id", ondelete="SET NULL")
    )
    industry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id")
    )
    admin_division_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_divisions.id")
    )

    started_on: Mapped[date | None] = mapped_column()
    ended_on: Mapped[date | None] = mapped_column()
    duration_months: Mapped[int | None] = mapped_column(Integer)

    description: Mapped[str | None] = mapped_column(Text)
    results: Mapped[str | None] = mapped_column(Text)
    reference_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_contacts.id", ondelete="SET NULL")
    )

    is_public: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    verification_status: Mapped[str] = mapped_column(
        CaseStudyVerificationStatusEnum, nullable=False, server_default="UNVERIFIED"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class CaseStudyTaxonomyNode(Base):
    __tablename__ = "case_study_taxonomy_nodes"

    case_study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_studies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_nodes.id"), primary_key=True
    )


class CaseStudyMedia(Base):
    __tablename__ = "case_study_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    case_study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_studies.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
