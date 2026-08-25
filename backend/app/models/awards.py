"""Adjudicación: políticas de aprobación, awards, líneas y pasos (fase 8.6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import CHAR, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

AwardStatusEnum = ENUM(
    "DRAFT",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "PUBLISHED",
    name="award_status",
    schema="app",
    create_type=False,
)
ApprovalStatusEnum = ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="approval_status",
    schema="app",
    create_type=False,
)


class OrganizationApprovalPolicy(Base):
    __tablename__ = "organization_approval_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    step_order: Mapped[int] = mapped_column(nullable=False)
    required_role_code: Mapped[str] = mapped_column(Text, nullable=False)
    min_amount: Mapped[float] = mapped_column(
        Numeric, nullable=False, server_default="0"
    )
    max_amount: Mapped[float | None] = mapped_column(Numeric)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Award(Base):
    __tablename__ = "awards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    awarded_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    quotation_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotation_revisions.id")
    )

    status: Mapped[str] = mapped_column(
        AwardStatusEnum, nullable=False, server_default="DRAFT"
    )
    justification: Mapped[str | None] = mapped_column(Text)

    currency_code: Mapped[str] = mapped_column(CHAR(3), ForeignKey("currencies.code"))
    amount: Mapped[float] = mapped_column(Numeric, nullable=False)
    amount_base: Mapped[float] = mapped_column(Numeric, nullable=False)

    proposed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    proposed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AwardItem(Base):
    __tablename__ = "award_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    award_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("awards.id", ondelete="CASCADE")
    )
    sourcing_event_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_event_items.id", ondelete="CASCADE")
    )
    quotation_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotation_items.id")
    )

    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AwardApproval(Base):
    __tablename__ = "award_approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    award_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("awards.id", ondelete="CASCADE")
    )

    step_order: Mapped[int] = mapped_column(nullable=False)
    required_role_code: Mapped[str] = mapped_column(Text, nullable=False)
    approver_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_members.id", ondelete="CASCADE")
    )

    status: Mapped[str] = mapped_column(
        ApprovalStatusEnum, nullable=False, server_default="PENDING"
    )
    decided_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
