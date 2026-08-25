"""Router de necesidades de compra: /api/organizations/{id}/requirements/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.requirements import (
    AddRequirementItemRequest,
    CreatedOut,
    CreateRequirementRequest,
    RequirementDetailOut,
    RequirementOut,
    UpdateRequirementRequest,
)
from app.services import entitlements as entitlements_service
from app.services import requirements as requirements_service

router = APIRouter(
    prefix="/organizations/{organization_id}/requirements", tags=["requirements"]
)

_STATUS_BY_ERROR = {
    requirements_service.RequirementPermissionError: status.HTTP_403_FORBIDDEN,
    requirements_service.RequirementNotFoundError: status.HTTP_404_NOT_FOUND,
}


def _as_http_exception(exc: requirements_service.RequirementError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[RequirementOut])
async def list_requirements(
    organization_id: UUID, user_id: CurrentUserId
) -> list[RequirementOut]:
    try:
        rows = await requirements_service.list_requirements(
            user_id=user_id, organization_id=organization_id
        )
    except requirements_service.RequirementError as exc:
        raise _as_http_exception(exc) from exc
    return [RequirementOut.model_validate(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def create_requirement(
    organization_id: UUID, payload: CreateRequirementRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        requirement_id = await requirements_service.create_requirement(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except entitlements_service.EntitlementExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc
    except requirements_service.RequirementError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=requirement_id)


@router.get("/{requirement_id}", response_model=RequirementDetailOut)
async def get_requirement(
    organization_id: UUID, requirement_id: UUID, user_id: CurrentUserId
) -> RequirementDetailOut:
    try:
        detail = await requirements_service.get_requirement_detail(
            user_id=user_id,
            organization_id=organization_id,
            requirement_id=requirement_id,
        )
    except requirements_service.RequirementError as exc:
        raise _as_http_exception(exc) from exc
    return RequirementDetailOut(
        requirement=RequirementOut.model_validate(detail["requirement"]),
        items=detail["items"],
        locations=detail["locations"],
    )


@router.put(
    "/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def update_requirement(
    organization_id: UUID,
    requirement_id: UUID,
    payload: UpdateRequirementRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await requirements_service.update_requirement(
            user_id=user_id,
            organization_id=organization_id,
            requirement_id=requirement_id,
            **payload.model_dump(),
        )
    except requirements_service.RequirementError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{requirement_id}/items",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def add_item(
    organization_id: UUID,
    requirement_id: UUID,
    payload: AddRequirementItemRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        item_id = await requirements_service.add_item(
            user_id=user_id,
            organization_id=organization_id,
            requirement_id=requirement_id,
            **payload.model_dump(),
        )
    except requirements_service.RequirementError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=item_id)


@router.post(
    "/{requirement_id}/locations",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def add_location(
    organization_id: UUID,
    requirement_id: UUID,
    admin_division_id: UUID,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        location_id = await requirements_service.add_location(
            user_id=user_id,
            organization_id=organization_id,
            requirement_id=requirement_id,
            admin_division_id=admin_division_id,
        )
    except requirements_service.RequirementError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=location_id)
