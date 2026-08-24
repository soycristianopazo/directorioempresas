"""Cotizaciones: contenedor, revisiones append-only, líneas, respuestas y
documentos (fase 7.5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import CHAR, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

QuotationStatusEnum = ENUM(
    "DRAFT",
    "SUBMITTED",
    "WITHDRAWN",
    "DISQUALIFIED",
    name="quotation_status",
    schema="app",
    create_type=False,
)
QuotationRoundTypeEnum = ENUM(
    "INITIAL", name="quotation_round_type", schema="app", create_type=False
)


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    supplier_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    status: Mapped[str] = mapped_column(
        QuotationStatusEnum, nullable=False, server_default="DRAFT"
    )
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotation_revisions.id", use_alter=True)
    )
    first_submitted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
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


class QuotationRevision(Base):
    __tablename__ = "quotation_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE")
    )

    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_type: Mapped[str] = mapped_column(
        QuotationRoundTypeEnum, nullable=False, server_default="INITIAL"
    )
    is_current: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )

    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    valid_until: Mapped[date | None] = mapped_column()

    currency_code: Mapped[str] = mapped_column(CHAR(3), ForeignKey("currencies.code"))
    fx_rate_snapshot: Mapped[float | None] = mapped_column(Numeric)
    subtotal: Mapped[float | None] = mapped_column(Numeric)
    tax_amount: Mapped[float | None] = mapped_column(Numeric)
    total_amount: Mapped[float] = mapped_column(Numeric, nullable=False)
    total_amount_base: Mapped[float | None] = mapped_column(Numeric)

    payment_terms: Mapped[str | None] = mapped_column(Text)
    delivery_days: Mapped[int | None] = mapped_column(Integer)
    warranty_terms: Mapped[str | None] = mapped_column(Text)
    exclusions: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    quotation_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotation_revisions.id", ondelete="CASCADE")
    )
    sourcing_event_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_event_items.id")
    )

    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("units_of_measure.code")
    )
    unit_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    discount_pct: Mapped[float | None] = mapped_column(Numeric)
    tax_rate: Mapped[float | None] = mapped_column(Numeric)
    line_total: Mapped[float] = mapped_column(Numeric, nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    brand: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class QuotationResponse(Base):
    __tablename__ = "quotation_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    quotation_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotation_revisions.id", ondelete="CASCADE")
    )
    sourcing_event_criterion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_event_criteria.id")
    )

    complies: Mapped[bool | None] = mapped_column()
    value_text: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class QuotationDocument(Base):
    __tablename__ = "quotation_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    quotation_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotation_revisions.id", ondelete="CASCADE")
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
