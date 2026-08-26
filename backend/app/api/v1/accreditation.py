"""Router de acreditación (lado proveedor):
/api/organizations/{id}/accreditation/*, /api/accreditation/programs/*.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.accreditation import (
    CertificateOut,
    CreatedOut,
    EnrollmentDetailOut,
    EnrollmentOut,
    EnrollRequest,
    ProgramDetailOut,
    ProgramOut,
    SubmitEvidenceRequest,
)
from app.services import accreditation as accreditation_service

programs_router = APIRouter(prefix="/accreditation/programs", tags=["accreditation"])
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


@programs_router.get("", response_model=list[ProgramOut])
async def list_programs(
    user_id: CurrentUserId, for_organization_id: UUID | None = None
) -> list[ProgramOut]:
    """Sin for_organization_id: catálogo activo, orden alfabético (todas las
    audiencias). Con for_organization_id: mismo catálogo, ordenado por
    relevancia para esa organización (fase 9.4) — usado por el selector de
    programa al crear/editar un sourcing_event."""
    if for_organization_id is not None:
        rows = await accreditation_service.list_programs_for_organization(
            user_id=user_id, organization_id=for_organization_id
        )
    else:
        rows = await accreditation_service.list_programs(user_id=user_id)
    return [ProgramOut.model_validate(r) for r in rows]


@programs_router.get("/{program_id}", response_model=ProgramDetailOut)
async def get_program_detail(
    program_id: UUID, user_id: CurrentUserId
) -> ProgramDetailOut:
    try:
        result = await accreditation_service.get_program_detail(
            user_id=user_id, program_id=program_id
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return ProgramDetailOut(
        program=ProgramOut.model_validate(result["program"]),
        groups=result["groups"],
        requirements=result["requirements"],
    )


@router.get("/enrollments", response_model=list[EnrollmentOut])
async def list_enrollments(
    organization_id: UUID, user_id: CurrentUserId
) -> list[EnrollmentOut]:
    try:
        rows = await accreditation_service.list_enrollments(
            user_id=user_id, organization_id=organization_id
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return [EnrollmentOut(**r) for r in rows]


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentDetailOut)
async def get_enrollment_detail(
    organization_id: UUID, enrollment_id: UUID, user_id: CurrentUserId
) -> EnrollmentDetailOut:
    try:
        result = await accreditation_service.get_enrollment_detail(
            user_id=user_id,
            organization_id=organization_id,
            enrollment_id=enrollment_id,
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return EnrollmentDetailOut(
        enrollment=EnrollmentOut(**result["enrollment"]),
        fulfillments=result["fulfillments"],
        sections=result["sections"],
        history=result["history"],
    )


@router.post(
    "/enrollments", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def enroll(
    organization_id: UUID, payload: EnrollRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        enrollment_id = await accreditation_service.enroll(
            user_id=user_id,
            organization_id=organization_id,
            program_id=payload.program_id,
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=enrollment_id)


@router.post(
    "/enrollments/{enrollment_id}/evidence",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def submit_evidence(
    organization_id: UUID,
    enrollment_id: UUID,
    payload: SubmitEvidenceRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await accreditation_service.submit_evidence(
            user_id=user_id,
            organization_id=organization_id,
            enrollment_id=enrollment_id,
            **payload.model_dump(),
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/enrollments/{enrollment_id}/submit-for-review",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def submit_for_review(
    organization_id: UUID, enrollment_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await accreditation_service.submit_for_review(
            user_id=user_id,
            organization_id=organization_id,
            enrollment_id=enrollment_id,
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/enrollments/{enrollment_id}/respond-to-observation",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def respond_to_observation(
    organization_id: UUID, enrollment_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await accreditation_service.respond_to_observation(
            user_id=user_id,
            organization_id=organization_id,
            enrollment_id=enrollment_id,
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/enrollments/{enrollment_id}/renew",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def renew_enrollment(
    organization_id: UUID, enrollment_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await accreditation_service.renew_enrollment(
            user_id=user_id,
            organization_id=organization_id,
            enrollment_id=enrollment_id,
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc


@router.get(
    "/enrollments/{enrollment_id}/certificate", response_model=CertificateOut
)
async def get_certificate(
    organization_id: UUID, enrollment_id: UUID, user_id: CurrentUserId
) -> CertificateOut:
    try:
        result = await accreditation_service.get_certificate(
            user_id=user_id,
            organization_id=organization_id,
            enrollment_id=enrollment_id,
        )
    except accreditation_service.AccreditationError as exc:
        raise _as_http_exception(exc) from exc
    return CertificateOut(**result)
