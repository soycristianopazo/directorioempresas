"""Invitaciones, equipo y roles de miembros."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import settings
from app.db.rls import session_for_system, session_for_user
from app.repositories import members as members_repo
from app.repositories import organizations as orgs_repo

INVITATION_TTL_DAYS = 7


class TeamError(Exception):
    pass


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def invite_member(
    *, user_id: UUID, organization_id: UUID, email: str, role_code: str
) -> tuple[UUID, str]:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(db, organization_id, "member.manage"):
            raise TeamError("Sin permiso para administrar el equipo")

        role = await members_repo.find_role_by_code(db, role_code)
        if role is None:
            raise TeamError("El rol indicado no existe")
        if role.scope != "ORGANIZATION":
            raise TeamError("No se puede invitar con un rol de plataforma")

        existing = await members_repo.get_pending_invitation(
            db, organization_id=organization_id, email=email
        )
        if existing is not None:
            existing.status = "REVOKED"
            existing.revoked_at = datetime.now(UTC)

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS)

        invitation = await members_repo.create_invitation(
            db,
            organization_id=organization_id,
            email=email,
            role_id=role.id,
            invited_by=user_id,
            token_hash=_hash_token(token),
            expires_at=expires_at,
        )
        invitation_id = invitation.id

    accept_url = f"{settings.frontend_url}/invitaciones/{token}"
    return invitation_id, accept_url


async def revoke_invitation(
    *, user_id: UUID, organization_id: UUID, invitation_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(db, organization_id, "member.manage"):
            raise TeamError("Sin permiso para administrar el equipo")

        record = await members_repo.get_invitation_by_id(
            db, invitation_id, organization_id=organization_id
        )
        if record is None:
            raise TeamError("Invitación no encontrada")
        if record.status == "PENDING":
            record.status = "REVOKED"
            record.revoked_at = datetime.now(UTC)


async def accept_invitation(*, user_id: UUID, user_email: str, token: str) -> UUID:
    """No pasa por authorize(): quien acepta todavía no pertenece a la
    organización. La validez (hash, vigencia, correo coincidente) es lo único
    que autoriza esta operación, así que corre en contexto de sistema.
    """
    token_hash = _hash_token(token)

    async with session_for_system() as db:
        invitation = await members_repo.get_invitation_by_token_hash(db, token_hash)

        if invitation is None:
            raise TeamError("Invitación no encontrada")
        if invitation.status != "PENDING":
            raise TeamError(
                f"La invitación ya no está vigente (estado: {invitation.status})"
            )
        if invitation.expires_at < datetime.now(UTC):
            invitation.status = "EXPIRED"
            raise TeamError("La invitación expiró")
        if invitation.email.lower() != user_email.lower():
            raise TeamError("La invitación fue emitida para otra dirección de correo")

        existing = await members_repo.get_membership(
            db, user_id=user_id, organization_id=invitation.organization_id
        )
        if existing is not None:
            existing.status = "ACTIVE"
            existing.removed_at = None
            member = existing
        else:
            member = await members_repo.create_member(
                db,
                user_id=user_id,
                organization_id=invitation.organization_id,
                invited_by=invitation.invited_by,
            )

        await members_repo.assign_role(
            db,
            member_id=member.id,
            role_id=invitation.role_id,
            assigned_by=invitation.invited_by,
        )

        invitation.status = "ACCEPTED"
        invitation.accepted_at = datetime.now(UTC)
        invitation.accepted_by = user_id

        organization_id = invitation.organization_id

    return organization_id


async def remove_member(
    *, user_id: UUID, organization_id: UUID, member_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(db, organization_id, "member.manage"):
            raise TeamError("Sin permiso para administrar el equipo")

        if await members_repo.is_member_an_owner(db, member_id):
            owner_count = await members_repo.count_active_owners(db, organization_id)
            if owner_count <= 1:
                raise TeamError(
                    "No se puede remover al último dueño de la organización"
                )

        member = await members_repo.get_member_by_id(
            db, member_id, organization_id=organization_id
        )
        if member is None:
            raise TeamError("Miembro no encontrado")
        member.status = "REMOVED"
        member.removed_at = datetime.now(UTC)


async def change_member_roles(
    *, user_id: UUID, organization_id: UUID, member_id: UUID, role_codes: list[str]
) -> None:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(db, organization_id, "member.manage"):
            raise TeamError("Sin permiso para administrar el equipo")

        member = await members_repo.get_member_by_id(
            db, member_id, organization_id=organization_id
        )
        if member is None:
            raise TeamError("Miembro no encontrado")

        assignable = await members_repo.list_assignable_roles(db, organization_id)
        by_code = {r.code: r for r in assignable}

        role_ids = []
        for code in role_codes:
            role = by_code.get(code)
            if role is None:
                raise TeamError(f"Rol no asignable: {code}")
            role_ids.append(role.id)

        await members_repo.replace_roles(db, member_id=member_id, role_ids=role_ids)


async def list_team(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(db, organization_id, "member.read"):
            raise TeamError("Sin permiso para ver el equipo")

        members = await members_repo.list_team(db, organization_id)
        profiles = await members_repo.get_profiles_by_ids(
            db, [m.user_id for m in members]
        )

        return [
            {
                "member_id": m.id,
                "user_id": m.user_id,
                "status": m.status,
                "joined_at": m.joined_at,
                "full_name": (
                    profiles[m.user_id].full_name if m.user_id in profiles else None
                ),
                # El email vive en public.users, no en profiles, y solo se
                # resuelve para quien puede administrar el equipo — igual que
                # en la versión anterior. Se deja en None aquí: el router lo
                # completa con una consulta aparte solo si hace falta.
                "email": None,
                "roles": [
                    {"id": mr.role.id, "code": mr.role.code, "name": mr.role.name}
                    for mr in m.roles
                ],
            }
            for m in members
        ]


async def list_assignable_roles(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        roles = await members_repo.list_assignable_roles(db, organization_id)
        return [{"id": r.id, "code": r.code, "name": r.name} for r in roles]


async def list_pending_invitations(
    *, user_id: UUID, organization_id: UUID
) -> list[dict]:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(db, organization_id, "member.manage"):
            raise TeamError("Sin permiso para ver invitaciones")

        invitations = await members_repo.list_pending_invitations(db, organization_id)
        return [
            {
                "id": i.id,
                "email": str(i.email),
                "expires_at": i.expires_at,
                "created_at": i.created_at,
                "role": {"id": i.role.id, "code": i.role.code, "name": i.role.name},
            }
            for i in invitations
        ]
