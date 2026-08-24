"""Lectura pública del árbol de taxonomía/industrias y administración
(platform admin) de categorías, industrias y atributos dinámicos.

El chequeo de permiso ocurre ANTES de mutar (mismo motivo que
services/organizations.py: evita el StaleDataError de un flush bloqueado por
RLS después del hecho), dentro de session_for_user(user_id) — así
app.has_platform_permission() lee la identidad correcta vía SET LOCAL.
"""

from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.rls import session_for_user
from app.repositories import taxonomy as taxonomy_repo

PERMISSION_MANAGE_TAXONOMY = "platform.manage_taxonomy"

SELECT_LIKE_TYPES = {"SELECT", "MULTISELECT"}


class TaxonomyError(Exception):
    """Base — capturarla sola solo cuando de verdad no importa distinguir el
    motivo. Los routers deben capturar las subclases concretas primero, para
    devolver 403/404/409 en vez de un único código genérico.
    """


class TaxonomyPermissionError(TaxonomyError):
    pass


class TaxonomyNotFoundError(TaxonomyError):
    pass


class TaxonomyConflictError(TaxonomyError):
    pass


class TaxonomyValidationError(TaxonomyError):
    pass


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "nodo"


def _build_tree(rows: list, id_attr: str = "id") -> list[dict]:
    """Arma el árbol en memoria a partir de una lista plana ya ordenada por
    `path` (orden de un recorrido en profundidad). Evita una CTE recursiva:
    a la escala de esta fase (decenas/centenas de nodos) es más simple y
    suficientemente rápido.
    """
    by_id: dict[UUID, dict] = {}
    roots: list[dict] = []

    for row in rows:
        node = {
            "id": getattr(row, id_attr),
            "parent_id": row.parent_id,
            "slug": row.slug,
            "level": row.level,
            "path": row.path,
            "name": row.name,
            "sort_order": row.sort_order,
            "is_active": row.is_active,
            "children": [],
        }
        if hasattr(row, "node_type"):
            node["node_type"] = row.node_type
            node["is_leaf"] = row.is_leaf
            node["risk_level"] = row.risk_level
            node["description"] = row.description
        by_id[node["id"]] = node

    for node in by_id.values():
        parent_id = node["parent_id"]
        if parent_id is not None and parent_id in by_id:
            by_id[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


# ─── Lectura pública ─────────────────────────────────────────────────────────


async def get_taxonomy_tree(session: AsyncSession) -> list[dict]:
    nodes = await taxonomy_repo.list_active_taxonomy_nodes(session)
    return _build_tree(nodes)


async def get_industries_tree(session: AsyncSession) -> list[dict]:
    industries = await taxonomy_repo.list_active_industries(session)
    return _build_tree(industries)


async def get_effective_attributes_for_node(
    session: AsyncSession, node_id: UUID
) -> list[dict]:
    rows = await taxonomy_repo.list_effective_attributes(session, node_id)
    options_by_definition = await taxonomy_repo.list_attribute_options_by_definitions(
        session,
        [
            row.attribute_definition_id
            for row in rows
            if row.data_type in SELECT_LIKE_TYPES
        ],
    )
    result = []
    for row in rows:
        options = options_by_definition.get(row.attribute_definition_id, [])
        result.append(
            {
                "attribute_definition_id": row.attribute_definition_id,
                "code": row.code,
                "name": row.name,
                "data_type": row.data_type,
                "unit_code": row.unit_code,
                "min_value": row.min_value,
                "max_value": row.max_value,
                "is_filterable": row.is_filterable,
                "is_comparable": row.is_comparable,
                "help_text": row.help_text,
                "applies_to": row.applies_to,
                "is_required": row.is_required,
                "is_direct": row.is_direct,
                "options": [
                    {"value": opt.value, "label": opt.label} for opt in options
                ],
            }
        )
    return result


# ─── Administración (platform admin) ────────────────────────────────────────


async def create_taxonomy_node(
    *,
    user_id: UUID,
    parent_id: UUID | None,
    name: str,
    node_type: str,
    slug: str | None = None,
    description: str | None = None,
    risk_level: str | None = None,
    sort_order: int = 0,
) -> UUID:
    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar la taxonomía")

        final_slug = slugify(slug or name)
        if await taxonomy_repo.taxonomy_slug_exists(
            db, parent_id=parent_id, slug=final_slug
        ):
            raise TaxonomyConflictError(
                f"Ya existe un nodo con el slug '{final_slug}' en ese padre"
            )

        node = await taxonomy_repo.create_taxonomy_node(
            db,
            parent_id=parent_id,
            slug=final_slug,
            name=name.strip(),
            node_type=node_type,
            description=description,
            risk_level=risk_level,
            sort_order=sort_order,
        )
        node_id = node.id

    return node_id


async def update_taxonomy_node(
    *, user_id: UUID, node_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar la taxonomía")
        node = await taxonomy_repo.update_taxonomy_node(db, node_id, **fields)
        if node is None:
            raise TaxonomyNotFoundError("Nodo no encontrado")


async def deactivate_taxonomy_node(*, user_id: UUID, node_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar la taxonomía")
        if not await taxonomy_repo.deactivate_taxonomy_node(db, node_id):
            raise TaxonomyNotFoundError("Nodo no encontrado")


async def create_industry(
    *,
    user_id: UUID,
    parent_id: UUID | None,
    name: str,
    slug: str | None = None,
    sort_order: int = 0,
) -> UUID:
    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar industrias")

        final_slug = slugify(slug or name)
        if await taxonomy_repo.industry_slug_exists(
            db, parent_id=parent_id, slug=final_slug
        ):
            raise TaxonomyConflictError(
                f"Ya existe una industria con el slug '{final_slug}' en ese padre"
            )

        industry = await taxonomy_repo.create_industry(
            db,
            parent_id=parent_id,
            slug=final_slug,
            name=name.strip(),
            sort_order=sort_order,
        )
        industry_id = industry.id

    return industry_id


async def update_industry(
    *, user_id: UUID, industry_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar industrias")
        industry = await taxonomy_repo.update_industry(db, industry_id, **fields)
        if industry is None:
            raise TaxonomyNotFoundError("Industria no encontrada")


async def deactivate_industry(*, user_id: UUID, industry_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar industrias")
        if not await taxonomy_repo.deactivate_industry(db, industry_id):
            raise TaxonomyNotFoundError("Industria no encontrada")


async def create_attribute_definition(
    *,
    user_id: UUID,
    code: str,
    name: str,
    data_type: str,
    unit_code: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    is_filterable: bool = False,
    is_comparable: bool = False,
    help_text: str | None = None,
    options: list[dict] | None = None,
) -> UUID:
    if data_type in SELECT_LIKE_TYPES and not options:
        raise TaxonomyValidationError(
            f"Un atributo {data_type} necesita al menos una opción"
        )

    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar atributos")

        if await taxonomy_repo.attribute_code_exists(db, code):
            raise TaxonomyConflictError(f"Ya existe un atributo con el código '{code}'")

        definition = await taxonomy_repo.create_attribute_definition(
            db,
            code=code,
            name=name.strip(),
            data_type=data_type,
            unit_code=unit_code,
            min_value=min_value,
            max_value=max_value,
            is_filterable=is_filterable,
            is_comparable=is_comparable,
            help_text=help_text,
        )

        for index, option in enumerate(options or []):
            await taxonomy_repo.create_attribute_option(
                db,
                attribute_definition_id=definition.id,
                value=option["value"],
                label=option["label"],
                sort_order=option.get("sort_order", index),
            )

        definition_id = definition.id

    return definition_id


async def link_attribute_to_node(
    *,
    user_id: UUID,
    node_id: UUID,
    attribute_definition_id: UUID,
    applies_to: str,
    is_required: bool = False,
    is_inherited: bool = True,
    filter_weight: int = 0,
    sort_order: int = 0,
) -> UUID:
    async with session_for_user(user_id) as db:
        if not await taxonomy_repo.has_platform_permission(
            db, PERMISSION_MANAGE_TAXONOMY
        ):
            raise TaxonomyPermissionError("Sin permiso para administrar atributos")

        node = await taxonomy_repo.get_taxonomy_node(db, node_id)
        if node is None:
            raise TaxonomyNotFoundError("Nodo no encontrado")

        link = await taxonomy_repo.link_attribute_to_node(
            db,
            node_id=node_id,
            attribute_definition_id=attribute_definition_id,
            applies_to=applies_to,
            is_required=is_required,
            is_inherited=is_inherited,
            filter_weight=filter_weight,
            sort_order=sort_order,
        )
        link_id = link.id

    return link_id
