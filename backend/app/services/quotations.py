"""Cotizaciones: envío de revisiones, ceremonia de apertura (fase 7.5/7.6/7.7).

Cada revisión es append-only (revoke update, delete en la base) — nunca se
corrige una ya enviada, se envía una nueva (round_number incremental). Se
permite reenviar la ronda INITIAL varias veces antes del deadline (plan de
fase 7, decisión 1): la sellabilidad no depende de esto, nadie ve nada antes
de bid_opened_at sin importar cuántas veces el proveedor corrigió su precio.
quotations.current_revision_id es el puntero autoritativo a la vigente,
actualizado en la misma transacción del INSERT — quotation_revisions.is_current
es documental, nunca se lee para saber cuál es la vigente.

fx.to_base_amount() convierte cada envío a la moneda del propio evento — así
el comprador compara cotizaciones de distintos proveedores en una sola
moneda (services/fx.py, primer consumidor real de fx_rates).
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.core.file_validation import matches_pdf
from app.core.storage import StorageError, create_signed_url, upload_object
from app.db.rls import gather_for_user, session_for_user
from app.repositories import invitations as invitations_repo
from app.repositories import quotations as quotations_repo
from app.repositories import sourcing as sourcing_repo
from app.services import fx as fx_service
from app.services import invitations as invitations_service
from app.services import notifications as notifications_service

PERM_READ = "quotation.read"
PERM_WRITE = "quotation.write"
PERM_OPEN_BIDS = "sourcing_event.open_bids"

DOCUMENTS_BUCKET = "org-documents"
_MAX_DOCUMENT_BYTES = 20 * 1024 * 1024

_PARTICIPATING_STATUSES = ("INTERESTED", "PARTICIPATING", "QUOTED", "NEGOTIATING")


class QuotationError(Exception):
    pass


class QuotationPermissionError(QuotationError):
    pass


class QuotationNotFoundError(QuotationError):
    pass


class QuotationValidationError(QuotationError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await quotations_repo.has_permission(db, organization_id, permission):
        raise QuotationPermissionError(f"Sin permiso ({permission}) para esta acción")


# ─── Lado comprador ───────────────────────────────────────────────────────────


async def list_quotations(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
):
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await quotations_repo.list_for_event(db, sourcing_event_id)


async def open_bids(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_OPEN_BIDS)
        event = await sourcing_repo.get_event(db, sourcing_event_id)
        if event is None:
            raise QuotationNotFoundError("Evento no encontrado")
        if event.bid_opened_at is not None:
            raise QuotationValidationError(
                "Las ofertas de este evento ya fueron abiertas"
            )
        deadline = await quotations_repo.get_bid_deadline(db, sourcing_event_id)
        if deadline is not None and datetime.now(timezone.utc) < deadline:
            raise QuotationValidationError(
                "No se puede abrir antes del cierre de ofertas"
            )
        await sourcing_repo.update_event(
            event, bid_opened_at=datetime.now(timezone.utc), bid_opened_by=user_id
        )
        invitations = await invitations_repo.list_for_event(db, sourcing_event_id)
        recipients = [
            i.supplier_organization_id for i in invitations if i.status == "QUOTED"
        ]

    for org_id in recipients:
        await notifications_service.notify_org(
            organization_id=org_id,
            type="quotation.bids_opened",
            title="Se abrieron las ofertas",
            body="El comprador abrió las ofertas del proceso al que participaste.",
            entity_type="sourcing_event",
            entity_id=sourcing_event_id,
            action_url=f"/empresa/sourcing/{sourcing_event_id}",
        )


# ─── Lado proveedor ───────────────────────────────────────────────────────────


async def submit_revision(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
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
    round_type: str = "INITIAL",
) -> UUID:
    """round_type parametrizable (antes hardcodeado a INITIAL) para que
    services/negotiations.py::submit_counter() reutilice este mismo flujo de
    envío para rondas COUNTER/BAFO (fase 8.5) — la policy de INSERT de
    quotation_revisions (0061) es quien decide si la ronda vigente autoriza
    el envío, este service solo valida el conjunto de valores conocido."""
    if round_type not in ("INITIAL", "COUNTER", "BAFO"):
        raise QuotationValidationError(f"round_type inválido: {round_type}")
    if total_amount < 0:
        raise QuotationValidationError("El monto total no puede ser negativo")
    if not items:
        raise QuotationValidationError("La cotización necesita al menos una línea")

    async def _bid_deadline(db):
        # round_type COUNTER/BAFO: el deadline relevante es el de la ronda de
        # negociación (negotiation_rounds.deadline), no el BID_DEADLINE del
        # evento — la policy de RLS (0061) ya lo exige antes de aceptar el
        # INSERT, así que un envío tardío falla ahí, no acá.
        if round_type == "INITIAL":
            return await quotations_repo.get_bid_deadline(db, sourcing_event_id)
        return None

    # Las cuatro solo necesitan sourcing_event_id/organization_id, ya
    # conocidos — ninguna depende del resultado de otra — van en paralelo.
    invitation, deadline, event, event_items = await gather_for_user(
        user_id,
        lambda db: invitations_repo.get_by_event_and_supplier(
            db, sourcing_event_id, organization_id
        ),
        _bid_deadline,
        lambda db: sourcing_repo.get_event(db, sourcing_event_id),
        lambda db: sourcing_repo.list_items(db, sourcing_event_id),
    )
    if invitation is None or invitation.status not in _PARTICIPATING_STATUSES:
        raise QuotationPermissionError(
            "Esta organización no tiene una invitación activa para cotizar en este evento"
        )
    if (
        round_type == "INITIAL"
        and deadline is not None
        and datetime.now(timezone.utc) > deadline
    ):
        raise QuotationValidationError("El plazo para cotizar ya venció")
    if event is None:
        raise QuotationNotFoundError("Evento no encontrado")

    valid_item_ids = {i.id for i in event_items}
    for item in items:
        if item["sourcing_event_item_id"] not in valid_item_ids:
            raise QuotationValidationError("Una línea no corresponde a este evento")

    async with session_for_user(user_id) as db:
        quotation = await quotations_repo.get_or_create(
            db,
            sourcing_event_id=sourcing_event_id,
            supplier_organization_id=organization_id,
            created_by=user_id,
        )

        base_currency = event.currency_code or "CLP"
        try:
            total_amount_base, fx_rate = await fx_service.to_base_amount(
                db,
                amount=total_amount,
                currency_code=currency_code,
                on_date=date.today(),
                base_currency_code=base_currency,
            )
        except fx_service.FxRateNotFoundError as exc:
            raise QuotationValidationError(str(exc)) from exc

        round_number = await quotations_repo.next_round_number(db, quotation.id)
        revision = await quotations_repo.create_revision(
            db,
            quotation_id=quotation.id,
            round_number=round_number,
            round_type=round_type,
            submitted_by=user_id,
            valid_until=valid_until,
            currency_code=currency_code,
            fx_rate_snapshot=fx_rate,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            total_amount_base=total_amount_base,
            payment_terms=payment_terms,
            delivery_days=delivery_days,
            warranty_terms=warranty_terms,
            exclusions=exclusions,
            notes=notes,
        )

        for item in items:
            quantity = float(item["quantity"])
            unit_price = float(item["unit_price"])
            discount_pct = float(item.get("discount_pct") or 0)
            line_total = round(quantity * unit_price * (1 - discount_pct / 100), 2)
            await quotations_repo.add_item(
                db,
                quotation_revision_id=revision.id,
                sourcing_event_item_id=item["sourcing_event_item_id"],
                quantity=quantity,
                unit_code=item.get("unit_code"),
                unit_price=unit_price,
                discount_pct=item.get("discount_pct"),
                tax_rate=item.get("tax_rate"),
                line_total=line_total,
                lead_time_days=item.get("lead_time_days"),
                brand=item.get("brand"),
                model=item.get("model"),
                notes=item.get("notes"),
            )

        for response in responses or []:
            await quotations_repo.add_response(
                db,
                quotation_revision_id=revision.id,
                sourcing_event_criterion_id=response["sourcing_event_criterion_id"],
                complies=response.get("complies"),
                value_text=response.get("value_text"),
                notes=response.get("notes"),
            )

        await quotations_repo.update_quotation(
            quotation,
            status="SUBMITTED",
            current_revision_id=revision.id,
            first_submitted_at=quotation.first_submitted_at
            or datetime.now(timezone.utc),
            updated_by=user_id,
        )
        await invitations_service.mark_quoted(
            db, invitation_id=invitation.id, actor_id=user_id
        )

        revision_id = revision.id
        buyer_organization_id = event.organization_id

    await notifications_service.notify_org(
        organization_id=buyer_organization_id,
        type="quotation.received",
        title="Nueva cotización recibida",
        body="Un proveedor envió (o actualizó) su cotización.",
        entity_type="sourcing_event",
        entity_id=sourcing_event_id,
        action_url=f"/empresa/sourcing/{sourcing_event_id}",
    )
    return revision_id


async def list_my_revisions(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> list:
    """Lectura pura — a diferencia de submit_revision(), nunca crea el
    contenedor. Antes llamaba a get_or_create() acá, lo que le daba a un
    simple listado el efecto secundario de crear una fila; para un llamador
    sin invitación en este evento (is_member_of falso), el SELECT interno de
    get_or_create ya venía vacío por RLS, pero el INSERT subsiguiente
    reventaba contra el UNIQUE (event, organización) si otra organización YA
    tenía una fila ahí — invisible por RLS, pero el índice único la ve igual.
    RLS bloqueaba el resultado en ambos casos (nunca hubo fuga de datos),
    pero el error crudo llegaba como 500 en vez de una lista vacía. Encontrado
    en vivo verificando el aislamiento del modo sellado por HTTP."""
    async with session_for_user(user_id) as db:
        quotation = await quotations_repo.get_by_event_and_supplier(
            db,
            sourcing_event_id=sourcing_event_id,
            supplier_organization_id=organization_id,
        )
        if quotation is None:
            return []
        return await quotations_repo.list_revisions(db, quotation.id)


async def upload_document(
    *,
    user_id: UUID,
    organization_id: UUID,
    quotation_revision_id: UUID,
    content: bytes,
    content_type: str,
    filename: str,
) -> dict:
    if content_type != "application/pdf":
        raise QuotationValidationError("Solo se aceptan documentos PDF por ahora")
    if len(content) > _MAX_DOCUMENT_BYTES:
        raise QuotationValidationError("El archivo supera el máximo de 20 MB")
    if not matches_pdf(content):
        raise QuotationValidationError(
            "El contenido del archivo no coincide con un PDF válido"
        )

    async with session_for_user(user_id) as db:
        revision = await quotations_repo.get_revision(db, quotation_revision_id)
        if revision is None:
            raise QuotationNotFoundError("Revisión no encontrada")
        quotation = await quotations_repo.get_quotation(db, revision.quotation_id)
        if quotation is None or quotation.supplier_organization_id != organization_id:
            raise QuotationPermissionError(
                "Esta revisión no pertenece a esta organización"
            )

        storage_path = f"{organization_id}/quotations/{quotation.id}/{revision.id}/{uuid4()}_{filename}"
        try:
            await upload_object(
                bucket=DOCUMENTS_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise QuotationError(str(exc)) from exc

        checksum = hashlib.sha256(content).hexdigest()
        document = await quotations_repo.add_document(
            db,
            quotation_revision_id=quotation_revision_id,
            name=filename,
            storage_path=storage_path,
            checksum_sha256=checksum,
            created_by=user_id,
        )
        document_id = document.id
        path = storage_path

    try:
        url = await create_signed_url(
            bucket=DOCUMENTS_BUCKET, path=path, expires_in=3600
        )
    except StorageError:
        url = None
    return {"id": document_id, "url": url}
