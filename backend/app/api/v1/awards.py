"""Routers de adjudicación: awards anidados en el evento, bandeja plana de
aprobaciones pendientes, y políticas de aprobación a nivel de organización
(fase 8.6/8.7).

Tres routers en vez de dos porque las políticas no cuelgan de un evento
puntual (son configuración de la organización, reutilizada por todos sus
eventos) ni son parte de la bandeja de aprobaciones (que lista pasos ya
generados, no la configuración que los generó) — mismo criterio que separó
`templates_router` de `router` en evaluations.py."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.awards import (
    ApprovalPolicyIn,
    DecideApprovalRequest,
    ProposeAwardRequest,
)
from app.schemas.sourcing import CreatedOut
from app.services import awards as awards_service

_STATUS_BY_ERROR = {
    awards_service.AwardPermissionError: status.HTTP_403_FORBIDDEN,
    awards_service.AwardNotFoundError: status.HTTP_404_NOT_FOUND,
    awards_service.AwardValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: awards_service.AwardError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


def _award_out(a) -> dict:
    return {
        "id": a.id,
        "sourcing_event_id": a.sourcing_event_id,
        "awarded_organization_id": a.awarded_organization_id,
        "quotation_revision_id": a.quotation_revision_id,
        "status": a.status,
        "justification": a.justification,
        "currency_code": a.currency_code,
        "amount": float(a.amount),
        "amount_base": float(a.amount_base),
        "proposed_at": a.proposed_at,
        "decided_at": a.decided_at,
        "published_at": a.published_at,
    }


# ─── Awards: anidado en el evento ─────────────────────────────────────────────

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/awards",
    tags=["awards"],
)


@router.get("", response_model=list[dict])
async def list_awards(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        awards = await awards_service.list_awards(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except awards_service.AwardError as exc:
        raise _as_http_exception(exc) from exc
    return [_award_out(a) for a in awards]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def propose_award(
    organization_id: UUID,
    event_id: UUID,
    payload: ProposeAwardRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        award_id = await awards_service.propose_award(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            awarded_organization_id=payload.awarded_organization_id,
            quotation_revision_id=payload.quotation_revision_id,
            justification=payload.justification,
            items=[i.model_dump() for i in payload.items],
        )
    except awards_service.AwardError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=award_id)


@router.post(
    "/{award_id}/publish", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def publish_award(
    organization_id: UUID, event_id: UUID, award_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await awards_service.publish_award(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            award_id=award_id,
        )
    except awards_service.AwardError as exc:
        raise _as_http_exception(exc) from exc


# ─── Bandeja plana de aprobaciones pendientes ────────────────────────────────

approvals_router = APIRouter(
    prefix="/organizations/{organization_id}/award-approvals", tags=["awards"]
)


@approvals_router.get("", response_model=list[dict])
async def list_my_pending_approvals(
    organization_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        approvals = await awards_service.list_my_pending_approvals(
            user_id=user_id, organization_id=organization_id
        )
    except awards_service.AwardError as exc:
        raise _as_http_exception(exc) from exc
    return [
        {
            "id": a.id,
            "award_id": a.award_id,
            "step_order": a.step_order,
            "required_role_code": a.required_role_code,
            "status": a.status,
            "created_at": a.created_at,
        }
        for a in approvals
    ]


@approvals_router.post(
    "/{approval_id}/decide", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def decide_approval(
    organization_id: UUID,
    approval_id: UUID,
    payload: DecideApprovalRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await awards_service.decide(
            user_id=user_id,
            organization_id=organization_id,
            approval_id=approval_id,
            decision=payload.decision,
            comment=payload.comment,
        )
    except awards_service.AwardError as exc:
        raise _as_http_exception(exc) from exc


# ─── Políticas de aprobación: nivel organización ─────────────────────────────

policies_router = APIRouter(
    prefix="/organizations/{organization_id}/approval-policies", tags=["awards"]
)


@policies_router.get("", response_model=list[dict])
async def list_policies(organization_id: UUID, user_id: CurrentUserId) -> list[dict]:
    try:
        policies = await awards_service.list_policies(
            user_id=user_id, organization_id=organization_id
        )
    except awards_service.AwardError as exc:
        raise _as_http_exception(exc) from exc
    return [
        {
            "id": p.id,
            "step_order": p.step_order,
            "required_role_code": p.required_role_code,
            "min_amount": float(p.min_amount),
            "max_amount": float(p.max_amount) if p.max_amount is not None else None,
        }
        for p in policies
    ]


@policies_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def upsert_policy(
    organization_id: UUID, payload: ApprovalPolicyIn, user_id: CurrentUserId
) -> CreatedOut:
    try:
        policy_id = await awards_service.upsert_policy(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except awards_service.AwardError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=policy_id)
