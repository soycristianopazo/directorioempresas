"""Caminos críticos de acreditación (fase 5): la fórmula de completitud, la
máquina de estados como dato (no código), y el límite de permiso entre
proveedor y revisor — el error real que rompió esta fase en verificación
(confundir app.has_permission con app.has_platform_permission) es exactamente
la clase de bug que estos tests están para atrapar la próxima vez.

Nota de orden de fixtures: en cada test, `test_program` se declara ANTES que
`test_org` en la firma — pytest desarma los fixtures en orden inverso al que
los arma, así que `test_org` se borra primero (organizations ondelete=CASCADE
se lleva el enrollment de prueba) y recién después `test_program`, que de otro
modo fallaría por la FK de accreditation_enrollments.program_id (sin cascade).
"""

from __future__ import annotations

import pytest

from app.services import accreditation as accreditation_service
from app.services import documents as documents_service

pytestmark = pytest.mark.asyncio


def _fulfillment_id_for(detail: dict, requirement_id) -> str:
    return next(
        f for f in detail["fulfillments"] if f["requirement_id"] == requirement_id
    )["id"]


async def test_completion_formula_partial_and_full_credit(
    test_program, test_org, reviewer_user
):
    owner_id, org_id = test_org
    program_id = test_program["program_id"]
    req_a_id = test_program["req_a_id"]

    enrollment_id = await accreditation_service.enroll(
        user_id=owner_id, organization_id=org_id, program_id=program_id
    )

    detail = await accreditation_service.get_enrollment_detail(
        user_id=owner_id, organization_id=org_id, enrollment_id=enrollment_id
    )
    assert detail["enrollment"]["completion_pct"] == 0

    # SUBMITTED (sin revisar) vale la mitad del peso de la exigencia — 30 de
    # 100 total, factor 0.5 → 15%.
    await accreditation_service.submit_evidence(
        user_id=owner_id,
        organization_id=org_id,
        enrollment_id=enrollment_id,
        requirement_id=req_a_id,
        declared_value="cumplo",
    )
    detail = await accreditation_service.get_enrollment_detail(
        user_id=owner_id, organization_id=org_id, enrollment_id=enrollment_id
    )
    assert detail["enrollment"]["completion_pct"] == 15

    # APPROVED vigente vale el 100% del peso de la exigencia — 30/100 → 30%.
    fulfillment_id = _fulfillment_id_for(detail, req_a_id)
    await accreditation_service.review_fulfillment(
        user_id=reviewer_user, fulfillment_id=fulfillment_id, decision="APPROVED"
    )
    detail = await accreditation_service.get_enrollment_detail(
        user_id=owner_id, organization_id=org_id, enrollment_id=enrollment_id
    )
    assert detail["enrollment"]["completion_pct"] == 30

    # REJECTED no aporta nada, aunque haya sido revisado — factor 0.0.
    fulfillment_id = _fulfillment_id_for(detail, req_a_id)
    await accreditation_service.review_fulfillment(
        user_id=reviewer_user, fulfillment_id=fulfillment_id, decision="REJECTED"
    )
    detail = await accreditation_service.get_enrollment_detail(
        user_id=owner_id, organization_id=org_id, enrollment_id=enrollment_id
    )
    assert detail["enrollment"]["completion_pct"] == 0


async def test_invalid_transition_is_rejected(test_program, test_org):
    """accreditation_status_transitions es DATA — un enrollment recién creado
    está en PENDING_DOCUMENTS; responder a una observación (OBSERVED →
    PENDING_DOCUMENTS) no es una transición válida desde ese estado."""
    owner_id, org_id = test_org
    enrollment_id = await accreditation_service.enroll(
        user_id=owner_id, organization_id=org_id, program_id=test_program["program_id"]
    )

    with pytest.raises(accreditation_service.AccreditationValidationError):
        await accreditation_service.respond_to_observation(
            user_id=owner_id, organization_id=org_id, enrollment_id=enrollment_id
        )


async def test_provider_cannot_act_as_reviewer(test_program, test_org):
    """El dueño de la organización postulante tiene accreditation.submit/manage
    (vía el comodín '*' de ORG_OWNER) pero NUNCA platform.review_accreditation
    — decidir el propio estado de acreditación no puede quedar al alcance de
    quien se está acreditando."""
    owner_id, org_id = test_org
    enrollment_id = await accreditation_service.enroll(
        user_id=owner_id, organization_id=org_id, program_id=test_program["program_id"]
    )

    with pytest.raises(accreditation_service.AccreditationPermissionError):
        await accreditation_service.decide_enrollment(
            user_id=owner_id, enrollment_id=enrollment_id, decision="ACCREDITED"
        )

    with pytest.raises(accreditation_service.AccreditationPermissionError):
        await accreditation_service.list_review_queue(user_id=owner_id)


async def test_reviewer_cannot_submit_evidence(test_program, test_org, reviewer_user):
    """El revisor no es miembro de la organización postulante — adjuntar
    evidencia por ella debe rechazarse en el chequeo de permiso, ANTES de
    siquiera buscar el enrollment (por eso un id inventado sirve acá)."""
    _, org_id = test_org

    with pytest.raises(accreditation_service.AccreditationPermissionError):
        await accreditation_service.submit_evidence(
            user_id=reviewer_user,
            organization_id=org_id,
            enrollment_id="00000000-0000-0000-0000-000000000000",
            requirement_id=test_program["req_a_id"],
            declared_value="no debería poder",
        )


async def test_upload_rejects_spoofed_pdf():
    """Magic bytes, no Content-Type declarado — un archivo de texto disfrazado
    de PDF se rechaza ANTES de tocar la base o el storage (ver el orden de
    chequeos en services/documents.py::upload_version)."""
    with pytest.raises(documents_service.DocumentValidationError):
        await documents_service.upload_version(
            user_id="00000000-0000-0000-0000-000000000000",
            organization_id="00000000-0000-0000-0000-000000000000",
            document_type_id="00000000-0000-0000-0000-000000000000",
            content=b"esto no es un pdf de verdad",
            content_type="application/pdf",
            issued_at=None,
            valid_from=None,
            valid_until=None,
        )
