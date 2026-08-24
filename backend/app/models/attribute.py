"""Atributos dinámicos tipados (EAV) y su vínculo a nodos de taxonomía."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

AttributeDataTypeEnum = ENUM(
    "TEXT",
    "NUMBER",
    "BOOLEAN",
    "DATE",
    "SELECT",
    "MULTISELECT",
    "RANGE",
    name="attribute_data_type",
    schema="app",
    create_type=False,
)
AttributeAppliesToEnum = ENUM(
    "OFFERING",
    "REQUIREMENT",
    "ORGANIZATION",
    name="attribute_applies_to",
    schema="app",
    create_type=False,
)


class AttributeDefinition(Base):
    __tablename__ = "attribute_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    data_type: Mapped[str] = mapped_column(AttributeDataTypeEnum, nullable=False)
    unit_code: Mapped[str | None] = mapped_column(
        Text, ForeignKey("units_of_measure.code")
    )
    min_value: Mapped[float | None] = mapped_column(Numeric)
    max_value: Mapped[float | None] = mapped_column(Numeric)
    is_filterable: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    is_comparable: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    help_text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class AttributeOption(Base):
    __tablename__ = "attribute_options"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    attribute_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attribute_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))


class TaxonomyNodeAttribute(Base):
    __tablename__ = "taxonomy_node_attributes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    attribute_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attribute_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    applies_to: Mapped[str] = mapped_column(AttributeAppliesToEnum, nullable=False)
    is_required: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    is_inherited: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    filter_weight: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
