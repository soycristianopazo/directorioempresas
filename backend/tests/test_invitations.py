"""Invitaciones y NDA (fase 7.1/7.2): máquina de estados y autoservicio del
proveedor, contra la base real.

Orden de fixtures: `supplier_offering` (proveedor) ANTES que `test_org`
(comprador) — mismo criterio de teardown que test_matching.py: la fila que
referencia (sourcing_event_invitations.supplier_organization_id) se borra
antes que la fila referenciada.
"""

from __future__ import annotations

import pytest

from app.services import invitations as invitations_service
from app.services import sourcing as sourcing_service

pytestmark = pytest.mark.asyncio


async def _create_published_event(*, owner_id, org_id, requires_nda=False):
    event_id = await sourcing_service.create_event(
        user_id=owner_id,
        organization_id=org_id,
        name="Evento de prueba (invitaciones)",
        event_type="RFQ",
        requires_nda=requires_nda,
    )
    await sourcing_service.add_item(
        user_id=owner_id,
        organization_id=org_id,
        event_id=event_id,
        description="Línea de prueba",
        quantity=10,
    )
    await sourcing_service.publish_event(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )
    return event_id


async def test_invite_and_accept_flow(supplier_offering, test_org):
    owner_id, buyer_org_id = test_org
    supplier_user_id = supplier_offering["user_id"]
    supplier_org_id = supplier_offering["organization_id"]

    event_id = await _create_published_event(owner_id=owner_id, org_id=buyer_org_id)

    invitation_id = await invitations_service.invite_supplier(
        user_id=owner_id,
        organization_id=buyer_org_id,
        sourcing_event_id=event_id,
        supplier_organization_id=supplier_org_id,
    )
    assert invitation_id is not None

    # Doble invitación al mismo proveedor: rechazada.
    with pytest.raises(invitations_service.InvitationValidationError):
        await invitations_service.invite_supplier(
            user_id=owner_id,
            organization_id=buyer_org_id,
            sourcing_event_id=event_id,
            supplier_organization_id=supplier_org_id,
        )

    # El proveedor lista su bandeja y ve la invitación en INVITED.
    inbox = await invitations_service.list_my_invitations(
        user_id=supplier_user_id, organization_id=supplier_org_id
    )
    assert any(
        row["id"] == invitation_id and row["status"] == "INVITED" for row in inbox
    )

    # Ver el detalle transiciona automáticamente INVITED → VIEWED.
    detail = await invitations_service.get_invitation_detail(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )
    assert detail["status"] == "VIEWED"
    assert detail["viewed_at"] is not None

    await invitations_service.express_interest(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )
    await invitations_service.confirm_participation(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )

    detail = await invitations_service.get_invitation_detail(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )
    assert detail["status"] == "PARTICIPATING"
    statuses = [h["to_status"] for h in detail["history"]]
    assert statuses == ["INVITED", "VIEWED", "INTERESTED", "PARTICIPATING"]


async def test_invalid_transition_rejected(supplier_offering, test_org):
    owner_id, buyer_org_id = test_org
    supplier_user_id = supplier_offering["user_id"]
    supplier_org_id = supplier_offering["organization_id"]
    event_id = await _create_published_event(owner_id=owner_id, org_id=buyer_org_id)

    invitation_id = await invitations_service.invite_supplier(
        user_id=owner_id,
        organization_id=buyer_org_id,
        sourcing_event_id=event_id,
        supplier_organization_id=supplier_org_id,
    )

    # PARTICIPATING no es alcanzable desde INVITED sin pasar por VIEWED/INTERESTED.
    with pytest.raises(invitations_service.InvitationValidationError):
        await invitations_service.confirm_participation(
            user_id=supplier_user_id,
            organization_id=supplier_org_id,
            invitation_id=invitation_id,
        )


async def test_decline_with_reason(supplier_offering, test_org):
    owner_id, buyer_org_id = test_org
    supplier_user_id = supplier_offering["user_id"]
    supplier_org_id = supplier_offering["organization_id"]
    event_id = await _create_published_event(owner_id=owner_id, org_id=buyer_org_id)

    invitation_id = await invitations_service.invite_supplier(
        user_id=owner_id,
        organization_id=buyer_org_id,
        sourcing_event_id=event_id,
        supplier_organization_id=supplier_org_id,
    )
    await invitations_service.decline(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
        reason_code="NO_CAPACITY",
    )
    detail = await invitations_service.get_invitation_detail(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )
    assert detail["status"] == "DECLINED"
    assert detail["decline_reason_code"] == "NO_CAPACITY"


async def test_nda_required_before_participation(supplier_offering, test_org):
    owner_id, buyer_org_id = test_org
    supplier_user_id = supplier_offering["user_id"]
    supplier_org_id = supplier_offering["organization_id"]
    event_id = await _create_published_event(
        owner_id=owner_id, org_id=buyer_org_id, requires_nda=True
    )

    await invitations_service.upsert_nda(
        user_id=owner_id,
        organization_id=buyer_org_id,
        sourcing_event_id=event_id,
        title="NDA de prueba",
        body_text="Texto de confidencialidad de prueba.",
    )

    invitation_id = await invitations_service.invite_supplier(
        user_id=owner_id,
        organization_id=buyer_org_id,
        sourcing_event_id=event_id,
        supplier_organization_id=supplier_org_id,
    )
    await invitations_service.get_invitation_detail(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )  # INVITED → VIEWED

    # No se puede saltar directo a INTERESTED sin aceptar el NDA primero.
    with pytest.raises(invitations_service.InvitationValidationError):
        await invitations_service.express_interest(
            user_id=supplier_user_id,
            organization_id=supplier_org_id,
            invitation_id=invitation_id,
        )

    await invitations_service.accept_nda(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await invitations_service.express_interest(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )
    detail = await invitations_service.get_invitation_detail(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        invitation_id=invitation_id,
    )
    assert detail["status"] == "INTERESTED"
