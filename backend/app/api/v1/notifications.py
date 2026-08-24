"""Router de notificaciones in-app: /api/notifications/*.

Sin prefijo de organización a propósito: una notificación es per-usuario, no
per-organización (RLS ya lo refleja: recipient_id = current_user_id()).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserId
from app.schemas.notifications import (
    NotificationOut,
    NotificationPreferenceOut,
    SetPreferenceRequest,
)
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

_STATUS_BY_ERROR = {
    notifications_service.NotificationPermissionError: status.HTTP_403_FORBIDDEN,
    notifications_service.NotificationNotFoundError: status.HTTP_404_NOT_FOUND,
    notifications_service.NotificationValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: notifications_service.NotificationError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user_id: CurrentUserId, unread_only: bool = Query(default=False)
) -> list[NotificationOut]:
    try:
        rows = await notifications_service.list_notifications(
            user_id=user_id, unread_only=unread_only
        )
    except notifications_service.NotificationError as exc:
        raise _as_http_exception(exc) from exc
    return [NotificationOut(**r) for r in rows]


@router.post(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def mark_read(notification_id: UUID, user_id: CurrentUserId) -> None:
    try:
        await notifications_service.mark_read(
            user_id=user_id, notification_id=notification_id
        )
    except notifications_service.NotificationError as exc:
        raise _as_http_exception(exc) from exc


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def mark_all_read(user_id: CurrentUserId) -> None:
    await notifications_service.mark_all_read(user_id=user_id)


@router.get("/preferences", response_model=list[NotificationPreferenceOut])
async def list_preferences(user_id: CurrentUserId) -> list[NotificationPreferenceOut]:
    rows = await notifications_service.list_preferences(user_id=user_id)
    return [NotificationPreferenceOut(**r) for r in rows]


@router.put("/preferences", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def set_preference(payload: SetPreferenceRequest, user_id: CurrentUserId) -> None:
    try:
        await notifications_service.set_preference(
            user_id=user_id, **payload.model_dump()
        )
    except notifications_service.NotificationError as exc:
        raise _as_http_exception(exc) from exc
