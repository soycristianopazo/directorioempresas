"""Router de acreditación (lado comprador — revisión de programa propio,
fase 9): /api/organizations/{id}/accreditation/*.

Comparte el prefix con accreditation.py (lado proveedor: /enrollments/*) sin
colisionar — este router cubre /review/*, que ese no toca. Separado en su
propio archivo por la misma razón que accreditation.py y
admin_accreditation.py ya están separados: audiencias distintas sobre el
mismo dominio.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.accreditation import (
    DecideEnrollmentRequest,
    ReviewFulfillmentRequest,
    ReviewQueueItemOut,
)
from app.services import accreditation as accreditation_service

router = APIRouter(
    prefix="/organizations/{organization_id}/accreditation", tags=["accreditation"]
)

_STATUS_BY_ERROR = {
    accreditation_service.AccreditationPermissionError: status.HTTP_403_FORBIDDEN,
    accreditation_service.AccreditationNotFoundError: status.HTTP_404_NOT_FOUND,
    accreditation_service.AccreditationValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: accreditation_service.AccreditationError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


# ─── Revisión de programa propio ───────────────────────────────────────────────


@router.get("/review/queue", response_model=list[ReviewQueueItemOut])
async def list_own_review_queue(
    organization_id: UUID, user_id: CurrentUserId, review_status: str | None = None
) -> list[ReviewQueueItemOut]:
    try:
        rows = await accreditation_service.list_own_review_queue(
            user_id=user_id, organization_id=organization_id, status=review_status
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return [ReviewQueueItemOut(**r) for r in rows]


@router.post(
    "/review/fulfillments/{fulfillment_id}/review",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def review_fulfillment(
    organization_id: UUID,
    fulfillment_id: UUID,
    payload: ReviewFulfillmentRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await accreditation_service.review_fulfillment(
            user_id=user_id,
            fulfillment_id=fulfillment_id,
            organization_id=organization_id,
            **payload.model_dump(),
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/review/enrollments/{enrollment_id}/decide",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def decide_enrollment(
    organization_id: UUID,
    enrollment_id: UUID,
    payload: DecideEnrollmentRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await accreditation_service.decide_enrollment(
            user_id=user_id,
            enrollment_id=enrollment_id,
            organization_id=organization_id,
            **payload.model_dump(),
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
