"""Router del proceso de sourcing: /api/organizations/{id}/sourcing-events/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.sourcing import (
    AddItemRequest,
    AddLotRequest,
    CreatedOut,
    CreateCriterionRequest,
    CreateSourcingEventRequest,
    DeclareVoidRequest,
    SourcingEventDetailOut,
    SourcingEventListOut,
    SourcingEventOut,
    UpdateSourcingEventRequest,
    UpsertStageRequest,
)
from app.services import entitlements as entitlements_service
from app.services import sourcing as sourcing_service

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events", tags=["sourcing"]
)

_STATUS_BY_ERROR = {
    sourcing_service.SourcingPermissionError: status.HTTP_403_FORBIDDEN,
    sourcing_service.SourcingNotFoundError: status.HTTP_404_NOT_FOUND,
    sourcing_service.SourcingValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: sourcing_service.SourcingError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[SourcingEventListOut])
async def list_events(
    organization_id: UUID, user_id: CurrentUserId
) -> list[SourcingEventListOut]:
    try:
        rows = await sourcing_service.list_events_with_stage(
            user_id=user_id, organization_id=organization_id
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
    return [SourcingEventListOut.model_validate(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def create_event(
    organization_id: UUID, payload: CreateSourcingEventRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        event_id = await sourcing_service.create_event(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except entitlements_service.EntitlementExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=event_id)


@router.get("/{event_id}", response_model=SourcingEventDetailOut)
async def get_event(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> SourcingEventDetailOut:
    try:
        detail = await sourcing_service.get_event_detail(
            user_id=user_id, organization_id=organization_id, event_id=event_id
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
    return SourcingEventDetailOut(
        event=SourcingEventOut.model_validate(detail["event"]),
        lots=detail["lots"],
        items=detail["items"],
        stages=detail["stages"],
        criteria=detail["criteria"],
    )


@router.put("/{event_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def update_event(
    organization_id: UUID,
    event_id: UUID,
    payload: UpdateSourcingEventRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await sourcing_service.update_event(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            **payload.model_dump(),
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{event_id}/publish", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def publish_event(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await sourcing_service.publish_event(
            user_id=user_id, organization_id=organization_id, event_id=event_id
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{event_id}/cancel", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def cancel_event(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await sourcing_service.cancel_event(
            user_id=user_id, organization_id=organization_id, event_id=event_id
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{event_id}/void", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def declare_void(
    organization_id: UUID,
    event_id: UUID,
    payload: DeclareVoidRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await sourcing_service.declare_void(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            reason=payload.reason,
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{event_id}/lots", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def add_lot(
    organization_id: UUID,
    event_id: UUID,
    payload: AddLotRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        lot_id = await sourcing_service.add_lot(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            **payload.model_dump(),
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=lot_id)


@router.post(
    "/{event_id}/items", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def add_item(
    organization_id: UUID,
    event_id: UUID,
    payload: AddItemRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        item_id = await sourcing_service.add_item(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            **payload.model_dump(),
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=item_id)


@router.put(
    "/{event_id}/stages", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def upsert_stage(
    organization_id: UUID,
    event_id: UUID,
    payload: UpsertStageRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        stage_id = await sourcing_service.upsert_stage(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            **payload.model_dump(),
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=stage_id)


@router.post(
    "/{event_id}/criteria",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def add_criterion(
    organization_id: UUID,
    event_id: UUID,
    payload: CreateCriterionRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        criterion_id = await sourcing_service.add_criterion(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            **payload.model_dump(),
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=criterion_id)


@router.delete(
    "/{event_id}/criteria/{criterion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_criterion(
    organization_id: UUID, event_id: UUID, criterion_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await sourcing_service.delete_criterion(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            criterion_id=criterion_id,
        )
    except sourcing_service.SourcingError as exc:
        raise _as_http_exception(exc) from exc
