"""Esquemas de datos de referencia: países, monedas, unidades, idiomas,
divisiones administrativas.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CountryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    default_currency_code: str | None
    phone_prefix: str | None


class CurrencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    symbol: str
    decimal_places: int
    is_index_unit: bool


class UnitOfMeasureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    family: str


class LanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class AdminDivisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_id: UUID | None
    level: int
    level_name: str
    slug: str
    official_code: str | None
    name: str
