"""Acceso a datos de políticas de aprobación, awards, sus líneas y los pasos
de aprobación (fase 8.6/8.7)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awards import (
    Award,
    AwardApproval,
    AwardItem,
    OrganizationApprovalPolicy,
)
from app.models.rbac import MemberRole, OrganizationMember, Role


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


# ─── Awards ─────────────────────────────────────────────────────────────────


async def create_award(session: AsyncSession, **fields: object) -> Award:
    award = Award(**fields)
    session.add(award)
    await session.flush()
    return award


async def get_award(session: AsyncSession, award_id: UUID) -> Award | None:
    result = await session.execute(select(Award).where(Award.id == award_id))
    return result.scalar_one_or_none()


async def update_award(award: Award, **fields: object) -> None:
    for key, value in fields.items():
        setattr(award, key, value)


async def list_awards_for_event(
    session: AsyncSession, sourcing_event_id: UUID
) -> list[Award]:
    result = await session.execute(
        select(Award)
        .where(Award.sourcing_event_id == sourcing_event_id)
        .order_by(Award.proposed_at.desc())
    )
    return list(result.scalars())


# ─── Líneas del award (append-only) ──────────────────────────────────────────


async def add_award_item(session: AsyncSession, **fields: object) -> AwardItem:
    item = AwardItem(**fields)
    session.add(item)
    await session.flush()
    return item


async def list_award_items(session: AsyncSession, award_id: UUID) -> list[AwardItem]:
    result = await session.execute(
        select(AwardItem).where(AwardItem.award_id == award_id)
    )
    return list(result.scalars())


# ─── Pasos de aprobación ─────────────────────────────────────────────────────


async def create_approval_step(
    session: AsyncSession, **fields: object
) -> AwardApproval:
    approval = AwardApproval(**fields)
    session.add(approval)
    await session.flush()
    return approval


async def list_approvals_for_award(
    session: AsyncSession, award_id: UUID
) -> list[AwardApproval]:
    result = await session.execute(
        select(AwardApproval)
        .where(AwardApproval.award_id == award_id)
        .order_by(AwardApproval.step_order)
    )
    return list(result.scalars())


async def get_approval(
    session: AsyncSession, approval_id: UUID
) -> AwardApproval | None:
    result = await session.execute(
        select(AwardApproval).where(AwardApproval.id == approval_id)
    )
    return result.scalar_one_or_none()


async def update_approval(approval: AwardApproval, **fields: object) -> None:
    for key, value in fields.items():
        setattr(approval, key, value)


async def list_pending_approvals_for_member(
    session: AsyncSession, organization_member_id: UUID
) -> list[AwardApproval]:
    result = await session.execute(
        select(AwardApproval)
        .where(
            AwardApproval.approver_member_id == organization_member_id,
            AwardApproval.status == "PENDING",
        )
        .order_by(AwardApproval.created_at)
    )
    return list(result.scalars())


async def find_eligible_approver(
    session: AsyncSession,
    organization_id: UUID,
    required_role_code: str,
    amount_base: float,
) -> OrganizationMember | None:
    """El miembro ACTIVO con rol `required_role_code` y
    `approval_limit_amount` suficiente para cubrir `amount_base`, priorizando
    el de MENOR límite que igual alcanza — evita escalar siempre al de mayor
    jerarquía cuando uno más chico ya podría aprobar. `approval_limit_amount`
    NULL (según el comentario original de 0005_rbac.sql) significa "no puede
    aprobar montos", así que queda excluido por el `is_not(None)`."""
    result = await session.execute(
        select(OrganizationMember)
        .join(MemberRole, MemberRole.member_id == OrganizationMember.id)
        .join(Role, Role.id == MemberRole.role_id)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "ACTIVE",
            Role.code == required_role_code,
            OrganizationMember.approval_limit_amount.is_not(None),
            OrganizationMember.approval_limit_amount >= amount_base,
        )
        .order_by(OrganizationMember.approval_limit_amount.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ─── Políticas de aprobación ──────────────────────────────────────────────────


async def list_policies(
    session: AsyncSession, organization_id: UUID
) -> list[OrganizationApprovalPolicy]:
    result = await session.execute(
        select(OrganizationApprovalPolicy)
        .where(OrganizationApprovalPolicy.organization_id == organization_id)
        .order_by(OrganizationApprovalPolicy.step_order)
    )
    return list(result.scalars())


async def create_policy(
    session: AsyncSession, **fields: object
) -> OrganizationApprovalPolicy:
    policy = OrganizationApprovalPolicy(**fields)
    session.add(policy)
    await session.flush()
    return policy


async def update_policy(policy: OrganizationApprovalPolicy, **fields: object) -> None:
    for key, value in fields.items():
        setattr(policy, key, value)
