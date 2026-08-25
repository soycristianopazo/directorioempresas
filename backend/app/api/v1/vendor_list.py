"""Router de Vendor List / AVL: /api/organizations/{id}/vendor-list/*
(fase 8.8). Nunca visible al proveedor calificado — RLS de la 0068 no tiene
policy de lectura para él."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserId
from app.schemas.vendor_list import (
    AddNoteRequest,
    CreatedOut,
    NoteOut,
    RelationshipOut,
    SetRelationshipStatusRequest,
)
from app.services import vendor_list as vendor_list_service

router = APIRouter(
    prefix="/organizations/{organization_id}/vendor-list", tags=["vendor-list"]
)

_STATUS_BY_ERROR = {
    vendor_list_service.VendorListPermissionError: status.HTTP_403_FORBIDDEN,
    vendor_list_service.VendorListNotFoundError: status.HTTP_404_NOT_FOUND,
    vendor_list_service.VendorListValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: vendor_list_service.VendorListError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[RelationshipOut])
async def list_relationships(
    organization_id: UUID,
    user_id: CurrentUserId,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[RelationshipOut]:
    try:
        rows = await vendor_list_service.list_relationships(
            user_id=user_id,
            organization_id=organization_id,
            status_filter=status_filter,
        )
    except vendor_list_service.VendorListError as exc:
        raise _as_http_exception(exc) from exc
    return [RelationshipOut.model_validate(r) for r in rows]


@router.put(
    "/relationships", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def set_relationship_status(
    organization_id: UUID,
    payload: SetRelationshipStatusRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        relationship_id = await vendor_list_service.set_relationship_status(
            user_id=user_id,
            organization_id=organization_id,
            supplier_organization_id=payload.supplier_organization_id,
            status=payload.status,
        )
    except vendor_list_service.VendorListError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=relationship_id)


@router.get("/relationships/{relationship_id}/notes", response_model=list[NoteOut])
async def list_notes(
    organization_id: UUID, relationship_id: UUID, user_id: CurrentUserId
) -> list[NoteOut]:
    try:
        rows = await vendor_list_service.list_notes(
            user_id=user_id,
            organization_id=organization_id,
            relationship_id=relationship_id,
        )
    except vendor_list_service.VendorListError as exc:
        raise _as_http_exception(exc) from exc
    return [NoteOut.model_validate(r) for r in rows]


@router.post(
    "/relationships/{relationship_id}/notes",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def add_note(
    organization_id: UUID,
    relationship_id: UUID,
    payload: AddNoteRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        note_id = await vendor_list_service.add_note(
            user_id=user_id,
            organization_id=organization_id,
            relationship_id=relationship_id,
            body=payload.body,
        )
    except vendor_list_service.VendorListError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=note_id)
