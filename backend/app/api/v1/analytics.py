"""Router de analítica agregada: /api/organizations/{id}/analytics/*
(fase 8.9)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.services import analytics as analytics_service

router = APIRouter(
    prefix="/organizations/{organization_id}/analytics", tags=["analytics"]
)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    analytics_service.AnalyticsPermissionError: status.HTTP_403_FORBIDDEN,
}


def _as_http_exception(exc: analytics_service.AnalyticsError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("/buyer-summary", response_model=dict)
async def buyer_summary(organization_id: UUID, user_id: CurrentUserId) -> dict:
    try:
        return await analytics_service.buyer_summary(
            user_id=user_id, organization_id=organization_id
        )
    except analytics_service.AnalyticsError as exc:
        raise _as_http_exception(exc) from exc


@router.get("/supplier-summary", response_model=dict)
async def supplier_summary(organization_id: UUID, user_id: CurrentUserId) -> dict:
    try:
        return await analytics_service.supplier_summary(
            user_id=user_id, organization_id=organization_id
        )
    except analytics_service.AnalyticsError as exc:
        raise _as_http_exception(exc) from exc
