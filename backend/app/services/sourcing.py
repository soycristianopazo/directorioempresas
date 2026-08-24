"""El proceso de sourcing: sourcing_events y su estructura (fase 6.2/6.3).

Backstop grueso en RLS (cualquiera de los permisos de sourcing_event toca la
fila); acá se decide CUÁL hace falta para CADA acción — create para
crear/editar mientras está en DRAFT (mismo criterio que offering.write cubrió
create+edit en fase 3), publish/cancel para sus transiciones específicas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import requirements as requirements_repo
from app.repositories import sourcing as sourcing_repo

PERM_READ = "sourcing_event.read"
PERM_CREATE = "sourcing_event.create"
PERM_PUBLISH = "sourcing_event.publish"
PERM_CANCEL = "sourcing_event.cancel"


class SourcingError(Exception):
    pass


class SourcingPermissionError(SourcingError):
    pass


class SourcingNotFoundError(SourcingError):
    pass


class SourcingValidationError(SourcingError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await sourcing_repo.has_permission(db, organization_id, permission):
        raise SourcingPermissionError(f"Sin permiso ({permission}) para esta acción")


async def _get_owned_event(db, event_id: UUID, organization_id: UUID):
    event = await sourcing_repo.get_event(db, event_id)
    if event is None or event.organization_id != organization_id:
        raise SourcingNotFoundError("Evento no encontrado")
    return event


async def list_events(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await sourcing_repo.list_events(db, organization_id)


async def get_event_detail(
    *, user_id: UUID, organization_id: UUID, event_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        event = await _get_owned_event(db, event_id, organization_id)
        return {
            "event": event,
            "lots": await sourcing_repo.list_lots(db, event_id),
            "items": await sourcing_repo.list_items(db, event_id),
            "stages": await sourcing_repo.list_stages(db, event_id),
            "documents": await sourcing_repo.list_documents(db, event_id),
            "criteria": await sourcing_repo.list_criteria(db, event_id),
        }


async def create_event(
    *,
    user_id: UUID,
    organization_id: UUID,
    name: str,
    event_type: str = "RFQ",
    requirement_id: UUID | None = None,
    **fields: object,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)

        requirement = None
        if requirement_id is not None:
            requirement = await requirements_repo.get_requirement(db, requirement_id)
            if requirement is None or requirement.organization_id != organization_id:
                raise SourcingNotFoundError("Necesidad no encontrada")

        event_code = await sourcing_repo.next_event_code(
            db, event_type=event_type, year=datetime.now(timezone.utc).year
        )
        event = await sourcing_repo.create_event(
            db,
            organization_id=organization_id,
            requirement_id=requirement_id,
            name=name,
            event_type=event_type,
            event_code=event_code,
            **fields,
        )
        if requirement is not None:
            await requirements_repo.update_requirement(requirement, status="CONVERTED")
        event_id = event.id
    return event_id


async def update_event(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        event = await _get_owned_event(db, event_id, organization_id)
        if event.status != "DRAFT":
            raise SourcingValidationError("Solo se puede editar un evento en borrador")
        await sourcing_repo.update_event(event, **fields)


async def publish_event(
    *, user_id: UUID, organization_id: UUID, event_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_PUBLISH)
        event = await _get_owned_event(db, event_id, organization_id)
        if event.status != "DRAFT":
            raise SourcingValidationError(
                "Solo un evento en borrador se puede publicar"
            )
        items = await sourcing_repo.list_items(db, event_id)
        if not items:
            raise SourcingValidationError(
                "El evento necesita al menos una línea antes de publicarse"
            )
        await sourcing_repo.update_event(
            event, status="PUBLISHED", published_at=datetime.now(timezone.utc)
        )


async def cancel_event(*, user_id: UUID, organization_id: UUID, event_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CANCEL)
        event = await _get_owned_event(db, event_id, organization_id)
        if event.status == "CANCELLED":
            raise SourcingValidationError("El evento ya está cancelado")
        await sourcing_repo.update_event(event, status="CANCELLED")


async def add_lot(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        lot = await sourcing_repo.add_lot(db, sourcing_event_id=event_id, **fields)
        lot_id = lot.id
    return lot_id


async def add_item(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        item = await sourcing_repo.add_item(db, sourcing_event_id=event_id, **fields)
        item_id = item.id
    return item_id


async def upsert_stage(
    *,
    user_id: UUID,
    organization_id: UUID,
    event_id: UUID,
    stage_type: str,
    **fields: object,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        stage = await sourcing_repo.upsert_stage(
            db, event_id=event_id, stage_type=stage_type, **fields
        )
        stage_id = stage.id
    return stage_id


async def add_criterion(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        criterion = await sourcing_repo.add_criterion(
            db, sourcing_event_id=event_id, **fields
        )
        criterion_id = criterion.id
    return criterion_id


async def delete_criterion(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, criterion_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        criterion = await sourcing_repo.get_criterion(db, criterion_id)
        if criterion is None or criterion.sourcing_event_id != event_id:
            raise SourcingNotFoundError("Criterio no encontrado")
        await sourcing_repo.delete_criterion(db, criterion_id)
