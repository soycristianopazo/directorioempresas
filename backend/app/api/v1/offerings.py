"""Router del catálogo de oferta: /api/organizations/{id}/offerings/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUserId
from app.schemas.offerings import (
    AddOfferingTerritoryRequest,
    AttributeValueOut,
    CreateOfferingRequest,
    CreatedOut,
    DocumentOut,
    MediaOut,
    OfferingIndustryOut,
    OfferingOut,
    OfferingTaxonomyNodeOut,
    OfferingTerritoryOut,
    PricingOut,
    SetAttributeValueRequest,
    SetOfferingIndustriesRequest,
    SetPricingRequest,
    SetStatusRequest,
    SetTaxonomyNodesRequest,
    UpdateOfferingRequest,
)
from app.services import offerings as offerings_service

router = APIRouter(
    prefix="/organizations/{organization_id}/offerings", tags=["offerings"]
)

_STATUS_BY_ERROR = {
    offerings_service.OfferingPermissionError: status.HTTP_403_FORBIDDEN,
    offerings_service.OfferingNotFoundError: status.HTTP_404_NOT_FOUND,
    offerings_service.OfferingConflictError: status.HTTP_409_CONFLICT,
    offerings_service.OfferingValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: offerings_service.OfferingError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[OfferingOut])
async def list_offerings(
    organization_id: UUID, user_id: CurrentUserId, offering_status: str | None = None
) -> list[OfferingOut]:
    try:
        rows = await offerings_service.list_offerings(
            user_id=user_id, organization_id=organization_id, status=offering_status
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return [OfferingOut.model_validate(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def create_offering(
    organization_id: UUID, payload: CreateOfferingRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        offering_id = await offerings_service.create_offering(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=offering_id)


@router.get("/{offering_id}", response_model=OfferingOut)
async def get_offering(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> OfferingOut:
    try:
        offering = await offerings_service.get_offering(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return OfferingOut.model_validate(offering)


@router.put(
    "/{offering_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def update_offering(
    organization_id: UUID,
    offering_id: UUID,
    payload: UpdateOfferingRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await offerings_service.update_offering(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            **payload.model_dump(),
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{offering_id}/publish",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def publish_offering(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await offerings_service.publish_offering(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{offering_id}/status", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def set_status(
    organization_id: UUID,
    offering_id: UUID,
    payload: SetStatusRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await offerings_service.set_status(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            status=payload.status,
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


@router.delete(
    "/{offering_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_offering(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await offerings_service.delete_offering(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


# ─── Taxonomía / industrias / territorio ─────────────────────────────────────


@router.get(
    "/{offering_id}/taxonomy-nodes", response_model=list[OfferingTaxonomyNodeOut]
)
async def list_taxonomy_nodes(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> list[OfferingTaxonomyNodeOut]:
    try:
        rows = await offerings_service.list_taxonomy_nodes(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return [OfferingTaxonomyNodeOut(**r) for r in rows]


@router.put(
    "/{offering_id}/taxonomy-nodes",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def set_taxonomy_nodes(
    organization_id: UUID,
    offering_id: UUID,
    payload: SetTaxonomyNodesRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await offerings_service.set_taxonomy_nodes(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            nodes=[n.model_dump() for n in payload.nodes],
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


@router.get("/{offering_id}/industries", response_model=list[OfferingIndustryOut])
async def list_industries(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> list[OfferingIndustryOut]:
    try:
        rows = await offerings_service.list_industries(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return [OfferingIndustryOut(**r) for r in rows]


@router.put(
    "/{offering_id}/industries",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def set_industries(
    organization_id: UUID,
    offering_id: UUID,
    payload: SetOfferingIndustriesRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await offerings_service.set_industries(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            industry_ids=payload.industry_ids,
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


@router.get("/{offering_id}/territories", response_model=list[OfferingTerritoryOut])
async def list_territories(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> list[OfferingTerritoryOut]:
    try:
        rows = await offerings_service.list_territories(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return [OfferingTerritoryOut(**r) for r in rows]


@router.post(
    "/{offering_id}/territories",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def add_territory(
    organization_id: UUID,
    offering_id: UUID,
    payload: AddOfferingTerritoryRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        territory_id = await offerings_service.add_territory(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            admin_division_id=payload.admin_division_id,
            coverage_type=payload.coverage_type,
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=territory_id)


@router.delete(
    "/{offering_id}/territories/{territory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_territory(
    organization_id: UUID, offering_id: UUID, territory_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await offerings_service.remove_territory(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            territory_id=territory_id,
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


# ─── Precio ──────────────────────────────────────────────────────────────────


@router.get("/{offering_id}/pricing", response_model=PricingOut | None)
async def get_pricing(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> PricingOut | None:
    try:
        pricing = await offerings_service.get_pricing(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return PricingOut.model_validate(pricing) if pricing else None


@router.put(
    "/{offering_id}/pricing",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def set_pricing(
    organization_id: UUID,
    offering_id: UUID,
    payload: SetPricingRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await offerings_service.set_pricing(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            **payload.model_dump(),
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


# ─── Media ───────────────────────────────────────────────────────────────────


@router.get("/{offering_id}/media", response_model=list[MediaOut])
async def list_media(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> list[MediaOut]:
    try:
        rows = await offerings_service.list_media(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return [MediaOut(**r) for r in rows]


@router.post(
    "/{offering_id}/media", status_code=status.HTTP_201_CREATED, response_model=MediaOut
)
async def upload_media(
    organization_id: UUID,
    offering_id: UUID,
    user_id: CurrentUserId,
    file: UploadFile = File(...),
) -> MediaOut:
    content = await file.read()
    try:
        result = await offerings_service.upload_media(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return MediaOut(**result)


@router.delete(
    "/{offering_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_media(
    organization_id: UUID, offering_id: UUID, media_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await offerings_service.delete_media(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            media_id=media_id,
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


# ─── Documentos ──────────────────────────────────────────────────────────────


@router.get("/{offering_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> list[DocumentOut]:
    try:
        rows = await offerings_service.list_documents(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return [DocumentOut(**r) for r in rows]


@router.post(
    "/{offering_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentOut,
)
async def upload_document(
    organization_id: UUID,
    offering_id: UUID,
    user_id: CurrentUserId,
    name: str = Form(...),
    is_public: bool = Form(default=True),
    file: UploadFile = File(...),
) -> DocumentOut:
    content = await file.read()
    try:
        result = await offerings_service.upload_document(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            name=name,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            is_public=is_public,
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return DocumentOut(**result, is_public=is_public)


@router.delete(
    "/{offering_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_document(
    organization_id: UUID, offering_id: UUID, document_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await offerings_service.delete_document(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            document_id=document_id,
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc


# ─── Atributos dinámicos ──────────────────────────────────────────────────────


@router.get("/{offering_id}/attributes", response_model=list[AttributeValueOut])
async def list_attribute_values(
    organization_id: UUID, offering_id: UUID, user_id: CurrentUserId
) -> list[AttributeValueOut]:
    try:
        rows = await offerings_service.list_attribute_values(
            user_id=user_id, organization_id=organization_id, offering_id=offering_id
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return [AttributeValueOut(**r) for r in rows]


@router.put(
    "/{offering_id}/attributes",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def set_attribute_value(
    organization_id: UUID,
    offering_id: UUID,
    payload: SetAttributeValueRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        value_id = await offerings_service.set_attribute_value(
            user_id=user_id,
            organization_id=organization_id,
            offering_id=offering_id,
            **payload.model_dump(),
        )
    except offerings_service.OfferingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=value_id)
