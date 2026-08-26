"""Adjudicación: políticas de aprobación, propuesta, decisión y publicación
de awards (fase 8.6/8.7).

Mecanismo de dos capas de `propose_award` (plan de fase 8, Decisión de este
módulo): las políticas de la organización cuyo rango [min_amount, max_amount)
cubre `amount_base` deciden CUÁNTOS pasos hacen falta; por cada paso,
`awards_repo.find_eligible_approver` resuelve el miembro CONCRETO (rol +
límite de aprobación suficiente, el de menor límite que igual alcanza). Cero
políticas aplicables = sin burocracia forzada, el award queda APPROVED de
inmediato. Si una política aplica pero ningún miembro con ese rol tiene
límite suficiente, se falla alto (AwardValidationError) en vez de crear una
aprobación irresoluble.

`decide()` duplica en Python el chequeo de autoservicio que RLS ya exige en
0063 (award_approvals_decide) — mismo criterio que el resto del proyecto
(evaluations, invitations): RLS es el backstop real, Python da un mensaje de
error legible antes de que la base rechace la fila.

`publish_award()` termina llamando a `services/sourcing.py::close_event()`
DESPUÉS de cerrar su propio bloque `session_for_user` — mismo patrón que
`quotations.py::open_bids()`: mutar y salir de la transacción, notificar (acá,
además, cerrar el evento) después.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from app.db.rls import gather_for_user, session_for_user
from app.repositories import awards as awards_repo
from app.repositories import members as members_repo
from app.repositories import quotations as quotations_repo
from app.repositories import sourcing as sourcing_repo
from app.services import fx as fx_service
from app.services import notifications as notifications_service
from app.services import sourcing as sourcing_service

PERM_CREATE = "award.create"
PERM_APPROVE = "award.approve"


class AwardError(Exception):
    pass


class AwardPermissionError(AwardError):
    pass


class AwardNotFoundError(AwardError):
    pass


class AwardValidationError(AwardError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await awards_repo.has_permission(db, organization_id, permission):
        raise AwardPermissionError(f"Sin permiso ({permission}) para esta acción")


async def _require_read(db, organization_id: UUID) -> None:
    if not (
        await awards_repo.has_permission(db, organization_id, PERM_CREATE)
        or await awards_repo.has_permission(db, organization_id, PERM_APPROVE)
    ):
        raise AwardPermissionError("Sin permiso para ver adjudicaciones")


# ─── Awards ─────────────────────────────────────────────────────────────────


async def list_awards(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> list:
    async with session_for_user(user_id) as db:
        await _require_read(db, organization_id)
        return await awards_repo.list_awards_for_event(db, sourcing_event_id)


async def propose_award(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    awarded_organization_id: UUID,
    quotation_revision_id: UUID,
    justification: str | None,
    items: list[dict],
) -> UUID:
    if not items:
        raise AwardValidationError("El award necesita al menos una línea")

    approver_user_ids: list[UUID] = []

    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)

    # Las cuatro solo necesitan sourcing_event_id/quotation_revision_id, ya
    # conocidos — ninguna depende del resultado de otra — van en paralelo.
    event, revision, event_items, quotation_items = await gather_for_user(
        user_id,
        lambda db: sourcing_repo.get_event(db, sourcing_event_id),
        lambda db: quotations_repo.get_revision(db, quotation_revision_id),
        lambda db: sourcing_repo.list_items(db, sourcing_event_id),
        lambda db: quotations_repo.list_items(db, quotation_revision_id),
    )
    if event is None or event.organization_id != organization_id:
        raise AwardNotFoundError("Evento no encontrado")
    if event.status == "CANCELLED":
        raise AwardValidationError("No se puede adjudicar un evento cancelado")
    if revision is None:
        raise AwardNotFoundError("Revisión de cotización no encontrada")

    valid_item_ids = {i.id for i in event_items}
    quotation_items_by_event_item = {
        qi.sourcing_event_item_id: qi for qi in quotation_items
    }

    async with session_for_user(user_id) as db:
        quotation = await quotations_repo.get_quotation(db, revision.quotation_id)
        if (
            quotation is None
            or quotation.sourcing_event_id != sourcing_event_id
            or quotation.supplier_organization_id != awarded_organization_id
        ):
            raise AwardValidationError(
                "La revisión no corresponde a una cotización de ese proveedor en este evento"
            )

        prepared_items = []
        amount = 0.0
        for item in items:
            event_item_id = item["sourcing_event_item_id"]
            if event_item_id not in valid_item_ids:
                raise AwardValidationError("Una línea no corresponde a este evento")
            quantity = float(item["quantity"])
            unit_price = float(item["unit_price"])
            if quantity <= 0 or unit_price < 0:
                raise AwardValidationError("Cantidad y precio unitario inválidos")
            line_total = round(quantity * unit_price, 2)
            amount += line_total
            matched = quotation_items_by_event_item.get(event_item_id)
            prepared_items.append(
                {
                    "sourcing_event_item_id": event_item_id,
                    "quotation_item_id": matched.id if matched is not None else None,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                }
            )
        amount = round(amount, 2)

        currency_code = revision.currency_code
        base_currency = event.currency_code or "CLP"
        try:
            amount_base, _fx_rate = await fx_service.to_base_amount(
                db,
                amount=amount,
                currency_code=currency_code,
                on_date=date.today(),
                base_currency_code=base_currency,
            )
        except fx_service.FxRateNotFoundError as exc:
            raise AwardValidationError(str(exc)) from exc

        award = await awards_repo.create_award(
            db,
            sourcing_event_id=sourcing_event_id,
            awarded_organization_id=awarded_organization_id,
            quotation_revision_id=quotation_revision_id,
            justification=justification,
            currency_code=currency_code,
            amount=amount,
            amount_base=amount_base,
            proposed_by=user_id,
        )
        for prepared in prepared_items:
            await awards_repo.add_award_item(db, award_id=award.id, **prepared)

        policies = await awards_repo.list_policies(db, organization_id)
        applicable = sorted(
            (
                p
                for p in policies
                if float(p.min_amount) <= amount_base
                and (p.max_amount is None or amount_base < float(p.max_amount))
            ),
            key=lambda p: p.step_order,
        )

        if not applicable:
            # Sin políticas configuradas para este rango: no forzar burocracia
            # donde la organización no la pidió.
            await awards_repo.update_award(
                award, status="APPROVED", decided_at=datetime.now(timezone.utc)
            )
        else:
            for policy in applicable:
                approver = await awards_repo.find_eligible_approver(
                    db, organization_id, policy.required_role_code, amount_base
                )
                if approver is None:
                    raise AwardValidationError(
                        f"No hay ningún miembro con rol {policy.required_role_code} "
                        "y límite de aprobación suficiente para este monto"
                    )
                await awards_repo.create_approval_step(
                    db,
                    award_id=award.id,
                    step_order=policy.step_order,
                    required_role_code=policy.required_role_code,
                    approver_member_id=approver.id,
                )
                approver_user_ids.append(approver.user_id)
            await awards_repo.update_award(award, status="PENDING_APPROVAL")

        award_id = award.id

    if approver_user_ids:
        await notifications_service.notify_org(
            organization_id=organization_id,
            type="award.approval_pending",
            title="Adjudicación pendiente de tu aprobación",
            body="Hay una propuesta de adjudicación esperando tu aprobación.",
            entity_type="award",
            entity_id=award_id,
            action_url=f"/empresa/sourcing/{sourcing_event_id}/adjudicacion",
        )
    return award_id


async def decide(
    *,
    user_id: UUID,
    organization_id: UUID,
    approval_id: UUID,
    decision: str,
    comment: str | None = None,
) -> None:
    if decision not in ("APPROVED", "REJECTED"):
        raise AwardValidationError("decision debe ser APPROVED o REJECTED")

    async with session_for_user(user_id) as db:
        # `approval` se muta más abajo (update_approval) y necesita quedar
        # atado a ESTA sesión para que el cambio se persista al comitear —
        # por eso se trae acá y no en una conexión paralela aparte.
        approval = await awards_repo.get_approval(db, approval_id)
        if approval is None:
            raise AwardNotFoundError("Aprobación no encontrada")

        member = await members_repo.get_membership(
            db, user_id=user_id, organization_id=organization_id
        )
        if member is None or approval.approver_member_id != member.id:
            # Defensa extra además de RLS (0063 award_approvals_decide):
            # nadie decide el paso de otro.
            raise AwardPermissionError("Esta aprobación no te corresponde")
        if approval.status != "PENDING":
            raise AwardValidationError("Esta aprobación ya fue decidida")

        award = await awards_repo.get_award(db, approval.award_id)
        if award is None or award.status != "PENDING_APPROVAL":
            raise AwardValidationError("Este award ya no está pendiente de aprobación")

        now = datetime.now(timezone.utc)
        await awards_repo.update_approval(
            approval, status=decision, decided_at=now, comment=comment
        )

        if decision == "REJECTED":
            # Un rechazo en cualquier paso mata el award; no sigue a los
            # demás pasos pendientes.
            await awards_repo.update_award(award, status="REJECTED", decided_at=now)
        else:
            remaining = await awards_repo.list_approvals_for_award(db, award.id)
            still_pending = [
                a for a in remaining if a.id != approval.id and a.status == "PENDING"
            ]
            if not still_pending:
                await awards_repo.update_award(award, status="APPROVED", decided_at=now)


async def list_my_pending_approvals(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        member = await members_repo.get_membership(
            db, user_id=user_id, organization_id=organization_id
        )
        if member is None:
            raise AwardPermissionError("No pertenece a esta organización")
        return await awards_repo.list_pending_approvals_for_member(db, member.id)


async def publish_award(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID, award_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)

        event = await sourcing_repo.get_event(db, sourcing_event_id)
        if event is None or event.organization_id != organization_id:
            raise AwardNotFoundError("Evento no encontrado")

        award = await awards_repo.get_award(db, award_id)
        if award is None or award.sourcing_event_id != sourcing_event_id:
            raise AwardNotFoundError("Award no encontrado")
        if award.status != "APPROVED":
            raise AwardValidationError("Solo se puede publicar un award aprobado")

        now = datetime.now(timezone.utc)
        await awards_repo.update_award(
            award, status="PUBLISHED", published_at=now, published_by=user_id
        )

    await sourcing_service.close_event(
        user_id=user_id,
        organization_id=organization_id,
        sourcing_event_id=sourcing_event_id,
    )


# ─── Políticas de aprobación (CRUD simple) ───────────────────────────────────


async def list_policies(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        return await awards_repo.list_policies(db, organization_id)


async def upsert_policy(
    *,
    user_id: UUID,
    organization_id: UUID,
    step_order: int,
    required_role_code: str,
    min_amount: float = 0,
    max_amount: float | None = None,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        existing = next(
            (
                p
                for p in await awards_repo.list_policies(db, organization_id)
                if p.step_order == step_order
            ),
            None,
        )
        if existing is not None:
            await awards_repo.update_policy(
                existing,
                required_role_code=required_role_code,
                min_amount=min_amount,
                max_amount=max_amount,
            )
            policy_id = existing.id
        else:
            policy = await awards_repo.create_policy(
                db,
                organization_id=organization_id,
                step_order=step_order,
                required_role_code=required_role_code,
                min_amount=min_amount,
                max_amount=max_amount,
            )
            policy_id = policy.id
    return policy_id
