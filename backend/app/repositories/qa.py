"""Acceso a datos de preguntas y respuestas del evento de sourcing (fase 7.4)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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


async def list_questions(session: AsyncSession, sourcing_event_id: UUID) -> list[dict]:
    """LEFT JOIN pregunta + su respuesta (si existe) — RLS ya filtra qué filas
    devuelve la consulta según quién pregunta, no hace falta filtrar de
    nuevo acá."""
    result = await session.execute(
        text(
            "select q.id, q.sourcing_event_id, q.asked_by_organization_id, "
            "       q.asked_by, q.body, q.is_answered, q.asked_at, "
            "       a.id as answer_id, a.body as answer_body, "
            "       a.visibility as answer_visibility, a.answered_by, "
            "       a.answered_at, a.published_at "
            "from public.sourcing_questions q "
            "left join public.sourcing_answers a on a.question_id = q.id "
            "where q.sourcing_event_id = :event_id "
            "order by q.asked_at"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    return [dict(row._mapping) for row in result]


async def create_question(
    session: AsyncSession,
    *,
    sourcing_event_id: UUID,
    asked_by_organization_id: UUID,
    asked_by: UUID,
    body: str,
) -> UUID:
    result = await session.execute(
        text(
            "insert into public.sourcing_questions "
            "(sourcing_event_id, asked_by_organization_id, asked_by, body) "
            "values (:sourcing_event_id, :asked_by_organization_id, :asked_by, :body) "
            "returning id"
        ),
        {
            "sourcing_event_id": str(sourcing_event_id),
            "asked_by_organization_id": str(asked_by_organization_id),
            "asked_by": str(asked_by),
            "body": body,
        },
    )
    return result.scalar_one()


async def get_question(session: AsyncSession, question_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            "select id, sourcing_event_id, asked_by_organization_id, asked_by, "
            "body, is_answered, asked_at "
            "from public.sourcing_questions where id = :id"
        ),
        {"id": str(question_id)},
    )
    row = result.first()
    return dict(row._mapping) if row is not None else None


async def get_answer(session: AsyncSession, question_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            "select id, question_id, body, visibility, answered_by, answered_at, "
            "published_at from public.sourcing_answers where question_id = :qid"
        ),
        {"qid": str(question_id)},
    )
    row = result.first()
    return dict(row._mapping) if row is not None else None


async def upsert_answer(
    session: AsyncSession,
    *,
    question_id: UUID,
    body: str,
    visibility: str,
    answered_by: UUID,
) -> None:
    await session.execute(
        text(
            "insert into public.sourcing_answers "
            "(question_id, body, visibility, answered_by, answered_at) "
            "values (:question_id, :body, :visibility, :answered_by, now()) "
            "on conflict (question_id) do update set "
            "body = excluded.body, visibility = excluded.visibility, "
            "answered_by = excluded.answered_by, answered_at = now()"
        ),
        {
            "question_id": str(question_id),
            "body": body,
            "visibility": visibility,
            "answered_by": str(answered_by),
        },
    )


async def mark_question_answered(session: AsyncSession, question_id: UUID) -> None:
    await session.execute(
        text("update public.sourcing_questions set is_answered = true where id = :id"),
        {"id": str(question_id)},
    )


async def publish_answer(
    session: AsyncSession, question_id: UUID
) -> tuple[dict | None, bool]:
    """Publica (published_at = now()) solo si todavía no lo estaba. Devuelve
    (fila de la respuesta, True) si esta llamada la publicó recién, o
    (fila existente, False) si ya estaba publicada o no hay respuesta aún."""
    result = await session.execute(
        text(
            "update public.sourcing_answers set published_at = now() "
            "where question_id = :qid and published_at is null "
            "returning id, question_id, body, visibility, answered_by, "
            "answered_at, published_at"
        ),
        {"qid": str(question_id)},
    )
    row = result.first()
    if row is not None:
        return dict(row._mapping), True
    return await get_answer(session, question_id), False
