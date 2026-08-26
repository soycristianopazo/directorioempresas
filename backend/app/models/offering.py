"""supplier_offerings y sus tablas relacionadas (D4 — el núcleo)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import CHAR, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

OfferingTypeEnum = ENUM(
    "PRODUCT",
    "SERVICE",
    "RENTAL",
    "SOFTWARE",
    "TRAINING",
    "CONSULTING",
    name="offering_type",
    schema="app",
    create_type=False,
)
OfferingStatusEnum = ENUM(
    "DRAFT",
    "ACTIVE",
    "PAUSED",
    "ARCHIVED",
    name="offering_status",
    schema="app",
    create_type=False,
)
OfferingAvailabilityStatusEnum = ENUM(
    "AVAILABLE",
    "LIMITED",
    "ON_REQUEST",
    "UNAVAILABLE",
    name="offering_availability_status",
    schema="app",
    create_type=False,
)
OfferingCoverageTypeEnum = ENUM(
    "OPERATIONAL",
    "COMMERCIAL",
    "MOBILIZABLE",
    name="offering_coverage_type",
    schema="app",
    create_type=False,
)
OfferingPriceTypeEnum = ENUM(
    "FIXED",
    "FROM",
    "RANGE",
    "ON_REQUEST",
    name="offering_price_type",
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


class SupplierOffering(Base):
    __tablename__ = "supplier_offerings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    offering_type: Mapped[str] = mapped_column(OfferingTypeEnum, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)

    short_description: Mapped[str | None] = mapped_column(Text)
    full_description: Mapped[str | None] = mapped_column(Text)
    specifications: Mapped[str | None] = mapped_column(Text)
    applications: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)

    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    moq: Mapped[int | None] = mapped_column(Integer)
    monthly_capacity: Mapped[float | None] = mapped_column(Numeric)
    capacity_unit_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("units_of_measure.code")
    )
    warranty_months: Mapped[int | None] = mapped_column(Integer)
    has_after_sales: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )

    availability_status: Mapped[str] = mapped_column(
        OfferingAvailabilityStatusEnum, nullable=False, server_default="AVAILABLE"
    )
    visibility: Mapped[str] = mapped_column(
        VisibilityLevelEnum, nullable=False, server_default="PUBLIC"
    )
    status: Mapped[str] = mapped_column(
        OfferingStatusEnum, nullable=False, server_default="DRAFT"
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completion_pct: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class OfferingTaxonomyNode(Base):
    __tablename__ = "offering_taxonomy_nodes"

    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_nodes.id"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )


class OfferingIndustry(Base):
    __tablename__ = "offering_industries"

    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id"), primary_key=True
    )


class OfferingTag(Base):
    __tablename__ = "offering_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OfferingTerritory(Base):
    __tablename__ = "offering_territories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    admin_division_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_divisions.id"), nullable=False
    )
    coverage_type: Mapped[str] = mapped_column(
        OfferingCoverageTypeEnum, nullable=False, server_default="OPERATIONAL"
    )
    mobilization_days: Mapped[int | None] = mapped_column(Integer)
    has_local_base: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )


class OfferingPricing(Base):
    __tablename__ = "offering_pricing"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_type: Mapped[str] = mapped_column(
        OfferingPriceTypeEnum, nullable=False, server_default="ON_REQUEST"
    )
    amount_min: Mapped[float | None] = mapped_column(Numeric(18, 4))
    amount_max: Mapped[float | None] = mapped_column(Numeric(18, 4))
    currency_code: Mapped[str | None] = mapped_column(
        CHAR(3), ForeignKey("currencies.code")
    )
    unit_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("units_of_measure.code")
    )
    valid_until: Mapped[date | None] = mapped_column()
    is_public: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OfferingMedia(Base):
    __tablename__ = "offering_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OfferingDeal(Base):
    """Oferta por stock u cuenta regresiva sobre un producto/servicio ya
    publicado (fase 11) — ver alembic/sql/0092_offering_deals.sql. Sin
    columna de estado: vigencia = cancelled_at is null and (expires_at is
    null or expires_at > now()) and (stock_quantity is null or
    stock_remaining > 0), calculada donde se lea, no guardada."""

    __tablename__ = "offering_deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )

    deal_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    original_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    currency_code: Mapped[str] = mapped_column(
        CHAR(3), ForeignKey("currencies.code"), nullable=False
    )
    unit_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("units_of_measure.code")
    )

    stock_quantity: Mapped[int | None] = mapped_column(Integer)
    stock_remaining: Mapped[int | None] = mapped_column(Integer)
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    cancelled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )


class OfferingDocument(Base):
    __tablename__ = "offering_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
