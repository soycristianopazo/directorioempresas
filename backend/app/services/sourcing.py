"""El proceso de sourcing: sourcing_events y su estructura (fase 6.2/6.3).

Backstop grueso en RLS (cualquiera de los permisos de sourcing_event toca la
fila); acá se decide CUÁL hace falta para CADA acción — create para
crear/editar mientras está en DRAFT (mismo criterio que offering.write cubrió
create+edit en fase 3), publish/cancel para sus transiciones específicas.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.db.rls import gather_for_user, session_for_user
from app.repositories import accreditation as accreditation_repo
from app.repositories import awards as awards_repo
from app.repositories import invitations as invitations_repo
from app.repositories import requirements as requirements_repo
from app.repositories import sourcing as sourcing_repo
from app.services import entitlements as entitlements_service
from app.services import invitations as invitations_service
from app.services import notifications as notifications_service

PERM_READ = "sourcing_event.read"
PERM_CREATE = "sourcing_event.create"
PERM_PUBLISH = "sourcing_event.publish"
PERM_CANCEL = "sourcing_event.cancel"


class SourcingError(Exception):
    pass


class SourcingPermissionError(SourcingError):
    pass


class SourcingNotFoundError(SourcingError):
    pass


class SourcingValidationError(SourcingError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await sourcing_repo.has_permission(db, organization_id, permission):
        raise SourcingPermissionError(f"Sin permiso ({permission}) para esta acción")


async def _get_owned_event(db, event_id: UUID, organization_id: UUID):
    event = await sourcing_repo.get_event(db, event_id)
    if event is None or event.organization_id != organization_id:
        raise SourcingNotFoundError("Evento no encontrado")
    return event


async def _validate_accreditation_program(
    db, organization_id: UUID, program_id: object
) -> None:
    """requires_accreditation_program_id/accreditation_program_id era hasta
    ahora una FK completamente libre: cualquier comprador podía exigir el
    programa PRIVADO (owner_scope=ORGANIZATION) de OTRO comprador al crear
    un evento o un criterio, sin ninguna validación — hueco real, no solo
    teórico, desde que fase 9 permite crear programas propios."""
    if program_id is None:
        return
    assert isinstance(program_id, UUID)
    program = await accreditation_repo.get_program(db, program_id)
    if program is None:
        raise SourcingNotFoundError("Programa de acreditación no encontrado")
    if (
        program.owner_scope == "ORGANIZATION"
        and program.owner_organization_id != organization_id
    ):
        raise SourcingValidationError(
            "No se puede exigir un programa de acreditación de otra organización"
        )


async def list_events_with_stage(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await sourcing_repo.list_events_with_stage(db, organization_id)


async def get_event_detail(
    *, user_id: UUID, organization_id: UUID, event_id: UUID
) -> dict:
    """A diferencia de `_get_owned_event` (usado por las mutaciones, siempre
    estrictamente del comprador dueño), esta lectura también debe servir al
    proveedor invitado — fase 7 (0048_fase7_rls_invitations_qa_ndas.sql ya le
    da a RLS una rama adicional para eso, `has_active_sourcing_invitation`).
    Encontrado en vivo: `_get_owned_event` rechazaba con 404 a un proveedor
    con invitación activa real, porque comparaba
    `event.organization_id != organization_id` sin contemplar que
    `organization_id` acá puede ser la organización PROVEEDORA, no la
    compradora. La sesión ya está fijada por usuario (`session_for_user`), así
    que si `get_event` devuelve una fila, es porque RLS ya decidió que este
    usuario puede verla — por cualquiera de las dos ramas — no hace falta
    repetir esa decisión en Python. El chequeo de `sourcing_event.read` solo
    aplica cuando quien pregunta ES el comprador dueño; para el proveedor,
    RLS ya es la única puerta."""
    # Las seis lecturas solo necesitan `event_id`, ya conocido — ninguna
    # depende del resultado de otra — así que van en paralelo en vez de
    # encadenadas.
    event, lots, items, stages, documents, criteria = await gather_for_user(
        user_id,
        lambda db: sourcing_repo.get_event(db, event_id),
        lambda db: sourcing_repo.list_lots(db, event_id),
        lambda db: sourcing_repo.list_items(db, event_id),
        lambda db: sourcing_repo.list_stages(db, event_id),
        lambda db: sourcing_repo.list_documents(db, event_id),
        lambda db: sourcing_repo.list_criteria(db, event_id),
    )
    if event is None:
        raise SourcingNotFoundError("Evento no encontrado")
    if event.organization_id == organization_id:
        async with session_for_user(user_id) as db:
            await _require(db, organization_id, PERM_READ)
    return {
        "event": event,
        "lots": lots,
        "items": items,
        "stages": stages,
        "documents": documents,
        "criteria": criteria,
    }


async def create_event(
    *,
    user_id: UUID,
    organization_id: UUID,
    name: str,
    event_type: str = "RFQ",
    requirement_id: UUID | None = None,
    **fields: object,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await entitlements_service.assert_entitlement(
            organization_id, "sourcing_event.create"
        )
        await _validate_accreditation_program(
            db, organization_id, fields.get("requires_accreditation_program_id")
        )

        requirement = None
        if requirement_id is not None:
            requirement = await requirements_repo.get_requirement(db, requirement_id)
            if requirement is None or requirement.organization_id != organization_id:
                raise SourcingNotFoundError("Necesidad no encontrada")

        event_code = await sourcing_repo.next_event_code(
            db, event_type=event_type, year=datetime.now(timezone.utc).year
        )
        event = await sourcing_repo.create_event(
            db,
            organization_id=organization_id,
            requirement_id=requirement_id,
            name=name,
            event_type=event_type,
            event_code=event_code,
            **fields,
        )
        if requirement is not None:
            await requirements_repo.update_requirement(requirement, status="CONVERTED")
        event_id = event.id
    return event_id


async def update_event(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        event = await _get_owned_event(db, event_id, organization_id)
        if event.status != "DRAFT":
            raise SourcingValidationError("Solo se puede editar un evento en borrador")
        await _validate_accreditation_program(
            db, organization_id, fields.get("requires_accreditation_program_id")
        )
        await sourcing_repo.update_event(event, **fields)


async def publish_event(
    *, user_id: UUID, organization_id: UUID, event_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_PUBLISH)
        event = await _get_owned_event(db, event_id, organization_id)
        if event.status != "DRAFT":
            raise SourcingValidationError(
                "Solo un evento en borrador se puede publicar"
            )
        items = await sourcing_repo.list_items(db, event_id)
        if not items:
            raise SourcingValidationError(
                "El evento necesita al menos una línea antes de publicarse"
            )
        await sourcing_repo.update_event(
            event, status="PUBLISHED", published_at=datetime.now(timezone.utc)
        )


async def cancel_event(*, user_id: UUID, organization_id: UUID, event_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CANCEL)
        event = await _get_owned_event(db, event_id, organization_id)
        if event.status == "CANCELLED":
            raise SourcingValidationError("El evento ya está cancelado")
        await sourcing_repo.update_event(event, status="CANCELLED")


async def declare_void(
    *,
    user_id: UUID,
    organization_id: UUID,
    event_id: UUID,
    reason: str | None = None,
) -> None:
    """"Desierta": el comprador decide a mano que ninguna cotización calificó.

    Sin corredor de tareas programadas en el backend, un plazo vencido no
    puede disparar esto solo — es siempre una acción explícita del comprador,
    solo válida mientras el evento sigue PUBLISHED (una vez que
    close_event() lo saca de ahí hacia AWARDED/CLOSED, declarar desierta ya
    no tiene sentido; reusa PERM_CANCEL, mismo gesto de "terminar el proceso
    sin adjudicar" que cancelar).
    """
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CANCEL)
        event = await _get_owned_event(db, event_id, organization_id)
        if event.status != "PUBLISHED":
            raise SourcingValidationError(
                "Solo un evento publicado se puede declarar desierto"
            )
        await sourcing_repo.update_event(
            event, status="VOID", void_reason=reason or None
        )


async def add_lot(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        lot = await sourcing_repo.add_lot(db, sourcing_event_id=event_id, **fields)
        lot_id = lot.id
    return lot_id


async def add_item(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        item = await sourcing_repo.add_item(db, sourcing_event_id=event_id, **fields)
        item_id = item.id
    return item_id


async def upsert_stage(
    *,
    user_id: UUID,
    organization_id: UUID,
    event_id: UUID,
    stage_type: str,
    **fields: object,
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        stage = await sourcing_repo.upsert_stage(
            db, event_id=event_id, stage_type=stage_type, **fields
        )
        stage_id = stage.id
    return stage_id


async def add_criterion(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, **fields: object
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        await _validate_accreditation_program(
            db, organization_id, fields.get("accreditation_program_id")
        )
        criterion = await sourcing_repo.add_criterion(
            db, sourcing_event_id=event_id, **fields
        )
        criterion_id = criterion.id
    return criterion_id


async def delete_criterion(
    *, user_id: UUID, organization_id: UUID, event_id: UUID, criterion_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_CREATE)
        await _get_owned_event(db, event_id, organization_id)
        criterion = await sourcing_repo.get_criterion(db, criterion_id)
        if criterion is None or criterion.sourcing_event_id != event_id:
            raise SourcingNotFoundError("Criterio no encontrado")
        await sourcing_repo.delete_criterion(db, criterion_id)


# ─── Cierre del evento tras adjudicación (fase 8.7) ──────────────────────────

_INVITATION_TERMINAL = {
    "WITHDRAWN",
    "DISQUALIFIED",
    "EXPIRED",
    "DECLINED",
    "NO_RESPONSE",
    "AWARDED",
    "NOT_AWARDED",
}
_INVITATION_QUOTED_LIKE = {"QUOTED", "SHORTLISTED", "NEGOTIATING"}
_INVITATION_EARLY = {"INVITED", "VIEWED", "NDA_ACCEPTED", "INTERESTED"}


async def close_event(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> None:
    """Llamado por `services/awards.py::publish_award()` justo después de
    publicar un award — nunca directamente por un router, así que no repite
    el chequeo de permiso (`publish_award` ya validó `award.create` sobre
    esta misma organización antes de llamar acá).

    Transiciona `sourcing_events.status` a AWARDED (si hay algún award
    PUBLISHED para el evento) y luego a CLOSED — dos `update_event` con un
    `flush` intermedio para que la primera transición quede realmente escrita,
    no solo pisada en memoria por la segunda antes del commit.

    Para las invitaciones no terminales: las que llegaron a cotizar
    (QUOTED/SHORTLISTED/NEGOTIATING, agregado por 0065/0066) pasan a AWARDED
    si su organización ganó algún award PUBLISHED de este evento, NOT_AWARDED
    si no. Las que nunca llegaron a cotizar (INVITED/VIEWED/NDA_ACCEPTED/
    INTERESTED) pasan a EXPIRED — la transición ya existente en 0044 para
    "evento cerrado sin respuesta", que es exactamente su caso. PARTICIPATING
    (confirmó participar pero nunca envió cotización) no tiene ninguna
    transición válida hacia un estado de cierre en
    sourcing_event_invitation_transitions (ni en 0044 ni en 0066 se agregó
    una) — se deja tal cual en vez de forzar una transición inexistente, que
    rompería el principio de "transición-como-dato" de este módulo (ver
    services/invitations.py). Terminales ya (WITHDRAWN/DISQUALIFIED/EXPIRED/
    DECLINED/NO_RESPONSE) o ya decididas (AWARDED/NOT_AWARDED) se ignoran —
    idempotente si se llama más de una vez para el mismo evento.
    """
    notify_targets: list[tuple[UUID, bool]] = []

    async with session_for_user(user_id) as db:
        event = await _get_owned_event(db, sourcing_event_id, organization_id)

        event_awards = await awards_repo.list_awards_for_event(db, sourcing_event_id)
        published_awards = [a for a in event_awards if a.status == "PUBLISHED"]
        winners = {a.awarded_organization_id for a in published_awards}

        if published_awards:
            await sourcing_repo.update_event(event, status="AWARDED")
            await db.flush()
        await sourcing_repo.update_event(event, status="CLOSED")

        invitations = await invitations_repo.list_for_event(db, sourcing_event_id)
        for invitation in invitations:
            if invitation.status in _INVITATION_TERMINAL:
                continue
            if invitation.status in _INVITATION_QUOTED_LIKE:
                won = invitation.supplier_organization_id in winners
                target = "AWARDED" if won else "NOT_AWARDED"
                reason = "Adjudicado" if won else "Evento adjudicado a otro proveedor"
            elif invitation.status in _INVITATION_EARLY:
                won = False
                target = "EXPIRED"
                reason = "Evento cerrado sin respuesta"
            else:
                # PARTICIPATING sin cotización: sin transición válida, se deja.
                continue
            await invitations_service._transition(
                db, invitation, to_status=target, actor_id=user_id, reason=reason
            )
            notify_targets.append((invitation.supplier_organization_id, won))

    def _notify(supplier_org_id: UUID, won: bool):
        if won:
            return notifications_service.notify_org(
                organization_id=supplier_org_id,
                type="award.won",
                title="Fuiste adjudicado",
                body="Tu oferta fue adjudicada en un proceso de sourcing.",
                entity_type="sourcing_event",
                entity_id=sourcing_event_id,
                action_url=f"/empresa/sourcing/{sourcing_event_id}",
            )
        return notifications_service.notify_org(
            organization_id=supplier_org_id,
            type="award.lost",
            title="Proceso adjudicado a otro proveedor",
            body="El proceso de sourcing en el que participaste fue adjudicado a otro proveedor.",
            entity_type="sourcing_event",
            entity_id=sourcing_event_id,
            action_url=f"/empresa/sourcing/{sourcing_event_id}",
        )

    # En paralelo, no secuencial: cada notify_org() abre su propia
    # session_for_system() independiente (mismo criterio que el resto del
    # proyecto — notificar es un efecto de sistema, no comparte transacción
    # con nadie), así que no hay estado compartido que proteja un await
    # secuencial. Encontrado en vivo: con solo 2 destinatarios, la cadena
    # secuencial (open_bids ya tenía este mismo patrón, pero para un único
    # llamado) sumada al resto de close_event superaba el timeout de 15s del
    # cliente HTTP — el award se publicaba igual (era solo el aviso al
    # navegador el que llegaba tarde), pero el usuario veía un error donde no
    # lo había.
    if notify_targets:
        await asyncio.gather(
            *(_notify(supplier_org_id, won) for supplier_org_id, won in notify_targets)
        )
