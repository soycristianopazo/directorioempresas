"""Router de equipo e invitaciones: /api/organizations/{id}/team, /api/invitations/*."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserId
from app.db.rls import session_for_system
from app.repositories import users as users_repo
from app.schemas.organization import (
    ChangeMemberRolesRequest,
    InvitationResult,
    InviteMemberRequest,
    PendingInvitationOut,
    TeamMemberOut,
    TeamRoleOut,
)
from app.services import entitlements as entitlements_service
from app.services import team as team_service

router = APIRouter(tags=["team"])


@router.get("/organizations/{organization_id}/team", response_model=list[TeamMemberOut])
async def list_team(
    organization_id: UUID, user_id: CurrentUserId
) -> list[TeamMemberOut]:
    try:
        members = await team_service.list_team(
            user_id=user_id, organization_id=organization_id
        )
    except team_service.TeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    return [TeamMemberOut(**m) for m in members]


@router.get("/organizations/{organization_id}/roles", response_model=list[TeamRoleOut])
async def list_assignable_roles(
    organization_id: UUID, user_id: CurrentUserId
) -> list[TeamRoleOut]:
    roles = await team_service.list_assignable_roles(
        user_id=user_id, organization_id=organization_id
    )
    return [TeamRoleOut(**r) for r in roles]


@router.get(
    "/organizations/{organization_id}/invitations",
    response_model=list[PendingInvitationOut],
)
async def list_pending_invitations(
    organization_id: UUID, user_id: CurrentUserId
) -> list[PendingInvitationOut]:
    try:
        invitations = await team_service.list_pending_invitations(
            user_id=user_id, organization_id=organization_id
        )
    except team_service.TeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    return [PendingInvitationOut(**i) for i in invitations]


@router.post(
    "/invitations", response_model=InvitationResult, status_code=status.HTTP_201_CREATED
)
async def invite_member(
    payload: InviteMemberRequest, user_id: CurrentUserId
) -> InvitationResult:
    try:
        invitation_id, accept_url = await team_service.invite_member(
            user_id=user_id,
            organization_id=payload.organization_id,
            email=payload.email,
            role_code=payload.role_code,
        )
    except entitlements_service.EntitlementExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc
    except team_service.TeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return InvitationResult(invitation_id=invitation_id, accept_url=accept_url)


@router.post("/invitations/{token}/accept")
async def accept_invitation(token: str, user_id: CurrentUserId) -> dict:
    async with session_for_system() as db:
        user = await users_repo.get_by_id(db, user_id)
        user_email = str(user.email) if user else ""

    try:
        organization_id = await team_service.accept_invitation(
            user_id=user_id, user_email=user_email, token=token
        )
    except team_service.TeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return {"organization_id": str(organization_id)}


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def revoke_invitation(
    invitation_id: UUID, organization_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await team_service.revoke_invitation(
            user_id=user_id,
            organization_id=organization_id,
            invitation_id=invitation_id,
        )
    except team_service.TeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.delete(
    "/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def remove_member(
    member_id: UUID, organization_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await team_service.remove_member(
            user_id=user_id, organization_id=organization_id, member_id=member_id
        )
    except team_service.TeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.put(
    "/members/{member_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def change_member_roles(
    member_id: UUID, payload: ChangeMemberRolesRequest, user_id: CurrentUserId
) -> None:
    try:
        await team_service.change_member_roles(
            user_id=user_id,
            organization_id=payload.organization_id,
            member_id=member_id,
            role_codes=payload.role_codes,
        )
    except team_service.TeamError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
