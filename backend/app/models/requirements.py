"""requirements — la necesidad de compra (fase 6.1)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import CHAR, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

RequirementStatusEnum = ENUM(
    "DRAFT",
    "CONVERTED",
    "ARCHIVED",
    name="requirement_status",
    schema="app",
    create_type=False,
)
RequirementSourceEnum = ENUM(
    "FORM",
    "FREE_TEXT",
    "DISCOVERY",
    name="requirement_source",
    schema="app",
    create_type=False,
)


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    primary_taxonomy_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_nodes.id")
    )
    industry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id")
    )

    needed_from: Mapped[date | None] = mapped_column()
    needed_until: Mapped[date | None] = mapped_column()
    duration_months: Mapped[int | None] = mapped_column(Integer)
    estimated_budget: Mapped[float | None] = mapped_column(Numeric)
    currency_code: Mapped[str | None] = mapped_column(
        CHAR(3), ForeignKey("currencies.code")
    )
    commercial_terms: Mapped[str | None] = mapped_column(Text)
    payment_terms: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        RequirementStatusEnum, nullable=False, server_default="DRAFT"
    )
    source: Mapped[str] = mapped_column(
        RequirementSourceEnum, nullable=False, server_default="FORM"
    )
    raw_input_text: Mapped[str | None] = mapped_column(Text)

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


class RequirementItem(Base):
    __tablename__ = "requirement_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("units_of_measure.code")
    )
    specifications: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class RequirementLocation(Base):
    __tablename__ = "requirement_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE")
    )
    admin_division_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_divisions.id")
    )


class RequirementDocument(Base):
    __tablename__ = "requirement_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )


class RequirementTag(Base):
    __tablename__ = "requirement_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE")
    )
    tag: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
