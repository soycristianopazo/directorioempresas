"""Acceso a datos de sourcing_events y su estructura: lotes, ítems, hitos,
documentos, criterios MUST/NICE (fase 6.2/6.3)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sourcing import (
    SourcingEvent,
    SourcingEventCriterion,
    SourcingEventDocument,
    SourcingEventItem,
    SourcingEventLot,
    SourcingEventStage,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def next_event_code(session: AsyncSession, *, event_type: str, year: int) -> str:
    """RFQ-2026-0142: correlativo por año, compartido entre todos los
    event_type (RFI/RFQ/RFP/...) — el prefijo identifica el tipo, no cambia
    la serie."""
    result = await session.execute(
        text(
            "select count(*) from public.sourcing_events where event_code like :pattern"
        ),
        {"pattern": f"%-{year}-%"},
    )
    count = result.scalar_one()
    return f"{event_type}-{year}-{count + 1:04d}"


async def list_events(
    session: AsyncSession, organization_id: UUID
) -> list[SourcingEvent]:
    result = await session.execute(
        select(SourcingEvent)
        .where(SourcingEvent.organization_id == organization_id)
        .order_by(SourcingEvent.created_at.desc())
    )
    return list(result.scalars())


async def get_event(session: AsyncSession, event_id: UUID) -> SourcingEvent | None:
    result = await session.execute(
        select(SourcingEvent).where(SourcingEvent.id == event_id)
    )
    return result.scalar_one_or_none()


async def create_event(session: AsyncSession, **fields: object) -> SourcingEvent:
    event = SourcingEvent(**fields)
    session.add(event)
    await session.flush()
    return event


async def update_event(event: SourcingEvent, **fields: object) -> None:
    for key, value in fields.items():
        setattr(event, key, value)


async def list_lots(session: AsyncSession, event_id: UUID) -> list[SourcingEventLot]:
    result = await session.execute(
        select(SourcingEventLot)
        .where(SourcingEventLot.sourcing_event_id == event_id)
        .order_by(SourcingEventLot.sort_order)
    )
    return list(result.scalars())


async def add_lot(session: AsyncSession, **fields: object) -> SourcingEventLot:
    lot = SourcingEventLot(**fields)
    session.add(lot)
    await session.flush()
    return lot


async def list_items(session: AsyncSession, event_id: UUID) -> list[SourcingEventItem]:
    result = await session.execute(
        select(SourcingEventItem)
        .where(SourcingEventItem.sourcing_event_id == event_id)
        .order_by(SourcingEventItem.sort_order)
    )
    return list(result.scalars())


async def add_item(session: AsyncSession, **fields: object) -> SourcingEventItem:
    item = SourcingEventItem(**fields)
    session.add(item)
    await session.flush()
    return item


async def total_quantity(session: AsyncSession, event_id: UUID) -> float:
    """Cantidad agregada de las líneas del evento — capacity_fit (§H.4.8)
    compara la capacidad declarada del offering contra este total."""
    result = await session.execute(
        text(
            "select coalesce(sum(quantity), 0) from public.sourcing_event_items "
            "where sourcing_event_id = :event_id and not is_optional"
        ),
        {"event_id": str(event_id)},
    )
    return float(result.scalar_one())


async def list_stages(
    session: AsyncSession, event_id: UUID
) -> list[SourcingEventStage]:
    result = await session.execute(
        select(SourcingEventStage).where(
            SourcingEventStage.sourcing_event_id == event_id
        )
    )
    return list(result.scalars())


async def upsert_stage(
    session: AsyncSession, *, event_id: UUID, stage_type: str, **fields: object
) -> SourcingEventStage:
    result = await session.execute(
        select(SourcingEventStage).where(
            SourcingEventStage.sourcing_event_id == event_id,
            SourcingEventStage.stage_type == stage_type,
        )
    )
    stage = result.scalar_one_or_none()
    if stage is None:
        stage = SourcingEventStage(
            sourcing_event_id=event_id, stage_type=stage_type, **fields
        )
        session.add(stage)
    else:
        for key, value in fields.items():
            setattr(stage, key, value)
    await session.flush()
    return stage


async def list_documents(
    session: AsyncSession, event_id: UUID
) -> list[SourcingEventDocument]:
    result = await session.execute(
        select(SourcingEventDocument).where(
            SourcingEventDocument.sourcing_event_id == event_id
        )
    )
    return list(result.scalars())


async def add_document(
    session: AsyncSession, **fields: object
) -> SourcingEventDocument:
    document = SourcingEventDocument(**fields)
    session.add(document)
    await session.flush()
    return document


async def list_criteria(
    session: AsyncSession, event_id: UUID
) -> list[SourcingEventCriterion]:
    result = await session.execute(
        select(SourcingEventCriterion)
        .where(SourcingEventCriterion.sourcing_event_id == event_id)
        .order_by(SourcingEventCriterion.sort_order)
    )
    return list(result.scalars())


async def get_criterion(
    session: AsyncSession, criterion_id: UUID
) -> SourcingEventCriterion | None:
    result = await session.execute(
        select(SourcingEventCriterion).where(SourcingEventCriterion.id == criterion_id)
    )
    return result.scalar_one_or_none()


async def add_criterion(
    session: AsyncSession, **fields: object
) -> SourcingEventCriterion:
    criterion = SourcingEventCriterion(**fields)
    session.add(criterion)
    await session.flush()
    return criterion


async def delete_criterion(session: AsyncSession, criterion_id: UUID) -> None:
    await session.execute(
        text("delete from public.sourcing_event_criteria where id = :id"),
        {"id": str(criterion_id)},
    )
