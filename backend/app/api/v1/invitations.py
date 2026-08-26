"""Routers de invitaciones: lado comprador (anidado en el evento) y lado
proveedor (autoservicio, /organizations/{id}/invitations) (fase 7.1/7.2)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUserId
from app.schemas.invitations import (
    DeclineRequest,
    DisqualifyRequest,
    InvitationDetailOut,
    InviteSupplierRequest,
    NdaOut,
    NdaUpsertRequest,
)
from app.schemas.sourcing import CreatedOut
from app.services import invitations as invitations_service

_STATUS_BY_ERROR = {
    invitations_service.InvitationPermissionError: status.HTTP_403_FORBIDDEN,
    invitations_service.InvitationNotFoundError: status.HTTP_404_NOT_FOUND,
    invitations_service.InvitationValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: invitations_service.InvitationError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


# ─── Lado comprador: anidado en el evento ─────────────────────────────────────

router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-events/{event_id}/invitations",
    tags=["invitations"],
)


@router.get("", response_model=list[dict])
async def list_invitations(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        rows = await invitations_service.list_invitations(
            user_id=user_id, organization_id=organization_id, sourcing_event_id=event_id
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc
    return [
        {
            "id": r.id,
            "supplier_organization_id": r.supplier_organization_id,
            "status": r.status,
            "source": r.source,
            "invited_at": r.invited_at,
            "viewed_at": r.viewed_at,
            "responded_at": r.responded_at,
        }
        for r in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def invite_supplier(
    organization_id: UUID,
    event_id: UUID,
    payload: InviteSupplierRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        invitation_id = await invitations_service.invite_supplier(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            **payload.model_dump(),
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=invitation_id)


@router.post(
    "/{invitation_id}/disqualify",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def disqualify_invitation(
    organization_id: UUID,
    event_id: UUID,
    invitation_id: UUID,
    payload: DisqualifyRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await invitations_service.disqualify(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
            reason=payload.reason,
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc


@router.get("/nda", response_model=NdaOut | None)
async def get_event_nda(
    organization_id: UUID, event_id: UUID, user_id: CurrentUserId
) -> NdaOut | None:
    nda = await invitations_service.get_nda(user_id=user_id, sourcing_event_id=event_id)
    return NdaOut.model_validate(nda) if nda else None


@router.put("/nda", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def upsert_event_nda(
    organization_id: UUID,
    event_id: UUID,
    payload: NdaUpsertRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        nda_id = await invitations_service.upsert_nda(
            user_id=user_id,
            organization_id=organization_id,
            sourcing_event_id=event_id,
            **payload.model_dump(),
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=nda_id)


# ─── Lado proveedor: autoservicio ─────────────────────────────────────────────
#
# "sourcing-invitations", no "invitations" a secas: ese path exacto
# (/organizations/{id}/invitations) ya lo tiene team.py para invitaciones de
# MIEMBROS DE EQUIPO (list_pending_invitations) — un choque de rutas real,
# encontrado en vivo probando la bandeja del proveedor en el navegador. Como
# team_router se monta antes en main.py, su GET ganaba silenciosamente el
# match y esta ruta nunca se alcanzaba — sin error, solo una lista vacía
# donde debía haber una invitación real.

supplier_router = APIRouter(
    prefix="/organizations/{organization_id}/sourcing-invitations", tags=["invitations"]
)


@supplier_router.get("", response_model=list[dict])
async def list_my_invitations(
    organization_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    return await invitations_service.list_my_invitations(
        user_id=user_id, organization_id=organization_id
    )


@supplier_router.get("/{invitation_id}", response_model=InvitationDetailOut)
async def get_invitation(
    organization_id: UUID, invitation_id: UUID, user_id: CurrentUserId
) -> InvitationDetailOut:
    try:
        detail = await invitations_service.get_invitation_detail(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc
    return InvitationDetailOut.model_validate(detail)


@supplier_router.post(
    "/{invitation_id}/accept-nda",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def accept_nda(
    organization_id: UUID, invitation_id: UUID, user_id: CurrentUserId, request: Request
) -> None:
    try:
        await invitations_service.accept_nda(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc


@supplier_router.post(
    "/{invitation_id}/interest",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def express_interest(
    organization_id: UUID, invitation_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await invitations_service.express_interest(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc


@supplier_router.post(
    "/{invitation_id}/confirm-participation",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def confirm_participation(
    organization_id: UUID, invitation_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await invitations_service.confirm_participation(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc


@supplier_router.post(
    "/{invitation_id}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def decline_invitation(
    organization_id: UUID,
    invitation_id: UUID,
    payload: DeclineRequest,
    user_id: CurrentUserId,
) -> None:
    try:
        await invitations_service.decline(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
            reason_code=payload.reason_code,
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc


@supplier_router.post(
    "/{invitation_id}/withdraw",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def withdraw_invitation(
    organization_id: UUID, invitation_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await invitations_service.withdraw(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc


# ─── Lado comprador: vista agregada (todos los eventos) ───────────────────────
#
# list_invitations() de más arriba está anidado bajo un event_id — sirve para
# la ficha de UN proceso. Esta es la vista "a quién invité en total", sin
# entrar evento por evento — pestaña "Enviadas" de /empresa/invitaciones.

sent_router = APIRouter(
    prefix="/organizations/{organization_id}/sent-invitations", tags=["invitations"]
)


@sent_router.get("", response_model=list[dict])
async def list_sent_invitations(
    organization_id: UUID, user_id: CurrentUserId
) -> list[dict]:
    try:
        rows = await invitations_service.list_sent_invitations(
            user_id=user_id, organization_id=organization_id
        )
    except invitations_service.InvitationError as exc:
        raise _as_http_exception(exc) from exc
    return rows
