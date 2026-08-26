"""organization_locations, organization_contacts, organization_media,
organization_settings, organization_industries, organization_territories.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CHAR, CITEXT, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

LocationTypeEnum = ENUM(
    "HEADQUARTERS",
    "BRANCH",
    "OPERATIONAL_BASE",
    "WAREHOUSE",
    "PLANT",
    "OFFICE",
    name="location_type",
    schema="app",
    create_type=False,
)
ContactTypeEnum = ENUM(
    "GENERAL",
    "COMERCIAL",
    "VENTAS",
    "GERENCIA",
    "OPERACIONES",
    "ABASTECIMIENTO",
    "CONTRATOS",
    "FINANZAS",
    "RRHH",
    "HSE",
    "ADMINISTRADOR_CONTRATO",
    "SOPORTE_TECNICO",
    name="contact_type",
    schema="app",
    create_type=False,
)


class OrganizationLocation(Base):
    __tablename__ = "organization_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    location_type: Mapped[str] = mapped_column(
        LocationTypeEnum, nullable=False, server_default="OFFICE"
    )
    is_headquarters: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )

    address_line: Mapped[str] = mapped_column(Text, nullable=False)
    admin_division_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_divisions.id")
    )
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))

    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OrganizationContact(Base):
    __tablename__ = "organization_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    job_title: Mapped[str | None] = mapped_column(Text)
    contact_type: Mapped[str] = mapped_column(
        ContactTypeEnum, nullable=False, server_default="GENERAL"
    )

    email: Mapped[str | None] = mapped_column(CITEXT)
    phone: Mapped[str | None] = mapped_column(Text)
    whatsapp: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(Text)

    is_public: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    is_primary: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OrganizationMedia(Base):
    __tablename__ = "organization_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    # Solo aplica a media_type=LOGO — 'SQUARE' u 'HORIZONTAL'. NULL para el
    # resto de media_types y para logos subidos antes de esta columna.
    logo_shape: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    base_currency_code: Mapped[str | None] = mapped_column(
        CHAR(3), server_default="CLP"
    )
    preferred_language: Mapped[str | None] = mapped_column(Text, server_default="es-CL")
    notify_new_message: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    notify_new_requirement: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OrganizationIndustry(Base):
    __tablename__ = "organization_industries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id"), primary_key=True
    )
    years_experience: Mapped[int | None] = mapped_column(SmallInteger)
    is_primary: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OrganizationEconomicActivity(Base):
    __tablename__ = "organization_economic_activities"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sii_code: Mapped[str] = mapped_column(
        Text, ForeignKey("sii_economic_activities.code"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OrganizationTerritory(Base):
    __tablename__ = "organization_territories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    admin_division_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_divisions.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
