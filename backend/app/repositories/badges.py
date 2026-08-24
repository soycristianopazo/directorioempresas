"""Badges de confianza (fase 5.9)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import BadgeDefinition, OrganizationBadge


async def list_badge_definitions(session: AsyncSession) -> list[BadgeDefinition]:
    result = await session.execute(
        select(BadgeDefinition).where(BadgeDefinition.is_active.is_(True))
    )
    return list(result.scalars())


async def get_active_grant(
    session: AsyncSession, organization_id: UUID, badge_id: UUID
) -> OrganizationBadge | None:
    result = await session.execute(
        select(OrganizationBadge).where(
            OrganizationBadge.organization_id == organization_id,
            OrganizationBadge.badge_id == badge_id,
            OrganizationBadge.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def grant_badge(session: AsyncSession, **fields: object) -> OrganizationBadge:
    grant = OrganizationBadge(**fields)
    session.add(grant)
    await session.flush()
    return grant


async def revoke_badge(grant: OrganizationBadge) -> None:
    grant.revoked_at = datetime.now(timezone.utc)


async def list_org_badges(session: AsyncSession, organization_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select ob.id, ob.badge_id, ob.granted_at, ob.expires_at, "
            "       bd.code, bd.name, bd.description, bd.icon "
            "from public.organization_badges ob "
            "join public.badge_definitions bd on bd.id = ob.badge_id "
            "where ob.organization_id = :org_id and ob.revoked_at is null "
            "order by ob.granted_at desc"
        ),
        {"org_id": str(organization_id)},
    )
    return [dict(row._mapping) for row in result]
