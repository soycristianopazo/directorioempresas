"""organizations, organization_capabilities, organization_business_roles,
organization_legal_identifiers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# `create_type=False`: los tipos ya existen en Postgres (creados por el SQL de
# la migración 0001). Si SQLAlchemy intentara crearlos aquí, chocaría con lo
# que ya está, porque estos modelos nunca corren create_all().
OrganizationCapabilityEnum = ENUM(
    "BUYER",
    "SUPPLIER",
    "PLATFORM_ADMIN",
    name="organization_capability",
    schema="app",
    create_type=False,
)
OrganizationBusinessRoleEnum = ENUM(
    "MANDANTE",
    "CONTRATISTA",
    "SUBCONTRATISTA",
    "FABRICANTE",
    "DISTRIBUIDOR",
    "REPRESENTANTE",
    "CONSULTORA",
    "OTEC",
    "SERVICIOS_PROFESIONALES",
    name="organization_business_role",
    schema="app",
    create_type=False,
)
OrganizationStatusEnum = ENUM(
    "DRAFT",
    "ACTIVE",
    "SUSPENDED",
    "ARCHIVED",
    name="organization_status",
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
CompanySizeEnum = ENUM(
    "MICRO",
    "SMALL",
    "MEDIUM",
    "LARGE",
    "ENTERPRISE",
    name="company_size",
    schema="app",
    create_type=False,
)
RevenueBandEnum = ENUM(
    "UNDER_2400_UF",
    "UF_2400_25000",
    "UF_25000_100000",
    "UF_100000_1000000",
    "OVER_1000000_UF",
    "UNDISCLOSED",
    name="revenue_band",
    schema="app",
    create_type=False,
)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    trade_name: Mapped[str | None] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, server_default="CL")

    founded_year: Mapped[int | None] = mapped_column(SmallInteger)
    company_size: Mapped[str | None] = mapped_column(CompanySizeEnum)
    employee_count: Mapped[int | None]
    revenue_band: Mapped[str] = mapped_column(
        RevenueBandEnum, nullable=False, server_default="UNDISCLOSED"
    )
    legal_form: Mapped[str | None] = mapped_column(Text)

    short_description: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    value_proposition: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    general_email: Mapped[str | None] = mapped_column(CITEXT)
    general_phone: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        OrganizationStatusEnum, nullable=False, server_default="DRAFT"
    )
    visibility: Mapped[str] = mapped_column(
        VisibilityLevelEnum, nullable=False, server_default="PRIVATE"
    )

    is_claimed: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    data_source: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="SELF_REGISTERED"
    )
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )

    completion_pct: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    capabilities: Mapped[list["OrganizationCapability"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    business_roles: Mapped[list["OrganizationBusinessRole"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    legal_identifiers: Mapped[list["OrganizationLegalIdentifier"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationCapability(Base):
    __tablename__ = "organization_capabilities"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    capability: Mapped[str] = mapped_column(
        OrganizationCapabilityEnum, primary_key=True
    )
    enabled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    enabled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )

    organization: Mapped[Organization] = relationship(back_populates="capabilities")


class OrganizationBusinessRole(Base):
    __tablename__ = "organization_business_roles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    business_role: Mapped[str] = mapped_column(
        OrganizationBusinessRoleEnum, primary_key=True
    )

    organization: Mapped[Organization] = relationship(back_populates="business_roles")


class OrganizationLegalIdentifier(Base):
    __tablename__ = "organization_legal_identifiers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    identifier_type: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str | None] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_normalized: Mapped[str] = mapped_column(Text, nullable=False)

    is_primary: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    organization: Mapped[Organization] = relationship(
        back_populates="legal_identifiers"
    )
