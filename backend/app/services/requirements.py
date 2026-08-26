"""La necesidad de compra (fase 6.1).

Mismo patrón que services/offerings.py: permiso verificado ANTES de mutar,
dentro de session_for_user(user_id). Documentos suben al mismo bucket
org-documents que el resto de la plataforma (ver services/documents.py),
bajo el prefijo requirements/ — siempre privado, nunca is_public.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from app.core.file_validation import matches_pdf
from app.core.storage import StorageError, create_signed_url, upload_object
from app.db.rls import gather_for_user, session_for_user
from app.repositories import requirements as requirements_repo
from app.services import entitlements as entitlements_service

PERM_READ = "requirement.read"
PERM_WRITE = "requirement.write"

DOCUMENTS_BUCKET = "org-documents"
_MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


class RequirementError(Exception):
    pass


class RequirementPermissionError(RequirementError):
    pass


class RequirementNotFoundError(RequirementError):
    pass


class RequirementValidationError(RequirementError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await requirements_repo.has_permission(db, organization_id, permission):
        raise RequirementPermissionError(f"Sin permiso ({permission}) para esta acción")


async def list_requirements(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await requirements_repo.list_requirements(db, organization_id)


async def _signed_url_or_none(storage_path: str) -> str | None:
    try:
        return await create_signed_url(
            bucket=DOCUMENTS_BUCKET, path=storage_path, expires_in=3600
        )
    except StorageError:
        return None


async def get_requirement_detail(
    *, user_id: UUID, organization_id: UUID, requirement_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)

    # Las cinco solo necesitan requirement_id, ya conocido — ninguna depende
    # del resultado de otra — van en paralelo en vez de encadenadas.
    requirement, items, locations, documents, tags = await gather_for_user(
        user_id,
        lambda db: requirements_repo.get_requirement(db, requirement_id),
        lambda db: requirements_repo.list_items(db, requirement_id),
        lambda db: requirements_repo.list_locations_with_names(db, requirement_id),
        lambda db: requirements_repo.list_documents(db, requirement_id),
        lambda db: requirements_repo.list_tags(db, requirement_id),
    )
    if requirement is None or requirement.organization_id != organization_id:
        raise RequirementNotFoundError("Necesidad no encontrada")

    # Firmar cada URL es una llamada HTTP a Supabase Storage, no una consulta
    # a la BD — en paralelo, mismo patrón que services/documents.py.
    urls = await asyncio.gather(
        *(_signed_url_or_none(d.storage_path) for d in documents)
    )
    documents_out = [
        {"id": d.id, "name": d.name, "url": url, "created_at": d.created_at}
        for d, url in zip(documents, urls, strict=True)
    ]

    return {
        "requirement": requirement,
        "items": items,
        "locations": locations,
        "documents": documents_out,
        "tags": tags,
    }


async def create_requirement(
    *, user_id: UUID, organization_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await entitlements_service.assert_entitlement(
            organization_id, "requirement.create"
        )
        requirement = await requirements_repo.create_requirement(
            db, organization_id=organization_id, **fields
        )
        requirement_id = requirement.id
    return requirement_id


async def update_requirement(
    *, user_id: UUID, organization_id: UUID, requirement_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        requirement = await requirements_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.organization_id != organization_id:
            raise RequirementNotFoundError("Necesidad no encontrada")
        await requirements_repo.update_requirement(requirement, **fields)


async def add_item(
    *, user_id: UUID, organization_id: UUID, requirement_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        requirement = await requirements_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.organization_id != organization_id:
            raise RequirementNotFoundError("Necesidad no encontrada")
        item = await requirements_repo.add_item(
            db, requirement_id=requirement_id, **fields
        )
        item_id = item.id
    return item_id


async def add_location(
    *,
    user_id: UUID,
    organization_id: UUID,
    requirement_id: UUID,
    admin_division_id: UUID,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        requirement = await requirements_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.organization_id != organization_id:
            raise RequirementNotFoundError("Necesidad no encontrada")
        location = await requirements_repo.add_location(
            db, requirement_id=requirement_id, admin_division_id=admin_division_id
        )
        location_id = location.id
    return location_id


async def remove_location(
    *,
    user_id: UUID,
    organization_id: UUID,
    requirement_id: UUID,
    location_id: UUID,
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        requirement = await requirements_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.organization_id != organization_id:
            raise RequirementNotFoundError("Necesidad no encontrada")
        location = await requirements_repo.get_location(db, location_id)
        if location is None or location.requirement_id != requirement_id:
            raise RequirementNotFoundError("Ubicación no encontrada")
        await requirements_repo.remove_location(db, location)


async def set_tags(
    *, user_id: UUID, organization_id: UUID, requirement_id: UUID, tags: list[str]
) -> None:
    # Normaliza igual que offerings_service.set_tags — evita que "Minería" y
    # "mineria " convivan como tags distintos.
    normalized = list(dict.fromkeys(t.strip().lower() for t in tags if t.strip()))
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        requirement = await requirements_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.organization_id != organization_id:
            raise RequirementNotFoundError("Necesidad no encontrada")
        await requirements_repo.set_tags(db, requirement_id, normalized)


async def upload_document(
    *,
    user_id: UUID,
    organization_id: UUID,
    requirement_id: UUID,
    name: str,
    content: bytes,
    content_type: str,
) -> dict:
    if content_type != "application/pdf":
        raise RequirementValidationError("Solo se aceptan archivos PDF")
    if len(content) > _MAX_DOCUMENT_BYTES:
        raise RequirementValidationError("El archivo supera el máximo de 2 MB")
    if not matches_pdf(content):
        raise RequirementValidationError(
            "El contenido del archivo no coincide con un PDF válido"
        )

    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        requirement = await requirements_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.organization_id != organization_id:
            raise RequirementNotFoundError("Necesidad no encontrada")

        storage_path = f"{organization_id}/requirements/{requirement_id}/{uuid4()}.pdf"
        try:
            await upload_object(
                bucket=DOCUMENTS_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise RequirementError(str(exc)) from exc

        document = await requirements_repo.add_document(
            db,
            requirement_id=requirement_id,
            name=name,
            storage_path=storage_path,
            created_by=user_id,
        )
        document_id = document.id

    url = await _signed_url_or_none(storage_path)
    return {"id": document_id, "name": name, "url": url}
