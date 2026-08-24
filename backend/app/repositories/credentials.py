"""Acceso a datos de certificaciones, referencias de clientes y casos de
éxito.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credentials import (
    CaseStudy,
    CaseStudyMedia,
    CaseStudyTaxonomyNode,
    CertificationType,
    ClientReference,
    OrganizationCertification,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


# ─── Tipos de certificación (catálogo de plataforma) ─────────────────────────


async def list_certification_types(session: AsyncSession) -> list[CertificationType]:
    result = await session.execute(
        select(CertificationType)
        .where(CertificationType.is_active.is_(True))
        .order_by(CertificationType.name)
    )
    return list(result.scalars())


# ─── Certificaciones de la empresa ────────────────────────────────────────────


async def list_certifications(
    session: AsyncSession, organization_id: UUID
) -> list[OrganizationCertification]:
    result = await session.execute(
        select(OrganizationCertification)
        .where(OrganizationCertification.organization_id == organization_id)
        .order_by(OrganizationCertification.created_at.desc())
    )
    return list(result.scalars())


async def create_certification(
    session: AsyncSession, **fields: object
) -> OrganizationCertification:
    row = OrganizationCertification(**fields)
    session.add(row)
    await session.flush()
    return row


async def get_certification(
    session: AsyncSession, certification_id: UUID, *, organization_id: UUID
) -> OrganizationCertification | None:
    result = await session.execute(
        select(OrganizationCertification).where(
            OrganizationCertification.id == certification_id,
            OrganizationCertification.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_certification(
    session: AsyncSession, row: OrganizationCertification
) -> None:
    await session.delete(row)


# ─── Referencias de clientes ──────────────────────────────────────────────────


async def list_client_references(
    session: AsyncSession, organization_id: UUID
) -> list[ClientReference]:
    result = await session.execute(
        select(ClientReference).where(
            ClientReference.organization_id == organization_id
        )
    )
    return list(result.scalars())


async def create_client_reference(
    session: AsyncSession, **fields: object
) -> ClientReference:
    row = ClientReference(**fields)
    session.add(row)
    await session.flush()
    return row


async def delete_client_reference(
    session: AsyncSession, reference_id: UUID, *, organization_id: UUID
) -> bool:
    result = await session.execute(
        delete(ClientReference).where(
            ClientReference.id == reference_id,
            ClientReference.organization_id == organization_id,
        )
    )
    return result.rowcount > 0  # type: ignore[attr-defined]


# ─── Casos de éxito ────────────────────────────────────────────────────────────


async def list_case_studies(
    session: AsyncSession, organization_id: UUID
) -> list[CaseStudy]:
    result = await session.execute(
        select(CaseStudy)
        .where(CaseStudy.organization_id == organization_id)
        .order_by(CaseStudy.created_at.desc())
    )
    return list(result.scalars())


async def create_case_study(session: AsyncSession, **fields: object) -> CaseStudy:
    row = CaseStudy(**fields)
    session.add(row)
    await session.flush()
    return row


async def get_case_study(
    session: AsyncSession, case_study_id: UUID, *, organization_id: UUID
) -> CaseStudy | None:
    result = await session.execute(
        select(CaseStudy).where(
            CaseStudy.id == case_study_id, CaseStudy.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()


async def update_case_study(case_study: CaseStudy, **fields: object) -> None:
    for key, value in fields.items():
        setattr(case_study, key, value)


async def delete_case_study(session: AsyncSession, case_study: CaseStudy) -> None:
    await session.delete(case_study)


async def set_case_study_taxonomy(
    session: AsyncSession, case_study_id: UUID, node_ids: list[UUID]
) -> None:
    await session.execute(
        delete(CaseStudyTaxonomyNode).where(
            CaseStudyTaxonomyNode.case_study_id == case_study_id
        )
    )
    for node_id in node_ids:
        session.add(CaseStudyTaxonomyNode(case_study_id=case_study_id, node_id=node_id))
    await session.flush()


async def list_case_study_media(
    session: AsyncSession, case_study_id: UUID
) -> list[CaseStudyMedia]:
    result = await session.execute(
        select(CaseStudyMedia)
        .where(CaseStudyMedia.case_study_id == case_study_id)
        .order_by(CaseStudyMedia.sort_order)
    )
    return list(result.scalars())


async def create_case_study_media(
    session: AsyncSession, **fields: object
) -> CaseStudyMedia:
    row = CaseStudyMedia(**fields)
    session.add(row)
    await session.flush()
    return row


async def get_case_study_media(
    session: AsyncSession, media_id: UUID, *, case_study_id: UUID
) -> CaseStudyMedia | None:
    result = await session.execute(
        select(CaseStudyMedia).where(
            CaseStudyMedia.id == media_id, CaseStudyMedia.case_study_id == case_study_id
        )
    )
    return result.scalar_one_or_none()


async def delete_case_study_media(session: AsyncSession, media: CaseStudyMedia) -> None:
    await session.delete(media)
