"""countries, currencies, fx_rates, units_of_measure, languages,
sii_economic_activities."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CHAR, ENUM, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

SiiVatStatusEnum = ENUM(
    "SI", "NO", "G", name="sii_vat_status", schema="app", create_type=False
)
SiiTaxCategoryEnum = ENUM(
    "1", "2", "G", name="sii_tax_category", schema="app", create_type=False
)


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    default_currency_code: Mapped[str | None] = mapped_column(CHAR(3))
    phone_prefix: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    decimal_places: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="2"
    )
    is_index_unit: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class FxRate(Base):
    __tablename__ = "fx_rates"

    from_code: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    to_code: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    valid_on: Mapped[date] = mapped_column(primary_key=True)
    rate: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    family: Mapped[str] = mapped_column(Text, nullable=False)
    factor_to_base: Mapped[float | None] = mapped_column(Numeric)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class Language(Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class SiiEconomicActivity(Base):
    """Código de actividad económica (giro) del SII — catálogo público."""

    __tablename__ = "sii_economic_activities"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sector: Mapped[str] = mapped_column(Text, nullable=False)
    subgroup: Mapped[str | None] = mapped_column(Text)
    vat_affected: Mapped[str] = mapped_column(SiiVatStatusEnum, nullable=False)
    tax_category: Mapped[str] = mapped_column(SiiTaxCategoryEnum, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
