"""Acceso a datos de ubicaciones, contactos, media, settings, industrias y
territorios de una organización.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_profile import (
    OrganizationContact,
    OrganizationIndustry,
    OrganizationLocation,
    OrganizationMedia,
    OrganizationSettings,
    OrganizationTerritory,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def create_default_settings(session: AsyncSession, organization_id: UUID) -> None:
    session.add(OrganizationSettings(organization_id=organization_id))
    await session.flush()


# ─── Ubicaciones ─────────────────────────────────────────────────────────────


async def list_locations(
    session: AsyncSession, organization_id: UUID
) -> list[OrganizationLocation]:
    result = await session.execute(
        select(OrganizationLocation)
        .where(
            OrganizationLocation.organization_id == organization_id,
            OrganizationLocation.is_active,
        )
        .order_by(
            OrganizationLocation.is_headquarters.desc(), OrganizationLocation.created_at
        )
    )
    return list(result.scalars())


async def create_location(
    session: AsyncSession, **fields: object
) -> OrganizationLocation:
    location = OrganizationLocation(**fields)
    session.add(location)
    await session.flush()
    return location


async def get_location(
    session: AsyncSession, location_id: UUID, *, organization_id: UUID
) -> OrganizationLocation | None:
    result = await session.execute(
        select(OrganizationLocation).where(
            OrganizationLocation.id == location_id,
            OrganizationLocation.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_location(location: OrganizationLocation, **fields: object) -> None:
    for key, value in fields.items():
        setattr(location, key, value)


async def deactivate_location(location: OrganizationLocation) -> None:
    location.is_active = False


# ─── Contactos ───────────────────────────────────────────────────────────────


async def list_contacts(
    session: AsyncSession, organization_id: UUID
) -> list[OrganizationContact]:
    result = await session.execute(
        select(OrganizationContact)
        .where(
            OrganizationContact.organization_id == organization_id,
            OrganizationContact.is_active,
        )
        .order_by(OrganizationContact.is_primary.desc(), OrganizationContact.created_at)
    )
    return list(result.scalars())


async def create_contact(
    session: AsyncSession, **fields: object
) -> OrganizationContact:
    contact = OrganizationContact(**fields)
    session.add(contact)
    await session.flush()
    return contact


async def get_contact(
    session: AsyncSession, contact_id: UUID, *, organization_id: UUID
) -> OrganizationContact | None:
    result = await session.execute(
        select(OrganizationContact).where(
            OrganizationContact.id == contact_id,
            OrganizationContact.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_contact(contact: OrganizationContact, **fields: object) -> None:
    for key, value in fields.items():
        setattr(contact, key, value)


async def deactivate_contact(contact: OrganizationContact) -> None:
    contact.is_active = False


# ─── Media ───────────────────────────────────────────────────────────────────


async def list_media(
    session: AsyncSession, organization_id: UUID
) -> list[OrganizationMedia]:
    result = await session.execute(
        select(OrganizationMedia)
        .where(OrganizationMedia.organization_id == organization_id)
        .order_by(OrganizationMedia.media_type, OrganizationMedia.sort_order)
    )
    return list(result.scalars())


async def replace_singleton_media(
    session: AsyncSession, *, organization_id: UUID, media_type: str
) -> None:
    """LOGO y BANNER son 1:1 (índice único parcial en la base) — subir uno
    nuevo reemplaza al anterior. Se borra la fila vieja antes de insertar la
    nueva en vez de hacer upsert, porque el storage_path físico también hay
    que borrarlo del bucket (ver services/organization_profile.py).
    """
    result = await session.execute(
        select(OrganizationMedia).where(
            OrganizationMedia.organization_id == organization_id,
            OrganizationMedia.media_type == media_type,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        await session.execute(
            delete(OrganizationMedia).where(OrganizationMedia.id == existing.id)
        )
    await session.flush()


async def create_media(session: AsyncSession, **fields: object) -> OrganizationMedia:
    media = OrganizationMedia(**fields)
    session.add(media)
    await session.flush()
    return media


async def get_media(
    session: AsyncSession, media_id: UUID, *, organization_id: UUID
) -> OrganizationMedia | None:
    result = await session.execute(
        select(OrganizationMedia).where(
            OrganizationMedia.id == media_id,
            OrganizationMedia.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_media(session: AsyncSession, media: OrganizationMedia) -> None:
    await session.delete(media)


# ─── Industrias y territorios ────────────────────────────────────────────────


async def list_industries(session: AsyncSession, organization_id: UUID) -> list[dict]:
    # Join a industries por el nombre — evita que el frontend tenga que
    # descargar el árbol completo y aplanarlo solo para mostrar una etiqueta.
    result = await session.execute(
        text(
            "select oi.industry_id, oi.years_experience, oi.is_primary, i.name "
            "from public.organization_industries oi "
            "join public.industries i on i.id = oi.industry_id "
            "where oi.organization_id = :org_id "
            "order by i.name"
        ),
        {"org_id": str(organization_id)},
    )
    return [dict(row._mapping) for row in result]


async def upsert_industry(
    session: AsyncSession,
    *,
    organization_id: UUID,
    industry_id: UUID,
    years_experience: int | None,
    is_primary: bool,
) -> OrganizationIndustry:
    result = await session.execute(
        select(OrganizationIndustry).where(
            OrganizationIndustry.organization_id == organization_id,
            OrganizationIndustry.industry_id == industry_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = OrganizationIndustry(
            organization_id=organization_id,
            industry_id=industry_id,
            years_experience=years_experience,
            is_primary=is_primary,
        )
        session.add(row)
    else:
        row.years_experience = years_experience
        row.is_primary = is_primary
    await session.flush()
    return row


async def remove_industry(
    session: AsyncSession, *, organization_id: UUID, industry_id: UUID
) -> None:
    await session.execute(
        delete(OrganizationIndustry).where(
            OrganizationIndustry.organization_id == organization_id,
            OrganizationIndustry.industry_id == industry_id,
        )
    )


async def list_territories(session: AsyncSession, organization_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select ot.id, ot.admin_division_id, ad.name, ad.level_name "
            "from public.organization_territories ot "
            "join public.admin_divisions ad on ad.id = ot.admin_division_id "
            "where ot.organization_id = :org_id "
            "order by ad.name"
        ),
        {"org_id": str(organization_id)},
    )
    return [dict(row._mapping) for row in result]


async def add_territory(
    session: AsyncSession, *, organization_id: UUID, admin_division_id: UUID
) -> OrganizationTerritory:
    territory = OrganizationTerritory(
        organization_id=organization_id, admin_division_id=admin_division_id
    )
    session.add(territory)
    await session.flush()
    return territory


async def remove_territory(
    session: AsyncSession, territory_id: UUID, *, organization_id: UUID
) -> bool:
    result = await session.execute(
        delete(OrganizationTerritory).where(
            OrganizationTerritory.id == territory_id,
            OrganizationTerritory.organization_id == organization_id,
        )
    )
    return result.rowcount > 0  # type: ignore[attr-defined]
