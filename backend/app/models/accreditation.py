"""Programas de acreditación y estado por organización (fase 5.3/5.4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CHAR, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

AccreditationOwnerScopeEnum = ENUM(
    "PLATFORM",
    "ORGANIZATION",
    name="accreditation_owner_scope",
    schema="app",
    create_type=False,
)
AccreditationRequirementKindEnum = ENUM(
    "DOCUMENT",
    "CERTIFICATION",
    "ATTRIBUTE",
    "DECLARATION",
    "FORM",
    name="accreditation_requirement_kind",
    schema="app",
    create_type=False,
)
AccreditationEnrollmentStatusEnum = ENUM(
    "INCOMPLETE",
    "PENDING_DOCUMENTS",
    "UNDER_REVIEW",
    "ACCREDITED",
    "OBSERVED",
    "SUSPENDED",
    "REJECTED",
    "EXPIRED",
    name="accreditation_enrollment_status",
    schema="app",
    create_type=False,
)
AccreditationFulfillmentStatusEnum = ENUM(
    "PENDING",
    "SUBMITTED",
    "UNDER_REVIEW",
    "OBSERVED",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
    name="accreditation_fulfillment_status",
    schema="app",
    create_type=False,
)
RiskLevelEnum = ENUM(
    "LOW",
    "HIGH",
    "MEDIUM",
    "CRITICAL",
    name="risk_level",
    schema="app",
    create_type=False,
)


class AccreditationProgram(Base):
    __tablename__ = "accreditation_programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    owner_scope: Mapped[str] = mapped_column(
        AccreditationOwnerScopeEnum, nullable=False, server_default="PLATFORM"
    )
    owner_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    applies_to_taxonomy_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_nodes.id")
    )
    applies_to_industry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id")
    )
    applies_to_risk_level: Mapped[str | None] = mapped_column(RiskLevelEnum)
    country_code: Mapped[str | None] = mapped_column(
        CHAR(2), ForeignKey("countries.code")
    )

    validity_months: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="12"
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class RequirementGroup(Base):
    __tablename__ = "requirement_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accreditation_programs.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Numeric, nullable=False, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AccreditationRequirement(Base):
    __tablename__ = "accreditation_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accreditation_programs.id", ondelete="CASCADE")
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirement_groups.id", ondelete="CASCADE")
    )

    requirement_kind: Mapped[str] = mapped_column(
        AccreditationRequirementKindEnum, nullable=False
    )
    document_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_types.id")
    )
    certification_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certification_types.id")
    )
    attribute_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attribute_definitions.id")
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_mandatory: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    weight: Mapped[float] = mapped_column(Numeric, nullable=False, server_default="1")
    min_validity_days: Mapped[int | None] = mapped_column(Integer)
    reviewer_role: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="ACCREDITATION_REVIEWER"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AccreditationStatusTransition(Base):
    __tablename__ = "accreditation_status_transitions"

    from_status: Mapped[str] = mapped_column(
        AccreditationEnrollmentStatusEnum, primary_key=True
    )
    to_status: Mapped[str] = mapped_column(
        AccreditationEnrollmentStatusEnum, primary_key=True
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    requires_reviewer: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )


class AccreditationEnrollment(Base):
    __tablename__ = "accreditation_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accreditation_programs.id")
    )

    status: Mapped[str] = mapped_column(
        AccreditationEnrollmentStatusEnum, nullable=False, server_default="INCOMPLETE"
    )
    completion_pct: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    score: Mapped[float | None] = mapped_column(Numeric)

    valid_from: Mapped[date | None] = mapped_column()
    valid_until: Mapped[date | None] = mapped_column()
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AccreditationFulfillment(Base):
    __tablename__ = "accreditation_fulfillments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accreditation_enrollments.id", ondelete="CASCADE"),
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accreditation_requirements.id")
    )

    document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_document_versions.id")
    )
    certification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_certifications.id")
    )
    declared_value: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        AccreditationFulfillmentStatusEnum, nullable=False, server_default="PENDING"
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    observation: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[date | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AccreditationSectionProgress(Base):
    __tablename__ = "accreditation_section_progress"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accreditation_enrollments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requirement_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    completion_pct: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AccreditationStatusHistory(Base):
    __tablename__ = "accreditation_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accreditation_enrollments.id", ondelete="CASCADE"),
    )
    from_status: Mapped[str | None] = mapped_column(AccreditationEnrollmentStatusEnum)
    to_status: Mapped[str] = mapped_column(
        AccreditationEnrollmentStatusEnum, nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AccreditationReviewEvent(Base):
    __tablename__ = "accreditation_review_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    fulfillment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accreditation_fulfillments.id", ondelete="CASCADE"),
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
