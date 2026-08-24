"""Esquemas de ubicaciones, contactos, media, industrias y territorios."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LocationType = Literal[
    "HEADQUARTERS", "BRANCH", "OPERATIONAL_BASE", "WAREHOUSE", "PLANT", "OFFICE"
]
ContactType = Literal[
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
]


class CreateLocationRequest(BaseModel):
    location_type: LocationType = "OFFICE"
    address_line: str = Field(min_length=3, max_length=500)
    admin_division_id: UUID | None = None
    is_headquarters: bool = False
    lat: float | None = None
    lng: float | None = None


class UpdateLocationRequest(CreateLocationRequest):
    pass


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_type: str
    address_line: str
    admin_division_id: UUID | None
    is_headquarters: bool
    lat: float | None
    lng: float | None


class CreateContactRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    contact_type: ContactType = "GENERAL"
    email: str | None = None
    phone: str | None = Field(default=None, max_length=32)
    whatsapp: str | None = Field(default=None, max_length=32)
    linkedin_url: str | None = None
    is_public: bool = False
    is_primary: bool = False


class UpdateContactRequest(CreateContactRequest):
    pass


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    job_title: str | None
    contact_type: str
    email: str | None
    phone: str | None
    whatsapp: str | None
    linkedin_url: str | None
    is_public: bool
    is_primary: bool


class MediaOut(BaseModel):
    id: UUID
    media_type: str
    alt_text: str | None = None
    sort_order: int = 0
    url: str


class SetIndustryRequest(BaseModel):
    industry_id: UUID
    years_experience: int | None = Field(default=None, ge=0)
    is_primary: bool = False


class IndustryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    industry_id: UUID
    name: str
    years_experience: int | None
    is_primary: bool


class AddTerritoryRequest(BaseModel):
    admin_division_id: UUID


class TerritoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admin_division_id: UUID
    name: str
    level_name: str


class CreatedOut(BaseModel):
    id: UUID
