"""Repositorio único de evidencia documental (fase 5.1/5.2)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import (
    DocumentType,
    OrganizationDocument,
    OrganizationDocumentVersion,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def list_document_types(session: AsyncSession) -> list[DocumentType]:
    result = await session.execute(
        select(DocumentType)
        .where(DocumentType.is_active.is_(True))
        .order_by(DocumentType.category, DocumentType.name)
    )
    return list(result.scalars())


async def get_document_type(
    session: AsyncSession, document_type_id: UUID
) -> DocumentType | None:
    result = await session.execute(
        select(DocumentType).where(DocumentType.id == document_type_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_document(
    session: AsyncSession, *, organization_id: UUID, document_type_id: UUID
) -> OrganizationDocument:
    result = await session.execute(
        select(OrganizationDocument).where(
            OrganizationDocument.organization_id == organization_id,
            OrganizationDocument.document_type_id == document_type_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is not None:
        return document
    document = OrganizationDocument(
        organization_id=organization_id, document_type_id=document_type_id
    )
    session.add(document)
    await session.flush()
    return document


async def list_documents_with_types(
    session: AsyncSession, organization_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select od.id, od.document_type_id, dt.code, dt.name, dt.category, "
            "       dt.requires_expiry, dt.is_sensitive, "
            "       v.id as active_version_id, v.valid_until, v.issued_at, v.status as version_status "
            "from public.organization_documents od "
            "join public.document_types dt on dt.id = od.document_type_id "
            "left join lateral ("
            "  select ov.id, ov.valid_until, ov.issued_at, ov.status "
            "  from public.organization_document_versions ov "
            "  where ov.document_id = od.id and ov.status = 'ACTIVE' "
            "  order by ov.created_at desc limit 1"
            ") v on true "
            "where od.organization_id = :org_id "
            "order by dt.category, dt.name"
        ),
        {"org_id": str(organization_id)},
    )
    return [dict(row._mapping) for row in result]


async def list_versions(
    session: AsyncSession, document_id: UUID
) -> list[OrganizationDocumentVersion]:
    result = await session.execute(
        select(OrganizationDocumentVersion)
        .where(OrganizationDocumentVersion.document_id == document_id)
        .order_by(OrganizationDocumentVersion.created_at.desc())
    )
    return list(result.scalars())


async def get_version(
    session: AsyncSession, version_id: UUID
) -> OrganizationDocumentVersion | None:
    result = await session.execute(
        select(OrganizationDocumentVersion).where(
            OrganizationDocumentVersion.id == version_id
        )
    )
    return result.scalar_one_or_none()


async def supersede_active_versions(session: AsyncSession, document_id: UUID) -> None:
    await session.execute(
        text(
            "update public.organization_document_versions "
            "set status = 'SUPERSEDED' "
            "where document_id = :document_id and status = 'ACTIVE'"
        ),
        {"document_id": str(document_id)},
    )


async def create_version(
    session: AsyncSession, **fields: object
) -> OrganizationDocumentVersion:
    version = OrganizationDocumentVersion(**fields)
    session.add(version)
    await session.flush()
    return version
