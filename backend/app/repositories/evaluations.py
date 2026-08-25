"""Acceso a datos de plantillas, comité, evaluaciones, puntajes y comparador
(fase 8.1-8.4)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluations import (
    Evaluation,
    EvaluationAssignment,
    EvaluationCriterion,
    EvaluationScore,
    EvaluationTemplate,
    EventEvaluationSetup,
    QuotationComparison,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


# ─── Plantillas ─────────────────────────────────────────────────────────────


async def list_templates(
    session: AsyncSession, organization_id: UUID
) -> list[EvaluationTemplate]:
    result = await session.execute(
        select(EvaluationTemplate)
        .where(EvaluationTemplate.organization_id == organization_id)
        .order_by(EvaluationTemplate.created_at.desc())
    )
    return list(result.scalars())


async def get_template(
    session: AsyncSession, template_id: UUID
) -> EvaluationTemplate | None:
    result = await session.execute(
        select(EvaluationTemplate).where(EvaluationTemplate.id == template_id)
    )
    return result.scalar_one_or_none()


async def create_template(
    session: AsyncSession, **fields: object
) -> EvaluationTemplate:
    template = EvaluationTemplate(**fields)
    session.add(template)
    await session.flush()
    return template


async def list_criteria(
    session: AsyncSession, template_id: UUID
) -> list[EvaluationCriterion]:
    result = await session.execute(
        select(EvaluationCriterion)
        .where(EvaluationCriterion.template_id == template_id)
        .order_by(EvaluationCriterion.sort_order)
    )
    return list(result.scalars())


async def add_criterion(session: AsyncSession, **fields: object) -> EvaluationCriterion:
    criterion = EvaluationCriterion(**fields)
    session.add(criterion)
    await session.flush()
    return criterion


# ─── Setup del evento ───────────────────────────────────────────────────────


async def get_setup(
    session: AsyncSession, sourcing_event_id: UUID
) -> EventEvaluationSetup | None:
    result = await session.execute(
        select(EventEvaluationSetup).where(
            EventEvaluationSetup.sourcing_event_id == sourcing_event_id
        )
    )
    return result.scalar_one_or_none()


async def upsert_setup(
    session: AsyncSession, *, sourcing_event_id: UUID, **fields: object
) -> EventEvaluationSetup:
    fields["sourcing_event_id"] = sourcing_event_id
    existing = await get_setup(session, sourcing_event_id)
    if existing is not None:
        for key, value in fields.items():
            setattr(existing, key, value)
        await session.flush()
        return existing
    setup = EventEvaluationSetup(**fields)
    session.add(setup)
    await session.flush()
    return setup


# ─── Comité ──────────────────────────────────────────────────────────────────


async def list_assignments(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[EvaluationAssignment]:
    result = await session.execute(
        select(EvaluationAssignment).where(
            EvaluationAssignment.sourcing_event_id == sourcing_event_id
        )
    )
    return list(result.scalars())


async def get_my_assignments(
    session: AsyncSession, sourcing_event_id: UUID, organization_member_id: UUID
) -> list[EvaluationAssignment]:
    result = await session.execute(
        select(EvaluationAssignment).where(
            EvaluationAssignment.sourcing_event_id == sourcing_event_id,
            EvaluationAssignment.organization_member_id == organization_member_id,
        )
    )
    return list(result.scalars())


async def create_assignment(
    session: AsyncSession, **fields: object
) -> EvaluationAssignment:
    assignment = EvaluationAssignment(**fields)
    session.add(assignment)
    await session.flush()
    return assignment


async def delete_assignments_for_event(
    session: AsyncSession, sourcing_event_id: UUID
) -> None:
    result = await session.execute(
        select(EvaluationAssignment).where(
            EvaluationAssignment.sourcing_event_id == sourcing_event_id
        )
    )
    for assignment in result.scalars():
        await session.delete(assignment)
    await session.flush()


# ─── Evaluaciones y puntajes (autoservicio) ────────────────────────────────


async def get_or_create_evaluation(
    session: AsyncSession,
    *,
    sourcing_event_id: UUID,
    quotation_id: UUID,
    organization_member_id: UUID,
) -> Evaluation:
    result = await session.execute(
        select(Evaluation).where(
            Evaluation.quotation_id == quotation_id,
            Evaluation.organization_member_id == organization_member_id,
        )
    )
    evaluation = result.scalar_one_or_none()
    if evaluation is not None:
        return evaluation
    evaluation = Evaluation(
        sourcing_event_id=sourcing_event_id,
        quotation_id=quotation_id,
        organization_member_id=organization_member_id,
    )
    session.add(evaluation)
    await session.flush()
    return evaluation


async def get_evaluation(
    session: AsyncSession, evaluation_id: UUID
) -> Evaluation | None:
    result = await session.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    return result.scalar_one_or_none()


async def update_evaluation(evaluation: Evaluation, **fields: object) -> None:
    for key, value in fields.items():
        setattr(evaluation, key, value)


async def list_scores(
    session: AsyncSession, evaluation_id: UUID
) -> list[EvaluationScore]:
    result = await session.execute(
        select(EvaluationScore).where(EvaluationScore.evaluation_id == evaluation_id)
    )
    return list(result.scalars())


async def upsert_score(
    session: AsyncSession,
    *,
    evaluation_id: UUID,
    evaluation_criterion_id: UUID,
    score: float,
    comment: str | None,
    evidence_document_id: UUID | None,
) -> EvaluationScore:
    result = await session.execute(
        select(EvaluationScore).where(
            EvaluationScore.evaluation_id == evaluation_id,
            EvaluationScore.evaluation_criterion_id == evaluation_criterion_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.score = score
        existing.comment = comment
        existing.evidence_document_id = evidence_document_id
        await session.flush()
        return existing
    row = EvaluationScore(
        evaluation_id=evaluation_id,
        evaluation_criterion_id=evaluation_criterion_id,
        score=score,
        comment=comment,
        evidence_document_id=evidence_document_id,
    )
    session.add(row)
    await session.flush()
    return row


# ─── Bloqueo económico — funciones SECURITY DEFINER de 0057 ────────────────


async def list_items_for_technical_evaluation(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select * from app.list_quotation_items_for_technical_evaluation(:event_id)"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    return [dict(row._mapping) for row in result]


async def list_responses_for_technical_evaluation(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select * from app.list_quotation_responses_for_technical_evaluation(:event_id)"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    return [dict(row._mapping) for row in result]


async def list_documents_for_technical_evaluation(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select * from app.list_quotation_documents_for_technical_evaluation(:event_id)"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    return [dict(row._mapping) for row in result]


async def list_revisions_for_commercial_evaluation(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select * from app.list_quotation_revisions_for_commercial_evaluation(:event_id)"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    return [dict(row._mapping) for row in result]


async def list_scores_for_event(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[dict]:
    """Puntajes SUBMITTED de todos los evaluadores, para armar el comparador
    (fase 8.1). No es monetario (0-100), así que no necesita pasar por las
    funciones SECURITY DEFINER de 0057 — RLS ya permite esta lectura a quien
    tiene evaluation.manage (0056)."""
    result = await session.execute(
        text(
            "select e.quotation_id, es.evaluation_criterion_id, ec.dimension, "
            "       ec.weight, es.score "
            "from public.evaluation_scores es "
            "join public.evaluations e on e.id = es.evaluation_id "
            "join public.evaluation_criteria ec on ec.id = es.evaluation_criterion_id "
            "where e.sourcing_event_id = :event_id and e.status = 'SUBMITTED'"
        ),
        {"event_id": str(sourcing_event_id)},
    )
    return [dict(row._mapping) for row in result]


# ─── Comparador ──────────────────────────────────────────────────────────────


async def create_comparison(
    session: AsyncSession, **fields: object
) -> QuotationComparison:
    comparison = QuotationComparison(**fields)
    session.add(comparison)
    await session.flush()
    return comparison


async def get_latest_comparison(
    session: AsyncSession, sourcing_event_id: UUID
) -> QuotationComparison | None:
    result = await session.execute(
        select(QuotationComparison)
        .where(QuotationComparison.sourcing_event_id == sourcing_event_id)
        .order_by(QuotationComparison.executed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
