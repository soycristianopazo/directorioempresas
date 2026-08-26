"""Esquemas del catálogo de oferta."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

OfferingType = Literal[
    "PRODUCT", "SERVICE", "RENTAL", "SOFTWARE", "TRAINING", "CONSULTING"
]
OfferingStatus = Literal["DRAFT", "ACTIVE", "PAUSED", "ARCHIVED"]
AvailabilityStatus = Literal["AVAILABLE", "LIMITED", "ON_REQUEST", "UNAVAILABLE"]
CoverageType = Literal["OPERATIONAL", "COMMERCIAL", "MOBILIZABLE"]
PriceType = Literal["FIXED", "FROM", "RANGE", "ON_REQUEST"]
Visibility = Literal["PUBLIC", "REGISTERED", "BUYERS_ONLY", "INVITED_ONLY", "PRIVATE"]


class CreateOfferingRequest(BaseModel):
    offering_type: OfferingType
    name: str = Field(min_length=2, max_length=200)
    short_description: str | None = Field(default=None, max_length=280)
    full_description: str | None = Field(default=None, max_length=5000)


class UpdateOfferingRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    short_description: str | None = Field(default=None, max_length=280)
    full_description: str | None = Field(default=None, max_length=5000)
    specifications: str | None = None
    applications: str | None = None
    brand: str | None = None
    model: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    moq: int | None = Field(default=None, gt=0)
    monthly_capacity: float | None = None
    capacity_unit_code: str | None = None
    warranty_months: int | None = Field(default=None, ge=0)
    has_after_sales: bool = False
    availability_status: AvailabilityStatus = "AVAILABLE"
    visibility: Visibility = "PUBLIC"


class SetStatusRequest(BaseModel):
    status: Literal["DRAFT", "PAUSED", "ARCHIVED"]


class OfferingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    offering_type: str
    name: str
    slug: str
    short_description: str | None
    full_description: str | None
    specifications: str | None
    applications: str | None
    brand: str | None
    model: str | None
    lead_time_days: int | None
    moq: int | None
    monthly_capacity: float | None
    capacity_unit_code: str | None
    warranty_months: int | None
    has_after_sales: bool
    availability_status: str
    visibility: str
    status: str
    published_at: datetime | None
    completion_pct: int


class TaxonomyNodeAssignment(BaseModel):
    node_id: UUID
    is_primary: bool = False


class SetTaxonomyNodesRequest(BaseModel):
    nodes: list[TaxonomyNodeAssignment] = Field(min_length=1)


class OfferingTaxonomyNodeOut(BaseModel):
    node_id: UUID
    is_primary: bool
    name: str


class SetOfferingIndustriesRequest(BaseModel):
    industry_ids: list[UUID] = Field(default_factory=list)


class OfferingIndustryOut(BaseModel):
    industry_id: UUID
    name: str


class SetOfferingTagsRequest(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=15)


class OfferingTagOut(BaseModel):
    tag: str


class AddOfferingTerritoryRequest(BaseModel):
    admin_division_id: UUID
    coverage_type: CoverageType = "OPERATIONAL"


class OfferingTerritoryOut(BaseModel):
    id: UUID
    admin_division_id: UUID
    coverage_type: str
    name: str
    level_name: str


class SetPricingRequest(BaseModel):
    price_type: PriceType = "ON_REQUEST"
    amount_min: float | None = None
    amount_max: float | None = None
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    unit_code: str | None = None
    valid_until: date | None = None
    is_public: bool = False


class PricingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price_type: str
    amount_min: float | None
    amount_max: float | None
    currency_code: str | None
    unit_code: str | None
    valid_until: date | None
    is_public: bool


class MediaOut(BaseModel):
    id: UUID
    alt_text: str | None = None
    sort_order: int = 0
    url: str


class DocumentOut(BaseModel):
    id: UUID
    name: str
    is_public: bool
    url: str | None = None


class SetAttributeValueRequest(BaseModel):
    attribute_definition_id: UUID
    value_text: str | None = None
    value_number: float | None = None
    value_boolean: bool | None = None
    value_date: date | None = None
    option_id: UUID | None = None
    option_ids: list[UUID] | None = None


class AttributeValueOut(BaseModel):
    id: UUID
    attribute_definition_id: UUID
    code: str
    name: str
    data_type: str
    value_text: str | None
    value_number: float | None
    value_boolean: bool | None
    value_date: date | None
    option_id: UUID | None
    multiselect_option_ids: list[UUID]


class CreatedOut(BaseModel):
    id: UUID


class CreateDealRequest(BaseModel):
    deal_price: float = Field(gt=0)
    original_price: float | None = Field(default=None, gt=0)
    currency_code: str = Field(min_length=3, max_length=3)
    unit_code: str | None = None
    stock_quantity: int | None = Field(default=None, gt=0)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _exactly_one_limit(self) -> "CreateDealRequest":
        if (self.stock_quantity is None) == (self.expires_at is None):
            raise ValueError(
                "La oferta necesita exactamente uno: stock límite o fecha límite"
            )
        return self


class UpdateDealStockRequest(BaseModel):
    stock_remaining: int = Field(ge=0)


class DealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    offering_id: UUID
    deal_price: float
    original_price: float | None
    currency_code: str
    unit_code: str | None
    stock_quantity: int | None
    stock_remaining: int | None
    expires_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    is_active: bool = False


class OrgDealOut(DealOut):
    """DealOut + de qué publicación es — solo para el listado agregado del
    dashboard de Ofertas (GET /organizations/{id}/deals), que cruza varias
    publicaciones a la vez."""

    offering_name: str
    offering_slug: str
    offering_status: str
