"""Esquemas de atributos dinámicos (EAV tipado)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

DataType = Literal[
    "TEXT", "NUMBER", "BOOLEAN", "DATE", "SELECT", "MULTISELECT", "RANGE"
]
AppliesTo = Literal["OFFERING", "REQUIREMENT", "ORGANIZATION"]

_SELECT_LIKE = {"SELECT", "MULTISELECT"}


class AttributeOptionIn(BaseModel):
    value: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    sort_order: int = 0


class AttributeOptionOut(BaseModel):
    id: UUID
    value: str
    label: str


class CreateAttributeDefinitionRequest(BaseModel):
    code: str = Field(min_length=2, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=2, max_length=200)
    data_type: DataType
    unit_code: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    is_filterable: bool = False
    is_comparable: bool = False
    help_text: str | None = Field(default=None, max_length=500)
    options: list[AttributeOptionIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def options_required_for_select(self) -> "CreateAttributeDefinitionRequest":
        if self.data_type in _SELECT_LIKE and not self.options:
            raise ValueError(
                f"Un atributo {self.data_type} necesita al menos una opción"
            )
        return self


class LinkAttributeRequest(BaseModel):
    attribute_definition_id: UUID
    applies_to: AppliesTo = "OFFERING"
    is_required: bool = False
    is_inherited: bool = True
    filter_weight: int = 0
    sort_order: int = 0


class EffectiveAttributeOut(BaseModel):
    attribute_definition_id: UUID
    code: str
    name: str
    data_type: DataType
    unit_code: str | None
    min_value: float | None
    max_value: float | None
    is_filterable: bool
    is_comparable: bool
    help_text: str | None
    applies_to: AppliesTo
    is_required: bool
    is_direct: bool
    options: list[AttributeOptionOut]


class CreatedOut(BaseModel):
    id: UUID
