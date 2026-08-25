"""Vendor List / AVL — estado del comprador sobre cada proveedor y sus notas
internas (fase 8.8). Mismo patrón que services/supplier_lists.py: permiso
verificado antes de mutar, RLS de la 0068 nunca expone esto al proveedor."""

from __future__ import annotations

from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import vendor_list as vendor_list_repo

PERM_READ = "vendor_list.read"
PERM_MANAGE = "vendor_list.manage"

VALID_STATUSES = {
    "POTENTIAL",
    "IN_EVALUATION",
    "APPROVED",
    "CONDITIONAL",
    "SUSPENDED",
    "BLOCKED",
}


class VendorListError(Exception):
    pass


class VendorListPermissionError(VendorListError):
    pass


class VendorListNotFoundError(VendorListError):
    pass


class VendorListValidationError(VendorListError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await vendor_list_repo.has_permission(db, organization_id, permission):
        raise VendorListPermissionError(f"Sin permiso ({permission}) para esta acción")


async def list_relationships(
    *, user_id: UUID, organization_id: UUID, status_filter: str | None = None
) -> list:
    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise VendorListValidationError(f"Estado inválido: {status_filter}")
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await vendor_list_repo.list_relationships(
            db, organization_id, status_filter
        )


async def set_relationship_status(
    *,
    user_id: UUID,
    organization_id: UUID,
    supplier_organization_id: UUID,
    status: str,
) -> UUID:
    if status not in VALID_STATUSES:
        raise VendorListValidationError(f"Estado inválido: {status}")
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        relationship = await vendor_list_repo.upsert_relationship(
            db,
            buyer_organization_id=organization_id,
            supplier_organization_id=supplier_organization_id,
            status=status,
            status_changed_by=user_id,
        )
        return relationship.id


async def list_notes(
    *, user_id: UUID, organization_id: UUID, relationship_id: UUID
) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        relationship = await vendor_list_repo.get_relationship(db, relationship_id)
        if (
            relationship is None
            or relationship.buyer_organization_id != organization_id
        ):
            raise VendorListNotFoundError("Relación no encontrada")
        return await vendor_list_repo.list_notes(db, relationship_id)


async def add_note(
    *, user_id: UUID, organization_id: UUID, relationship_id: UUID, body: str
) -> UUID:
    body = body.strip()
    if not body:
        raise VendorListValidationError("La nota no puede estar vacía")
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        relationship = await vendor_list_repo.get_relationship(db, relationship_id)
        if (
            relationship is None
            or relationship.buyer_organization_id != organization_id
        ):
            raise VendorListNotFoundError("Relación no encontrada")
        note = await vendor_list_repo.add_note(
            db,
            relationship_id=relationship_id,
            body=body,
            created_by=user_id,
        )
        return note.id
