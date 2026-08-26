"""Acceso a datos de invitaciones, su historial y el NDA del evento
(fase 7.1/7.2)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ndas import NdaAcceptance, SourcingEventNda
from app.models.sourcing_invitations import (
    InvitationStatusHistory,
    SourcingEventInvitation,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def has_active_invitation(session: AsyncSession, sourcing_event_id: UUID) -> bool:
    result = await session.execute(
        text("select app.has_active_sourcing_invitation(:event_id)"),
        {"event_id": str(sourcing_event_id)},
    )
    return bool(result.scalar_one())


async def is_valid_transition(
    session: AsyncSession, from_status: str, to_status: str
) -> bool:
    result = await session.execute(
        text(
            "select exists(select 1 from public.sourcing_event_invitation_transitions "
            "where from_status = :from_status and to_status = :to_status)"
        ),
        {"from_status": from_status, "to_status": to_status},
    )
    return bool(result.scalar_one())


# ─── Invitaciones ─────────────────────────────────────────────────────────────


async def list_for_event(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[SourcingEventInvitation]:
    result = await session.execute(
        select(SourcingEventInvitation)
        .where(SourcingEventInvitation.sourcing_event_id == sourcing_event_id)
        .order_by(SourcingEventInvitation.invited_at.desc())
    )
    return list(result.scalars())


async def list_for_supplier(
    session: AsyncSession, supplier_organization_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select sei.id, sei.sourcing_event_id, sei.status, sei.source, "
            "       sei.invited_at, sei.viewed_at, sei.responded_at, "
            "       se.event_code, se.name as event_name, se.event_type, "
            "       se.bid_mode, se.requires_nda "
            "from public.sourcing_event_invitations sei "
            "join public.sourcing_events se on se.id = sei.sourcing_event_id "
            "where sei.supplier_organization_id = :org_id "
            "order by sei.invited_at desc"
        ),
        {"org_id": str(supplier_organization_id)},
    )
    return [dict(row._mapping) for row in result]


async def list_for_buyer_organization(
    session: AsyncSession, buyer_organization_id: UUID
) -> list[dict]:
    """Espejo de list_for_supplier() para el otro lado de la fila: todas las
    invitaciones que ESTA organización mandó, a través de TODOS sus
    sourcing_events — antes solo existía list_for_event() (un evento a la
    vez), sin vista agregada."""
    result = await session.execute(
        text(
            "select sei.id, sei.sourcing_event_id, sei.status, sei.source, "
            "       sei.invited_at, sei.viewed_at, sei.responded_at, "
            "       se.event_code, se.name as event_name, se.event_type, "
            "       se.bid_mode, se.requires_nda, "
            "       sei.supplier_organization_id, "
            "       o.legal_name as supplier_legal_name, "
            "       o.trade_name as supplier_trade_name "
            "from public.sourcing_event_invitations sei "
            "join public.sourcing_events se on se.id = sei.sourcing_event_id "
            "join public.organizations o on o.id = sei.supplier_organization_id "
            "where se.organization_id = :org_id "
            "order by sei.invited_at desc"
        ),
        {"org_id": str(buyer_organization_id)},
    )
    return [dict(row._mapping) for row in result]


async def get_invitation(
    session: AsyncSession, invitation_id: UUID
) -> SourcingEventInvitation | None:
    result = await session.execute(
        select(SourcingEventInvitation).where(
            SourcingEventInvitation.id == invitation_id
        )
    )
    return result.scalar_one_or_none()


async def get_by_event_and_supplier(
    session: AsyncSession, sourcing_event_id: UUID, supplier_organization_id: UUID
) -> SourcingEventInvitation | None:
    result = await session.execute(
        select(SourcingEventInvitation).where(
            SourcingEventInvitation.sourcing_event_id == sourcing_event_id,
            SourcingEventInvitation.supplier_organization_id
            == supplier_organization_id,
        )
    )
    return result.scalar_one_or_none()


async def list_by_event_and_suppliers(
    session: AsyncSession,
    sourcing_event_id: UUID,
    supplier_organization_ids: list[UUID],
) -> list[SourcingEventInvitation]:
    """Como `get_by_event_and_supplier`, para varios proveedores a la vez —
    una sola query en vez de una por proveedor (negotiations.py::open_round/
    close_round, que hoy resuelven la invitación de cada participante en un
    loop)."""
    if not supplier_organization_ids:
        return []
    result = await session.execute(
        select(SourcingEventInvitation).where(
            SourcingEventInvitation.sourcing_event_id == sourcing_event_id,
            SourcingEventInvitation.supplier_organization_id.in_(
                supplier_organization_ids
            ),
        )
    )
    return list(result.scalars())


async def create_invitation(
    session: AsyncSession, **fields: object
) -> SourcingEventInvitation:
    invitation = SourcingEventInvitation(**fields)
    session.add(invitation)
    await session.flush()
    return invitation


async def update_invitation(
    invitation: SourcingEventInvitation, **fields: object
) -> None:
    for key, value in fields.items():
        setattr(invitation, key, value)


async def add_status_history(session: AsyncSession, **fields: object) -> None:
    session.add(InvitationStatusHistory(**fields))
    await session.flush()


async def list_status_history(
    session: AsyncSession, invitation_id: UUID
) -> list[InvitationStatusHistory]:
    result = await session.execute(
        select(InvitationStatusHistory)
        .where(InvitationStatusHistory.invitation_id == invitation_id)
        .order_by(InvitationStatusHistory.created_at)
    )
    return list(result.scalars())


# ─── NDA ────────────────────────────────────────────────────────────────────


async def get_current_nda(
    session: AsyncSession, sourcing_event_id: UUID
) -> SourcingEventNda | None:
    result = await session.execute(
        select(SourcingEventNda)
        .where(SourcingEventNda.sourcing_event_id == sourcing_event_id)
        .order_by(SourcingEventNda.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_nda(session: AsyncSession, **fields: object) -> SourcingEventNda:
    nda = SourcingEventNda(**fields)
    session.add(nda)
    await session.flush()
    return nda


async def get_acceptance(
    session: AsyncSession, nda_id: UUID, organization_id: UUID
) -> NdaAcceptance | None:
    result = await session.execute(
        select(NdaAcceptance).where(
            NdaAcceptance.nda_id == nda_id,
            NdaAcceptance.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def create_acceptance(session: AsyncSession, **fields: object) -> NdaAcceptance:
    acceptance = NdaAcceptance(**fields)
    session.add(acceptance)
    await session.flush()
    return acceptance
