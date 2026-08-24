"""Listas de proveedores guardadas (fase 4.9)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateSupplierListRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    is_shared_with_org: bool = True


class SupplierListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_shared_with_org: bool


class AddSupplierListItemRequest(BaseModel):
    target_organization_id: UUID
    note: str | None = Field(default=None, max_length=1000)


class SupplierListItemOut(BaseModel):
    id: UUID
    target_organization_id: UUID
    note: str | None
    sort_order: int
    legal_name: str
    trade_name: str | None
    slug: str


class CreatedOut(BaseModel):
    id: UUID
