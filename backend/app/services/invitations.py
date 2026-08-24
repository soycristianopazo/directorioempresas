"""Invitaciones a proveedores y NDA del evento (fase 7.1/7.2).

Máquina de estados en Python, no en trigger — mismo criterio que
services/accreditation.py. sourcing_event_invitation_transitions es DATA:
toda transición pasa por _transition(), que la valida contra esa tabla antes
de aplicarla — nunca un `invitation.status = "..."` suelto.

Dos lados de la misma fila, dos criterios de autorización distintos:
del lado comprador, el backstop de 4 permisos de sourcing_event.* (mismo que
0043/0048); del lado proveedor, autoservicio puro sobre su propia fila
(is_member_of), sin permiso de plataforma — RLS ya lo exige en 0048, este
módulo repite el chequeo como defensa 2 (docs/RLS.md).

mark_quoted() es la única función pensada para ser llamada DESDE OTRO
service (services/quotations.py) dentro de una transacción ya abierta — no
envuelve su propia session_for_user, a diferencia de todo lo demás acá.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import invitations as invitations_repo
from app.repositories import sourcing as sourcing_repo
from app.services import notifications as notifications_service

PERM_PUBLISH = "sourcing_event.publish"
PERM_CANCEL = "sourcing_event.cancel"
PERM_READ = "sourcing_event.read"


class InvitationError(Exception):
    pass


class InvitationPermissionError(InvitationError):
    pass


class InvitationNotFoundError(InvitationError):
    pass


class InvitationValidationError(InvitationError):
    pass


async def _require_buyer_manage(db, organization_id: UUID) -> None:
    if not (
        await invitations_repo.has_permission(db, organization_id, PERM_PUBLISH)
        or await invitations_repo.has_permission(db, organization_id, PERM_CANCEL)
    ):
        raise InvitationPermissionError("Sin permiso para gestionar invitaciones")


async def _get_owned_invitation(
    db, invitation_id: UUID, *, supplier_organization_id: UUID
):
    invitation = await invitations_repo.get_invitation(db, invitation_id)
    if (
        invitation is None
        or invitation.supplier_organization_id != supplier_organization_id
    ):
        raise InvitationNotFoundError("Invitación no encontrada")
    return invitation


async def _transition(
    db, invitation, *, to_status: str, actor_id: UUID | None, reason: str | None = None
) -> None:
    if not await invitations_repo.is_valid_transition(db, invitation.status, to_status):
        raise InvitationValidationError(
            f"No se puede pasar de {invitation.status} a {to_status}"
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


async def list_invitations(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> list:
    async with session_for_user(user_id) as db:
        await invitations_repo.has_permission(db, organization_id, PERM_READ)
        return await invitations_repo.list_for_event(db, sourcing_event_id)


async def invite_supplier(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    supplier_organization_id: UUID,
    source: str = "MANUAL",
    match_score_snapshot: float | None = None,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require_buyer_manage(db, organization_id)

        existing = await invitations_repo.get_by_event_and_supplier(
            db, sourcing_event_id, supplier_organization_id
        )
        if existing is not None:
            raise InvitationValidationError(
                "Este proveedor ya fue invitado a este evento"
            )

        invitation = await invitations_repo.create_invitation(
            db,
            sourcing_event_id=sourcing_event_id,
            supplier_organization_id=supplier_organization_id,
            source=source,
            match_score_snapshot=match_score_snapshot,
            created_by=user_id,
        )
        await db.flush()
        await invitations_repo.add_status_history(
            db,
            invitation_id=invitation.id,
            from_status=None,
            to_status="INVITED",
            actor_id=user_id,
            reason="Invitación enviada",
        )
        invitation_id = invitation.id

    await notifications_service.notify_org(
        organization_id=supplier_organization_id,
        type="invitation.received",
        title="Nueva invitación a cotizar",
        body="Fuiste invitado a participar de un proceso de sourcing.",
        entity_type="sourcing_event_invitation",
        entity_id=invitation_id,
        action_url="/empresa/invitaciones",
    )
    return invitation_id


async def disqualify(
    *,
    user_id: UUID,
    organization_id: UUID,
    invitation_id: UUID,
    reason: str | None = None,
) -> None:
    async with session_for_user(user_id) as db:
        await _require_buyer_manage(db, organization_id)
        invitation = await invitations_repo.get_invitation(db, invitation_id)
        if invitation is None:
            raise InvitationNotFoundError("Invitación no encontrada")
        await _transition(
            db, invitation, to_status="DISQUALIFIED", actor_id=user_id, reason=reason
        )


# ─── NDA (lado comprador: crear/versionar) ────────────────────────────────────


async def get_nda(*, user_id: UUID, sourcing_event_id: UUID) -> dict | None:
    async with session_for_user(user_id) as db:
        nda = await invitations_repo.get_current_nda(db, sourcing_event_id)
        if nda is None:
            return None
        return {
            "id": nda.id,
            "version": nda.version,
            "title": nda.title,
            "body_text": nda.body_text,
        }


async def upsert_nda(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    title: str,
    body_text: str,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require_buyer_manage(db, organization_id)
        current = await invitations_repo.get_current_nda(db, sourcing_event_id)
        next_version = (current.version + 1) if current else 1
        checksum = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
        nda = await invitations_repo.create_nda(
            db,
            sourcing_event_id=sourcing_event_id,
            version=next_version,
            title=title,
            body_text=body_text,
            checksum_sha256=checksum,
            created_by=user_id,
        )
        nda_id = nda.id
    return nda_id


# ─── Lado proveedor (autoservicio) ────────────────────────────────────────────


async def list_my_invitations(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        return await invitations_repo.list_for_supplier(db, organization_id)


async def get_invitation_detail(
    *, user_id: UUID, organization_id: UUID, invitation_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        invitation = await _get_owned_invitation(
            db, invitation_id, supplier_organization_id=organization_id
        )
        if invitation.status == "INVITED":
            await _transition(
                db,
                invitation,
                to_status="VIEWED",
                actor_id=user_id,
                reason="Invitación vista",
            )
            await invitations_repo.update_invitation(
                invitation, viewed_at=datetime.now(timezone.utc)
            )
        history = await invitations_repo.list_status_history(db, invitation.id)
        return {
            "id": invitation.id,
            "sourcing_event_id": invitation.sourcing_event_id,
            "status": invitation.status,
            "source": invitation.source,
            "invited_at": invitation.invited_at,
            "viewed_at": invitation.viewed_at,
            "responded_at": invitation.responded_at,
            "decline_reason_code": invitation.decline_reason_code,
            "history": [
                {
                    "from_status": h.from_status,
                    "to_status": h.to_status,
                    "reason": h.reason,
                    "created_at": h.created_at,
                }
                for h in history
            ],
        }


async def accept_nda(
    *,
    user_id: UUID,
    organization_id: UUID,
    invitation_id: UUID,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    async with session_for_user(user_id) as db:
        invitation = await _get_owned_invitation(
            db, invitation_id, supplier_organization_id=organization_id
        )
        nda = await invitations_repo.get_current_nda(db, invitation.sourcing_event_id)
        if nda is None:
            raise InvitationValidationError("Este evento no tiene NDA configurado")

        existing = await invitations_repo.get_acceptance(db, nda.id, organization_id)
        if existing is None:
            await invitations_repo.create_acceptance(
                db,
                nda_id=nda.id,
                organization_id=organization_id,
                accepted_by=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                checksum_sha256=nda.checksum_sha256,
            )
        await _transition(
            db,
            invitation,
            to_status="NDA_ACCEPTED",
            actor_id=user_id,
            reason="NDA aceptado",
        )


async def express_interest(
    *, user_id: UUID, organization_id: UUID, invitation_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        invitation = await _get_owned_invitation(
            db, invitation_id, supplier_organization_id=organization_id
        )
        event = await sourcing_repo.get_event(db, invitation.sourcing_event_id)
        if event is not None and event.requires_nda and invitation.status == "VIEWED":
            # sourcing_event_invitation_transitions permite VIEWED→INTERESTED
            # de forma estructural (para eventos sin NDA) — la tabla no sabe
            # de requires_nda, así que este chequeo va acá, no en la tabla de
            # transiciones. Encontrado en vivo por
            # tests/test_invitations.py::test_nda_required_before_participation.
            raise InvitationValidationError(
                "Este evento exige aceptar el NDA antes de confirmar interés"
            )
        await invitations_repo.update_invitation(
            invitation, responded_at=datetime.now(timezone.utc)
        )
        await _transition(
            db,
            invitation,
            to_status="INTERESTED",
            actor_id=user_id,
            reason="Interés confirmado",
        )


async def confirm_participation(
    *, user_id: UUID, organization_id: UUID, invitation_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        invitation = await _get_owned_invitation(
            db, invitation_id, supplier_organization_id=organization_id
        )
        await _transition(
            db,
            invitation,
            to_status="PARTICIPATING",
            actor_id=user_id,
            reason="Participación confirmada",
        )


async def decline(
    *,
    user_id: UUID,
    organization_id: UUID,
    invitation_id: UUID,
    reason_code: str | None = None,
) -> None:
    async with session_for_user(user_id) as db:
        invitation = await _get_owned_invitation(
            db, invitation_id, supplier_organization_id=organization_id
        )
        await invitations_repo.update_invitation(
            invitation,
            decline_reason_code=reason_code,
            responded_at=datetime.now(timezone.utc),
        )
        await _transition(
            db, invitation, to_status="DECLINED", actor_id=user_id, reason=reason_code
        )


async def withdraw(
    *, user_id: UUID, organization_id: UUID, invitation_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        invitation = await _get_owned_invitation(
            db, invitation_id, supplier_organization_id=organization_id
        )
        await _transition(
            db,
            invitation,
            to_status="WITHDRAWN",
            actor_id=user_id,
            reason="Proveedor se retiró",
        )


# ─── Cruce con services/quotations.py (misma transacción ya abierta) ─────────


async def mark_quoted(db, *, invitation_id: UUID, actor_id: UUID | None) -> None:
    """Se llama desde services/quotations.py al insertar la primera revisión
    enviada. Idempotente: si ya está QUOTED, no hace nada."""
    invitation = await invitations_repo.get_invitation(db, invitation_id)
    if invitation is None or invitation.status == "QUOTED":
        return
    await _transition(
        db,
        invitation,
        to_status="QUOTED",
        actor_id=actor_id,
        reason="Cotización enviada",
    )
