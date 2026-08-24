"""Catálogo de oferta: supplier_offerings y sus tablas relacionadas.

Mismo patrón que services/taxonomy.py y services/organization_profile.py:
permiso verificado ANTES de mutar, dentro de session_for_user(user_id).

Los tres permisos ya sembrados en 0009 (offering.write / offering.publish /
offering.delete) se usan tal como se pensaron: write para altas y ediciones
de borrador, publish específicamente para la transición a ACTIVE, delete para
el borrado lógico. RLS (0029) acepta cualquiera de los tres como base para
escribir la fila — la distinción fina de CUÁL permiso hace falta para CADA
acción específica vive acá, no en la policy.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.file_validation import matches_declared_image_type, matches_pdf
from app.core.storage import (
    StorageError,
    create_signed_url,
    delete_object,
    public_url,
    upload_object,
)
from app.db.rls import session_for_user
from app.models.attribute import AttributeDefinition
from app.models.offering import OfferingPricing
from app.repositories import offerings as offerings_repo
from app.services import search as search_service
from app.services.completion import recompute_completion_pct

PERM_READ = "offering.read"
PERM_WRITE = "offering.write"
PERM_PUBLISH = "offering.publish"
PERM_DELETE = "offering.delete"

MEDIA_BUCKET = "org-media"
DOCUMENTS_BUCKET = "org-documents"

_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


class OfferingError(Exception):
    pass


class OfferingPermissionError(OfferingError):
    pass


class OfferingNotFoundError(OfferingError):
    pass


class OfferingConflictError(OfferingError):
    pass


class OfferingValidationError(OfferingError):
    pass


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "oferta"


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await offerings_repo.has_permission(db, organization_id, permission):
        raise OfferingPermissionError(f"Sin permiso ({permission}) para esta acción")


async def _get_owned_offering(db, offering_id: UUID, organization_id: UUID):
    offering = await offerings_repo.get_offering(db, offering_id)
    if offering is None or offering.organization_id != organization_id:
        raise OfferingNotFoundError("Oferta no encontrada")
    return offering


# ─── CRUD principal ──────────────────────────────────────────────────────────


async def list_offerings(
    *, user_id: UUID, organization_id: UUID, status: str | None = None
) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return list(
            await offerings_repo.list_offerings(db, organization_id, status=status)
        )


async def get_offering(*, user_id: UUID, organization_id: UUID, offering_id: UUID):
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await _get_owned_offering(db, offering_id, organization_id)


async def create_offering(
    *,
    user_id: UUID,
    organization_id: UUID,
    offering_type: str,
    name: str,
    short_description: str | None = None,
    full_description: str | None = None,
    **extra: object,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)

        base_slug = _slugify(name)[:90]
        slug = base_slug
        suffix = 0
        while await offerings_repo.slug_exists(
            db, organization_id=organization_id, slug=slug
        ):
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        offering = await offerings_repo.create_offering(
            db,
            organization_id=organization_id,
            offering_type=offering_type,
            name=name.strip(),
            slug=slug,
            short_description=short_description,
            full_description=full_description,
            **extra,
        )
        offering_id = offering.id
        await search_service.reindex_offering(db, offering_id)
    return offering_id


async def update_offering(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        offering = await _get_owned_offering(db, offering_id, organization_id)
        await offerings_repo.update_offering(offering, **fields)
        await search_service.reindex_offering(db, offering_id)


async def publish_offering(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_PUBLISH)
        offering = await _get_owned_offering(db, offering_id, organization_id)

        missing = []
        if not offering.short_description:
            missing.append("descripción corta")
        nodes = await offerings_repo.list_taxonomy_nodes(db, offering_id)
        if not nodes:
            missing.append("al menos una categoría")
        if missing:
            raise OfferingValidationError(
                f"Faltan datos para publicar: {', '.join(missing)}"
            )

        await offerings_repo.publish_offering(offering)
        await recompute_completion_pct(db, organization_id)
        await search_service.reindex_offering(db, offering_id)


async def set_status(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, status: str
) -> None:
    """PAUSED / ARCHIVED / vuelta a DRAFT — cualquier transición que no sea
    publicar (que tiene su propio permiso y su propia validación)."""
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        offering = await _get_owned_offering(db, offering_id, organization_id)
        await offerings_repo.update_offering(offering, status=status)
        await search_service.reindex_offering(db, offering_id)


async def delete_offering(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_DELETE)
        offering = await _get_owned_offering(db, offering_id, organization_id)
        await offerings_repo.soft_delete_offering(offering)
        await recompute_completion_pct(db, organization_id)
        await search_service.reindex_offering(db, offering_id)


# ─── Taxonomía / industrias / territorio ─────────────────────────────────────


async def list_taxonomy_nodes(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        await _get_owned_offering(db, offering_id, organization_id)
        return await offerings_repo.list_taxonomy_nodes_with_names(db, offering_id)


async def list_industries(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        await _get_owned_offering(db, offering_id, organization_id)
        return await offerings_repo.list_industries_with_names(db, offering_id)


async def list_territories(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        await _get_owned_offering(db, offering_id, organization_id)
        return await offerings_repo.list_territories_with_names(db, offering_id)


async def set_taxonomy_nodes(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, nodes: list[dict]
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)
        await offerings_repo.set_taxonomy_nodes(db, offering_id, nodes)
        await search_service.reindex_offering(db, offering_id)


async def set_industries(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, industry_ids: list[UUID]
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)
        await offerings_repo.set_industries(db, offering_id, industry_ids)
        await search_service.reindex_offering(db, offering_id)


async def add_territory(
    *,
    user_id: UUID,
    organization_id: UUID,
    offering_id: UUID,
    admin_division_id: UUID,
    coverage_type: str,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)
        territory = await offerings_repo.add_territory(
            db,
            offering_id=offering_id,
            admin_division_id=admin_division_id,
            coverage_type=coverage_type,
        )
        territory_id = territory.id
        await search_service.reindex_offering(db, offering_id)
    return territory_id


async def remove_territory(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, territory_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)
        removed = await offerings_repo.remove_territory(
            db, territory_id, offering_id=offering_id
        )
        if not removed:
            raise OfferingNotFoundError("Territorio no encontrado")
        await search_service.reindex_offering(db, offering_id)


# ─── Precio ──────────────────────────────────────────────────────────────────


async def get_pricing(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> OfferingPricing | None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        await _get_owned_offering(db, offering_id, organization_id)
        return await offerings_repo.get_pricing(db, offering_id)


async def set_pricing(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)
        await offerings_repo.upsert_pricing(db, offering_id, **fields)
        await search_service.reindex_offering(db, offering_id)


# ─── Media / documentos ──────────────────────────────────────────────────────


async def list_media(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        rows = await offerings_repo.list_media(db, offering_id)
        return [
            {
                "id": r.id,
                "alt_text": r.alt_text,
                "sort_order": r.sort_order,
                "url": public_url(bucket=MEDIA_BUCKET, path=r.storage_path),
            }
            for r in rows
        ]


async def upload_media(
    *,
    user_id: UUID,
    organization_id: UUID,
    offering_id: UUID,
    content: bytes,
    content_type: str,
) -> dict:
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise OfferingValidationError(f"Tipo de archivo no permitido: {content_type}")
    if len(content) > _MAX_IMAGE_BYTES:
        raise OfferingValidationError("El archivo supera el máximo de 8 MB")
    if not matches_declared_image_type(content, content_type):
        raise OfferingValidationError(
            "El contenido del archivo no coincide con el tipo declarado"
        )

    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)

        extension = _ALLOWED_IMAGE_TYPES[content_type]
        storage_path = f"{organization_id}/{offering_id}/{uuid4()}.{extension}"
        try:
            await upload_object(
                bucket=MEDIA_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise OfferingError(str(exc)) from exc

        media = await offerings_repo.create_media(
            db, offering_id=offering_id, storage_path=storage_path
        )
        media_id = media.id

    return {"id": media_id, "url": public_url(bucket=MEDIA_BUCKET, path=storage_path)}


async def delete_media(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, media_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)
        media = await offerings_repo.get_media(db, media_id, offering_id=offering_id)
        if media is None:
            raise OfferingNotFoundError("Archivo no encontrado")
        storage_path = media.storage_path
        await offerings_repo.delete_media(db, media)

    try:
        await delete_object(bucket=MEDIA_BUCKET, path=storage_path)
    except StorageError:
        pass


async def list_documents(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        rows = await offerings_repo.list_documents(db, offering_id)
        result = []
        for r in rows:
            try:
                url = await create_signed_url(
                    bucket=DOCUMENTS_BUCKET, path=r.storage_path, expires_in=3600
                )
            except StorageError:
                url = None
            result.append(
                {"id": r.id, "name": r.name, "is_public": r.is_public, "url": url}
            )
        return result


async def upload_document(
    *,
    user_id: UUID,
    organization_id: UUID,
    offering_id: UUID,
    name: str,
    content: bytes,
    content_type: str,
    is_public: bool = True,
) -> dict:
    if content_type != "application/pdf":
        raise OfferingValidationError("Solo se aceptan documentos PDF por ahora")
    if len(content) > _MAX_DOCUMENT_BYTES:
        raise OfferingValidationError("El archivo supera el máximo de 20 MB")
    if not matches_pdf(content):
        raise OfferingValidationError(
            "El contenido del archivo no coincide con un PDF válido"
        )

    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)

        storage_path = f"{organization_id}/{offering_id}/{uuid4()}.pdf"
        try:
            await upload_object(
                bucket=DOCUMENTS_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise OfferingError(str(exc)) from exc

        document = await offerings_repo.create_document(
            db,
            offering_id=offering_id,
            name=name.strip(),
            storage_path=storage_path,
            is_public=is_public,
        )
        document_id = document.id
        path = storage_path

    try:
        url = await create_signed_url(
            bucket=DOCUMENTS_BUCKET, path=path, expires_in=3600
        )
    except StorageError:
        url = None
    return {"id": document_id, "name": name, "url": url}


async def delete_document(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID, document_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)
        document = await offerings_repo.get_document(
            db, document_id, offering_id=offering_id
        )
        if document is None:
            raise OfferingNotFoundError("Documento no encontrado")
        storage_path = document.storage_path
        await offerings_repo.delete_document(db, document)

    try:
        await delete_object(bucket=DOCUMENTS_BUCKET, path=storage_path)
    except StorageError:
        pass


# ─── Valores de atributos dinámicos ───────────────────────────────────────────


async def list_attribute_values(
    *, user_id: UUID, organization_id: UUID, offering_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await offerings_repo.list_attribute_values(db, offering_id)


async def set_attribute_value(
    *,
    user_id: UUID,
    organization_id: UUID,
    offering_id: UUID,
    attribute_definition_id: UUID,
    value_text: str | None = None,
    value_number: float | None = None,
    value_boolean: bool | None = None,
    value_date: date | None = None,
    option_id: UUID | None = None,
    option_ids: list[UUID] | None = None,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
        await _get_owned_offering(db, offering_id, organization_id)

        result = await db.execute(
            select(AttributeDefinition).where(
                AttributeDefinition.id == attribute_definition_id
            )
        )
        definition = result.scalar_one_or_none()
        if definition is None:
            raise OfferingNotFoundError("Atributo no encontrado")

        slots_by_type: dict[str, dict[str, object]] = {
            "TEXT": {"value_text": value_text},
            "NUMBER": {"value_number": value_number},
            "BOOLEAN": {"value_boolean": value_boolean},
            "DATE": {"value_date": value_date},
            "SELECT": {"option_id": option_id},
        }

        if definition.data_type == "MULTISELECT":
            if not option_ids:
                raise OfferingValidationError(
                    "Un atributo MULTISELECT necesita al menos una opción"
                )
            row = await offerings_repo.upsert_attribute_value(
                db,
                offering_id=offering_id,
                attribute_definition_id=attribute_definition_id,
            )
            await offerings_repo.set_multiselect_options(db, row.id, option_ids)
            await search_service.reindex_offering(db, offering_id)
            return row.id

        slots = slots_by_type.get(definition.data_type)
        if slots is None:
            raise OfferingValidationError(
                f"Tipo de atributo no soportado todavía: {definition.data_type}"
            )
        if all(v is None for v in slots.values()):
            raise OfferingValidationError(
                f"Falta el valor para un atributo {definition.data_type}"
            )

        row = await offerings_repo.upsert_attribute_value(
            db,
            offering_id=offering_id,
            attribute_definition_id=attribute_definition_id,
            **slots,
        )
        await search_service.reindex_offering(db, offering_id)
        return row.id
