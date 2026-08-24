"""Pipeline completo del motor de matching (fase 6.4-6.7), de punta a punta
contra la base real: recall → elegibilidad → scoring.

Orden de fixtures en cada test: `supplier_offering` se declara ANTES que
`test_org` — pytest desarma en orden inverso, así que la organización
compradora (dueña de sourcing_events/match_runs/match_results) se borra
primero (cascada hasta match_results) y recién después la organización
proveedora — de otro modo match_results.offering_id (sin cascada) rompe al
intentar borrar el offering con resultados todavía referenciándolo.
"""

from __future__ import annotations

import pytest

from app.services import matching as matching_service
from app.services import sourcing as sourcing_service

pytestmark = pytest.mark.asyncio


async def _create_published_event(*, owner_id, org_id, taxonomy_node_id, quantity=50):
    event_id = await sourcing_service.create_event(
        user_id=owner_id,
        organization_id=org_id,
        name="Evento de prueba",
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


async def test_matching_eligible_and_scored(supplier_offering, test_org):
    owner_id, org_id = test_org
    event_id = await _create_published_event(
        owner_id=owner_id,
        org_id=org_id,
        taxonomy_node_id=supplier_offering["taxonomy_node_id"],
        quantity=50,
    )

    result = await matching_service.run_matching(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )

    assert result["candidates_evaluated"] >= 1
    matches = {r["offering_id"]: r for r in result["results"]}
    match = matches[supplier_offering["offering_id"]]
    assert match["is_eligible"] is True
    assert match["total_score"] > 0
    assert match["blocking_reasons"] == []
    assert match["score_breakdown"]["engine_version"] == matching_service.ENGINE_VERSION

    # Persistido de verdad — no es una corrida dry_run.
    latest = await matching_service.get_latest_results(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )
    assert latest is not None
    assert latest["run"].id == result["match_run_id"]


async def test_matching_must_have_capacity_blocks_ineligible(
    supplier_offering, test_org
):
    owner_id, org_id = test_org
    event_id = await _create_published_event(
        owner_id=owner_id,
        org_id=org_id,
        taxonomy_node_id=supplier_offering["taxonomy_node_id"],
        # El offering de prueba declara monthly_capacity=100 — pedir 500
        # asegura que el MUST de capacidad lo descarte.
        quantity=500,
    )
    await sourcing_service.add_criterion(
        user_id=owner_id,
        organization_id=org_id,
        event_id=event_id,
        criterion_type="CAPACITY",
        requirement_level="MUST_HAVE",
        is_blocking=True,
        min_capacity=500,
    )

    result = await matching_service.run_matching(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )

    matches = {r["offering_id"]: r for r in result["results"]}
    match = matches[supplier_offering["offering_id"]]
    assert match["is_eligible"] is False
    assert match["total_score"] == 0
    assert any("CAPACITY" in reason for reason in match["blocking_reasons"])


async def test_matching_dry_run_does_not_persist(supplier_offering, test_org):
    owner_id, org_id = test_org
    event_id = await _create_published_event(
        owner_id=owner_id,
        org_id=org_id,
        taxonomy_node_id=supplier_offering["taxonomy_node_id"],
    )

    before = await matching_service.get_latest_results(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )
    assert before is None

    result = await matching_service.run_matching(
        user_id=owner_id, organization_id=org_id, event_id=event_id, dry_run=True
    )
    assert "match_run_id" not in result

    after = await matching_service.get_latest_results(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )
    assert after is None
