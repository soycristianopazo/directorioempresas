"""Repositorio único de evidencia documental (fase 5.1/5.2).

Mismo patrón que services/offerings.py: permiso verificado ANTES de mutar,
subida a Storage vía app/core/storage.py, validación por magic bytes vía
app/core/file_validation.py — reutiliza exactamente el mecanismo de fase 3,
mismo bucket org-documents (privado, PDF, 20 MB) bajo un prefijo de ruta
distinto para no mezclarse con las fichas técnicas de ofertas.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from uuid import UUID, uuid4

from app.core.file_validation import matches_pdf
from app.core.storage import StorageError, create_signed_url, upload_object
from app.db.rls import session_for_user
from app.repositories import documents as documents_repo

PERM_READ = "document.read"
PERM_WRITE = "document.write"
PERM_DELETE = "document.delete"

DOCUMENTS_BUCKET = "org-documents"
_MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


class DocumentError(Exception):
    pass


class DocumentPermissionError(DocumentError):
    pass


class DocumentNotFoundError(DocumentError):
    pass


class DocumentValidationError(DocumentError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await documents_repo.has_permission(db, organization_id, permission):
        raise DocumentPermissionError(f"Sin permiso ({permission}) para esta acción")


async def list_document_types(*, user_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        return await documents_repo.list_document_types(db)


async def list_documents(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await documents_repo.list_documents_with_types(db, organization_id)


async def list_versions(
    *, user_id: UUID, organization_id: UUID, document_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        versions = await documents_repo.list_versions(db, document_id)
        result = []
        for v in versions:
            try:
                url = await create_signed_url(
                    bucket=DOCUMENTS_BUCKET, path=v.storage_path, expires_in=3600
                )
            except StorageError:
                url = None
            result.append(
                {
                    "id": v.id,
                    "status": v.status,
                    "issued_at": v.issued_at,
                    "valid_from": v.valid_from,
                    "valid_until": v.valid_until,
                    "url": url,
                }
            )
        return result


async def upload_version(
    *,
    user_id: UUID,
    organization_id: UUID,
    document_type_id: UUID,
    content: bytes,
    content_type: str,
    issued_at: date | None,
    valid_from: date | None,
    valid_until: date | None,
) -> dict:
    if content_type != "application/pdf":
        raise DocumentValidationError("Solo se aceptan documentos PDF por ahora")
    if len(content) > _MAX_DOCUMENT_BYTES:
        raise DocumentValidationError("El archivo supera el máximo de 20 MB")
    if not matches_pdf(content):
        raise DocumentValidationError(
            "El contenido del archivo no coincide con un PDF válido"
        )

    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)

        document_type = await documents_repo.get_document_type(db, document_type_id)
        if document_type is None:
            raise DocumentNotFoundError("Tipo de documento no encontrado")

        document = await documents_repo.get_or_create_document(
            db, organization_id=organization_id, document_type_id=document_type_id
        )

        if (
            valid_until is None
            and issued_at is not None
            and document_type.default_validity_days
        ):
            valid_until = issued_at + timedelta(
                days=document_type.default_validity_days
            )

        storage_path = f"{organization_id}/accreditation/{document.id}/{uuid4()}.pdf"
        try:
            await upload_object(
                bucket=DOCUMENTS_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise DocumentError(str(exc)) from exc

        checksum = hashlib.sha256(content).hexdigest()

        await documents_repo.supersede_active_versions(db, document.id)
        version = await documents_repo.create_version(
            db,
            document_id=document.id,
            storage_path=storage_path,
            checksum_sha256=checksum,
            issued_at=issued_at,
            valid_from=valid_from,
            valid_until=valid_until,
            uploaded_by=user_id,
        )
        version_id = version.id
        path = storage_path

    try:
        url = await create_signed_url(
            bucket=DOCUMENTS_BUCKET, path=path, expires_in=3600
        )
    except StorageError:
        url = None
    return {"id": version_id, "url": url, "valid_until": valid_until}
