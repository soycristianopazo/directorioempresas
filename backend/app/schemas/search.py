"""Esquemas de búsqueda pública y perfil de organización (fase 4)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SearchResultOut(BaseModel):
    offering_id: UUID
    organization_id: UUID
    offering_name: str
    offering_slug: str
    short_description: str | None
    offering_type: str
    availability_status: str
    legal_name: str
    trade_name: str | None
    organization_slug: str
    completion_pct: int
    price_type: str | None
    amount_min: float | None
    amount_max: float | None
    currency_code: str | None
    unit_code: str | None
    pricing_is_public: bool | None
    rank: float


class FacetItemOut(BaseModel):
    label: str
    value: UUID
    count: int


class FacetsOut(BaseModel):
    taxonomy_nodes: list[FacetItemOut]
    industries: list[FacetItemOut]
    admin_divisions: list[FacetItemOut]


class SearchResponseOut(BaseModel):
    results: list[SearchResultOut]
    total: int
    page: int
    page_size: int
    facets: FacetsOut


class PublicOfferingSummaryOut(BaseModel):
    id: UUID
    name: str
    slug: str
    short_description: str | None
    offering_type: str
    primary_category: str | None
    price_type: str | None
    amount_min: float | None
    amount_max: float | None
    currency_code: str | None
    photo_url: str | None


class PublicOrganizationOut(BaseModel):
    id: UUID
    legal_name: str
    trade_name: str | None
    slug: str
    short_description: str | None
    description: str | None
    website_url: str | None
    completion_pct: int
    logo_url: str | None
    industries: list[str]
    territories: list[str]
    offerings: list[PublicOfferingSummaryOut]
    certifications: list[str]
