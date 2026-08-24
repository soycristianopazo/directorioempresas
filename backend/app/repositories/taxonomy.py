"""Acceso a datos de taxonomía (qué se vende), industrias (a quién se le
vende) y atributos dinámicos.

Lectura: árbol completo en memoria (el volumen — decenas/centenas de nodos,
no miles — no justifica una CTE recursiva; se arma en el servicio a partir de
level/parent_id/path, ya ordenado por path).

Escritura: solo para platform admin, nunca DELETE — ver deactivate_*
(gobernanza §D.5 de docs/02-MODELO-DATOS.md: los nodos no se borran).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute import (
    AttributeDefinition,
    AttributeOption,
    TaxonomyNodeAttribute,
)
from app.models.taxonomy import Industry, TaxonomyNode


async def has_platform_permission(session: AsyncSession, permission_code: str) -> bool:
    """Espejo de app.has_platform_permission() del SQL (0018).

    Se verifica ANTES de mutar, mismo motivo que orgs_repo.has_permission():
    evita el StaleDataError de un flush que RLS bloquea después del hecho.
    """
    result = await session.execute(
        text("select app.has_platform_permission(:perm)"),
        {"perm": permission_code},
    )
    return bool(result.scalar_one())


# ─── Taxonomy nodes ─────────────────────────────────────────────────────────


async def list_active_taxonomy_nodes(session: AsyncSession) -> list[TaxonomyNode]:
    result = await session.execute(
        select(TaxonomyNode)
        .where(TaxonomyNode.is_active.is_(True))
        .order_by(TaxonomyNode.path)
    )
    return list(result.scalars())


async def get_taxonomy_node(
    session: AsyncSession, node_id: UUID
) -> TaxonomyNode | None:
    return await session.get(TaxonomyNode, node_id)


async def taxonomy_slug_exists(
    session: AsyncSession, *, parent_id: UUID | None, slug: str
) -> bool:
    query = select(TaxonomyNode.id).where(TaxonomyNode.slug == slug)
    query = (
        query.where(TaxonomyNode.parent_id.is_(None))
        if parent_id is None
        else query.where(TaxonomyNode.parent_id == parent_id)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def create_taxonomy_node(
    session: AsyncSession,
    *,
    parent_id: UUID | None,
    slug: str,
    name: str,
    node_type: str,
    description: str | None = None,
    risk_level: str | None = None,
    sort_order: int = 0,
) -> TaxonomyNode:
    node = TaxonomyNode(
        parent_id=parent_id,
        slug=slug,
        name=name,
        node_type=node_type,
        description=description,
        risk_level=risk_level,
        sort_order=sort_order,
        # level/path NO se pasan: los calcula app.maintain_hierarchy_path()
        # en el propio INSERT (trigger BEFORE INSERT). Dejar el atributo sin
        # tocar es justamente lo que hace que SQLAlchemy lo omita del INSERT
        # en vez de mandar un valor — mandar cualquier valor, incluso "" como
        # placeholder, revienta: asyncpg compila el bind como ::VARCHAR (el
        # tipo Python-side del mapped_column) y Postgres no tiene cast
        # implícito varchar→ltree para un parámetro preparado, así que el
        # INSERT falla en el PREPARE antes de que el trigger llegue a
        # sobreescribirlo. Sin la columna en el INSERT, Postgres la trata
        # como no especificada (NULL) hasta que el trigger la fija — y el
        # NOT NULL se valida DESPUÉS de que el trigger corre, no antes.
    )
    session.add(node)
    await session.flush()
    await session.refresh(node)
    return node


async def update_taxonomy_node(
    session: AsyncSession, node_id: UUID, **fields: object
) -> TaxonomyNode | None:
    node = await session.get(TaxonomyNode, node_id)
    if node is None:
        return None
    for key, value in fields.items():
        setattr(node, key, value)
    await session.flush()
    return node


async def deactivate_taxonomy_node(session: AsyncSession, node_id: UUID) -> bool:
    node = await session.get(TaxonomyNode, node_id)
    if node is None:
        return False
    node.is_active = False
    await session.flush()
    return True


# ─── Industries ─────────────────────────────────────────────────────────────


async def list_active_industries(session: AsyncSession) -> list[Industry]:
    result = await session.execute(
        select(Industry).where(Industry.is_active.is_(True)).order_by(Industry.path)
    )
    return list(result.scalars())


async def get_industry(session: AsyncSession, industry_id: UUID) -> Industry | None:
    return await session.get(Industry, industry_id)


async def industry_slug_exists(
    session: AsyncSession, *, parent_id: UUID | None, slug: str
) -> bool:
    query = select(Industry.id).where(Industry.slug == slug)
    query = (
        query.where(Industry.parent_id.is_(None))
        if parent_id is None
        else query.where(Industry.parent_id == parent_id)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def create_industry(
    session: AsyncSession,
    *,
    parent_id: UUID | None,
    slug: str,
    name: str,
    sort_order: int = 0,
) -> Industry:
    industry = Industry(
        parent_id=parent_id,
        slug=slug,
        name=name,
        sort_order=sort_order,
        # level/path sin tocar a propósito — ver el comentario en
        # create_taxonomy_node más arriba.
    )
    session.add(industry)
    await session.flush()
    await session.refresh(industry)
    return industry


async def update_industry(
    session: AsyncSession, industry_id: UUID, **fields: object
) -> Industry | None:
    industry = await session.get(Industry, industry_id)
    if industry is None:
        return None
    for key, value in fields.items():
        setattr(industry, key, value)
    await session.flush()
    return industry


async def deactivate_industry(session: AsyncSession, industry_id: UUID) -> bool:
    industry = await session.get(Industry, industry_id)
    if industry is None:
        return False
    industry.is_active = False
    await session.flush()
    return True


# ─── Atributos ──────────────────────────────────────────────────────────────


class EffectiveAttributeRow:
    """Fila de v_effective_node_attributes ⋈ attribute_definitions.

    Las anotaciones de tipo junto a __slots__ son lo que le permite a mypy
    reconocer estos atributos en vez de reportarlos como inexistentes: los
    asigna dinámicamente __init__ vía setattr/getattr en un loop, no como
    asignaciones explícitas que mypy pueda inferir por sí solo.
    """

    __slots__ = (
        "attribute_definition_id",
        "code",
        "name",
        "data_type",
        "unit_code",
        "min_value",
        "max_value",
        "is_filterable",
        "is_comparable",
        "help_text",
        "applies_to",
        "is_required",
        "is_direct",
        "filter_weight",
        "sort_order",
    )

    attribute_definition_id: UUID
    code: str
    name: str
    data_type: str
    unit_code: str | None
    min_value: float | None
    max_value: float | None
    is_filterable: bool
    is_comparable: bool
    help_text: str | None
    applies_to: str
    is_required: bool
    is_direct: bool
    filter_weight: int
    sort_order: int

    def __init__(self, row: object) -> None:
        for field in self.__slots__:
            setattr(self, field, getattr(row, field))


async def list_effective_attributes(
    session: AsyncSession, node_id: UUID
) -> list[EffectiveAttributeRow]:
    result = await session.execute(
        text(
            """
            select
              ad.id as attribute_definition_id,
              ad.code, ad.name, ad.data_type, ad.unit_code,
              ad.min_value, ad.max_value, ad.is_filterable, ad.is_comparable, ad.help_text,
              v.applies_to, v.is_required, v.is_direct, v.filter_weight, v.sort_order
            from public.v_effective_node_attributes v
            join public.attribute_definitions ad on ad.id = v.attribute_definition_id
            where v.node_id = :node_id
            order by v.sort_order, ad.name
            """
        ),
        {"node_id": str(node_id)},
    )
    return [EffectiveAttributeRow(row) for row in result]


async def list_attribute_options_by_definitions(
    session: AsyncSession, attribute_definition_ids: list[UUID]
) -> dict[UUID, list[AttributeOption]]:
    if not attribute_definition_ids:
        return {}
    result = await session.execute(
        select(AttributeOption)
        .where(
            AttributeOption.attribute_definition_id.in_(attribute_definition_ids),
            AttributeOption.is_active.is_(True),
        )
        .order_by(AttributeOption.sort_order)
    )
    grouped: dict[UUID, list[AttributeOption]] = {}
    for option in result.scalars():
        grouped.setdefault(option.attribute_definition_id, []).append(option)
    return grouped


async def attribute_code_exists(session: AsyncSession, code: str) -> bool:
    result = await session.execute(
        select(AttributeDefinition.id).where(AttributeDefinition.code == code)
    )
    return result.scalar_one_or_none() is not None


async def create_attribute_definition(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    data_type: str,
    unit_code: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    is_filterable: bool = False,
    is_comparable: bool = False,
    help_text: str | None = None,
) -> AttributeDefinition:
    definition = AttributeDefinition(
        code=code,
        name=name,
        data_type=data_type,
        unit_code=unit_code,
        min_value=min_value,
        max_value=max_value,
        is_filterable=is_filterable,
        is_comparable=is_comparable,
        help_text=help_text,
    )
    session.add(definition)
    await session.flush()
    return definition


async def create_attribute_option(
    session: AsyncSession,
    *,
    attribute_definition_id: UUID,
    value: str,
    label: str,
    sort_order: int = 0,
) -> AttributeOption:
    option = AttributeOption(
        attribute_definition_id=attribute_definition_id,
        value=value,
        label=label,
        sort_order=sort_order,
    )
    session.add(option)
    await session.flush()
    return option


async def link_attribute_to_node(
    session: AsyncSession,
    *,
    node_id: UUID,
    attribute_definition_id: UUID,
    applies_to: str,
    is_required: bool = False,
    is_inherited: bool = True,
    filter_weight: int = 0,
    sort_order: int = 0,
) -> TaxonomyNodeAttribute:
    link = TaxonomyNodeAttribute(
        node_id=node_id,
        attribute_definition_id=attribute_definition_id,
        applies_to=applies_to,
        is_required=is_required,
        is_inherited=is_inherited,
        filter_weight=filter_weight,
        sort_order=sort_order,
    )
    session.add(link)
    await session.flush()
    return link
