"""Plantillas, comité, evaluaciones y comparador (fase 8.1-8.4).

El bloqueo económico (evaluador técnico nunca ve montos, comercial solo tras
la apertura) NO se implementa con RLS de fila — Postgres RLS es estrictamente
a nivel de fila, nunca de columna, y EVALUATOR no tiene quotation.read. Todo
acceso de un evaluador a datos de cotización pasa por las funciones
SECURITY DEFINER de 0057 (repositories/evaluations.py::list_*_for_*_evaluation),
nunca por un select directo a quotation_items/quotation_revisions. Ver
plan de fase 8, Decisión 1.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import evaluations as evaluations_repo
from app.repositories import members as members_repo
from app.repositories import quotations as quotations_repo
from app.services import notifications as notifications_service

PERM_READ = "evaluation.read"
PERM_MANAGE = "evaluation.manage"


class EvaluationError(Exception):
    pass


class EvaluationPermissionError(EvaluationError):
    pass


class EvaluationNotFoundError(EvaluationError):
    pass


class EvaluationValidationError(EvaluationError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await evaluations_repo.has_permission(db, organization_id, permission):
        raise EvaluationPermissionError(f"Sin permiso ({permission}) para esta acción")


async def _require_member(db, user_id: UUID, organization_id: UUID):
    member = await members_repo.get_membership(
        db, user_id=user_id, organization_id=organization_id
    )
    if member is None:
        raise EvaluationPermissionError("No pertenece a esta organización")
    return member


# ─── Plantillas ─────────────────────────────────────────────────────────────


async def list_templates(*, user_id: UUID, organization_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await evaluations_repo.list_templates(db, organization_id)


async def get_template_detail(
    *, user_id: UUID, organization_id: UUID, template_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        template = await evaluations_repo.get_template(db, template_id)
        if template is None or template.organization_id != organization_id:
            raise EvaluationNotFoundError("Plantilla no encontrada")
        criteria = await evaluations_repo.list_criteria(db, template_id)
        return {"template": template, "criteria": criteria}


async def create_template(
    *,
    user_id: UUID,
    organization_id: UUID,
    name: str,
    description: str | None,
    criteria: list[dict],
) -> UUID:
    if not criteria:
        raise EvaluationValidationError("La plantilla necesita al menos un criterio")
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        template = await evaluations_repo.create_template(
            db,
            organization_id=organization_id,
            name=name,
            description=description,
            created_by=user_id,
            updated_by=user_id,
        )
        for i, criterion in enumerate(criteria):
            await evaluations_repo.add_criterion(
                db,
                template_id=template.id,
                dimension=criterion["dimension"],
                name=criterion["name"],
                description=criterion.get("description"),
                weight=criterion.get("weight", 1),
                sort_order=criterion.get("sort_order", i),
            )
        template_id = template.id
    return template_id


# ─── Setup del evento ───────────────────────────────────────────────────────


async def apply_template_to_event(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID, template_id: UUID
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)

        existing = await evaluations_repo.get_setup(db, sourcing_event_id)
        if existing is not None:
            submitted = await _count_submitted(db, sourcing_event_id)
            if submitted:
                raise EvaluationValidationError(
                    "No se puede reconfigurar: ya hay evaluaciones enviadas"
                )

        template = await evaluations_repo.get_template(db, template_id)
        if template is None or template.organization_id != organization_id:
            raise EvaluationNotFoundError("Plantilla no encontrada")
        criteria = await evaluations_repo.list_criteria(db, template_id)
        if not criteria:
            raise EvaluationValidationError("La plantilla no tiene criterios")

        total_weight = sum(float(c.weight) for c in criteria)
        if total_weight <= 0:
            raise EvaluationValidationError("La suma de pesos debe ser mayor a 0")

        snapshot = [
            {
                "id": str(c.id),
                "dimension": c.dimension,
                "name": c.name,
                "weight": float(c.weight),
            }
            for c in criteria
        ]
        setup = await evaluations_repo.upsert_setup(
            db,
            sourcing_event_id=sourcing_event_id,
            template_id=template.id,
            template_name_snapshot=template.name,
            criteria_snapshot=snapshot,
            applied_by=user_id,
        )
        setup_id = setup.id
    return setup_id


async def get_setup(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> dict | None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        setup = await evaluations_repo.get_setup(db, sourcing_event_id)
        return (
            None
            if setup is None
            else {
                "id": setup.id,
                "template_name_snapshot": setup.template_name_snapshot,
                "criteria_snapshot": setup.criteria_snapshot,
                "applied_at": setup.applied_at,
            }
        )


async def _count_submitted(db, sourcing_event_id: UUID) -> int:
    scores = await evaluations_repo.list_scores_for_event(db, sourcing_event_id)
    return len(scores)


# ─── Comité ──────────────────────────────────────────────────────────────────


async def assign_committee(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    assignments: list[dict],
) -> None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)
        await evaluations_repo.delete_assignments_for_event(db, sourcing_event_id)
        for a in assignments:
            await evaluations_repo.create_assignment(
                db,
                sourcing_event_id=sourcing_event_id,
                organization_member_id=a["organization_member_id"],
                dimension=a["dimension"],
                can_view_commercial=a.get("can_view_commercial", False),
                assigned_by=user_id,
            )


async def list_committee(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> list:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await evaluations_repo.list_assignments(db, sourcing_event_id)


# ─── Autoservicio del evaluador ─────────────────────────────────────────────


async def get_my_evaluation_view(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        member = await _require_member(db, user_id, organization_id)
        assignments = await evaluations_repo.get_my_assignments(
            db, sourcing_event_id, member.id
        )
        if not assignments:
            raise EvaluationPermissionError("No tiene una asignación en este evento")

        dimensions = {a.dimension for a in assignments}
        can_view_commercial = any(a.can_view_commercial for a in assignments)

        setup = await evaluations_repo.get_setup(db, sourcing_event_id)
        criteria = [
            c
            for c in (setup.criteria_snapshot if setup else [])
            if c["dimension"] in dimensions
        ]

        items = await evaluations_repo.list_items_for_technical_evaluation(
            db, sourcing_event_id
        )
        responses = await evaluations_repo.list_responses_for_technical_evaluation(
            db, sourcing_event_id
        )
        documents = await evaluations_repo.list_documents_for_technical_evaluation(
            db, sourcing_event_id
        )
        revisions = []
        if can_view_commercial:
            revisions = await evaluations_repo.list_revisions_for_commercial_evaluation(
                db, sourcing_event_id
            )

        quotation_ids = {i["quotation_id"] for i in items}
        my_evaluations: dict[str, dict] = {}
        for quotation_id in quotation_ids:
            evaluation = await evaluations_repo.get_or_create_evaluation(
                db,
                sourcing_event_id=sourcing_event_id,
                quotation_id=quotation_id,
                organization_member_id=member.id,
            )
            scores = await evaluations_repo.list_scores(db, evaluation.id)
            my_evaluations[str(quotation_id)] = {
                "evaluation_id": evaluation.id,
                "status": evaluation.status,
                "overall_comment": evaluation.overall_comment,
                "scores": [
                    {
                        "evaluation_criterion_id": s.evaluation_criterion_id,
                        "score": float(s.score),
                        "comment": s.comment,
                    }
                    for s in scores
                ],
            }

        return {
            "can_view_commercial": can_view_commercial,
            "criteria": criteria,
            "items": items,
            "responses": responses,
            "documents": documents,
            "revisions": revisions,
            "evaluations": my_evaluations,
        }


async def submit_score(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    quotation_id: UUID,
    evaluation_criterion_id: UUID,
    score: float,
    comment: str | None = None,
    evidence_document_id: UUID | None = None,
) -> None:
    if score < 0 or score > 100:
        raise EvaluationValidationError("El puntaje debe estar entre 0 y 100")
    async with session_for_user(user_id) as db:
        member = await _require_member(db, user_id, organization_id)
        assignments = await evaluations_repo.get_my_assignments(
            db, sourcing_event_id, member.id
        )
        if not assignments:
            raise EvaluationPermissionError("No tiene una asignación en este evento")

        evaluation = await evaluations_repo.get_or_create_evaluation(
            db,
            sourcing_event_id=sourcing_event_id,
            quotation_id=quotation_id,
            organization_member_id=member.id,
        )
        if evaluation.status != "DRAFT":
            raise EvaluationValidationError("Esta evaluación ya fue enviada")
        await evaluations_repo.upsert_score(
            db,
            evaluation_id=evaluation.id,
            evaluation_criterion_id=evaluation_criterion_id,
            score=score,
            comment=comment,
            evidence_document_id=evidence_document_id,
        )


async def submit_evaluation(
    *,
    user_id: UUID,
    organization_id: UUID,
    sourcing_event_id: UUID,
    quotation_id: UUID,
    overall_comment: str | None = None,
) -> None:
    async with session_for_user(user_id) as db:
        member = await _require_member(db, user_id, organization_id)
        assignments = await evaluations_repo.get_my_assignments(
            db, sourcing_event_id, member.id
        )
        if not assignments:
            raise EvaluationPermissionError("No tiene una asignación en este evento")

        evaluation = await evaluations_repo.get_or_create_evaluation(
            db,
            sourcing_event_id=sourcing_event_id,
            quotation_id=quotation_id,
            organization_member_id=member.id,
        )
        if evaluation.status != "DRAFT":
            raise EvaluationValidationError("Esta evaluación ya fue enviada")
        scores = await evaluations_repo.list_scores(db, evaluation.id)
        if not scores:
            raise EvaluationValidationError(
                "Registre al menos un puntaje antes de enviar"
            )
        await evaluations_repo.update_evaluation(
            evaluation,
            status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc),
            overall_comment=overall_comment,
        )


# ─── Comparador ──────────────────────────────────────────────────────────────


async def run_comparator(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_MANAGE)

        setup = await evaluations_repo.get_setup(db, sourcing_event_id)
        if setup is None:
            raise EvaluationValidationError("El evento no tiene una plantilla aplicada")

        rows = await evaluations_repo.list_scores_for_event(db, sourcing_event_id)
        quotations = await quotations_repo.list_for_event(db, sourcing_event_id)
        supplier_by_quotation = {
            str(q["id"]): str(q["supplier_organization_id"]) for q in quotations
        }

        # score promedio por (quotation, criterio), luego ponderado por peso.
        by_quotation_criterion: dict[tuple[str, str], list[float]] = defaultdict(list)
        weight_by_criterion: dict[str, float] = {}
        for row in rows:
            key = (str(row["quotation_id"]), str(row["evaluation_criterion_id"]))
            by_quotation_criterion[key].append(float(row["score"]))
            weight_by_criterion[str(row["evaluation_criterion_id"])] = float(
                row["weight"]
            )

        total_weight = sum(weight_by_criterion.values()) or 1.0
        totals: dict[str, float] = defaultdict(float)
        breakdown: dict[str, dict] = defaultdict(dict)
        for (quotation_id, criterion_id), values in by_quotation_criterion.items():
            avg = sum(values) / len(values)
            weight = weight_by_criterion[criterion_id]
            totals[quotation_id] += avg * weight / total_weight
            breakdown[quotation_id][criterion_id] = avg

        ordered_quotation_ids = sorted(
            totals.keys(), key=lambda qid: totals[qid], reverse=True
        )
        ranking = [
            {
                "quotation_id": qid,
                "supplier_organization_id": supplier_by_quotation.get(qid),
                "total_score": round(totals[qid], 2),
                "breakdown": breakdown[qid],
            }
            for qid in ordered_quotation_ids
        ]

        comparison = await evaluations_repo.create_comparison(
            db,
            sourcing_event_id=sourcing_event_id,
            criteria_snapshot=setup.criteria_snapshot,
            ranking=ranking,
            executed_by=user_id,
        )
        comparison_id = comparison.id

    await notifications_service.notify_org(
        organization_id=organization_id,
        type="evaluation.comparator_run",
        title="Comparador actualizado",
        body="Se generó una nueva corrida del comparador de ofertas.",
        entity_type="sourcing_event",
        entity_id=sourcing_event_id,
        action_url=f"/empresa/sourcing/{sourcing_event_id}/comparador",
    )
    return {"id": comparison_id, "ranking": ranking}


async def get_latest_comparison(
    *, user_id: UUID, organization_id: UUID, sourcing_event_id: UUID
):
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        return await evaluations_repo.get_latest_comparison(db, sourcing_event_id)
