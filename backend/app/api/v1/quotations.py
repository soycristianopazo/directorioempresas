"""Routers de cotizaciones: lado comprador y lado proveedor
(fase 7.5/7.6/7.7)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUserId
from app.schemas.quotations import SubmitRevisionRequest
from app.schemas.sourcing import CreatedOut
from app.services import quotations as quotations_service

_STATUS_BY_ERROR = {
    quotations_service.QuotationPermissionError: status.HTTP_403_FORBIDDEN,
    quotations_service.QuotationNotFoundError: status.HTTP_404_NOT_FOUND,
    quotations_service.QuotationValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: quotations_service.QuotationError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


# ─── Lado comprador ───────────────────────────────────────────────────────────

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/quotations",
    tags=["quotations"],
)


@router.get("", response_model=list[dict])
async def list_quotations(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        return await quotations_service.list_quotations(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except quotations_service.QuotationError as exc:
        raise _as_http_exception(exc) from exc


@router.post("/open-bids", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def open_bids(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await quotations_service.open_bids(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except quotations_service.QuotationError as exc:
        raise _as_http_exception(exc) from exc


# ─── Lado proveedor ───────────────────────────────────────────────────────────

supplier_router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/my-quotation",
    tags=["quotations"],
)


@supplier_router.get("/revisions", response_model=list[dict])
async def list_my_revisions(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    revisions = await quotations_service.list_my_revisions(
        user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
    )
    return [
        {
            "id": r.id,
            "round_number": r.round_number,
            "round_type": r.round_type,
            "submitted_at": r.submitted_at,
            "currency_code": r.currency_code,
            "total_amount": r.total_amount,
            "total_amount_base": r.total_amount_base,
        }
        for r in revisions
    ]


@supplier_router.post(
    "/revisions", status_code=status.HTTP_201_CREATED, response_model=CreatedOut
)
async def submit_revision(
    organization_id: UUID,
    event_id: UUID,
    payload: SubmitRevisionRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        revision_id = await quotations_service.submit_revision(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
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
    except quotations_service.QuotationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=revision_id)


@supplier_router.post(
    "/revisions/{revision_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
)
async def upload_document(
    organization_id: UUID,
    event_id: UUID,
    revision_id: UUID,
    user_id: CurrentUserId,
    file: UploadFile = File(...),
) -> dict:
    content = await file.read()
    try:
        return await quotations_service.upload_document(
            user_id=user_id,
            organization_id=organization_id,
            quotation_revision_id=revision_id,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "documento.pdf",
        )
    except quotations_service.QuotationError as exc:
        raise _as_http_exception(exc) from exc
