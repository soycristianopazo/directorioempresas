"""Rondas de negociación (COUNTER/BAFO) sobre un evento de sourcing (fase 8.5).

Reutiliza services/quotations.py::submit_revision() para el envío de la
contraoferta del proveedor (mismo flujo de validación de líneas, FX y
documento) — este módulo solo administra el ciclo de vida de la ronda y la
transición de la invitación del proveedor a NEGOTIATING mientras dura.

La transición de invitación NO se delega a services/invitations.py::_transition()
porque ese nombre es privado por convención (prefijo `_`); en su lugar este
módulo replica la llamada mínima directo contra invitations_repo (mismo
criterio que documenta invitations.py para mark_quoted(): funciones públicas
de otro repo pueden llamarse dentro de una transacción ya abierta).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import invitations as invitations_repo
from app.repositories import negotiations as negotiations_repo
from app.services import notifications as notifications_service
from app.services import quotations as quotations_service

PERM_MANAGE = "negotiation.manage"

_OPENABLE_ROUND_TYPES = ("COUNTER", "BAFO")


class NegotiationError(Exception):
    pass


class NegotiationPermissionError(NegotiationError):
    pass


class NegotiationNotFoundError(NegotiationError):
    pass


class NegotiationValidationError(NegotiationError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await negotiations_repo.has_permission(db, organization_id, permission):
        raise NegotiationPermissionError(f"Sin permiso ({permission}) para esta acción")


async def _transition_invitation(
    db, invitation, *, to_status: str, actor_id: UUID | None, reason: str | None
) -> None:
    if not await invitations_repo.is_valid_transition(db, invitation.status, to_status):
        raise NegotiationValidationError(
            f"El proveedor con invitación en estado {invitation.status} "
            f"no puede pasar a {to_status}"
        )
    from_status = invitation.status
    await invitations_repo.update_invitation(invitation, status=to_status)
    await db.flush()
    await invitations_repo.add_status_history(
        db,
        invitation_id=invitation.id,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
        reason=reason,
    )


# ─── Lado comprador ───────────────────────────────────────────────────────────


async def open_round(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    round_type: str,
    participant_supplier_organization_ids: list[UUID],
    deadline: datetime | None,
    target_reduction_pct: float | None = None,
    instructions: str | None = None,
) -> UUID:
    if round_type not in _OPENABLE_ROUND_TYPES:
        raise NegotiationValidationError(f"round_type inválido: {round_type}")
    if not participant_supplier_organization_ids:
        raise NegotiationValidationError(
            "La ronda necesita al menos un proveedor participante"
        )

    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)

        round_ = await negotiations_repo.create_round(
            db,
            sourcing_event_id=sourcing_event_id,
            round_type=round_type,
            instructions=instructions,
            target_reduction_pct=target_reduction_pct,
            deadline=deadline,
            opened_by=user_id,
        )

        for supplier_org_id in participant_supplier_organization_ids:
            invitation = await invitations_repo.get_by_event_and_supplier(
                db, sourcing_event_id, supplier_org_id
            )
            if invitation is None:
                raise NegotiationValidationError(
                    "Uno de los proveedores no tiene invitación en este evento"
                )
            await negotiations_repo.add_participant(
                db,
                negotiation_round_id=round_.id,
                supplier_organization_id=supplier_org_id,
            )
            if invitation.status != "NEGOTIATING":
                await _transition_invitation(
                    db,
                    invitation,
                    to_status="NEGOTIATING",
                    actor_id=user_id,
                    reason="Ronda de negociación abierta",
                )

        round_id = round_.id
        participant_org_ids = list(participant_supplier_organization_ids)

    for supplier_org_id in participant_org_ids:
        await notifications_service.notify_org(
            organization_id=supplier_org_id,
            type="negotiation.round_opened",
            title="Nueva ronda de negociación",
            body="El comprador abrió una nueva ronda de negociación para tu cotización.",
            entity_type="sourcing_event",
            entity_id=sourcing_event_id,
            action_url=f"/empresa/sourcing/{sourcing_event_id}/negociacion",
        )
    return round_id


async def list_rounds(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        return await negotiations_repo.list_rounds(db, sourcing_event_id)


async def close_round(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    negotiation_round_id: UUID,
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)

        round_ = await negotiations_repo.get_round(db, negotiation_round_id)
        if round_ is None or round_.sourcing_event_id != sourcing_event_id:
            raise NegotiationNotFoundError("Ronda de negociación no encontrada")
        if round_.closed_at is not None:
            raise NegotiationValidationError("Esta ronda ya fue cerrada")

        participants = await negotiations_repo.list_participants(
            db, negotiation_round_id
        )
        for participant in participants:
            invitation = await invitations_repo.get_by_event_and_supplier(
                db, sourcing_event_id, participant.supplier_organization_id
            )
            if invitation is not None and invitation.status == "NEGOTIATING":
                await _transition_invitation(
                    db,
                    invitation,
                    to_status="QUOTED",
                    actor_id=user_id,
                    reason="Ronda cerrada, vuelve a comparación",
                )

        await negotiations_repo.update_round(
            round_, closed_at=datetime.now(timezone.utc), closed_by=user_id
        )
        await db.flush()


# ─── Lado proveedor (autoservicio) ────────────────────────────────────────────


async def list_my_round(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        return await negotiations_repo.list_rounds_for_participant(
            db,
            sourcing_event_id=sourcing_event_id,
            supplier_organization_id=organization_id,
        )


async def submit_counter(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    negotiation_round_id: UUID,
    currency_code: str,
    valid_until: date | None,
    subtotal: float | None,
    tax_amount: float | None,
    total_amount: float,
    payment_terms: str | None,
    delivery_days: int | None,
    warranty_terms: str | None,
    exclusions: str | None,
    notes: str | None,
    items: list[dict],
    responses: list[dict] | None = None,
) -> UUID:
    async with session_for_user(user_id) as db:
        round_ = await negotiations_repo.get_round(db, negotiation_round_id)
        if round_ is None or round_.sourcing_event_id != sourcing_event_id:
            raise NegotiationNotFoundError("Ronda de negociación no encontrada")
        if round_.closed_at is not None:
            raise NegotiationValidationError("Esta ronda ya fue cerrada")

        participant = await negotiations_repo.get_participant(
            db, negotiation_round_id, organization_id
        )
        if participant is None:
            raise NegotiationPermissionError(
                "Esta organización no participa en esta ronda de negociación"
            )
        if participant.responded_quotation_revision_id is not None:
            raise NegotiationValidationError(
                "Esta organización ya respondió esta ronda de negociación"
            )
        round_type = round_.round_type

    # submit_revision() abre y cierra su propia session_for_user (valida contra
    # la RLS policy de 0061, que exige justo esta fila pendiente antes del
    # deadline de la ronda) — no se anida dentro de la sesión de arriba.
    #
    # Sus excepciones son QuotationError, no NegotiationError — sin traducirlas
    # acá, un 400 legítimo (línea vacía, monto negativo, FX faltante) se
    # colaría sin capturar por el router de negociación (que solo atrapa
    # NegotiationError) y saldría como 500. Se traducen preservando el mensaje.
    try:
        revision_id = await quotations_service.submit_revision(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=sourcing_event_id,
            currency_code=currency_code,
            valid_until=valid_until,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            payment_terms=payment_terms,
            delivery_days=delivery_days,
            warranty_terms=warranty_terms,
            exclusions=exclusions,
            notes=notes,
            items=items,
            responses=responses,
            round_type=round_type,
        )
    except quotations_service.QuotationPermissionError as exc:
        raise NegotiationPermissionError(str(exc)) from exc
    except quotations_service.QuotationNotFoundError as exc:
        raise NegotiationNotFoundError(str(exc)) from exc
    except quotations_service.QuotationValidationError as exc:
        raise NegotiationValidationError(str(exc)) from exc
    except quotations_service.QuotationError as exc:
        raise NegotiationError(str(exc)) from exc

    async with session_for_user(user_id) as db:
        participant = await negotiations_repo.get_participant(
            db, negotiation_round_id, organization_id
        )
        if participant is None:
            raise NegotiationNotFoundError("Ronda de negociación no encontrada")
        await negotiations_repo.mark_responded(
            participant,
            responded_quotation_revision_id=revision_id,
            responded_at=datetime.now(timezone.utc),
        )
        await db.flush()

    return revision_id
