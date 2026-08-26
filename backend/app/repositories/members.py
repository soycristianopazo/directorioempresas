"""Acceso a datos de roles, membresías, equipo e invitaciones."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.rbac import MemberRole, OrganizationInvitation, OrganizationMember, Role
from app.models.user import Profile


async def find_role_by_code(
    session: AsyncSession, code: str, *, system_only: bool = True
) -> Role | None:
    stmt = select(Role).where(Role.code == code)
    if system_only:
        stmt = stmt.where(Role.organization_id.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_default_owner_role(session: AsyncSession) -> Role | None:
    result = await session.execute(
        select(Role)
        .where(Role.organization_id.is_(None), Role.is_default_owner.is_(True))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_assignable_roles(
    session: AsyncSession, organization_id: UUID
) -> list[Role]:
    result = await session.execute(
        select(Role)
        .where(
            Role.scope == "ORGANIZATION",
            or_(
                Role.organization_id.is_(None), Role.organization_id == organization_id
            ),
        )
        .order_by(Role.sort_order)
    )
    return list(result.scalars())


async def get_membership(
    session: AsyncSession, *, user_id: UUID, organization_id: UUID
) -> OrganizationMember | None:
    result = await session.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def create_member(
    session: AsyncSession,
    *,
    user_id: UUID,
    organization_id: UUID,
    invited_by: UUID | None = None,
) -> OrganizationMember:
    member = OrganizationMember(
        user_id=user_id,
        organization_id=organization_id,
        status="ACTIVE",
        invited_by=invited_by,
        invited_at=datetime.now().astimezone() if invited_by else None,
    )
    session.add(member)
    await session.flush()
    return member


async def assign_role(
    session: AsyncSession, *, member_id: UUID, role_id: UUID, assigned_by: UUID | None
) -> None:
    session.add(
        MemberRole(member_id=member_id, role_id=role_id, assigned_by=assigned_by)
    )
    await session.flush()


async def replace_roles(
    session: AsyncSession, *, member_id: UUID, role_ids: list[UUID]
) -> None:
    await session.execute(
        MemberRole.__table__.delete().where(MemberRole.member_id == member_id)
    )
    for role_id in role_ids:
        session.add(MemberRole(member_id=member_id, role_id=role_id))
    await session.flush()


async def list_team(
    session: AsyncSession, organization_id: UUID
) -> list[tuple[OrganizationMember, Profile]]:
    """(miembro, perfil) en una sola consulta.

    La versión anterior encadenaba DOS selectinload (roles, luego role
    dentro de cada rol) y una segunda consulta aparte para los perfiles — 3
    round trips extra a una BD remota solo para listar un puñado de
    miembros. Acá: un JOIN a Profile (organization_members.user_id no tiene
    relación ORM declarada hacia Profile, por eso el join es explícito, no
    parte de `.options()`) más joinedload de roles, todo en un solo round
    trip. `.unique()` es obligatorio con joinedload sobre una colección
    uno-a-muchos — si no, SQLAlchemy devuelve una fila por cada rol en vez
    de un miembro con su lista de roles.
    """
    result = await session.execute(
        select(OrganizationMember, Profile)
        .join(Profile, Profile.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status != "REMOVED",
        )
        .options(joinedload(OrganizationMember.roles).joinedload(MemberRole.role))
        .order_by(OrganizationMember.joined_at)
    )
    return [(m, p) for m, p in result.unique().all()]


async def count_active_owners(session: AsyncSession, organization_id: UUID) -> int:
    result = await session.execute(
        select(OrganizationMember.id)
        .join(MemberRole, MemberRole.member_id == OrganizationMember.id)
        .join(Role, Role.id == MemberRole.role_id)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "ACTIVE",
            Role.is_default_owner.is_(True),
        )
    )
    return len(result.all())


async def is_member_an_owner(session: AsyncSession, member_id: UUID) -> bool:
    result = await session.execute(
        select(MemberRole.member_id)
        .join(Role, Role.id == MemberRole.role_id)
        .where(MemberRole.member_id == member_id, Role.is_default_owner.is_(True))
    )
    return result.scalar_one_or_none() is not None


async def get_member_by_id(
    session: AsyncSession, member_id: UUID, *, organization_id: UUID
) -> OrganizationMember | None:
    """Acotado a la organización a propósito: sin este filtro, un permiso
    verificado sobre una organización podría intentar mutar un member_id de
    otra. RLS lo bloquearía igual por la columna real de la fila, pero de
    forma menos predecible (una excepción de bajo nivel en vez de "no
    encontrado"). Acotar aquí hace que el caso incorrecto ni siquiera exista.
    """
    result = await session.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def get_invitation_by_id(
    session: AsyncSession, invitation_id: UUID, *, organization_id: UUID
) -> OrganizationInvitation | None:
    result = await session.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


# ── Invitaciones ─────────────────────────────────────────────────────────────


async def get_pending_invitation(
    session: AsyncSession, *, organization_id: UUID, email: str
) -> OrganizationInvitation | None:
    result = await session.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.email == email,
            OrganizationInvitation.status == "PENDING",
        )
    )
    return result.scalar_one_or_none()


async def create_invitation(
    session: AsyncSession,
    *,
    organization_id: UUID,
    email: str,
    role_id: UUID,
    invited_by: UUID,
    token_hash: str,
    expires_at: datetime,
) -> OrganizationInvitation:
    record = OrganizationInvitation(
        organization_id=organization_id,
        email=email,
        role_id=role_id,
        invited_by=invited_by,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(record)
    await session.flush()
    return record


async def get_invitation_by_token_hash(
    session: AsyncSession, token_hash: str
) -> OrganizationInvitation | None:
    result = await session.execute(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.token_hash == token_hash)
        .options(selectinload(OrganizationInvitation.role))
    )
    return result.scalar_one_or_none()


async def list_pending_invitations(
    session: AsyncSession, organization_id: UUID
) -> list[OrganizationInvitation]:
    result = await session.execute(
        select(OrganizationInvitation)
        .where(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.status == "PENDING",
        )
        .options(selectinload(OrganizationInvitation.role))
        .order_by(OrganizationInvitation.created_at.desc())
    )
    return list(result.scalars())
