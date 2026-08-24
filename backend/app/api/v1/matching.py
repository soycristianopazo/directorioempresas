"""Router del motor de matching:
/api/organizations/{id}/sourcing-events/{id}/matching/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.matching import (
    LatestResultsOut,
    RunMatchingRequest,
    RunMatchingResponse,
)
from app.services import matching as matching_service

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/matching",
    tags=["matching"],
)

_STATUS_BY_ERROR = {
    matching_service.MatchingPermissionError: status.HTTP_403_FORBIDDEN,
    matching_service.MatchingNotFoundError: status.HTTP_404_NOT_FOUND,
    matching_service.MatchingValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: matching_service.MatchingError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.post("/run", response_model=RunMatchingResponse)
async def run_matching(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> RunMatchingResponse:
    try:
        result = await matching_service.run_matching(
            user_id=user_id, organization_id=organization_id, event_id=event_id
        )
    except matching_service.MatchingError as exc:
        raise _as_http_exception(exc) from exc
    return RunMatchingResponse(**result)


@router.post("/preview", response_model=RunMatchingResponse)
async def preview_matching(
    organization_id: UUID,
    event_id: UUID,
    payload: RunMatchingRequest,
    user_id: CurrentUserId,
) -> RunMatchingResponse:
    try:
        result = await matching_service.run_matching(
            user_id=user_id,
            organization_id=organization_id,
            event_id=event_id,
            dry_run=True,
            weights_override=payload.weights,
        )
    except matching_service.MatchingError as exc:
        raise _as_http_exception(exc) from exc
    return RunMatchingResponse(**result)


@router.get("/results", response_model=LatestResultsOut | None)
async def get_latest_results(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> LatestResultsOut | None:
    try:
        latest = await matching_service.get_latest_results(
            user_id=user_id, organization_id=organization_id, event_id=event_id
        )
    except matching_service.MatchingError as exc:
        raise _as_http_exception(exc) from exc
    if latest is None:
        return None
    return LatestResultsOut(run=latest["run"], results=latest["results"])
