"""Router de certificaciones, referencias de clientes y casos de éxito:
/api/organizations/{id}/certifications, /client-references, /case-studies,
/api/certification-types.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUserId, PublicSession
from app.repositories import credentials as credentials_repo
from app.schemas.credentials import (
    CaseStudyMediaOut,
    CaseStudyOut,
    CertificationOut,
    CertificationTypeOut,
    ClientReferenceOut,
    CreateCaseStudyRequest,
    CreateCertificationRequest,
    CreateClientReferenceRequest,
    CreatedOut,
    SetCaseStudyTaxonomyRequest,
    UpdateCaseStudyRequest,
)
from app.services import credentials as credentials_service

reference_router = APIRouter(tags=["credentials"])
router = APIRouter(prefix="/organizations/{organization_id}", tags=["credentials"])

_STATUS_BY_ERROR = {
    credentials_service.CredentialsPermissionError: status.HTTP_403_FORBIDDEN,
    credentials_service.CredentialsNotFoundError: status.HTTP_404_NOT_FOUND,
    credentials_service.CredentialsValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: credentials_service.CredentialsError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@reference_router.get("/certification-types", response_model=list[CertificationTypeOut])
async def list_certification_types(
    session: PublicSession,
) -> list[CertificationTypeOut]:
    rows = await credentials_repo.list_certification_types(session)
    return [CertificationTypeOut.model_validate(r) for r in rows]


# ─── Certificaciones ───────────────────────────────────────────────────────────


@router.get("/certifications", response_model=list[CertificationOut])
async def list_certifications(
    organization_id: UUID, user_id: CurrentUserId
) -> list[CertificationOut]:
    rows = await credentials_service.list_certifications(
        user_id=user_id, organization_id=organization_id
    )
    return [CertificationOut.model_validate(r) for r in rows]


@router.post(
    "/certifications", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_certification(
    organization_id: UUID, payload: CreateCertificationRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        certification_id = await credentials_service.create_certification(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=certification_id)


@router.delete(
    "/certifications/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_certification(
    organization_id: UUID, certification_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await credentials_service.delete_certification(
            user_id=user_id,
            organization_id=organization_id,
            certification_id=certification_id,
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc


# ─── Referencias de clientes ──────────────────────────────────────────────────


@router.get("/client-references", response_model=list[ClientReferenceOut])
async def list_client_references(
    organization_id: UUID, user_id: CurrentUserId
) -> list[ClientReferenceOut]:
    rows = await credentials_service.list_client_references(
        user_id=user_id, organization_id=organization_id
    )
    return [ClientReferenceOut.model_validate(r) for r in rows]


@router.post(
    "/client-references", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_client_reference(
    organization_id: UUID, payload: CreateClientReferenceRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        reference_id = await credentials_service.create_client_reference(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=reference_id)


@router.delete(
    "/client-references/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_client_reference(
    organization_id: UUID, reference_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await credentials_service.delete_client_reference(
            user_id=user_id, organization_id=organization_id, reference_id=reference_id
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc


# ─── Casos de éxito ────────────────────────────────────────────────────────────


@router.get("/case-studies", response_model=list[CaseStudyOut])
async def list_case_studies(
    organization_id: UUID, user_id: CurrentUserId
) -> list[CaseStudyOut]:
    rows = await credentials_service.list_case_studies(
        user_id=user_id, organization_id=organization_id
    )
    return [CaseStudyOut.model_validate(r) for r in rows]


@router.post(
    "/case-studies", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_case_study(
    organization_id: UUID, payload: CreateCaseStudyRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        case_study_id = await credentials_service.create_case_study(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=case_study_id)


@router.put(
    "/case-studies/{case_study_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def update_case_study(
    organization_id: UUID,
    case_study_id: UUID,
    payload: UpdateCaseStudyRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await credentials_service.update_case_study(
            user_id=user_id,
            organization_id=organization_id,
            case_study_id=case_study_id,
            **payload.model_dump(),
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc


@router.delete(
    "/case-studies/{case_study_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_case_study(
    organization_id: UUID, case_study_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await credentials_service.delete_case_study(
            user_id=user_id,
            organization_id=organization_id,
            case_study_id=case_study_id,
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc


@router.put(
    "/case-studies/{case_study_id}/taxonomy-nodes",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def set_case_study_taxonomy(
    organization_id: UUID,
    case_study_id: UUID,
    payload: SetCaseStudyTaxonomyRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await credentials_service.set_case_study_taxonomy(
            user_id=user_id,
            organization_id=organization_id,
            case_study_id=case_study_id,
            node_ids=payload.node_ids,
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc


@router.get(
    "/case-studies/{case_study_id}/media", response_model=list[CaseStudyMediaOut]
)
async def list_case_study_media(
    organization_id: UUID, case_study_id: UUID, user_id: CurrentUserId
) -> list[CaseStudyMediaOut]:
    try:
        rows = await credentials_service.list_case_study_media(
            user_id=user_id,
            organization_id=organization_id,
            case_study_id=case_study_id,
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc
    return [CaseStudyMediaOut(**r) for r in rows]


@router.post(
    "/case-studies/{case_study_id}/media",
    status_code=status.HTTP_201_CREATED,
    response_model=CaseStudyMediaOut,
)
async def upload_case_study_media(
    organization_id: UUID,
    case_study_id: UUID,
    user_id: CurrentUserId,
    caption: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> CaseStudyMediaOut:
    content = await file.read()
    try:
        result = await credentials_service.upload_case_study_media(
            user_id=user_id,
            organization_id=organization_id,
            case_study_id=case_study_id,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            caption=caption,
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc
    return CaseStudyMediaOut(**result)


@router.delete(
    "/case-studies/{case_study_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_case_study_media(
    organization_id: UUID, case_study_id: UUID, media_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await credentials_service.delete_case_study_media(
            user_id=user_id,
            organization_id=organization_id,
            case_study_id=case_study_id,
            media_id=media_id,
        )
    except credentials_service.CredentialsError as exc:
        raise _as_http_exception(exc) from exc
