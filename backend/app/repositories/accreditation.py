"""Programas de acreditación y estado por organización (fase 5.3/5.4)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accreditation import (
    AccreditationEnrollment,
    AccreditationFulfillment,
    AccreditationProgram,
    AccreditationRequirement,
    RequirementGroup,
)


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def has_platform_permission(session: AsyncSession, permission_code: str) -> bool:
    """Espejo de app.has_platform_permission() (0018) — permiso de rol de
    plataforma (platform_admins), no de membresía de organización. Es lo
    que tiene un ACCREDITATION_REVIEWER, que no pertenece a ninguna
    organización postulante."""
    result = await session.execute(
        text("select app.has_platform_permission(:perm)"),
        {"perm": permission_code},
    )
    return bool(result.scalar_one())


# ─── Programas / exigencias ──────────────────────────────────────────────────


async def list_programs(session: AsyncSession) -> list[AccreditationProgram]:
    result = await session.execute(
        select(AccreditationProgram)
        .where(AccreditationProgram.is_active.is_(True))
        .order_by(AccreditationProgram.name)
    )
    return list(result.scalars())


async def get_program(
    session: AsyncSession, program_id: UUID
) -> AccreditationProgram | None:
    result = await session.execute(
        select(AccreditationProgram).where(AccreditationProgram.id == program_id)
    )
    return result.scalar_one_or_none()


async def get_program_by_code(
    session: AsyncSession, code: str
) -> AccreditationProgram | None:
    result = await session.execute(
        select(AccreditationProgram).where(AccreditationProgram.code == code)
    )
    return result.scalar_one_or_none()


async def list_requirement_groups(
    session: AsyncSession, program_id: UUID
) -> list[RequirementGroup]:
    result = await session.execute(
        select(RequirementGroup)
        .where(RequirementGroup.program_id == program_id)
        .order_by(RequirementGroup.sort_order)
    )
    return list(result.scalars())


async def list_requirements(
    session: AsyncSession, program_id: UUID
) -> list[AccreditationRequirement]:
    result = await session.execute(
        select(AccreditationRequirement)
        .where(AccreditationRequirement.program_id == program_id)
        .order_by(AccreditationRequirement.sort_order)
    )
    return list(result.scalars())


async def get_requirement(
    session: AsyncSession, requirement_id: UUID
) -> AccreditationRequirement | None:
    result = await session.execute(
        select(AccreditationRequirement).where(
            AccreditationRequirement.id == requirement_id
        )
    )
    return result.scalar_one_or_none()


async def create_program(
    session: AsyncSession, **fields: object
) -> AccreditationProgram:
    program = AccreditationProgram(**fields)
    session.add(program)
    await session.flush()
    return program


async def create_requirement_group(
    session: AsyncSession, **fields: object
) -> RequirementGroup:
    group = RequirementGroup(**fields)
    session.add(group)
    await session.flush()
    return group


async def create_requirement(
    session: AsyncSession, **fields: object
) -> AccreditationRequirement:
    requirement = AccreditationRequirement(**fields)
    session.add(requirement)
    await session.flush()
    return requirement


async def is_valid_transition(
    session: AsyncSession, from_status: str, to_status: str
) -> bool:
    result = await session.execute(
        text(
            "select exists(select 1 from public.accreditation_status_transitions "
            "where from_status = :from_status and to_status = :to_status)"
        ),
        {"from_status": from_status, "to_status": to_status},
    )
    return bool(result.scalar_one())


# ─── Enrollments ──────────────────────────────────────────────────────────────


async def list_enrollments(session: AsyncSession, organization_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select ae.id, ae.program_id, ae.status, ae.completion_pct, ae.valid_from, "
            "       ae.valid_until, ae.submitted_at, ae.decided_at, "
            "       ap.code as program_code, ap.name as program_name "
            "from public.accreditation_enrollments ae "
            "join public.accreditation_programs ap on ap.id = ae.program_id "
            "where ae.organization_id = :org_id "
            "order by ae.created_at desc"
        ),
        {"org_id": str(organization_id)},
    )
    return [dict(row._mapping) for row in result]


async def list_review_queue(
    session: AsyncSession, *, status: str | None = None
) -> list[dict]:
    """Cola de revisión. RLS ya restringe el SELECT a quien tenga
    platform.review_accreditation (o admin) — ver 0038_fase5_rls.sql."""
    query = (
        "select ae.id, ae.organization_id, ae.program_id, ae.status, ae.completion_pct, "
        "       ae.submitted_at, ae.created_at, "
        "       ap.code as program_code, ap.name as program_name, "
        "       o.legal_name as organization_name "
        "from public.accreditation_enrollments ae "
        "join public.accreditation_programs ap on ap.id = ae.program_id "
        "join public.organizations o on o.id = ae.organization_id "
        "where (cast(:status as text) is null or ae.status = cast(:status as app.accreditation_enrollment_status)) "
        "order by ae.submitted_at nulls last, ae.created_at desc"
    )
    result = await session.execute(text(query), {"status": status})
    return [dict(row._mapping) for row in result]


async def get_enrollment(
    session: AsyncSession, enrollment_id: UUID
) -> AccreditationEnrollment | None:
    result = await session.execute(
        select(AccreditationEnrollment).where(
            AccreditationEnrollment.id == enrollment_id
        )
    )
    return result.scalar_one_or_none()


async def get_enrollment_by_program(
    session: AsyncSession, organization_id: UUID, program_id: UUID
) -> AccreditationEnrollment | None:
    result = await session.execute(
        select(AccreditationEnrollment).where(
            AccreditationEnrollment.organization_id == organization_id,
            AccreditationEnrollment.program_id == program_id,
        )
    )
    return result.scalar_one_or_none()


async def create_enrollment(
    session: AsyncSession, **fields: object
) -> AccreditationEnrollment:
    enrollment = AccreditationEnrollment(**fields)
    session.add(enrollment)
    await session.flush()
    return enrollment


async def update_enrollment(
    enrollment: AccreditationEnrollment, **fields: object
) -> None:
    for key, value in fields.items():
        setattr(enrollment, key, value)


# ─── Fulfillments ─────────────────────────────────────────────────────────────


async def list_fulfillments(session: AsyncSession, enrollment_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select af.id, af.requirement_id, af.document_version_id, af.certification_id, "
            "       af.declared_value, af.status, af.reviewer_id, af.reviewed_at, "
            "       af.observation, af.expires_at, "
            "       ar.name as requirement_name, ar.requirement_kind, ar.is_mandatory, "
            "       ar.weight, ar.group_id, rg.name as group_name "
            "from public.accreditation_fulfillments af "
            "join public.accreditation_requirements ar on ar.id = af.requirement_id "
            "join public.requirement_groups rg on rg.id = ar.group_id "
            "where af.enrollment_id = :enrollment_id "
            "order by rg.sort_order, ar.sort_order"
        ),
        {"enrollment_id": str(enrollment_id)},
    )
    return [dict(row._mapping) for row in result]


async def get_fulfillment(
    session: AsyncSession, fulfillment_id: UUID
) -> AccreditationFulfillment | None:
    result = await session.execute(
        select(AccreditationFulfillment).where(
            AccreditationFulfillment.id == fulfillment_id
        )
    )
    return result.scalar_one_or_none()


async def update_fulfillment(
    fulfillment: AccreditationFulfillment, **fields: object
) -> None:
    for key, value in fields.items():
        setattr(fulfillment, key, value)


async def get_fulfillment_by_requirement(
    session: AsyncSession, enrollment_id: UUID, requirement_id: UUID
) -> AccreditationFulfillment | None:
    result = await session.execute(
        select(AccreditationFulfillment).where(
            AccreditationFulfillment.enrollment_id == enrollment_id,
            AccreditationFulfillment.requirement_id == requirement_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert_fulfillment(
    session: AsyncSession,
    *,
    enrollment_id: UUID,
    requirement_id: UUID,
    **fields: object,
) -> AccreditationFulfillment:
    fulfillment = await get_fulfillment_by_requirement(
        session, enrollment_id, requirement_id
    )
    if fulfillment is None:
        fulfillment = AccreditationFulfillment(
            enrollment_id=enrollment_id, requirement_id=requirement_id, **fields
        )
        session.add(fulfillment)
    else:
        for key, value in fields.items():
            setattr(fulfillment, key, value)
    await session.flush()
    return fulfillment


# ─── Progreso por sección / historial / bitácora ─────────────────────────────


async def list_section_progress(
    session: AsyncSession, enrollment_id: UUID
) -> list[dict]:
    result = await session.execute(
        text(
            "select asp.group_id, asp.completion_pct, rg.name, rg.weight, rg.sort_order "
            "from public.accreditation_section_progress asp "
            "join public.requirement_groups rg on rg.id = asp.group_id "
            "where asp.enrollment_id = :enrollment_id "
            "order by rg.sort_order"
        ),
        {"enrollment_id": str(enrollment_id)},
    )
    return [dict(row._mapping) for row in result]


async def upsert_section_progress(
    session: AsyncSession, *, enrollment_id: UUID, group_id: UUID, completion_pct: int
) -> None:
    await session.execute(
        text(
            "insert into public.accreditation_section_progress (enrollment_id, group_id, completion_pct, updated_at) "
            "values (:enrollment_id, :group_id, :completion_pct, now()) "
            "on conflict (enrollment_id, group_id) "
            "do update set completion_pct = excluded.completion_pct, updated_at = now()"
        ),
        {
            "enrollment_id": str(enrollment_id),
            "group_id": str(group_id),
            "completion_pct": completion_pct,
        },
    )


async def add_status_history(session: AsyncSession, **fields: object) -> None:
    await session.execute(
        text(
            "insert into public.accreditation_status_history "
            "(enrollment_id, from_status, to_status, actor_id, reason) "
            "values (:enrollment_id, :from_status, :to_status, :actor_id, :reason)"
        ),
        fields,
    )


async def list_status_history(session: AsyncSession, enrollment_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select id, from_status, to_status, actor_id, reason, created_at "
            "from public.accreditation_status_history "
            "where enrollment_id = :enrollment_id "
            "order by created_at desc"
        ),
        {"enrollment_id": str(enrollment_id)},
    )
    return [dict(row._mapping) for row in result]


async def add_review_event(session: AsyncSession, **fields: object) -> None:
    await session.execute(
        text(
            "insert into public.accreditation_review_events (fulfillment_id, actor_id, message) "
            "values (:fulfillment_id, :actor_id, :message)"
        ),
        fields,
    )


async def list_review_events(session: AsyncSession, fulfillment_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select id, actor_id, message, created_at "
            "from public.accreditation_review_events "
            "where fulfillment_id = :fulfillment_id "
            "order by created_at"
        ),
        {"fulfillment_id": str(fulfillment_id)},
    )
    return [dict(row._mapping) for row in result]


# ─── Fórmula de completitud (F.4) ────────────────────────────────────────────


async def compute_completion(session: AsyncSession, enrollment_id: UUID) -> dict:
    """Σ(requirement.weight × fulfillment_factor) / Σ requirement.weight,
    global y por sección — docs/01-ARQUITECTURA.md §F.4. "Vigente" se evalúa
    acá mismo (expires_at is null or expires_at >= current_date), no depende
    de que algo haya marcado el fulfillment EXPIRED — ver el plan de fase 5."""
    result = await session.execute(
        text(
            """
            select
              ar.group_id,
              coalesce(sum(ar.weight * case
                when af.status = 'APPROVED' and (af.expires_at is null or af.expires_at >= current_date) then 1.0
                when af.status in ('SUBMITTED', 'UNDER_REVIEW') then 0.5
                else 0.0
              end), 0) as weighted,
              coalesce(sum(ar.weight), 0) as total_weight
            from public.accreditation_requirements ar
            left join public.accreditation_fulfillments af
              on af.requirement_id = ar.id and af.enrollment_id = :enrollment_id
            where ar.program_id = (
              select program_id from public.accreditation_enrollments where id = :enrollment_id
            )
            group by ar.group_id
            """
        ),
        {"enrollment_id": str(enrollment_id)},
    )
    rows = [dict(row._mapping) for row in result]
    total_weighted = sum(r["weighted"] for r in rows)
    total_weight = sum(r["total_weight"] for r in rows)
    overall_pct = round(100 * total_weighted / total_weight) if total_weight else 0
    sections = {
        r["group_id"]: (
            round(100 * r["weighted"] / r["total_weight"]) if r["total_weight"] else 0
        )
        for r in rows
    }
    return {"overall_pct": overall_pct, "sections": sections}


async def count_expired_documents(session: AsyncSession, organization_id: UUID) -> int:
    result = await session.execute(
        text(
            "select count(*) from public.organization_document_versions v "
            "join public.organization_documents d on d.id = v.document_id "
            "where d.organization_id = :org_id and v.status = 'ACTIVE' "
            "and v.valid_until is not null and v.valid_until < current_date"
        ),
        {"org_id": str(organization_id)},
    )
    return int(result.scalar_one())
