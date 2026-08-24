"""Routers de lectura pública: /api/taxonomy/* y /api/industries/*.

Dos APIRouter en el mismo archivo en vez de separar industries.py: son un
puñado de rutas cada uno, y separar solo para tener un archivo de 15 líneas
no gana nada — mismo criterio que ya usa el resto de la capa de rutas.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import PublicSession
from app.schemas.attributes import EffectiveAttributeOut
from app.schemas.taxonomy import IndustryTreeOut, TaxonomyNodeTreeOut
from app.services import taxonomy as taxonomy_service

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])
industries_router = APIRouter(prefix="/industries", tags=["industries"])


@router.get("/nodes", response_model=list[TaxonomyNodeTreeOut])
async def get_taxonomy_tree(session: PublicSession) -> list[TaxonomyNodeTreeOut]:
    tree = await taxonomy_service.get_taxonomy_tree(session)
    return [TaxonomyNodeTreeOut(**node) for node in tree]


@router.get("/nodes/{node_id}/attributes", response_model=list[EffectiveAttributeOut])
async def get_node_attributes(
    node_id: UUID, session: PublicSession
) -> list[EffectiveAttributeOut]:
    attributes = await taxonomy_service.get_effective_attributes_for_node(
        session, node_id
    )
    return [EffectiveAttributeOut(**attr) for attr in attributes]


@industries_router.get("", response_model=list[IndustryTreeOut])
async def get_industries_tree(session: PublicSession) -> list[IndustryTreeOut]:
    tree = await taxonomy_service.get_industries_tree(session)
    return [IndustryTreeOut(**node) for node in tree]
