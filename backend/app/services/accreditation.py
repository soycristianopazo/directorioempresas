"""Acreditación: postulación, evidencia, revisión y decisión.

Máquina de estados y fórmula de completitud en Python, no en trigger —
mismo criterio que services/completion.py y services/search.py de fases
anteriores. accreditation_status_transitions es DATA (docs/01-ARQUITECTURA.md
§F.3): toda transición pasa por _transition(), que la valida contra esa
tabla antes de aplicarla — nunca un `enrollment.status = "..."` suelto.

Dos permisos, dos lados de la misma fila: accreditation.submit/manage (la
organización postulante) y platform.review_accreditation (el revisor). RLS
acepta cualquiera de los dos como backstop; CUÁL función se puede invocar
para CADA transición lo decide este archivo — el proveedor nunca puede
llamar review_fulfillment/decide_enrollment, el revisor nunca puede llamar
submit_evidence.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import accreditation as accreditation_repo
from app.repositories import documents as documents_repo
from app.services import badges as badges_service

PERM_SUBMIT = "accreditation.submit"
PERM_MANAGE = "accreditation.manage"
PERM_REVIEW = "platform.review_accreditation"
PERM_MANAGE_TAXONOMY = "platform.manage_taxonomy"

_DECIDED_STATUSES = {"ACCREDITED", "OBSERVED", "REJECTED"}


class AccreditationError(Exception):
    pass


class AccreditationPermissionError(AccreditationError):
    pass


class AccreditationNotFoundError(AccreditationError):
    pass


class AccreditationValidationError(AccreditationError):
    pass


async def _require_org(db, organization_id: UUID) -> None:
    if not (
        await accreditation_repo.has_permission(db, organization_id, PERM_SUBMIT)
        or await accreditation_repo.has_permission(db, organization_id, PERM_MANAGE)
    ):
        raise AccreditationPermissionError(
            "Sin permiso para postular por esta organización"
        )


async def _require_reviewer(db) -> None:
    if not await accreditation_repo.has_platform_permission(db, PERM_REVIEW):
        raise AccreditationPermissionError("Sin permiso para revisar acreditaciones")


async def _get_owned_enrollment(db, enrollment_id: UUID, organization_id: UUID):
    enrollment = await accreditation_repo.get_enrollment(db, enrollment_id)
    if enrollment is None or enrollment.organization_id != organization_id:
        raise AccreditationNotFoundError("Postulación no encontrada")
    return enrollment


async def _transition(
    db, enrollment, *, to_status: str, actor_id: UUID | None, reason: str | None
) -> None:
    if not await accreditation_repo.is_valid_transition(
        db, enrollment.status, to_status
    ):
        raise AccreditationValidationError(
            f"No se puede pasar de {enrollment.status} a {to_status}"
        )
    from_status = enrollment.status
    await accreditation_repo.update_enrollment(enrollment, status=to_status)
    await db.flush()
    await accreditation_repo.add_status_history(
        db,
        enrollment_id=str(enrollment.id),
        from_status=from_status,
        to_status=to_status,
        actor_id=str(actor_id) if actor_id else None,
        reason=reason,
    )


async def _recompute_completion(db, enrollment_id: UUID) -> None:
    await db.flush()
    result = await accreditation_repo.compute_completion(db, enrollment_id)
    enrollment = await accreditation_repo.get_enrollment(db, enrollment_id)
    if enrollment is not None:
        await accreditation_repo.update_enrollment(
            enrollment, completion_pct=result["overall_pct"]
        )
    for group_id, pct in result["sections"].items():
        await accreditation_repo.upsert_section_progress(
            db, enrollment_id=enrollment_id, group_id=group_id, completion_pct=pct
        )


# ─── Lectura pública de catálogo ──────────────────────────────────────────────


async def list_programs(*, user_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        return await accreditation_repo.list_programs(db)


async def get_program_detail(*, user_id: UUID, program_id: UUID) -> dict:
    async with session_for_user(user_id) as db:
        program = await accreditation_repo.get_program(db, program_id)
        if program is None:
            raise AccreditationNotFoundError("Programa no encontrado")
        groups = await accreditation_repo.list_requirement_groups(db, program_id)
        requirements = await accreditation_repo.list_requirements(db, program_id)
        return {"program": program, "groups": groups, "requirements": requirements}


# ─── Postulación (lado proveedor) ────────────────────────────────────────────


async def list_enrollments(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require_org(db, organization_id)
        return await accreditation_repo.list_enrollments(db, organization_id)


async def get_enrollment_detail(
    *, user_id: UUID, organization_id: UUID, enrollment_id: UUID
) -> dict:
    async with session_for_user(user_id) as db:
        enrollment = await _get_owned_enrollment(db, enrollment_id, organization_id)
        program = await accreditation_repo.get_program(db, enrollment.program_id)
        fulfillments = await accreditation_repo.list_fulfillments(db, enrollment_id)
        sections = await accreditation_repo.list_section_progress(db, enrollment_id)
        history = await accreditation_repo.list_status_history(db, enrollment_id)
        return {
            "enrollment": {
                "id": enrollment.id,
                "program_id": enrollment.program_id,
                "program_code": program.code if program else "",
                "program_name": program.name if program else "",
                "status": enrollment.status,
                "completion_pct": enrollment.completion_pct,
                "valid_from": enrollment.valid_from,
                "valid_until": enrollment.valid_until,
                "submitted_at": enrollment.submitted_at,
                "decided_at": enrollment.decided_at,
            },
            "fulfillments": fulfillments,
            "sections": sections,
            "history": history,
        }


async def enroll(*, user_id: UUID, organization_id: UUID, program_id: UUID) -> UUID:
    async with session_for_user(user_id) as db:
        await _require_org(db, organization_id)

        program = await accreditation_repo.get_program(db, program_id)
        if program is None or not program.is_active:
            raise AccreditationNotFoundError("Programa no encontrado")

        existing = await accreditation_repo.get_enrollment_by_program(
            db, organization_id, program_id
        )
        if existing is not None:
            raise AccreditationValidationError(
                "Ya existe una postulación a este programa"
            )

        enrollment = await accreditation_repo.create_enrollment(
            db,
            organization_id=organization_id,
            program_id=program_id,
            status="PENDING_DOCUMENTS",
            submitted_at=None,
        )
        await db.flush()
        await accreditation_repo.add_status_history(
            db,
            enrollment_id=str(enrollment.id),
            from_status=None,
            to_status="PENDING_DOCUMENTS",
            actor_id=str(user_id),
            reason="Postulación inicial",
        )

        requirements = await accreditation_repo.list_requirements(db, program_id)
        for requirement in requirements:
            await accreditation_repo.upsert_fulfillment(
                db, enrollment_id=enrollment.id, requirement_id=requirement.id
            )

        await _recompute_completion(db, enrollment.id)
        enrollment_id = enrollment.id
    return enrollment_id


async def submit_evidence(
    *,
    user_id: UUID,
    organization_id: UUID,
    enrollment_id: UUID,
    requirement_id: UUID,
    document_version_id: UUID | None = None,
    certification_id: UUID | None = None,
    declared_value: str | None = None,
) -> None:
    async with session_for_user(user_id) as db:
        await _require_org(db, organization_id)
        enrollment = await _get_owned_enrollment(db, enrollment_id, organization_id)
        if enrollment.status not in ("PENDING_DOCUMENTS", "OBSERVED"):
            raise AccreditationValidationError(
                "Solo se puede adjuntar evidencia mientras la postulación está en curso"
            )

        requirement = await accreditation_repo.get_requirement(db, requirement_id)
        if requirement is None or requirement.program_id != enrollment.program_id:
            raise AccreditationNotFoundError("Exigencia no encontrada")

        expires_at: date | None = None
        if document_version_id:
            version = await documents_repo.get_version(db, document_version_id)
            if version is None:
                raise AccreditationNotFoundError("Documento no encontrado")
            expires_at = version.valid_until

        await accreditation_repo.upsert_fulfillment(
            db,
            enrollment_id=enrollment_id,
            requirement_id=requirement_id,
            document_version_id=document_version_id,
            certification_id=certification_id,
            declared_value=declared_value,
            status="SUBMITTED",
            expires_at=expires_at,
            observation=None,
        )

        await _recompute_completion(db, enrollment_id)


async def submit_for_review(
    *, user_id: UUID, organization_id: UUID, enrollment_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require_org(db, organization_id)
        enrollment = await _get_owned_enrollment(db, enrollment_id, organization_id)

        requirements = await accreditation_repo.list_requirements(
            db, enrollment.program_id
        )
        fulfillments = await accreditation_repo.list_fulfillments(db, enrollment_id)
        by_requirement = {f["requirement_id"]: f for f in fulfillments}
        missing = [
            r.name
            for r in requirements
            if r.is_mandatory
            and by_requirement.get(r.id, {}).get("status") == "PENDING"
        ]
        if missing:
            raise AccreditationValidationError(
                f"Faltan exigencias obligatorias: {', '.join(missing)}"
            )

        await _transition(
            db,
            enrollment,
            to_status="UNDER_REVIEW",
            actor_id=user_id,
            reason="Enviado a revisión",
        )
        await accreditation_repo.update_enrollment(
            enrollment, submitted_at=datetime.now(timezone.utc)
        )


async def respond_to_observation(
    *, user_id: UUID, organization_id: UUID, enrollment_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require_org(db, organization_id)
        enrollment = await _get_owned_enrollment(db, enrollment_id, organization_id)
        await _transition(
            db,
            enrollment,
            to_status="PENDING_DOCUMENTS",
            actor_id=user_id,
            reason="Proveedor respondió observación",
        )


# ─── Revisión (lado revisor de plataforma) ────────────────────────────────────


async def list_review_queue(*, user_id: UUID, status: str | None = None) -> list[dict]:
    async with session_for_user(user_id) as db:
        await _require_reviewer(db)
        return await accreditation_repo.list_review_queue(db, status=status)


async def review_fulfillment(
    *,
    user_id: UUID,
    fulfillment_id: UUID,
    decision: str,
    observation: str | None = None,
) -> None:
    if decision not in ("APPROVED", "OBSERVED", "REJECTED"):
        raise AccreditationValidationError("Decisión inválida")

    async with session_for_user(user_id) as db:
        await _require_reviewer(db)
        fulfillment = await accreditation_repo.get_fulfillment(db, fulfillment_id)
        if fulfillment is None:
            raise AccreditationNotFoundError("Ítem no encontrado")

        await accreditation_repo.update_fulfillment(
            fulfillment,
            status=decision,
            reviewer_id=user_id,
            reviewed_at=datetime.now(timezone.utc),
            observation=observation,
        )
        await accreditation_repo.add_review_event(
            db,
            fulfillment_id=str(fulfillment_id),
            actor_id=str(user_id),
            message=observation or f"Ítem marcado {decision}",
        )
        await _recompute_completion(db, fulfillment.enrollment_id)


async def decide_enrollment(
    *,
    user_id: UUID,
    enrollment_id: UUID,
    decision: str,
    reason: str | None = None,
) -> None:
    if decision not in _DECIDED_STATUSES:
        raise AccreditationValidationError("Decisión inválida")

    async with session_for_user(user_id) as db:
        await _require_reviewer(db)
        enrollment = await accreditation_repo.get_enrollment(db, enrollment_id)
        if enrollment is None:
            raise AccreditationNotFoundError("Postulación no encontrada")

        await _transition(
            db, enrollment, to_status=decision, actor_id=user_id, reason=reason
        )
        await accreditation_repo.update_enrollment(
            enrollment, decided_at=datetime.now(timezone.utc), decided_by=user_id
        )
        if decision == "ACCREDITED":
            program = await accreditation_repo.get_program(db, enrollment.program_id)
            from datetime import timedelta

            valid_until = date.today() + timedelta(
                days=30 * (program.validity_months if program else 12)
            )
            await accreditation_repo.update_enrollment(
                enrollment, valid_from=date.today(), valid_until=valid_until
            )

        target_org_id = enrollment.organization_id
        await badges_service.evaluate_badges_for_org(db, target_org_id)


# ─── Autoría de programas (platform admin) ───────────────────────────────────


async def create_program(
    *,
    user_id: UUID,
    code: str,
    name: str,
    description: str | None = None,
    validity_months: int = 12,
) -> UUID:
    async with session_for_user(user_id) as db:
        if not await accreditation_repo.has_platform_permission(
            db, PERM_MANAGE_TAXONOMY
        ):
            raise AccreditationPermissionError("Sin permiso para administrar programas")
        existing = await accreditation_repo.get_program_by_code(db, code)
        if existing is not None:
            raise AccreditationValidationError(
                f"Ya existe un programa con el código '{code}'"
            )
        program = await accreditation_repo.create_program(
            db,
            code=code,
            name=name,
            description=description,
            owner_scope="PLATFORM",
            validity_months=validity_months,
        )
        program_id = program.id
    return program_id


async def create_requirement_group(
    *,
    user_id: UUID,
    program_id: UUID,
    name: str,
    weight: float = 1,
    sort_order: int = 0,
) -> UUID:
    async with session_for_user(user_id) as db:
        if not await accreditation_repo.has_platform_permission(
            db, PERM_MANAGE_TAXONOMY
        ):
            raise AccreditationPermissionError("Sin permiso para administrar programas")
        program = await accreditation_repo.get_program(db, program_id)
        if program is None:
            raise AccreditationNotFoundError("Programa no encontrado")
        group = await accreditation_repo.create_requirement_group(
            db, program_id=program_id, name=name, weight=weight, sort_order=sort_order
        )
        group_id = group.id
    return group_id


async def create_requirement(
    *,
    user_id: UUID,
    program_id: UUID,
    group_id: UUID,
    requirement_kind: str,
    name: str,
    description: str | None = None,
    is_mandatory: bool = True,
    weight: float = 1,
    document_type_id: UUID | None = None,
    certification_type_id: UUID | None = None,
    attribute_definition_id: UUID | None = None,
    sort_order: int = 0,
) -> UUID:
    async with session_for_user(user_id) as db:
        if not await accreditation_repo.has_platform_permission(
            db, PERM_MANAGE_TAXONOMY
        ):
            raise AccreditationPermissionError("Sin permiso para administrar programas")
        group = await accreditation_repo.list_requirement_groups(db, program_id)
        if not any(g.id == group_id for g in group):
            raise AccreditationNotFoundError("Sección no encontrada en este programa")
        requirement = await accreditation_repo.create_requirement(
            db,
            program_id=program_id,
            group_id=group_id,
            requirement_kind=requirement_kind,
            name=name,
            description=description,
            is_mandatory=is_mandatory,
            weight=weight,
            document_type_id=document_type_id,
            certification_type_id=certification_type_id,
            attribute_definition_id=attribute_definition_id,
            sort_order=sort_order,
        )
        requirement_id = requirement.id
    return requirement_id
