"""Router de administración de acreditación: /api/admin/accreditation/*.

Todas las rutas exigen un usuario autenticado; la autorización real
(¿es platform.review_accreditation o platform.manage_taxonomy?) la resuelve
el servicio dentro de la transacción — mismo criterio que admin_taxonomy.py.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.accreditation import (
    CreatedOut,
    CreateProgramRequest,
    CreateRequirementGroupRequest,
    CreateRequirementRequest,
    DecideEnrollmentRequest,
    ReviewFulfillmentRequest,
    ReviewQueueItemOut,
)
from app.services import accreditation as accreditation_service

router = APIRouter(prefix="/admin/accreditation", tags=["admin-accreditation"])

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


@router.get("/queue", response_model=list[ReviewQueueItemOut])
async def list_review_queue(
    user_id: CurrentUserId, review_status: str | None = None
) -> list[ReviewQueueItemOut]:
    try:
        rows = await accreditation_service.list_review_queue(
            user_id=user_id, status=review_status
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return [ReviewQueueItemOut(**r) for r in rows]


@router.post(
    "/fulfillments/{fulfillment_id}/review",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def review_fulfillment(
    fulfillment_id: UUID, payload: ReviewFulfillmentRequest, user_id: CurrentUserId
) -> None:
    try:
        await accreditation_service.review_fulfillment(
            user_id=user_id, fulfillment_id=fulfillment_id, **payload.model_dump()
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/enrollments/{enrollment_id}/decide",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def decide_enrollment(
    enrollment_id: UUID, payload: DecideEnrollmentRequest, user_id: CurrentUserId
) -> None:
    try:
        await accreditation_service.decide_enrollment(
            user_id=user_id, enrollment_id=enrollment_id, **payload.model_dump()
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc


# ─── Autoría de programas ─────────────────────────────────────────────────────


@router.post(
    "/programs", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_program(
    payload: CreateProgramRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        program_id = await accreditation_service.create_platform_program(
            user_id=user_id, **payload.model_dump()
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=program_id)


@router.post(
    "/programs/{program_id}/groups",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def create_requirement_group(
    program_id: UUID, payload: CreateRequirementGroupRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        group_id = await accreditation_service.create_requirement_group(
            user_id=user_id, program_id=program_id, **payload.model_dump()
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=group_id)


@router.post(
    "/programs/{program_id}/requirements",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def create_requirement(
    program_id: UUID, payload: CreateRequirementRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        requirement_id = await accreditation_service.create_requirement(
            user_id=user_id, program_id=program_id, **payload.model_dump()
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=requirement_id)
