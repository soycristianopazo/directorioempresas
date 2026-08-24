"""Router del repositorio de evidencia documental: /api/organizations/{id}/documents/*."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUserId
from app.schemas.documents import (
    DocumentTypeOut,
    DocumentVersionOut,
    OrganizationDocumentOut,
    UploadVersionResponse,
)
from app.services import documents as documents_service

types_router = APIRouter(prefix="/documents", tags=["documents"])
router = APIRouter(
    prefix="/organizations/{organization_id}/documents", tags=["documents"]
)

_STATUS_BY_ERROR = {
    documents_service.DocumentPermissionError: status.HTTP_403_FORBIDDEN,
    documents_service.DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
    documents_service.DocumentValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: documents_service.DocumentError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@types_router.get("/types", response_model=list[DocumentTypeOut])
async def list_document_types(user_id: CurrentUserId) -> list[DocumentTypeOut]:
    rows = await documents_service.list_document_types(user_id=user_id)
    return [DocumentTypeOut.model_validate(r) for r in rows]


@router.get("", response_model=list[OrganizationDocumentOut])
async def list_documents(
    organization_id: UUID, user_id: CurrentUserId
) -> list[OrganizationDocumentOut]:
    try:
        rows = await documents_service.list_documents(
            user_id=user_id, organization_id=organization_id
        )
    except documents_service.DocumentError as exc:
        raise _as_http_exception(exc) from exc
    return [OrganizationDocumentOut(**r) for r in rows]


@router.get("/{document_id}/versions", response_model=list[DocumentVersionOut])
async def list_versions(
    organization_id: UUID, document_id: UUID, user_id: CurrentUserId
) -> list[DocumentVersionOut]:
    try:
        rows = await documents_service.list_versions(
            user_id=user_id, organization_id=organization_id, document_id=document_id
        )
    except documents_service.DocumentError as exc:
        raise _as_http_exception(exc) from exc
    return [DocumentVersionOut(**r) for r in rows]


@router.post(
    "/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadVersionResponse,
)
async def upload_version(
    organization_id: UUID,
    user_id: CurrentUserId,
    document_type_id: UUID = Form(...),
    issued_at: date | None = Form(default=None),
    valid_from: date | None = Form(default=None),
    valid_until: date | None = Form(default=None),
    file: UploadFile = File(...),
) -> UploadVersionResponse:
    content = await file.read()
    try:
        result = await documents_service.upload_version(
            user_id=user_id,
            organization_id=organization_id,
            document_type_id=document_type_id,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            issued_at=issued_at,
            valid_from=valid_from,
            valid_until=valid_until,
        )
    except documents_service.DocumentError as exc:
        raise _as_http_exception(exc) from exc
    return UploadVersionResponse(**result)
