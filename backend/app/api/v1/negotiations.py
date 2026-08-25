"""Routers de rondas de negociación: lado comprador y lado proveedor
(fase 8.5)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.schemas.negotiations import OpenRoundRequest, SubmitCounterRequest
from app.schemas.sourcing import CreatedOut
from app.services import negotiations as negotiations_service

_STATUS_BY_ERROR = {
    negotiations_service.NegotiationPermissionError: status.HTTP_403_FORBIDDEN,
    negotiations_service.NegotiationNotFoundError: status.HTTP_404_NOT_FOUND,
    negotiations_service.NegotiationValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: negotiations_service.NegotiationError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


# ─── Lado comprador ───────────────────────────────────────────────────────────

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/negotiation-rounds",
    tags=["negotiations"],
)


@router.get("", response_model=list[dict])
async def list_rounds(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        rounds = await negotiations_service.list_rounds(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except negotiations_service.NegotiationError as exc:
        raise _as_http_exception(exc) from exc
    return [
        {
            "id": r.id,
            "round_type": r.round_type,
            "instructions": r.instructions,
            "target_reduction_pct": (
                float(r.target_reduction_pct)
                if r.target_reduction_pct is not None
                else None
            ),
            "deadline": r.deadline,
            "opened_at": r.opened_at,
            "opened_by": r.opened_by,
            "closed_at": r.closed_at,
            "closed_by": r.closed_by,
        }
        for r in rounds
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def open_round(
    organization_id: UUID,
    event_id: UUID,
    payload: OpenRoundRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        round_id = await negotiations_service.open_round(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            round_type=payload.round_type,
            participant_supplier_organization_ids=payload.participant_supplier_organization_ids,
            deadline=payload.deadline,
            target_reduction_pct=payload.target_reduction_pct,
            instructions=payload.instructions,
        )
    except negotiations_service.NegotiationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=round_id)


@router.post(
    "/{round_id}/close", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def close_round(
    organization_id: UUID, event_id: UUID, round_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await negotiations_service.close_round(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            negotiation_round_id=round_id,
        )
    except negotiations_service.NegotiationError as exc:
        raise _as_http_exception(exc) from exc


# ─── Lado proveedor ───────────────────────────────────────────────────────────

supplier_router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/my-negotiation",
    tags=["negotiations"],
)


@supplier_router.get("", response_model=list[dict])
async def list_my_round(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        return await negotiations_service.list_my_round(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except negotiations_service.NegotiationError as exc:
        raise _as_http_exception(exc) from exc


@supplier_router.post(
    "/{round_id}/respond",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def submit_counter(
    organization_id: UUID,
    event_id: UUID,
    round_id: UUID,
    payload: SubmitCounterRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    if payload.negotiation_round_id != round_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="negotiation_round_id del cuerpo no coincide con la ronda de la URL",
        )
    try:
        revision_id = await negotiations_service.submit_counter(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            negotiation_round_id=round_id,
            currency_code=payload.currency_code,
            valid_until=payload.valid_until,
            subtotal=payload.subtotal,
            tax_amount=payload.tax_amount,
            total_amount=payload.total_amount,
            payment_terms=payload.payment_terms,
            delivery_days=payload.delivery_days,
            warranty_terms=payload.warranty_terms,
            exclusions=payload.exclusions,
            notes=payload.notes,
            items=[i.model_dump() for i in payload.items],
            responses=[r.model_dump() for r in payload.responses],
        )
    except negotiations_service.NegotiationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=revision_id)
