"""sourcing_events y su estructura: lotes, ítems, hitos, documentos,
criterios MUST/NICE (fase 6.2/6.3)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, CHAR, ENUM, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

SourcingEventTypeEnum = ENUM(
    "RFI",
    "RFQ",
    "RFP",
    "QUICK_BUY",
    "DIRECT_AWARD",
    name="sourcing_event_type",
    schema="app",
    create_type=False,
)
SourcingBidModeEnum = ENUM(
    "OPEN", "SEALED", name="sourcing_bid_mode", schema="app", create_type=False
)
SourcingEventStatusEnum = ENUM(
    "DRAFT",
    "PUBLISHED",
    "CANCELLED",
    "AWARDED",
    "CLOSED",
    "VOID",
    name="sourcing_event_status",
    schema="app",
    create_type=False,
)
VisibilityLevelEnum = ENUM(
    "PUBLIC",
    "REGISTERED",
    "BUYERS_ONLY",
    "INVITED_ONLY",
    "PRIVATE",
    name="visibility_level",
    schema="app",
    create_type=False,
)
SourcingStageTypeEnum = ENUM(
    "PUBLICATION",
    "QUESTIONS_DEADLINE",
    "BID_DEADLINE",
    "BID_OPENING",
    "EVALUATION",
    "ESTIMATED_AWARD",
    name="sourcing_stage_type",
    schema="app",
    create_type=False,
)
SourcingCriterionTypeEnum = ENUM(
    "ATTRIBUTE",
    "CERTIFICATION",
    "ACCREDITATION",
    "TERRITORY",
    "EXPERIENCE_YEARS",
    "INDUSTRY_EXPERIENCE",
    "CAPACITY",
    "CUSTOM",
    name="sourcing_criterion_type",
    schema="app",
    create_type=False,
)
CriterionRequirementLevelEnum = ENUM(
    "MUST_HAVE",
    "NICE_TO_HAVE",
    name="criterion_requirement_level",
    schema="app",
    create_type=False,
)


class SourcingEvent(Base):
    __tablename__ = "sourcing_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id")
    )

    event_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(
        SourcingEventTypeEnum, nullable=False, server_default="RFQ"
    )
    visibility: Mapped[str] = mapped_column(
        VisibilityLevelEnum, nullable=False, server_default="PRIVATE"
    )
    bid_mode: Mapped[str] = mapped_column(
        SourcingBidModeEnum, nullable=False, server_default="OPEN"
    )
    status: Mapped[str] = mapped_column(
        SourcingEventStatusEnum, nullable=False, server_default="DRAFT"
    )
    void_reason: Mapped[str | None] = mapped_column(Text)

    currency_code: Mapped[str | None] = mapped_column(
        CHAR(3), ForeignKey("currencies.code")
    )
    estimated_amount: Mapped[float | None] = mapped_column(Numeric)

    requires_nda: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    requires_accreditation_program_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accreditation_programs.id")
    )
    max_invitations: Mapped[int | None] = mapped_column(Integer)

    matching_weights: Mapped[dict | None] = mapped_column(JSONB)

    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    bid_opened_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    bid_opened_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )


class SourcingEventLot(Base):
    __tablename__ = "sourcing_event_lots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class SourcingEventItem(Base):
    __tablename__ = "sourcing_event_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_event_lots.id", ondelete="SET NULL")
    )
    taxonomy_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_nodes.id")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("units_of_measure.code")
    )
    is_optional: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class SourcingEventStage(Base):
    __tablename__ = "sourcing_event_stages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    stage_type: Mapped[str] = mapped_column(SourcingStageTypeEnum, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class SourcingEventDocument(Base):
    __tablename__ = "sourcing_event_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    requires_nda: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )


class SourcingEventCriterion(Base):
    __tablename__ = "sourcing_event_criteria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )

    criterion_type: Mapped[str] = mapped_column(
        SourcingCriterionTypeEnum, nullable=False
    )
    requirement_level: Mapped[str] = mapped_column(
        CriterionRequirementLevelEnum, nullable=False, server_default="MUST_HAVE"
    )
    is_blocking: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    weight: Mapped[float] = mapped_column(Numeric, nullable=False, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    description: Mapped[str | None] = mapped_column(Text)

    attribute_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attribute_definitions.id")
    )
    operator: Mapped[str | None] = mapped_column(Text)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_number: Mapped[float | None] = mapped_column(Numeric)
    value_number_max: Mapped[float | None] = mapped_column(Numeric)
    value_boolean: Mapped[bool | None] = mapped_column()
    value_date: Mapped[date | None] = mapped_column()
    value_date_max: Mapped[date | None] = mapped_column()
    value_options: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    certification_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certification_types.id")
    )
    accreditation_program_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accreditation_programs.id")
    )
    admin_division_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_divisions.id")
    )
    max_mobilization_days: Mapped[int | None] = mapped_column(Integer)
    industry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id")
    )
    min_years: Mapped[int | None] = mapped_column(Integer)
    min_capacity: Mapped[float | None] = mapped_column(Numeric)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
