"""Preguntas y respuestas del evento de sourcing (fase 7.4).

Lado proveedor (preguntar): autoservicio, sin permiso de recurso — la policy
de INSERT de 0048 lo gatea con app.is_member_of() +
app.has_active_sourcing_invitation(). El service revalida la invitación antes
de insertar solo para devolver un mensaje de negocio legible en vez de la
violación de policy genérica (defensa 2, ver docs/RLS.md).

Lado comprador (responder/publicar): permiso 'sourcing_event.publish' — el
mismo que cubre publicar el evento e invitar proveedores (0048/0049 no
agregan un permiso nuevo para esto).

RLS ya resuelve qué preguntas/respuestas ve cada organización (quien
pregunta ve lo propio, el comprador ve todo, terceros invitados solo ven una
pregunta si tiene una respuesta ALL_PARTICIPANTS publicada) — list_questions
no vuelve a filtrar, solo devuelve lo que la consulta trae.
"""

from __future__ import annotations

from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import qa as qa_repo
from app.services import notifications as notifications_service

PERM_ANSWER = "sourcing_event.publish"

_VALID_VISIBILITIES = ("PRIVATE_TO_ASKER", "ALL_PARTICIPANTS")


class QaError(Exception):
    pass


class QaPermissionError(QaError):
    pass


class QaNotFoundError(QaError):
    pass


class QaValidationError(QaError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await qa_repo.has_permission(db, organization_id, permission):
        raise QaPermissionError(f"Sin permiso ({permission}) para esta acción")


async def list_questions(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        return await qa_repo.list_questions(db, sourcing_event_id)


async def ask_question(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID, body: str
) -> UUID:
    async with session_for_user(user_id) as db:
        if not await qa_repo.has_active_invitation(db, sourcing_event_id):
            raise QaPermissionError(
                "Solo un proveedor con invitación activa a este evento puede preguntar"
            )
        question_id = await qa_repo.create_question(
            db,
            sourcing_event_id=sourcing_event_id,
            asked_by_organization_id=organization_id,
            asked_by=user_id,
            body=body,
        )
    return question_id


async def answer_question(
    *,
    user_id: UUID,
    organization_id: UUID,
    question_id: UUID,
    body: str,
    visibility: str,
) -> None:
    if visibility not in _VALID_VISIBILITIES:
        raise QaValidationError("Visibilidad inválida")

    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_ANSWER)
        question = await qa_repo.get_question(db, question_id)
        if question is None:
            raise QaNotFoundError("Pregunta no encontrada")

        await qa_repo.upsert_answer(
            db,
            question_id=question_id,
            body=body,
            visibility=visibility,
            answered_by=user_id,
        )
        await qa_repo.mark_question_answered(db, question_id)


async def publish_answer(
    *, user_id: UUID, organization_id: UUID, question_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_ANSWER)
        question = await qa_repo.get_question(db, question_id)
        if question is None:
            raise QaNotFoundError("Pregunta no encontrada")

        answer, was_published_now = await qa_repo.publish_answer(db, question_id)
        if answer is None:
            raise QaNotFoundError("Esta pregunta todavía no tiene respuesta")

        sourcing_event_id = question["sourcing_event_id"]
        asking_org_id = question["asked_by_organization_id"]
        answer_body = answer["body"]

    if not was_published_now:
        # Idempotente: ya estaba publicada, no se reenvía la notificación.
        return

    # El asker siempre se entera, sea cual sea la visibilidad: anonimizar es
    # no exponer QUIÉN preguntó a LOS OTROS participantes, no ocultárselo al
    # propio asker (ver comentario de 0046_sourcing_qa.sql).
    await notifications_service.notify_org(
        organization_id=asking_org_id,
        type="qa.answered",
        title="Respondieron tu pregunta",
        body=answer_body[:100],
        entity_type="sourcing_event",
        entity_id=sourcing_event_id,
        action_url=f"/empresa/sourcing/{sourcing_event_id}",
    )
