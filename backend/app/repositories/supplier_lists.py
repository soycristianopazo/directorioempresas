"""Listas de proveedores guardadas (fase 4.9)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier_list import SupplierList, SupplierListItem


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def list_lists(
    session: AsyncSession, organization_id: UUID
) -> list[SupplierList]:
    result = await session.execute(
        select(SupplierList)
        .where(SupplierList.organization_id == organization_id)
        .order_by(SupplierList.created_at.desc())
    )
    return list(result.scalars())


async def get_list(
    session: AsyncSession, list_id: UUID, *, organization_id: UUID
) -> SupplierList | None:
    result = await session.execute(
        select(SupplierList).where(
            SupplierList.id == list_id, SupplierList.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()


async def create_list(session: AsyncSession, **fields: object) -> SupplierList:
    row = SupplierList(**fields)
    session.add(row)
    await session.flush()
    return row


async def delete_list(
    session: AsyncSession, list_id: UUID, *, organization_id: UUID
) -> bool:
    result = await session.execute(
        delete(SupplierList).where(
            SupplierList.id == list_id, SupplierList.organization_id == organization_id
        )
    )
    return result.rowcount > 0  # type: ignore[attr-defined]


async def list_items_with_names(session: AsyncSession, list_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select sli.id, sli.target_organization_id, sli.note, sli.sort_order, "
            "       o.legal_name, o.trade_name, o.slug "
            "from public.supplier_list_items sli "
            "join public.organizations o on o.id = sli.target_organization_id "
            "where sli.list_id = :list_id "
            "order by sli.sort_order, o.trade_name nulls last, o.legal_name"
        ),
        {"list_id": str(list_id)},
    )
    return [dict(row._mapping) for row in result]


async def add_item(
    session: AsyncSession,
    *,
    list_id: UUID,
    target_organization_id: UUID,
    note: str | None,
) -> UUID:
    # upsert por (list_id, target_organization_id): guardar dos veces el
    # mismo proveedor actualiza la nota en vez de fallar por el unique.
    result = await session.execute(
        text(
            "insert into public.supplier_list_items (list_id, target_organization_id, note) "
            "values (:list_id, :target_organization_id, :note) "
            "on conflict (list_id, target_organization_id) do update set note = excluded.note "
            "returning id"
        ),
        {
            "list_id": str(list_id),
            "target_organization_id": str(target_organization_id),
            "note": note,
        },
    )
    return result.scalar_one()


async def remove_item(session: AsyncSession, item_id: UUID, *, list_id: UUID) -> bool:
    result = await session.execute(
        delete(SupplierListItem).where(
            SupplierListItem.id == item_id, SupplierListItem.list_id == list_id
        )
    )
    return result.rowcount > 0  # type: ignore[attr-defined]
