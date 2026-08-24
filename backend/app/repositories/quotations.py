"""Acceso a datos de cotizaciones: contenedor, revisiones append-only,
líneas, respuestas y documentos (fase 7.5)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quotations import (
    Quotation,
    QuotationDocument,
    QuotationItem,
    QuotationResponse,
    QuotationRevision,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def get_or_create(
    session: AsyncSession,
    *,
    sourcing_event_id: UUID,
    supplier_organization_id: UUID,
    created_by: UUID,
) -> Quotation:
    result = await session.execute(
        select(Quotation).where(
            Quotation.sourcing_event_id == sourcing_event_id,
            Quotation.supplier_organization_id == supplier_organization_id,
        )
    )
    quotation = result.scalar_one_or_none()
    if quotation is not None:
        return quotation
    quotation = Quotation(
        sourcing_event_id=sourcing_event_id,
        supplier_organization_id=supplier_organization_id,
        created_by=created_by,
    )
    session.add(quotation)
    await session.flush()
    return quotation


async def get_by_event_and_supplier(
    session: AsyncSession, *, sourcing_event_id: UUID, supplier_organization_id: UUID
) -> Quotation | None:
    result = await session.execute(
        select(Quotation).where(
            Quotation.sourcing_event_id == sourcing_event_id,
            Quotation.supplier_organization_id == supplier_organization_id,
        )
    )
    return result.scalar_one_or_none()


async def get_quotation(session: AsyncSession, quotation_id: UUID) -> Quotation | None:
    result = await session.execute(
        select(Quotation).where(Quotation.id == quotation_id)
    )
    return result.scalar_one_or_none()


async def update_quotation(quotation: Quotation, **fields: object) -> None:
    for key, value in fields.items():
        setattr(quotation, key, value)


async def list_for_event(session: AsyncSession, sourcing_event_id: UUID) -> list[dict]:
    """Solo devuelve algo si RLS lo permite (comprador con evento abierto, o
    el propio proveedor) — no hay lógica de sellado acá, la hace la base."""
    result = await session.execute(
        text(
            "select q.id, q.supplier_organization_id, q.status, q.first_submitted_at, "
            "       qr.round_number, qr.total_amount, qr.total_amount_base, qr.currency_code, "
            "       qr.submitted_at "
            "from public.quotations q "
            "left join public.quotation_revisions qr on qr.id = q.current_revision_id "
            "where q.sourcing_event_id = :event_id "
            "order by qr.total_amount_base nulls last"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    return [dict(row._mapping) for row in result]


async def next_round_number(session: AsyncSession, quotation_id: UUID) -> int:
    result = await session.execute(
        text(
            "select coalesce(max(round_number), 0) + 1 from public.quotation_revisions "
            "where quotation_id = :quotation_id"
        ),
        {"quotation_id": str(quotation_id)},
    )
    return int(result.scalar_one())


async def create_revision(session: AsyncSession, **fields: object) -> QuotationRevision:
    revision = QuotationRevision(**fields)
    session.add(revision)
    await session.flush()
    return revision


async def get_revision(
    session: AsyncSession, revision_id: UUID
) -> QuotationRevision | None:
    result = await session.execute(
        select(QuotationRevision).where(QuotationRevision.id == revision_id)
    )
    return result.scalar_one_or_none()


async def list_revisions(
    session: AsyncSession, quotation_id: UUID
) -> list[QuotationRevision]:
    result = await session.execute(
        select(QuotationRevision)
        .where(QuotationRevision.quotation_id == quotation_id)
        .order_by(QuotationRevision.round_number)
    )
    return list(result.scalars())


async def add_item(session: AsyncSession, **fields: object) -> QuotationItem:
    item = QuotationItem(**fields)
    session.add(item)
    await session.flush()
    return item


async def list_items(
    session: AsyncSession, quotation_revision_id: UUID
) -> list[QuotationItem]:
    result = await session.execute(
        select(QuotationItem).where(
            QuotationItem.quotation_revision_id == quotation_revision_id
        )
    )
    return list(result.scalars())


async def add_response(session: AsyncSession, **fields: object) -> QuotationResponse:
    response = QuotationResponse(**fields)
    session.add(response)
    await session.flush()
    return response


async def add_document(session: AsyncSession, **fields: object) -> QuotationDocument:
    document = QuotationDocument(**fields)
    session.add(document)
    await session.flush()
    return document


async def list_documents(
    session: AsyncSession, quotation_revision_id: UUID
) -> list[QuotationDocument]:
    result = await session.execute(
        select(QuotationDocument).where(
            QuotationDocument.quotation_revision_id == quotation_revision_id
        )
    )
    return list(result.scalars())


async def get_bid_deadline(session: AsyncSession, sourcing_event_id: UUID):
    result = await session.execute(
        text(
            "select scheduled_at from public.sourcing_event_stages "
            "where sourcing_event_id = :event_id and stage_type = 'BID_DEADLINE'"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    row = result.first()
    return row[0] if row else None
