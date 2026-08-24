"""Valores de atributos dinámicos declarados por el proveedor en un offering."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OfferingAttributeValue(Base):
    __tablename__ = "offering_attribute_values"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    attribute_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attribute_definitions.id"), nullable=False
    )

    value_text: Mapped[str | None] = mapped_column(Text)
    value_number: Mapped[float | None] = mapped_column(Numeric)
    value_boolean: Mapped[bool | None] = mapped_column()
    value_date: Mapped[date | None] = mapped_column()
    # numrange no tiene un tipo dedicado simple en sqlalchemy.dialects.postgresql
    # con Mapped[...] directo — se maneja como texto en la capa Python (nunca se
    # construye ni parsea acá; RANGE no está entre los tipos de atributo usados
    # todavía por ningún seed real, así que no vale la pena un TypeDecorator
    # dedicado por ahora).
    option_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attribute_options.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class OfferingAttributeOptionValue(Base):
    __tablename__ = "offering_attribute_option_values"

    offering_attribute_value_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offering_attribute_values.id", ondelete="CASCADE"),
        primary_key=True,
    )
    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attribute_options.id"), primary_key=True
    )
