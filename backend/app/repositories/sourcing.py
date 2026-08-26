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
    """RFQ-2026-0142: el número viene de una secuencia real
    (`public.sourcing_event_code_seq`, 0053), no de `count(*)` — ese conteo
    corría dentro de la sesión RLS-scoped del usuario, que solo ve las filas
    de SU organización (0043_fase6_rls.sql), así que dos organizaciones
    distintas creando cada una su primer evento del año generaban ambas
    "...-0001" y colisionaban contra el UNIQUE de event_code. Una secuencia no
    está sujeta a RLS y nextval() es atómica — sin condición de carrera, sin
    fuga de conteo entre organizaciones. El número deja de reiniciar en 0001
    cada año (sigue subiendo); el año en el propio código sigue siendo el dato
    real de cuándo se creó."""
    result = await session.execute(
        text("select nextval('public.sourcing_event_code_seq')")
    )
    n = result.scalar_one()
    return f"{event_type}-{year}-{n:04d}"


async def list_events_with_stage(
    session: AsyncSession, organization_id: UUID
) -> list[dict]:
    """Como `list_events`, pero agrega `stage`: en qué de las 5 pestañas del
    workspace (publicar/match/evaluacion/negociacion/adjudicacion, mismas
    claves que `tabsFor()` en SourcingEventLayout.jsx) está el evento hoy.
    `sourcing_events.status` no alcanza para esto — PUBLISHED cubre tanto
    "recién publicado" como "en plena negociación", así que la etapa se
    infiere por EXISTS contra las tablas donde cada etapa deja rastro
    (evaluation_assignments, negotiation_rounds, awards) en una sola
    consulta, no N+1 por evento."""
    result = await session.execute(
        text(
            """
            select
                se.id, se.organization_id, se.requirement_id, se.event_code,
                se.name, se.description, se.event_type, se.visibility,
                se.bid_mode, se.status, se.void_reason, se.currency_code,
                se.estimated_amount, se.requires_nda,
                se.requires_accreditation_program_id, se.max_invitations,
                se.matching_weights, se.published_at, se.bid_opened_at,
                se.bid_opened_by, se.created_at,
                case
                    when se.status = 'AWARDED' or exists (
                        select 1 from public.awards a
                        where a.sourcing_event_id = se.id
                    ) then 'adjudicacion'
                    when exists (
                        select 1 from public.negotiation_rounds nr
                        where nr.sourcing_event_id = se.id
                    ) then 'negociacion'
                    when exists (
                        select 1 from public.evaluation_assignments ea
                        where ea.sourcing_event_id = se.id
                    ) then 'evaluacion'
                    when se.status = 'PUBLISHED' then 'match'
                    else 'publicar'
                end as stage
            from public.sourcing_events se
            where se.organization_id = :org_id
            order by se.created_at desc
            """
        ),
        {"org_id": str(organization_id)},
    )
    return [dict(row) for row in result.mappings()]


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
