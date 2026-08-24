"""Ubicaciones, contactos, media (logo/banner), settings, industrias y
cobertura territorial de una organización.

Mismo patrón que services/taxonomy.py: chequeo de permiso ANTES de mutar,
dentro de session_for_user(user_id); excepciones específicas por motivo para
que el router pueda devolver 403/404/409 en vez de un único código genérico.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.core.file_validation import matches_declared_image_type
from app.core.storage import StorageError, delete_object, public_url, upload_object
from app.db.rls import session_for_user
from app.repositories import organization_profile as profile_repo
from app.services.completion import recompute_completion_pct

PERMISSION_UPDATE = "organization.update"
MEDIA_BUCKET = "org-media"


class ProfileError(Exception):
    pass


class ProfilePermissionError(ProfileError):
    pass


class ProfileNotFoundError(ProfileError):
    pass


class ProfileValidationError(ProfileError):
    pass


async def _require_permission(db, organization_id: UUID) -> None:
    if not await profile_repo.has_permission(db, organization_id, PERMISSION_UPDATE):
        raise ProfilePermissionError("Sin permiso para editar esta organización")


# ─── Ubicaciones ─────────────────────────────────────────────────────────────


async def list_locations(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        return list(await profile_repo.list_locations(db, organization_id))


async def create_location(
    *,
    user_id: UUID,
    organization_id: UUID,
    location_type: str,
    address_line: str,
    admin_division_id: UUID | None,
    is_headquarters: bool,
    lat: float | None,
    lng: float | None,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        location = await profile_repo.create_location(
            db,
            organization_id=organization_id,
            location_type=location_type,
            address_line=address_line,
            admin_division_id=admin_division_id,
            is_headquarters=is_headquarters,
            lat=lat,
            lng=lng,
        )
        await recompute_completion_pct(db, organization_id)
        location_id = location.id
    return location_id


async def update_location(
    *, user_id: UUID, organization_id: UUID, location_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        location = await profile_repo.get_location(
            db, location_id, organization_id=organization_id
        )
        if location is None:
            raise ProfileNotFoundError("Ubicación no encontrada")
        await profile_repo.update_location(location, **fields)


async def deactivate_location(
    *, user_id: UUID, organization_id: UUID, location_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        location = await profile_repo.get_location(
            db, location_id, organization_id=organization_id
        )
        if location is None:
            raise ProfileNotFoundError("Ubicación no encontrada")
        await profile_repo.deactivate_location(location)
        await recompute_completion_pct(db, organization_id)


# ─── Contactos ───────────────────────────────────────────────────────────────


async def list_contacts(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        return list(await profile_repo.list_contacts(db, organization_id))


async def create_contact(
    *,
    user_id: UUID,
    organization_id: UUID,
    full_name: str,
    job_title: str | None,
    contact_type: str,
    email: str | None,
    phone: str | None,
    whatsapp: str | None,
    linkedin_url: str | None,
    is_public: bool,
    is_primary: bool,
) -> UUID:
    if not (email or phone or whatsapp):
        raise ProfileValidationError(
            "El contacto necesita al menos un canal (email, teléfono o WhatsApp)"
        )
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        contact = await profile_repo.create_contact(
            db,
            organization_id=organization_id,
            full_name=full_name.strip(),
            job_title=job_title,
            contact_type=contact_type,
            email=email,
            phone=phone,
            whatsapp=whatsapp,
            linkedin_url=linkedin_url,
            is_public=is_public,
            is_primary=is_primary,
        )
        await recompute_completion_pct(db, organization_id)
        contact_id = contact.id
    return contact_id


async def update_contact(
    *, user_id: UUID, organization_id: UUID, contact_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        contact = await profile_repo.get_contact(
            db, contact_id, organization_id=organization_id
        )
        if contact is None:
            raise ProfileNotFoundError("Contacto no encontrado")
        await profile_repo.update_contact(contact, **fields)


async def deactivate_contact(
    *, user_id: UUID, organization_id: UUID, contact_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        contact = await profile_repo.get_contact(
            db, contact_id, organization_id=organization_id
        )
        if contact is None:
            raise ProfileNotFoundError("Contacto no encontrado")
        await profile_repo.deactivate_contact(contact)


# ─── Media (logo / banner / galería) ─────────────────────────────────────────

_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
_MAX_IMAGE_BYTES = 8 * 1024 * 1024


async def list_media(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        rows = await profile_repo.list_media(db, organization_id)
        return [
            {
                "id": row.id,
                "media_type": row.media_type,
                "alt_text": row.alt_text,
                "sort_order": row.sort_order,
                "url": public_url(bucket=MEDIA_BUCKET, path=row.storage_path),
            }
            for row in rows
        ]


async def upload_media(
    *,
    user_id: UUID,
    organization_id: UUID,
    media_type: str,
    content: bytes,
    content_type: str,
    alt_text: str | None = None,
) -> dict:
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise ProfileValidationError(f"Tipo de archivo no permitido: {content_type}")
    if len(content) > _MAX_IMAGE_BYTES:
        raise ProfileValidationError("El archivo supera el máximo de 8 MB")
    if not matches_declared_image_type(content, content_type):
        raise ProfileValidationError(
            "El contenido del archivo no coincide con el tipo declarado"
        )

    extension = _ALLOWED_IMAGE_TYPES[content_type]
    storage_path = f"{organization_id}/{media_type.lower()}/{uuid4()}.{extension}"

    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)

        # LOGO/BANNER son 1:1 — reemplazan al anterior (fila + archivo físico).
        old_path = None
        if media_type in ("LOGO", "BANNER"):
            existing = await profile_repo.list_media(db, organization_id)
            old = next((m for m in existing if m.media_type == media_type), None)
            if old is not None:
                old_path = old.storage_path
            await profile_repo.replace_singleton_media(
                db, organization_id=organization_id, media_type=media_type
            )

        try:
            await upload_object(
                bucket=MEDIA_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise ProfileError(str(exc)) from exc

        media = await profile_repo.create_media(
            db,
            organization_id=organization_id,
            media_type=media_type,
            storage_path=storage_path,
            alt_text=alt_text,
            sort_order=0,
        )
        await recompute_completion_pct(db, organization_id)
        media_id = media.id

    if old_path:
        try:
            await delete_object(bucket=MEDIA_BUCKET, path=old_path)
        except StorageError:
            pass  # el archivo viejo queda huérfano en el bucket; no bloquea la subida nueva

    return {
        "id": media_id,
        "media_type": media_type,
        "url": public_url(bucket=MEDIA_BUCKET, path=storage_path),
    }


async def delete_media(*, user_id: UUID, organization_id: UUID, media_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        media = await profile_repo.get_media(
            db, media_id, organization_id=organization_id
        )
        if media is None:
            raise ProfileNotFoundError("Archivo no encontrado")
        storage_path = media.storage_path
        await profile_repo.delete_media(db, media)
        await recompute_completion_pct(db, organization_id)

    try:
        await delete_object(bucket=MEDIA_BUCKET, path=storage_path)
    except StorageError:
        pass


# ─── Industrias ──────────────────────────────────────────────────────────────


async def list_industries(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        return list(await profile_repo.list_industries(db, organization_id))


async def set_industry(
    *,
    user_id: UUID,
    organization_id: UUID,
    industry_id: UUID,
    years_experience: int | None,
    is_primary: bool,
) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        await profile_repo.upsert_industry(
            db,
            organization_id=organization_id,
            industry_id=industry_id,
            years_experience=years_experience,
            is_primary=is_primary,
        )
        await recompute_completion_pct(db, organization_id)


async def remove_industry(
    *, user_id: UUID, organization_id: UUID, industry_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        await profile_repo.remove_industry(
            db, organization_id=organization_id, industry_id=industry_id
        )
        await recompute_completion_pct(db, organization_id)


# ─── Territorios ─────────────────────────────────────────────────────────────


async def list_territories(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        return list(await profile_repo.list_territories(db, organization_id))


async def add_territory(
    *, user_id: UUID, organization_id: UUID, admin_division_id: UUID
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        territory = await profile_repo.add_territory(
            db, organization_id=organization_id, admin_division_id=admin_division_id
        )
        await recompute_completion_pct(db, organization_id)
        territory_id = territory.id
    return territory_id


async def remove_territory(
    *, user_id: UUID, organization_id: UUID, territory_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require_permission(db, organization_id)
        removed = await profile_repo.remove_territory(
            db, territory_id, organization_id=organization_id
        )
        if not removed:
            raise ProfileNotFoundError("Territorio no encontrado")
        await recompute_completion_pct(db, organization_id)
