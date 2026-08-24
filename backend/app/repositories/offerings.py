"""Acceso a datos del catálogo de oferta: supplier_offerings y sus tablas
relacionadas (taxonomía, industrias, territorio, precio, media, documentos,
valores de atributos).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offering import (
    OfferingDocument,
    OfferingIndustry,
    OfferingMedia,
    OfferingPricing,
    OfferingTaxonomyNode,
    OfferingTerritory,
    SupplierOffering,
)
from app.models.offering_attribute import (
    OfferingAttributeOptionValue,
    OfferingAttributeValue,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


# ─── Offerings ───────────────────────────────────────────────────────────────


async def slug_exists(
    session: AsyncSession, *, organization_id: UUID, slug: str
) -> bool:
    result = await session.execute(
        select(SupplierOffering.id).where(
            SupplierOffering.organization_id == organization_id,
            SupplierOffering.slug == slug,
            SupplierOffering.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none() is not None


async def create_offering(session: AsyncSession, **fields: object) -> SupplierOffering:
    offering = SupplierOffering(**fields)
    session.add(offering)
    await session.flush()
    return offering


async def get_offering(
    session: AsyncSession, offering_id: UUID
) -> SupplierOffering | None:
    result = await session.execute(
        select(SupplierOffering).where(
            SupplierOffering.id == offering_id, SupplierOffering.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def list_offerings(
    session: AsyncSession, organization_id: UUID, *, status: str | None = None
) -> list[SupplierOffering]:
    query = select(SupplierOffering).where(
        SupplierOffering.organization_id == organization_id,
        SupplierOffering.deleted_at.is_(None),
    )
    if status:
        query = query.where(SupplierOffering.status == status)
    result = await session.execute(query.order_by(SupplierOffering.created_at.desc()))
    return list(result.scalars())


async def update_offering(offering: SupplierOffering, **fields: object) -> None:
    for key, value in fields.items():
        setattr(offering, key, value)


async def publish_offering(offering: SupplierOffering) -> None:
    offering.status = "ACTIVE"
    offering.published_at = datetime.now(timezone.utc)


async def soft_delete_offering(offering: SupplierOffering) -> None:
    offering.deleted_at = datetime.now(timezone.utc)


# ─── Taxonomía / industrias / territorio ─────────────────────────────────────


async def set_taxonomy_nodes(
    session: AsyncSession, offering_id: UUID, nodes: list[dict]
) -> None:
    """Reemplaza el set completo — más simple y predecible que un diff
    incremental para un formulario que manda la lista completa cada vez."""
    await session.execute(
        delete(OfferingTaxonomyNode).where(
            OfferingTaxonomyNode.offering_id == offering_id
        )
    )
    for node in nodes:
        session.add(
            OfferingTaxonomyNode(
                offering_id=offering_id,
                node_id=node["node_id"],
                is_primary=node.get("is_primary", False),
            )
        )
    await session.flush()


async def list_taxonomy_nodes(
    session: AsyncSession, offering_id: UUID
) -> list[OfferingTaxonomyNode]:
    result = await session.execute(
        select(OfferingTaxonomyNode).where(
            OfferingTaxonomyNode.offering_id == offering_id
        )
    )
    return list(result.scalars())


async def list_taxonomy_nodes_with_names(
    session: AsyncSession, offering_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select otn.node_id, otn.is_primary, tn.name "
            "from public.offering_taxonomy_nodes otn "
            "join public.taxonomy_nodes tn on tn.id = otn.node_id "
            "where otn.offering_id = :offering_id "
            "order by otn.is_primary desc, tn.name"
        ),
        {"offering_id": str(offering_id)},
    )
    return [dict(row._mapping) for row in result]


async def set_industries(
    session: AsyncSession, offering_id: UUID, industry_ids: list[UUID]
) -> None:
    await session.execute(
        delete(OfferingIndustry).where(OfferingIndustry.offering_id == offering_id)
    )
    for industry_id in industry_ids:
        session.add(OfferingIndustry(offering_id=offering_id, industry_id=industry_id))
    await session.flush()


async def list_industries_with_names(
    session: AsyncSession, offering_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select oi.industry_id, i.name "
            "from public.offering_industries oi "
            "join public.industries i on i.id = oi.industry_id "
            "where oi.offering_id = :offering_id "
            "order by i.name"
        ),
        {"offering_id": str(offering_id)},
    )
    return [dict(row._mapping) for row in result]


async def add_territory(session: AsyncSession, **fields: object) -> OfferingTerritory:
    territory = OfferingTerritory(**fields)
    session.add(territory)
    await session.flush()
    return territory


async def list_territories_with_names(
    session: AsyncSession, offering_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select ot.id, ot.admin_division_id, ot.coverage_type, ad.name, ad.level_name "
            "from public.offering_territories ot "
            "join public.admin_divisions ad on ad.id = ot.admin_division_id "
            "where ot.offering_id = :offering_id "
            "order by ad.name"
        ),
        {"offering_id": str(offering_id)},
    )
    return [dict(row._mapping) for row in result]


async def remove_territory(
    session: AsyncSession, territory_id: UUID, *, offering_id: UUID
) -> bool:
    result = await session.execute(
        delete(OfferingTerritory).where(
            OfferingTerritory.id == territory_id,
            OfferingTerritory.offering_id == offering_id,
        )
    )
    return result.rowcount > 0  # type: ignore[attr-defined]


# ─── Precio ──────────────────────────────────────────────────────────────────


async def get_pricing(
    session: AsyncSession, offering_id: UUID
) -> OfferingPricing | None:
    result = await session.execute(
        select(OfferingPricing).where(OfferingPricing.offering_id == offering_id)
    )
    return result.scalar_one_or_none()


async def upsert_pricing(
    session: AsyncSession, offering_id: UUID, **fields: object
) -> OfferingPricing:
    pricing = await get_pricing(session, offering_id)
    if pricing is None:
        pricing = OfferingPricing(offering_id=offering_id, **fields)
        session.add(pricing)
    else:
        for key, value in fields.items():
            setattr(pricing, key, value)
    await session.flush()
    return pricing


# ─── Media / documentos ──────────────────────────────────────────────────────


async def list_media(session: AsyncSession, offering_id: UUID) -> list[OfferingMedia]:
    result = await session.execute(
        select(OfferingMedia)
        .where(OfferingMedia.offering_id == offering_id)
        .order_by(OfferingMedia.sort_order)
    )
    return list(result.scalars())


async def create_media(session: AsyncSession, **fields: object) -> OfferingMedia:
    media = OfferingMedia(**fields)
    session.add(media)
    await session.flush()
    return media


async def get_media(
    session: AsyncSession, media_id: UUID, *, offering_id: UUID
) -> OfferingMedia | None:
    result = await session.execute(
        select(OfferingMedia).where(
            OfferingMedia.id == media_id, OfferingMedia.offering_id == offering_id
        )
    )
    return result.scalar_one_or_none()


async def delete_media(session: AsyncSession, media: OfferingMedia) -> None:
    await session.delete(media)


async def list_documents(
    session: AsyncSession, offering_id: UUID
) -> list[OfferingDocument]:
    result = await session.execute(
        select(OfferingDocument).where(OfferingDocument.offering_id == offering_id)
    )
    return list(result.scalars())


async def create_document(session: AsyncSession, **fields: object) -> OfferingDocument:
    document = OfferingDocument(**fields)
    session.add(document)
    await session.flush()
    return document


async def get_document(
    session: AsyncSession, document_id: UUID, *, offering_id: UUID
) -> OfferingDocument | None:
    result = await session.execute(
        select(OfferingDocument).where(
            OfferingDocument.id == document_id,
            OfferingDocument.offering_id == offering_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_document(session: AsyncSession, document: OfferingDocument) -> None:
    await session.delete(document)


# ─── Valores de atributos ─────────────────────────────────────────────────────


async def upsert_attribute_value(
    session: AsyncSession,
    *,
    offering_id: UUID,
    attribute_definition_id: UUID,
    **slots: object,
) -> OfferingAttributeValue:
    result = await session.execute(
        select(OfferingAttributeValue).where(
            OfferingAttributeValue.offering_id == offering_id,
            OfferingAttributeValue.attribute_definition_id == attribute_definition_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = OfferingAttributeValue(
            offering_id=offering_id,
            attribute_definition_id=attribute_definition_id,
            **slots,
        )
        session.add(row)
    else:
        # Limpiar todos los slots antes de fijar el nuevo — el trigger de
        # validación exige que a lo más uno esté poblado en todo momento.
        for slot in (
            "value_text",
            "value_number",
            "value_boolean",
            "value_date",
            "option_id",
        ):
            setattr(row, slot, None)
        for key, value in slots.items():
            setattr(row, key, value)
    await session.flush()
    return row


async def set_multiselect_options(
    session: AsyncSession, offering_attribute_value_id: UUID, option_ids: list[UUID]
) -> None:
    await session.execute(
        delete(OfferingAttributeOptionValue).where(
            OfferingAttributeOptionValue.offering_attribute_value_id
            == offering_attribute_value_id
        )
    )
    for option_id in option_ids:
        session.add(
            OfferingAttributeOptionValue(
                offering_attribute_value_id=offering_attribute_value_id,
                option_id=option_id,
            )
        )
    await session.flush()


async def list_attribute_values(session: AsyncSession, offering_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            select
              v.id, v.attribute_definition_id, ad.code, ad.name, ad.data_type,
              v.value_text, v.value_number, v.value_boolean, v.value_date, v.option_id,
              coalesce(
                array_agg(oaov.option_id) filter (where oaov.option_id is not null),
                array[]::uuid[]
              ) as multiselect_option_ids
            from public.offering_attribute_values v
            join public.attribute_definitions ad on ad.id = v.attribute_definition_id
            left join public.offering_attribute_option_values oaov
              on oaov.offering_attribute_value_id = v.id
            where v.offering_id = :offering_id
            group by v.id, ad.code, ad.name, ad.data_type
            """
        ),
        {"offering_id": str(offering_id)},
    )
    return [dict(row._mapping) for row in result]
