"""Evaluador determinístico de badges automáticos (fase 5.9).

rule_expression es DATA, nunca código: {"all": [{"fact": "...", "op": "...",
"value": ...}]} — docs/01-ARQUITECTURA.md §F.6, "Nunca badges comprables con
el plan." Los facts resolubles en esta fase son accreditation.<program_code>.status
y documents.expired_count; supplier_score.total (fase 6) se reconoce pero
siempre resuelve como no cumplido, sin fallar.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import accreditation as accreditation_repo
from app.repositories import badges as badges_repo

_OPS = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a is not None and a >= b,
    "<=": lambda a, b: a is not None and a <= b,
    ">": lambda a, b: a is not None and a > b,
    "<": lambda a, b: a is not None and a < b,
    "in": lambda a, b: a in b,
}


async def _resolve_fact(
    session: AsyncSession, organization_id: UUID, fact: str
) -> object:
    if fact.startswith("accreditation.") and fact.endswith(".status"):
        program_code = fact[len("accreditation.") : -len(".status")]
        program = await accreditation_repo.get_program_by_code(session, program_code)
        if program is None:
            return None
        enrollment = await accreditation_repo.get_enrollment_by_program(
            session, organization_id, program.id
        )
        return enrollment.status if enrollment else None

    if fact == "documents.expired_count":
        return await accreditation_repo.count_expired_documents(
            session, organization_id
        )

    if fact == "supplier_score.total":
        # Fase 6 (matching) todavía no existe: el fact se reconoce pero
        # nunca se cumple, no debe romper la evaluación.
        return None

    return None


async def _rule_satisfied(
    session: AsyncSession, organization_id: UUID, rule_expression: dict
) -> bool:
    conditions = rule_expression.get("all", [])
    if not conditions:
        return False
    for condition in conditions:
        fact = condition.get("fact")
        op = condition.get("op")
        expected = condition.get("value")
        op_fn = _OPS.get(op)
        if op_fn is None:
            return False
        actual = await _resolve_fact(session, organization_id, fact)
        try:
            if not op_fn(actual, expected):
                return False
        except TypeError:
            return False
    return True


async def evaluate_badges_for_org(
    session: AsyncSession, organization_id: UUID
) -> list[str]:
    """Evalúa todas las definiciones automáticas activas para una organización,
    otorgando o revocando según corresponda. Se llama en la misma transacción
    que la decisión que pudo cambiar el estado (mismo criterio que
    recompute_completion_pct/reindex_offering). Devuelve los códigos de los
    badges recién otorgados."""
    granted: list[str] = []
    definitions = await badges_repo.list_badge_definitions(session)
    for definition in definitions:
        if not definition.is_automatic:
            continue
        satisfied = await _rule_satisfied(
            session, organization_id, definition.rule_expression
        )
        existing_grant = await badges_repo.get_active_grant(
            session, organization_id, definition.id
        )

        if satisfied and existing_grant is None:
            await badges_repo.grant_badge(
                session, organization_id=organization_id, badge_id=definition.id
            )
            granted.append(definition.code)
        elif not satisfied and existing_grant is not None:
            await badges_repo.revoke_badge(existing_grant)

    return granted
