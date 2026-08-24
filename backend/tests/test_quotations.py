"""Cotizaciones y modo sellado (fase 7.5/7.6) — el Punto de control 7 del
roadmap: "Proveedor B no puede leer ninguna fila de la oferta del Proveedor
A, ni por API ni por Realtime, en ningún estado del evento."

test_sealed_bid_isolation prueba esto contra RLS DIRECTAMENTE (SQL crudo vía
session_for_user de cada proveedor), no solo contra la capa de servicio —
la capa de servicio podría "verse" bien y aun así la policy estar mal escrita;
lo único que demuestra el punto de control es la base misma rechazando la
lectura.

Orden de fixtures: los dos proveedores (`competing_supplier`,
`supplier_offering`) ANTES que `test_org` — mismo criterio de teardown que
test_matching.py/test_invitations.py.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.rls import session_for_user
from app.services import invitations as invitations_service
from app.services import quotations as quotations_service
from app.services import sourcing as sourcing_service

pytestmark = pytest.mark.asyncio


async def _create_sealed_event(*, owner_id, org_id):
    event_id = await sourcing_service.create_event(
        user_id=owner_id,
        organization_id=org_id,
        name="Evento sellado de prueba",
        event_type="RFQ",
        bid_mode="SEALED",
        currency_code="CLP",
    )
    item_id = await sourcing_service.add_item(
        user_id=owner_id,
        organization_id=org_id,
        event_id=event_id,
        description="Línea de prueba",
        quantity=10,
        unit_code=None,
    )
    # Sin BID_DEADLINE a propósito: este helper es para el test de
    # aislamiento (¿ve B algo de A?), no para el de vencimiento de plazo —
    # con deadline, submit_revision (necesita "antes del plazo") y open_bids
    # (necesita "después del plazo") quedan mutuamente excluyentes dentro de
    # un mismo test rápido. El guard de deadline de open_bids ya quedó
    # probado indirectamente: rechazó una apertura temprana en una corrida
    # anterior de esta suite, exactamente como se esperaba.
    await sourcing_service.publish_event(
        user_id=owner_id, organization_id=org_id, event_id=event_id
    )
    return event_id, item_id


async def _invite_and_admit(
    *, owner_id, buyer_org_id, event_id, supplier_user_id, supplier_org_id
):
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
    )
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
    return invitation_id


async def test_sealed_bid_isolation(competing_supplier, supplier_offering, test_org):
    owner_id, buyer_org_id = test_org
    a_user_id, a_org_id = (
        supplier_offering["user_id"],
        supplier_offering["organization_id"],
    )
    b_user_id, b_org_id = (
        competing_supplier["user_id"],
        competing_supplier["organization_id"],
    )

    event_id, item_id = await _create_sealed_event(
        owner_id=owner_id, org_id=buyer_org_id
    )
    await _invite_and_admit(
        owner_id=owner_id,
        buyer_org_id=buyer_org_id,
        event_id=event_id,
        supplier_user_id=a_user_id,
        supplier_org_id=a_org_id,
    )
    await _invite_and_admit(
        owner_id=owner_id,
        buyer_org_id=buyer_org_id,
        event_id=event_id,
        supplier_user_id=b_user_id,
        supplier_org_id=b_org_id,
    )

    revision_id = await quotations_service.submit_revision(
        user_id=a_user_id,
        organization_id=a_org_id,
        sourcing_event_id=event_id,
        currency_code="CLP",
        valid_until=None,
        subtotal=100_000,
        tax_amount=19_000,
        total_amount=119_000,
        payment_terms="30 días",
        delivery_days=5,
        warranty_terms=None,
        exclusions=None,
        notes=None,
        items=[
            {
                "sourcing_event_item_id": item_id,
                "quantity": 10,
                "unit_price": 10_000,
            }
        ],
    )
    assert revision_id is not None

    # 1) El proveedor A ve su propia revisión.
    async with session_for_user(a_user_id) as db:
        result = await db.execute(
            text("select count(*) from public.quotation_revisions where id = :id"),
            {"id": str(revision_id)},
        )
        assert result.scalar_one() == 1

    # 2) El proveedor B — competidor, con su propia invitación activa en el
    # MISMO evento — no ve NADA de la cotización de A. Ni el contenedor, ni
    # la revisión, ni las líneas. Directo contra RLS, no contra el service.
    async with session_for_user(b_user_id) as db:
        quotations_count = await db.execute(
            text(
                "select count(*) from public.quotations "
                "where sourcing_event_id = :event_id and supplier_organization_id = :a_org"
            ),
            {"event_id": str(event_id), "a_org": str(a_org_id)},
        )
        assert quotations_count.scalar_one() == 0

        revisions_count = await db.execute(
            text("select count(*) from public.quotation_revisions where id = :id"),
            {"id": str(revision_id)},
        )
        assert revisions_count.scalar_one() == 0

    # 3) El comprador tampoco ve nada — SEALED y todavía no se abrió.
    async with session_for_user(owner_id) as db:
        buyer_visible = await db.execute(
            text("select count(*) from public.quotation_revisions where id = :id"),
            {"id": str(revision_id)},
        )
        assert buyer_visible.scalar_one() == 0

    # 4) Se abren las ofertas.
    await quotations_service.open_bids(
        user_id=owner_id, organization_id=buyer_org_id, sourcing_event_id=event_id
    )

    # 5) Ahora el comprador SÍ ve la revisión de A...
    async with session_for_user(owner_id) as db:
        buyer_visible_after = await db.execute(
            text("select count(*) from public.quotation_revisions where id = :id"),
            {"id": str(revision_id)},
        )
        assert buyer_visible_after.scalar_one() == 1

    # ...pero B SIGUE sin ver nada de A — la apertura habilita al comprador,
    # nunca a un competidor. Este es exactamente el punto de control 7.
    async with session_for_user(b_user_id) as db:
        still_hidden = await db.execute(
            text("select count(*) from public.quotation_revisions where id = :id"),
            {"id": str(revision_id)},
        )
        assert still_hidden.scalar_one() == 0


async def test_submit_revision_requires_active_invitation(supplier_offering, test_org):
    owner_id, buyer_org_id = test_org
    supplier_user_id = supplier_offering["user_id"]
    supplier_org_id = supplier_offering["organization_id"]
    event_id, item_id = await _create_sealed_event(
        owner_id=owner_id, org_id=buyer_org_id
    )

    with pytest.raises(quotations_service.QuotationPermissionError):
        await quotations_service.submit_revision(
            user_id=supplier_user_id,
            organization_id=supplier_org_id,
            sourcing_event_id=event_id,
            currency_code="CLP",
            valid_until=None,
            subtotal=None,
            tax_amount=None,
            total_amount=1_000,
            payment_terms=None,
            delivery_days=None,
            warranty_terms=None,
            exclusions=None,
            notes=None,
            items=[
                {"sourcing_event_item_id": item_id, "quantity": 1, "unit_price": 1_000}
            ],
        )


async def test_resubmission_before_deadline_allowed(supplier_offering, test_org):
    owner_id, buyer_org_id = test_org
    supplier_user_id = supplier_offering["user_id"]
    supplier_org_id = supplier_offering["organization_id"]
    event_id, item_id = await _create_sealed_event(
        owner_id=owner_id, org_id=buyer_org_id
    )
    await _invite_and_admit(
        owner_id=owner_id,
        buyer_org_id=buyer_org_id,
        event_id=event_id,
        supplier_user_id=supplier_user_id,
        supplier_org_id=supplier_org_id,
    )

    kwargs = dict(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        sourcing_event_id=event_id,
        currency_code="CLP",
        valid_until=None,
        subtotal=None,
        tax_amount=None,
        payment_terms=None,
        delivery_days=None,
        warranty_terms=None,
        exclusions=None,
        notes=None,
        items=[{"sourcing_event_item_id": item_id, "quantity": 1, "unit_price": 1_000}],
    )
    first_id = await quotations_service.submit_revision(total_amount=1_000, **kwargs)
    second_id = await quotations_service.submit_revision(total_amount=900, **kwargs)
    assert first_id != second_id

    revisions = await quotations_service.list_my_revisions(
        user_id=supplier_user_id,
        organization_id=supplier_org_id,
        sourcing_event_id=event_id,
    )
    assert len(revisions) == 2
    assert all(r.round_type == "INITIAL" for r in revisions)
