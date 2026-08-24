"""Router de listas de proveedores guardadas: /api/organizations/{id}/supplier-lists/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.supplier_lists import (
    AddSupplierListItemRequest,
    CreatedOut,
    CreateSupplierListRequest,
    SupplierListItemOut,
    SupplierListOut,
)
from app.services import supplier_lists as lists_service

router = APIRouter(
    prefix="/organizations/{organization_id}/supplier-lists", tags=["supplier-lists"]
)

_STATUS_BY_ERROR = {
    lists_service.SupplierListPermissionError: status.HTTP_403_FORBIDDEN,
    lists_service.SupplierListNotFoundError: status.HTTP_404_NOT_FOUND,
}


def _as_http_exception(exc: lists_service.SupplierListError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[SupplierListOut])
async def list_lists(
    organization_id: UUID, user_id: CurrentUserId
) -> list[SupplierListOut]:
    try:
        rows = await lists_service.list_lists(
            user_id=user_id, organization_id=organization_id
        )
    except lists_service.SupplierListError as exc:
        raise _as_http_exception(exc) from exc
    return [SupplierListOut.model_validate(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def create_list(
    organization_id: UUID, payload: CreateSupplierListRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        list_id = await lists_service.create_list(
            user_id=user_id,
            organization_id=organization_id,
            name=payload.name,
            is_shared_with_org=payload.is_shared_with_org,
        )
    except lists_service.SupplierListError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=list_id)


@router.delete(
    "/{list_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_list(
    organization_id: UUID, list_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await lists_service.delete_list(
            user_id=user_id, organization_id=organization_id, list_id=list_id
        )
    except lists_service.SupplierListError as exc:
        raise _as_http_exception(exc) from exc


@router.get("/{list_id}/items", response_model=list[SupplierListItemOut])
async def list_items(
    organization_id: UUID, list_id: UUID, user_id: CurrentUserId
) -> list[SupplierListItemOut]:
    try:
        rows = await lists_service.list_items(
            user_id=user_id, organization_id=organization_id, list_id=list_id
        )
    except lists_service.SupplierListError as exc:
        raise _as_http_exception(exc) from exc
    return [SupplierListItemOut(**r) for r in rows]


@router.post(
    "/{list_id}/items", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def add_item(
    organization_id: UUID,
    list_id: UUID,
    payload: AddSupplierListItemRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        item_id = await lists_service.add_item(
            user_id=user_id,
            organization_id=organization_id,
            list_id=list_id,
            target_organization_id=payload.target_organization_id,
            note=payload.note,
        )
    except lists_service.SupplierListError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=item_id)


@router.delete(
    "/{list_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_item(
    organization_id: UUID, list_id: UUID, item_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await lists_service.remove_item(
            user_id=user_id,
            organization_id=organization_id,
            list_id=list_id,
            item_id=item_id,
        )
    except lists_service.SupplierListError as exc:
        raise _as_http_exception(exc) from exc
