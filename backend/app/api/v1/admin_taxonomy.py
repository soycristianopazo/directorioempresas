"""Router de administración de taxonomía: /api/admin/taxonomy/*,
/api/admin/industries/*.

Todas las rutas exigen un usuario autenticado; la autorización real
(¿tiene platform.manage_taxonomy?) la resuelve el servicio dentro de la
transacción — ver services/taxonomy.py. El código HTTP de cada error lo
decide el TIPO de excepción (TaxonomyPermissionError → 403,
TaxonomyNotFoundError → 404, TaxonomyConflictError → 409,
TaxonomyValidationError → 400), no un 403 genérico para cualquier fallo.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.attributes import (
    CreateAttributeDefinitionRequest,
    CreatedOut,
    LinkAttributeRequest,
)
from app.schemas.taxonomy import (
    CreateIndustryRequest,
    CreateTaxonomyNodeRequest,
    UpdateIndustryRequest,
    UpdateTaxonomyNodeRequest,
)
from app.services import taxonomy as taxonomy_service

router = APIRouter(prefix="/admin/taxonomy", tags=["admin-taxonomy"])
industries_router = APIRouter(prefix="/admin/industries", tags=["admin-industries"])

_STATUS_BY_ERROR = {
    taxonomy_service.TaxonomyPermissionError: status.HTTP_403_FORBIDDEN,
    taxonomy_service.TaxonomyNotFoundError: status.HTTP_404_NOT_FOUND,
    taxonomy_service.TaxonomyConflictError: status.HTTP_409_CONFLICT,
    taxonomy_service.TaxonomyValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: taxonomy_service.TaxonomyError) -> HTTPException:
    status_code = _STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=status_code, detail=str(exc))


@router.post("/nodes", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def create_taxonomy_node(
    payload: CreateTaxonomyNodeRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        node_id = await taxonomy_service.create_taxonomy_node(
            user_id=user_id,
            parent_id=payload.parent_id,
            name=payload.name,
            node_type=payload.node_type,
            slug=payload.slug,
            description=payload.description,
            risk_level=payload.risk_level,
            sort_order=payload.sort_order,
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=node_id)


@router.put(
    "/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def update_taxonomy_node(
    node_id: UUID, payload: UpdateTaxonomyNodeRequest, user_id: CurrentUserId
) -> None:
    try:
        await taxonomy_service.update_taxonomy_node(
            user_id=user_id,
            node_id=node_id,
            name=payload.name,
            description=payload.description,
            risk_level=payload.risk_level,
            sort_order=payload.sort_order,
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/nodes/{node_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def deactivate_taxonomy_node(node_id: UUID, user_id: CurrentUserId) -> None:
    try:
        await taxonomy_service.deactivate_taxonomy_node(
            user_id=user_id, node_id=node_id
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/nodes/{node_id}/attributes",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def link_attribute_to_node(
    node_id: UUID, payload: LinkAttributeRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        link_id = await taxonomy_service.link_attribute_to_node(
            user_id=user_id,
            node_id=node_id,
            attribute_definition_id=payload.attribute_definition_id,
            applies_to=payload.applies_to,
            is_required=payload.is_required,
            is_inherited=payload.is_inherited,
            filter_weight=payload.filter_weight,
            sort_order=payload.sort_order,
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=link_id)


@router.post(
    "/attribute-definitions",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def create_attribute_definition(
    payload: CreateAttributeDefinitionRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        definition_id = await taxonomy_service.create_attribute_definition(
            user_id=user_id,
            code=payload.code,
            name=payload.name,
            data_type=payload.data_type,
            unit_code=payload.unit_code,
            min_value=payload.min_value,
            max_value=payload.max_value,
            is_filterable=payload.is_filterable,
            is_comparable=payload.is_comparable,
            help_text=payload.help_text,
            options=[option.model_dump() for option in payload.options],
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=definition_id)


@industries_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_industry(
    payload: CreateIndustryRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        industry_id = await taxonomy_service.create_industry(
            user_id=user_id,
            parent_id=payload.parent_id,
            name=payload.name,
            slug=payload.slug,
            sort_order=payload.sort_order,
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=industry_id)


@industries_router.put(
    "/{industry_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def update_industry(
    industry_id: UUID, payload: UpdateIndustryRequest, user_id: CurrentUserId
) -> None:
    try:
        await taxonomy_service.update_industry(
            user_id=user_id,
            industry_id=industry_id,
            name=payload.name,
            sort_order=payload.sort_order,
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc


@industries_router.post(
    "/{industry_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def deactivate_industry(industry_id: UUID, user_id: CurrentUserId) -> None:
    try:
        await taxonomy_service.deactivate_industry(
            user_id=user_id, industry_id=industry_id
        )
    except taxonomy_service.TaxonomyError as exc:
        raise _as_http_exception(exc) from exc
