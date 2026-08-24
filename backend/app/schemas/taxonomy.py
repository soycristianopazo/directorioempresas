"""Esquemas de taxonomía (qué se vende) e industrias (a quién se le vende)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

NodeType = Literal["CATEGORY", "SUBCATEGORY", "SPECIALTY", "SERVICE", "PRODUCT"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class TaxonomyNodeTreeOut(BaseModel):
    id: UUID
    parent_id: UUID | None
    slug: str
    level: int
    path: str
    name: str
    description: str | None = None
    node_type: NodeType
    is_leaf: bool
    is_active: bool
    risk_level: RiskLevel | None
    sort_order: int
    children: list["TaxonomyNodeTreeOut"] = Field(default_factory=list)


class IndustryTreeOut(BaseModel):
    id: UUID
    parent_id: UUID | None
    slug: str
    level: int
    path: str
    name: str
    is_active: bool
    sort_order: int
    children: list["IndustryTreeOut"] = Field(default_factory=list)


class CreateTaxonomyNodeRequest(BaseModel):
    parent_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    node_type: NodeType
    slug: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    risk_level: RiskLevel | None = None
    sort_order: int = 0


class UpdateTaxonomyNodeRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    risk_level: RiskLevel | None = None
    sort_order: int = 0


class CreateIndustryRequest(BaseModel):
    parent_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, max_length=100)
    sort_order: int = 0


class UpdateIndustryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    sort_order: int = 0
