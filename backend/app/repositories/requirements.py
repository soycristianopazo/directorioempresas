"""Acceso a datos de requirements y sus líneas/ubicaciones/documentos
(fase 6.1)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirements import (
    Requirement,
    RequirementDocument,
    RequirementItem,
    RequirementLocation,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def list_requirements(
    session: AsyncSession, organization_id: UUID
) -> list[Requirement]:
    result = await session.execute(
        select(Requirement)
        .where(Requirement.organization_id == organization_id)
        .order_by(Requirement.created_at.desc())
    )
    return list(result.scalars())


async def get_requirement(
    session: AsyncSession, requirement_id: UUID
) -> Requirement | None:
    result = await session.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    return result.scalar_one_or_none()


async def create_requirement(session: AsyncSession, **fields: object) -> Requirement:
    requirement = Requirement(**fields)
    session.add(requirement)
    await session.flush()
    return requirement


async def update_requirement(requirement: Requirement, **fields: object) -> None:
    for key, value in fields.items():
        setattr(requirement, key, value)


async def list_items(
    session: AsyncSession, requirement_id: UUID
) -> list[RequirementItem]:
    result = await session.execute(
        select(RequirementItem)
        .where(RequirementItem.requirement_id == requirement_id)
        .order_by(RequirementItem.sort_order)
    )
    return list(result.scalars())


async def add_item(session: AsyncSession, **fields: object) -> RequirementItem:
    item = RequirementItem(**fields)
    session.add(item)
    await session.flush()
    return item


async def list_locations(
    session: AsyncSession, requirement_id: UUID
) -> list[RequirementLocation]:
    result = await session.execute(
        select(RequirementLocation).where(
            RequirementLocation.requirement_id == requirement_id
        )
    )
    return list(result.scalars())


async def add_location(session: AsyncSession, **fields: object) -> RequirementLocation:
    location = RequirementLocation(**fields)
    session.add(location)
    await session.flush()
    return location


async def list_documents(
    session: AsyncSession, requirement_id: UUID
) -> list[RequirementDocument]:
    result = await session.execute(
        select(RequirementDocument).where(
            RequirementDocument.requirement_id == requirement_id
        )
    )
    return list(result.scalars())


async def add_document(session: AsyncSession, **fields: object) -> RequirementDocument:
    document = RequirementDocument(**fields)
    session.add(document)
    await session.flush()
    return document
