"""Router de planes y facturación: /api/organizations/{id}/billing/*
(fase 8.10)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.services import billing as billing_service

router = APIRouter(prefix="/organizations/{organization_id}/billing", tags=["billing"])

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    billing_service.BillingPermissionError: status.HTTP_403_FORBIDDEN,
}


def _as_http_exception(exc: billing_service.BillingError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("/plans", response_model=list[dict])
async def list_plans(organization_id: UUID, user_id: CurrentUserId) -> list[dict]:
    # Catálogo público de planes — no depende de la pertenencia a
    # organization_id, se mantiene en el path solo por convención REST del
    # resto del proyecto.
    try:
        plans = await billing_service.list_plans(user_id=user_id)
    except billing_service.BillingError as exc:
        raise _as_http_exception(exc) from exc
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "description": p.description,
            "monthly_price": (
                float(p.monthly_price) if p.monthly_price is not None else None
            ),
            "currency_code": p.currency_code,
            "sort_order": p.sort_order,
        }
        for p in plans
    ]


@router.get("/subscription", response_model=dict | None)
async def get_subscription(organization_id: UUID, user_id: CurrentUserId):
    try:
        subscription = await billing_service.get_my_subscription(
            user_id=user_id, organization_id=organization_id
        )
    except billing_service.BillingError as exc:
        raise _as_http_exception(exc) from exc
    if subscription is None:
        return None
    return {
        "id": subscription.id,
        "organization_id": subscription.organization_id,
        "plan_id": subscription.plan_id,
        "status": subscription.status,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
    }
