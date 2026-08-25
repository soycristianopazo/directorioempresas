"""Acceso a datos de rondas de negociación y sus participantes (fase 8.5)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.negotiations import NegotiationRound, NegotiationRoundParticipant


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


# ─── Rondas ─────────────────────────────────────────────────────────────────


async def create_round(session: AsyncSession, **fields: object) -> NegotiationRound:
    round_ = NegotiationRound(**fields)
    session.add(round_)
    await session.flush()
    return round_


async def get_round(session: AsyncSession, round_id: UUID) -> NegotiationRound | None:
    result = await session.execute(
        select(NegotiationRound).where(NegotiationRound.id == round_id)
    )
    return result.scalar_one_or_none()


async def list_rounds(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[NegotiationRound]:
    result = await session.execute(
        select(NegotiationRound)
        .where(NegotiationRound.sourcing_event_id == sourcing_event_id)
        .order_by(NegotiationRound.opened_at.desc())
    )
    return list(result.scalars())


async def update_round(round_: NegotiationRound, **fields: object) -> None:
    for key, value in fields.items():
        setattr(round_, key, value)


# ─── Participantes ────────────────────────────────────────────────────────────


async def add_participant(
    session: AsyncSession, **fields: object
) -> NegotiationRoundParticipant:
    participant = NegotiationRoundParticipant(**fields)
    session.add(participant)
    await session.flush()
    return participant


async def list_participants(
    session: AsyncSession, negotiation_round_id: UUID
) -> list[NegotiationRoundParticipant]:
    result = await session.execute(
        select(NegotiationRoundParticipant).where(
            NegotiationRoundParticipant.negotiation_round_id == negotiation_round_id
        )
    )
    return list(result.scalars())


async def get_participant(
    session: AsyncSession, negotiation_round_id: UUID, supplier_organization_id: UUID
) -> NegotiationRoundParticipant | None:
    result = await session.execute(
        select(NegotiationRoundParticipant).where(
            NegotiationRoundParticipant.negotiation_round_id == negotiation_round_id,
            NegotiationRoundParticipant.supplier_organization_id
            == supplier_organization_id,
        )
    )
    return result.scalar_one_or_none()


async def mark_responded(
    participant: NegotiationRoundParticipant, **fields: object
) -> None:
    for key, value in fields.items():
        setattr(participant, key, value)


# ─── Autoservicio del proveedor: sus rondas a través de todos los eventos ────


async def list_rounds_for_participant(
    session: AsyncSession, *, sourcing_event_id: UUID, supplier_organization_id: UUID
) -> list[dict]:
    """Join de negotiation_rounds + la fila propia en
    negotiation_round_participants, para el lado proveedor (autoservicio,
    filtrado por RLS vía is_member_of — no hay chequeo de permiso acá, mismo
    criterio que quotations_service.list_my_revisions())."""
    result = await session.execute(
        text(
            "select nr.id, nr.round_type, nr.instructions, nr.target_reduction_pct, "
            "       nr.deadline, nr.opened_at, nr.closed_at, "
            "       nrp.id as participant_id, "
            "       nrp.responded_quotation_revision_id, nrp.responded_at "
            "from public.negotiation_rounds nr "
            "join public.negotiation_round_participants nrp "
            "  on nrp.negotiation_round_id = nr.id "
            "where nr.sourcing_event_id = :event_id "
            "  and nrp.supplier_organization_id = :org_id "
            "order by nr.opened_at desc"
        ),
        {"event_id": str(sourcing_event_id), "org_id": str(supplier_organization_id)},
    )
    return [dict(row._mapping) for row in result]
