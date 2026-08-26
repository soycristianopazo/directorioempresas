"""Certificaciones, referencias de clientes y casos de éxito."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from app.core import cache
from app.core.file_validation import matches_declared_image_type
from app.core.storage import StorageError, delete_object, public_url, upload_object
from app.db.rls import session_for_user
from app.repositories import credentials as credentials_repo
from app.services.completion import recompute_completion_pct

PERMISSION_UPDATE = "organization.update"
MEDIA_BUCKET = "org-media"

_LIST_CACHE_TTL_SECONDS = 30
# Tipos de certificación: catálogo de referencia, igual para cualquiera —
# TTL largo, una sola clave global.
_TYPES_CACHE_TTL_SECONDS = 300
_TYPES_CACHE_KEY = "certification_types"


def _credentials_cache_key(resource: str, organization_id: UUID, user_id: UUID) -> str:
    return f"credentials:{organization_id}:{user_id}:{resource}"


def _credentials_cache_prefix(organization_id: UUID) -> str:
    return f"credentials:{organization_id}:"


_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
_MAX_IMAGE_BYTES = 8 * 1024 * 1024


class CredentialsError(Exception):
    pass


class CredentialsPermissionError(CredentialsError):
    pass


class CredentialsNotFoundError(CredentialsError):
    pass


class CredentialsValidationError(CredentialsError):
    pass


async def _require(db, organization_id: UUID) -> None:
    if not await credentials_repo.has_permission(
        db, organization_id, PERMISSION_UPDATE
    ):
        raise CredentialsPermissionError("Sin permiso para editar esta organización")


# ─── Tipos de certificación ───────────────────────────────────────────────────


async def list_certification_types(*, user_id: UUID) -> list:
    cached = cache.get(_TYPES_CACHE_KEY)
    if cached is not None:
        return cached
    async with session_for_user(user_id) as db:
        result = list(await credentials_repo.list_certification_types(db))
    cache.set(_TYPES_CACHE_KEY, result, ttl_seconds=_TYPES_CACHE_TTL_SECONDS)
    return result


# ─── Certificaciones ───────────────────────────────────────────────────────────


async def list_certifications(*, user_id: UUID, organization_id: UUID) -> list:
    cache_key = _credentials_cache_key("certifications", organization_id, user_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    async with session_for_user(user_id) as db:
        result = list(await credentials_repo.list_certifications(db, organization_id))
    cache.set(cache_key, result, ttl_seconds=_LIST_CACHE_TTL_SECONDS)
    return result


async def create_certification(
    *,
    user_id: UUID,
    organization_id: UUID,
    certification_type_id: UUID,
    certificate_number: str | None,
    scope: str | None,
    issued_by: str | None,
    issued_at: date | None,
    valid_until: date | None,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        row = await credentials_repo.create_certification(
            db,
            organization_id=organization_id,
            certification_type_id=certification_type_id,
            certificate_number=certificate_number,
            scope=scope,
            issued_by=issued_by,
            issued_at=issued_at,
            valid_until=valid_until,
        )
        await recompute_completion_pct(db, organization_id)
        certification_id = row.id
    cache.invalidate_prefix(_credentials_cache_prefix(organization_id))
    return certification_id


async def delete_certification(
    *, user_id: UUID, organization_id: UUID, certification_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        row = await credentials_repo.get_certification(
            db, certification_id, organization_id=organization_id
        )
        if row is None:
            raise CredentialsNotFoundError("Certificación no encontrada")
        await credentials_repo.delete_certification(db, row)
        await recompute_completion_pct(db, organization_id)
    cache.invalidate_prefix(_credentials_cache_prefix(organization_id))


# ─── Referencias de clientes ──────────────────────────────────────────────────


async def list_client_references(*, user_id: UUID, organization_id: UUID) -> list:
    cache_key = _credentials_cache_key("client_references", organization_id, user_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    async with session_for_user(user_id) as db:
        result = list(
            await credentials_repo.list_client_references(db, organization_id)
        )
    cache.set(cache_key, result, ttl_seconds=_LIST_CACHE_TTL_SECONDS)
    return result


async def create_client_reference(
    *,
    user_id: UUID,
    organization_id: UUID,
    client_organization_id: UUID | None,
    client_name: str | None,
    industry_id: UUID | None,
    since: date | None,
    is_public: bool,
) -> UUID:
    if not client_organization_id and not client_name:
        raise CredentialsValidationError(
            "Indica el cliente (de la plataforma o nombre libre)"
        )
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        row = await credentials_repo.create_client_reference(
            db,
            organization_id=organization_id,
            client_organization_id=client_organization_id,
            client_name=client_name,
            industry_id=industry_id,
            since=since,
            is_public=is_public,
        )
        reference_id = row.id
    cache.invalidate_prefix(_credentials_cache_prefix(organization_id))
    return reference_id


async def delete_client_reference(
    *, user_id: UUID, organization_id: UUID, reference_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        removed = await credentials_repo.delete_client_reference(
            db, reference_id, organization_id=organization_id
        )
        if not removed:
            raise CredentialsNotFoundError("Referencia no encontrada")
    cache.invalidate_prefix(_credentials_cache_prefix(organization_id))


# ─── Casos de éxito ────────────────────────────────────────────────────────────


async def list_case_studies(*, user_id: UUID, organization_id: UUID) -> list:
    cache_key = _credentials_cache_key("case_studies", organization_id, user_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    async with session_for_user(user_id) as db:
        result = list(await credentials_repo.list_case_studies(db, organization_id))
    cache.set(cache_key, result, ttl_seconds=_LIST_CACHE_TTL_SECONDS)
    return result


async def create_case_study(
    *, user_id: UUID, organization_id: UUID, name: str, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        row = await credentials_repo.create_case_study(
            db, organization_id=organization_id, name=name.strip(), **fields
        )
        await recompute_completion_pct(db, organization_id)
        case_study_id = row.id
    cache.invalidate_prefix(_credentials_cache_prefix(organization_id))
    return case_study_id


async def update_case_study(
    *, user_id: UUID, organization_id: UUID, case_study_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        case_study = await credentials_repo.get_case_study(
            db, case_study_id, organization_id=organization_id
        )
        if case_study is None:
            raise CredentialsNotFoundError("Caso de éxito no encontrado")
        await credentials_repo.update_case_study(case_study, **fields)
    cache.invalidate_prefix(_credentials_cache_prefix(organization_id))


async def delete_case_study(
    *, user_id: UUID, organization_id: UUID, case_study_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        case_study = await credentials_repo.get_case_study(
            db, case_study_id, organization_id=organization_id
        )
        if case_study is None:
            raise CredentialsNotFoundError("Caso de éxito no encontrado")
        await credentials_repo.delete_case_study(db, case_study)
        await recompute_completion_pct(db, organization_id)
    cache.invalidate_prefix(_credentials_cache_prefix(organization_id))


async def set_case_study_taxonomy(
    *, user_id: UUID, organization_id: UUID, case_study_id: UUID, node_ids: list[UUID]
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        case_study = await credentials_repo.get_case_study(
            db, case_study_id, organization_id=organization_id
        )
        if case_study is None:
            raise CredentialsNotFoundError("Caso de éxito no encontrado")
        await credentials_repo.set_case_study_taxonomy(db, case_study_id, node_ids)


async def list_case_study_media(
    *, user_id: UUID, organization_id: UUID, case_study_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        case_study = await credentials_repo.get_case_study(
            db, case_study_id, organization_id=organization_id
        )
        if case_study is None:
            raise CredentialsNotFoundError("Caso de éxito no encontrado")
        rows = await credentials_repo.list_case_study_media(db, case_study_id)
        return [
            {
                "id": r.id,
                "caption": r.caption,
                "url": public_url(bucket=MEDIA_BUCKET, path=r.storage_path),
            }
            for r in rows
        ]


async def upload_case_study_media(
    *,
    user_id: UUID,
    organization_id: UUID,
    case_study_id: UUID,
    content: bytes,
    content_type: str,
    caption: str | None = None,
) -> dict:
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise CredentialsValidationError(
            f"Tipo de archivo no permitido: {content_type}"
        )
    if len(content) > _MAX_IMAGE_BYTES:
        raise CredentialsValidationError("El archivo supera el máximo de 8 MB")
    if not matches_declared_image_type(content, content_type):
        raise CredentialsValidationError(
            "El contenido del archivo no coincide con el tipo declarado"
        )

    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        case_study = await credentials_repo.get_case_study(
            db, case_study_id, organization_id=organization_id
        )
        if case_study is None:
            raise CredentialsNotFoundError("Caso de éxito no encontrado")

        extension = _ALLOWED_IMAGE_TYPES[content_type]
        storage_path = f"{organization_id}/{case_study_id}/{uuid4()}.{extension}"
        try:
            await upload_object(
                bucket=MEDIA_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise CredentialsError(str(exc)) from exc

        media = await credentials_repo.create_case_study_media(
            db, case_study_id=case_study_id, storage_path=storage_path, caption=caption
        )
        media_id = media.id

    return {"id": media_id, "url": public_url(bucket=MEDIA_BUCKET, path=storage_path)}


async def delete_case_study_media(
    *, user_id: UUID, organization_id: UUID, case_study_id: UUID, media_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id)
        media = await credentials_repo.get_case_study_media(
            db, media_id, case_study_id=case_study_id
        )
        if media is None:
            raise CredentialsNotFoundError("Archivo no encontrado")
        storage_path = media.storage_path
        await credentials_repo.delete_case_study_media(db, media)

    try:
        await delete_object(bucket=MEDIA_BUCKET, path=storage_path)
    except StorageError:
        pass
