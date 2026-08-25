"""Routers de evaluación: plantillas (nivel organización), setup/comité/
comparador (anidado en el evento), autoservicio del evaluador (fase 8.1-8.4)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.evaluations import (
    ApplyTemplateRequest,
    AssignCommitteeRequest,
    CreateTemplateRequest,
    SubmitEvaluationRequest,
    SubmitScoreRequest,
)
from app.schemas.sourcing import CreatedOut
from app.services import evaluations as evaluations_service

_STATUS_BY_ERROR = {
    evaluations_service.EvaluationPermissionError: status.HTTP_403_FORBIDDEN,
    evaluations_service.EvaluationNotFoundError: status.HTTP_404_NOT_FOUND,
    evaluations_service.EvaluationValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: evaluations_service.EvaluationError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


# ─── Plantillas: nivel organización ───────────────────────────────────────────

templates_router = APIRouter(
    prefix="/organizations/{organization_id}/evaluation-templates", tags=["evaluations"]
)


@templates_router.get("", response_model=list[dict])
async def list_templates(organization_id: UUID, user_id: CurrentUserId) -> list[dict]:
    try:
        templates = await evaluations_service.list_templates(
            user_id=user_id, organization_id=organization_id
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc
    return [
        {"id": t.id, "name": t.name, "description": t.description} for t in templates
    ]


@templates_router.get("/{template_id}", response_model=dict)
async def get_template(
    organization_id: UUID, template_id: UUID, user_id: CurrentUserId
) -> dict:
    try:
        detail = await evaluations_service.get_template_detail(
            user_id=user_id, organization_id=organization_id, template_id=template_id
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc
    return {
        "id": detail["template"].id,
        "name": detail["template"].name,
        "description": detail["template"].description,
        "criteria": [
            {
                "id": c.id,
                "dimension": c.dimension,
                "name": c.name,
                "description": c.description,
                "weight": float(c.weight),
                "sort_order": c.sort_order,
            }
            for c in detail["criteria"]
        ],
    }


@templates_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def create_template(
    organization_id: UUID, payload: CreateTemplateRequest, user_id: CurrentUserId
) -> CreatedOut:
    try:
        template_id = await evaluations_service.create_template(
            user_id=user_id,
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            criteria=[c.model_dump() for c in payload.criteria],
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=template_id)


# ─── Setup/comité/comparador: anidado en el evento ────────────────────────────

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/evaluations",
    tags=["evaluations"],
)


@router.get("/setup", response_model=dict | None)
async def get_setup(organization_id: UUID, event_id: UUID, user_id: CurrentUserId):
    try:
        return await evaluations_service.get_setup(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc


@router.post("/setup", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def apply_template(
    organization_id: UUID,
    event_id: UUID,
    payload: ApplyTemplateRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        setup_id = await evaluations_service.apply_template_to_event(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            template_id=payload.template_id,
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=setup_id)


@router.get("/committee", response_model=list[dict])
async def list_committee(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        assignments = await evaluations_service.list_committee(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc
    return [
        {
            "id": a.id,
            "organization_member_id": a.organization_member_id,
            "dimension": a.dimension,
            "can_view_commercial": a.can_view_commercial,
        }
        for a in assignments
    ]


@router.post("/committee", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def assign_committee(
    organization_id: UUID,
    event_id: UUID,
    payload: AssignCommitteeRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await evaluations_service.assign_committee(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            assignments=[a.model_dump() for a in payload.assignments],
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc


@router.get("/comparator", response_model=dict | None)
async def get_comparator(organization_id: UUID, event_id: UUID, user_id: CurrentUserId):
    try:
        comparison = await evaluations_service.get_latest_comparison(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc
    if comparison is None:
        return None
    return {
        "id": comparison.id,
        "criteria_snapshot": comparison.criteria_snapshot,
        "ranking": comparison.ranking,
        "executed_at": comparison.executed_at,
    }


@router.post("/comparator/run", response_model=dict)
async def run_comparator(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> dict:
    try:
        return await evaluations_service.run_comparator(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc


# ─── Autoservicio del evaluador ─────────────────────────────────────────────


@router.get("/mine", response_model=dict)
async def get_my_evaluation_view(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> dict:
    try:
        return await evaluations_service.get_my_evaluation_view(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/mine/scores", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def submit_score(
    organization_id: UUID,
    event_id: UUID,
    payload: SubmitScoreRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await evaluations_service.submit_score(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            **payload.model_dump(),
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/mine/submit", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def submit_evaluation(
    organization_id: UUID,
    event_id: UUID,
    payload: SubmitEvaluationRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await evaluations_service.submit_evaluation(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            **payload.model_dump(),
        )
    except evaluations_service.EvaluationError as exc:
        raise _as_http_exception(exc) from exc
