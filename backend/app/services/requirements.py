"""La necesidad de compra (fase 6.1).

Mismo patrón que services/offerings.py: permiso verificado ANTES de mutar,
dentro de session_for_user(user_id).
"""

from __future__ import annotations

from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import requirements as requirements_repo

PERM_READ = "requirement.read"
PERM_WRITE = "requirement.write"


class RequirementError(Exception):
    pass


class RequirementPermissionError(RequirementError):
    pass


class RequirementNotFoundError(RequirementError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await requirements_repo.has_permission(db, organization_id, permission):
        raise RequirementPermissionError(f"Sin permiso ({permission}) para esta acción")


async def list_requirements(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await requirements_repo.list_requirements(db, organization_id)


async def get_requirement_detail(
    *, user_id: UUID, organization_id: UUID, requirement_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        requirement = await requirements_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.organization_id != organization_id:
            raise RequirementNotFoundError("Necesidad no encontrada")
        items = await requirements_repo.list_items(db, requirement_id)
        locations = await requirements_repo.list_locations(db, requirement_id)
        documents = await requirements_repo.list_documents(db, requirement_id)
        return {
            "requirement": requirement,
            "items": items,
            "locations": locations,
            "documents": documents,
        }


async def create_requirement(
    *, user_id: UUID, organization_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_WRITE)
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
