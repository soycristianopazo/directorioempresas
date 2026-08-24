"""Listas de proveedores guardadas (fase 4.9). Mismo patrón que
services/credentials.py: permiso verificado antes de mutar."""

from __future__ import annotations

from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import supplier_lists as lists_repo

PERM_READ = "vendor_list.read"
PERM_MANAGE = "vendor_list.manage"


class SupplierListError(Exception):
    pass


class SupplierListPermissionError(SupplierListError):
    pass


class SupplierListNotFoundError(SupplierListError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await lists_repo.has_permission(db, organization_id, permission):
        raise SupplierListPermissionError(
            f"Sin permiso ({permission}) para esta acción"
        )


async def list_lists(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await lists_repo.list_lists(db, organization_id)


async def create_list(
    *, user_id: UUID, organization_id: UUID, name: str, is_shared_with_org: bool
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        row = await lists_repo.create_list(
            db,
            organization_id=organization_id,
            name=name.strip(),
            is_shared_with_org=is_shared_with_org,
        )
        return row.id


async def delete_list(*, user_id: UUID, organization_id: UUID, list_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        removed = await lists_repo.delete_list(
            db, list_id, organization_id=organization_id
        )
        if not removed:
            raise SupplierListNotFoundError("Lista no encontrada")


async def list_items(
    *, user_id: UUID, organization_id: UUID, list_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        supplier_list = await lists_repo.get_list(
            db, list_id, organization_id=organization_id
        )
        if supplier_list is None:
            raise SupplierListNotFoundError("Lista no encontrada")
        return await lists_repo.list_items_with_names(db, list_id)


async def add_item(
    *,
    user_id: UUID,
    organization_id: UUID,
    list_id: UUID,
    target_organization_id: UUID,
    note: str | None,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        supplier_list = await lists_repo.get_list(
            db, list_id, organization_id=organization_id
        )
        if supplier_list is None:
            raise SupplierListNotFoundError("Lista no encontrada")
        return await lists_repo.add_item(
            db,
            list_id=list_id,
            target_organization_id=target_organization_id,
            note=note,
        )


async def remove_item(
    *, user_id: UUID, organization_id: UUID, list_id: UUID, item_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        supplier_list = await lists_repo.get_list(
            db, list_id, organization_id=organization_id
        )
        if supplier_list is None:
            raise SupplierListNotFoundError("Lista no encontrada")
        removed = await lists_repo.remove_item(db, item_id, list_id=list_id)
        if not removed:
            raise SupplierListNotFoundError("Ítem no encontrado")
