"""Vendor List / AVL — acceso a datos de buyer_supplier_relationships y sus
notas (fase 8.8). Mismo patrón que repositories/supplier_lists.py y
repositories/evaluations.py."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor_list import BuyerSupplierNote, BuyerSupplierRelationship


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def list_relationships(
    session: AsyncSession,
    buyer_organization_id: UUID,
    status_filter: str | None = None,
) -> list[BuyerSupplierRelationship]:
    query = select(BuyerSupplierRelationship).where(
        BuyerSupplierRelationship.buyer_organization_id == buyer_organization_id
    )
    if status_filter is not None:
        query = query.where(BuyerSupplierRelationship.status == status_filter)
    query = query.order_by(BuyerSupplierRelationship.status_changed_at.desc())
    result = await session.execute(query)
    return list(result.scalars())


async def get_relationship(
    session: AsyncSession, relationship_id: UUID
) -> BuyerSupplierRelationship | None:
    result = await session.execute(
        select(BuyerSupplierRelationship).where(
            BuyerSupplierRelationship.id == relationship_id
        )
    )
    return result.scalar_one_or_none()


async def get_by_buyer_and_supplier(
    session: AsyncSession, buyer_organization_id: UUID, supplier_organization_id: UUID
) -> BuyerSupplierRelationship | None:
    result = await session.execute(
        select(BuyerSupplierRelationship).where(
            BuyerSupplierRelationship.buyer_organization_id == buyer_organization_id,
            BuyerSupplierRelationship.supplier_organization_id
            == supplier_organization_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert_relationship(
    session: AsyncSession,
    *,
    buyer_organization_id: UUID,
    supplier_organization_id: UUID,
    status: str,
    status_changed_by: UUID,
    created_by: UUID | None = None,
) -> BuyerSupplierRelationship:
    existing = await get_by_buyer_and_supplier(
        session, buyer_organization_id, supplier_organization_id
    )
    if existing is not None:
        existing.status = status
        existing.status_changed_at = datetime.now(timezone.utc)
        existing.status_changed_by = status_changed_by
        await session.flush()
        return existing
    relationship = BuyerSupplierRelationship(
        buyer_organization_id=buyer_organization_id,
        supplier_organization_id=supplier_organization_id,
        status=status,
        status_changed_by=status_changed_by,
        created_by=created_by or status_changed_by,
    )
    session.add(relationship)
    await session.flush()
    return relationship


async def list_notes(
    session: AsyncSession, relationship_id: UUID
) -> list[BuyerSupplierNote]:
    result = await session.execute(
        select(BuyerSupplierNote)
        .where(BuyerSupplierNote.relationship_id == relationship_id)
        .order_by(BuyerSupplierNote.created_at.desc())
    )
    return list(result.scalars())


async def add_note(session: AsyncSession, **fields: object) -> BuyerSupplierNote:
    note = BuyerSupplierNote(**fields)
    session.add(note)
    await session.flush()
    return note
