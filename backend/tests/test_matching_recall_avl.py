"""Recall (Etapa 1) excluye BLOCKED del AVL de este comprador (fase 8.8).

Reutiliza los fixtures de test_matching.py (`supplier_offering`, `test_org`):
un proveedor publicado, con taxonomía/territorio que normalmente calificaría
para recall. Confirma que un buyer_supplier_relationships.status='BLOCKED'
para ESE comprador lo saca del conjunto de candidatos incluso cumpliendo
taxonomía/territorio — es un filtro duro de elegibilidad (Etapa 1), no una
señal de puntaje (docs/03-MATCHING-ENGINE.md, mismo criterio que un
MUST_HAVE bloqueante)."""

from __future__ import annotations

import pytest

from app.repositories import vendor_list as vendor_list_repo
from app.db.rls import session_for_system
from app.services import matching as matching_service
from app.services import sourcing as sourcing_service

pytestmark = pytest.mark.asyncio


async def _create_published_event(*, owner_id, org_id, taxonomy_node_id, quantity=50):
    event_id = await sourcing_service.create_event(
        user_id=owner_id,
        organization_id=org_id,
        name="Evento de prueba (recall AVL)",
        event_type="RFQ",
    )
    await sourcing_service.add_item(
        user_id=owner_id,
        organization_id=org_id,
        event_id=event_id,
        description="Línea de prueba",
        quantity=quantity,
        taxonomy_node_id=taxonomy_node_id,
    )
    await sourcing_service.publish_event(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )
    return event_id


async def test_recall_excludes_blocked_avl_supplier(supplier_offering, test_org):
    owner_id, org_id = test_org

    async with session_for_system() as db:
        await vendor_list_repo.upsert_relationship(
            db,
            buyer_organization_id=org_id,
            supplier_organization_id=supplier_offering["organization_id"],
            status="BLOCKED",
            status_changed_by=owner_id,
        )

    event_id = await _create_published_event(
        owner_id=owner_id,
        org_id=org_id,
        taxonomy_node_id=supplier_offering["taxonomy_node_id"],
        quantity=50,
    )

    result = await matching_service.run_matching(
        user_id=owner_id, organization_id=org_id, event_id=event_id, dry_run=True
    )

    # No se asume candidates_evaluated == 0: la base es la misma de
    # desarrollo (conftest.py), sin aislamiento entre corridas, y
    # seeded_taxonomy_node es determinístico — otro proveedor de prueba ya
    # sembrado bajo el mismo nodo (sin relación BLOCKED con este comprador)
    # puede legítimamente aparecer como candidato. Lo que este test verifica
    # es específicamente que el proveedor BLOCKEADO no aparezca, ni por
    # offering_id ni por organization_id.
    matched_offering_ids = {r["offering_id"] for r in result["results"]}
    matched_organization_ids = {r["organization_id"] for r in result["results"]}
    assert supplier_offering["offering_id"] not in matched_offering_ids
    assert supplier_offering["organization_id"] not in matched_organization_ids
