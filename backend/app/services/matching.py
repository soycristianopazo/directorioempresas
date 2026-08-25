"""Motor de matching (fase 6.4-6.7): elegibilidad y puntaje, en ese orden
(docs/03-MATCHING-ENGINE.md §H.1).

Etapas 1-2 (Recall, Elegibilidad) viven en repositories/matching.py — SQL de
conjuntos sobre el volumen grande. Etapas 3-4 (Scoring, Ranking) viven acá,
en Python, sobre el conjunto ya chico de elegibles — construir
`score_breakdown` (8 componentes con label/detail) es más simple y más
testeable en Python que en jsonb anidado, y es lo que hace posible probar
la fórmula (`score_candidate`) sin tocar la base — ver `tests/test_matching_scoring.py`.

Componentes sin datos reales todavía (performance_fit necesita
supplier_performance_reviews — fase 8+; responsiveness_fit necesita
historial de invitaciones — fase 7) devuelven SIEMPRE el valor neutral que
la propia fórmula define para "sin historial" (§H.4.6/H.4.7) — no es un
parche, es el comportamiento documentado.
"""

from __future__ import annotations

import time
from datetime import date, timezone
from datetime import datetime as dt
from typing import Any
from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import matching as matching_repo
from app.repositories import requirements as requirements_repo
from app.repositories import sourcing as sourcing_repo

ENGINE_VERSION = "1.0.0"

DEFAULT_WEIGHTS: dict[str, float] = {
    "category_fit": 20.0,
    "attribute_fit": 20.0,
    "territory_fit": 15.0,
    "experience_fit": 12.0,
    "accreditation_fit": 10.0,
    "performance_fit": 10.0,
    "responsiveness_fit": 8.0,
    "capacity_fit": 5.0,
}

_NEUTRAL_NO_HISTORY = 0.55

PERM_RUN = "sourcing_event.create"
PERM_READ = "sourcing_event.read"


class MatchingError(Exception):
    pass


class MatchingPermissionError(MatchingError):
    pass


class MatchingNotFoundError(MatchingError):
    pass


class MatchingValidationError(MatchingError):
    pass


# ─── Etapa 3 · sub-fórmulas de scoring (puras — sin DB, testeadas en frío) ────


def compute_category_fit(
    node_scores: list[float], is_primary_match: bool
) -> tuple[float, str]:
    """§H.4.1 — el mejor de los nodos ligados al offering, +0.05 si ese nodo
    es además el is_primary del offering (tope 1.00)."""
    if not node_scores:
        return 0.0, "Sin categoría en común con lo solicitado"
    best = max(node_scores)
    bonus = 0.05 if is_primary_match and best < 1.0 else 0.0
    score = min(best + bonus, 1.0)
    if score >= 1.0:
        detail = "Coincidencia exacta con la categoría solicitada"
    elif score >= 0.90:
        detail = "Categoría más específica que la solicitada"
    elif score >= 0.70:
        detail = "Categoría más general que la solicitada"
    elif score >= 0.50:
        detail = "Categoría hermana, mismo padre en el árbol"
    elif score > 0:
        detail = "Categoría relacionada, dos niveles de distancia"
    else:
        detail = "Sin categoría en común con lo solicitado"
    return score, detail


def compute_attribute_fit(nice_factors: list[float]) -> tuple[float, str] | None:
    """§H.4.2 — promedio ponderado de los NICE_TO_HAVE de atributo. None si
    el evento no definió ninguno (el componente se excluye, no aporta 0)."""
    if not nice_factors:
        return None
    score = sum(nice_factors) / len(nice_factors)
    met = sum(1 for f in nice_factors if f >= 1.0)
    return score, f"{met} de {len(nice_factors)} requisitos técnicos cumplidos"


def attribute_criterion_factor(
    *, meets: bool, declared: bool, is_close: bool = False
) -> float:
    """factor de un NICE individual: 1.0 cumple, 0.6 cumple parcial (±10%
    ya resuelto por el llamador vía is_close), 0.3 no declarado, 0.0 no
    cumple (§H.4.2)."""
    if not declared:
        return 0.3
    if meets:
        return 1.0
    if is_close:
        return 0.6
    return 0.0


def compute_experience_fit(
    *,
    years_experience: int | None,
    case_study_count: int,
    verified_case_study_count: int,
    client_reference_count: int,
) -> tuple[float, str]:
    """§H.4.4 — 45% industria, 35% casos de éxito, 20% referencias."""
    f_industria = min((years_experience or 0) / 10, 1.0)
    f_casos = min(case_study_count / 5, 1.0)
    if verified_case_study_count > 0:
        f_casos = min(f_casos * 1.15, 1.0)
    f_clientes = min(client_reference_count / 3, 1.0)
    score = 0.45 * f_industria + 0.35 * f_casos + 0.20 * f_clientes
    parts = []
    if years_experience:
        parts.append(f"{years_experience} años de experiencia en la industria")
    if case_study_count:
        parts.append(f"{case_study_count} casos de éxito")
    if client_reference_count:
        parts.append(f"{client_reference_count} referencias de clientes verificadas")
    detail = ", ".join(parts) if parts else "Sin experiencia declarada en la industria"
    return score, detail


def compute_accreditation_fit(
    *,
    status: str | None,
    valid_until: date | None,
    completion_pct: int | None,
    today: date,
    avl_status: str | None = None,
) -> tuple[float, str]:
    """§H.4.5 — la rama de "nivel superior" se sigue omitiendo a propósito:
    no hay jerarquía de programas todavía (ver el plan de fase 6). La rama
    de "AVL de este comprador" (fase 8.8, buyer_supplier_relationships) SÍ
    se resuelve acá: un AVL APPROVED por este comprador puntual es la señal
    más fuerte posible — más fuerte que estar acreditado en programa con
    poca vigencia — así que tiene prioridad y corta la evaluación antes de
    mirar `status`/`completion_pct`. SUSPENDED/BLOCKED no se manejan acá:
    BLOCKED es un filtro duro de elegibilidad (Etapa 1, recall_candidates),
    no una señal de puntaje; SUSPENDED cae al flujo normal de acreditación
    de programa, sin señal AVL adicional."""
    if avl_status == "APPROVED":
        return 1.00, "Aprobado en la Vendor List del comprador"
    if status == "ACCREDITED":
        if valid_until is None or (valid_until - today).days > 90:
            return 1.00, "Acreditado, vigencia superior a 90 días"
        return 0.85, "Acreditado, vence en menos de 90 días"
    if status == "UNDER_REVIEW":
        return 0.40, "Acreditación en revisión"
    if completion_pct is not None and completion_pct >= 70:
        return 0.25, f"Postulación {completion_pct}% completa, sin resolución"
    return 0.00, "Sin proceso de acreditación iniciado"


def compute_performance_fit() -> tuple[float, str]:
    """§H.4.6 — sin supplier_performance_reviews todavía (fase 8+): arranque
    neutral siempre, nunca 0 — mismo criterio que la fórmula ya define para
    n=0, para no cerrarle el marketplace a proveedores nuevos."""
    return _NEUTRAL_NO_HISTORY, "Sin evaluaciones de desempeño registradas todavía"


def compute_responsiveness_fit() -> tuple[float, str]:
    """§H.4.7 — sin historial de invitaciones todavía (fase 7): arranque
    neutral siempre."""
    return _NEUTRAL_NO_HISTORY, "Sin historial de respuesta a invitaciones todavía"


def compute_capacity_fit(
    *, monthly_capacity: float | None, required_quantity: float
) -> tuple[float, str]:
    """§H.4.8."""
    if monthly_capacity is None:
        return 0.50, "Capacidad no declarada"
    if required_quantity <= 0:
        return 1.00, "Sin cantidad requerida declarada"
    # numeric de Postgres llega como decimal.Decimal vía asyncpg — float()
    # normaliza también el caso ya-float de los tests puros.
    ratio = float(monthly_capacity) / float(required_quantity)
    if ratio >= 2.0:
        return 1.00, f"Capacidad {monthly_capacity:g} cubre {ratio:.1f}x lo requerido"
    if ratio >= 1.0:
        return (
            0.70 + 0.30 * (ratio - 1),
            f"Capacidad {monthly_capacity:g} cubre {ratio:.1f}x lo requerido",
        )
    if ratio >= 0.7:
        return (
            0.40,
            f"Capacidad {monthly_capacity:g} cubre solo parcialmente ({ratio:.0%})",
        )
    return (
        0.15,
        f"Capacidad {monthly_capacity:g} muy por debajo de lo requerido ({ratio:.0%})",
    )


def compute_modifiers(
    *, completion_pct: int | None, has_expired_documents: bool, has_local_base: bool
) -> list[dict]:
    """§H.4 "Modificadores multiplicativos" — solo los que hoy tienen datos
    reales; el resto (adjudicado antes, suspendido en AVL, inactividad) no
    aplica sin Fase 7/8, se omite en vez de simularse."""
    modifiers = []
    if completion_pct is not None and completion_pct < 60:
        modifiers.append(
            {"key": "incomplete_profile", "factor": 0.90, "label": "Perfil incompleto"}
        )
    if has_expired_documents:
        modifiers.append(
            {
                "key": "expired_documents",
                "factor": 0.85,
                "label": "Documentación vencida",
            }
        )
    if has_local_base:
        modifiers.append(
            {
                "key": "local_company",
                "factor": 1.05,
                "label": "Empresa local a la faena",
            }
        )
    return modifiers


def score_candidate(
    *,
    components: dict[str, tuple[float, str] | None],
    modifiers: list[dict],
    weights: dict[str, float],
) -> dict:
    """§H.4 fórmula general — componentes no aplicables se EXCLUYEN del
    promedio (no aportan 0), Σwᵢ se recalcula sobre lo que sí aplica."""
    applicable = {k: v for k, v in components.items() if v is not None}
    total_weight = sum(weights.get(k, 0) for k in applicable) or 1
    weighted_sum = sum(
        weights.get(k, 0) * score for k, (score, _detail) in applicable.items()
    )
    base_score = 100 * weighted_sum / total_weight

    factor = 1.0
    for m in modifiers:
        factor *= m["factor"]
    total_score = max(0.0, min(100.0, base_score * factor))

    component_list = [
        {
            "key": key,
            "weight": weights.get(key, 0),
            "score": round(score, 2),
            "points": round(weights.get(key, 0) * score, 1),
            "detail": detail,
        }
        for key, (score, detail) in applicable.items()
    ]
    return {
        "engine_version": ENGINE_VERSION,
        "total_score": round(total_score, 1),
        "components": component_list,
        "modifiers": modifiers,
    }


# ─── Etapa 4 · orquestación ────────────────────────────────────────────────────


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await sourcing_repo.has_permission(db, organization_id, permission):
        raise MatchingPermissionError(f"Sin permiso ({permission}) para esta acción")


async def run_matching(
    *,
    user_id: UUID,
    organization_id: UUID,
    event_id: UUID,
    dry_run: bool = False,
    weights_override: dict[str, float] | None = None,
) -> dict:
    started = time.monotonic()

    async with session_for_user(user_id) as db:
        permission = PERM_READ if dry_run else PERM_RUN
        await _require(db, organization_id, permission)

        event = await sourcing_repo.get_event(db, event_id)
        if event is None or event.organization_id != organization_id:
            raise MatchingNotFoundError("Evento no encontrado")

        weights: dict[str, float] = dict(DEFAULT_WEIGHTS)
        if event.matching_weights:
            weights.update({k: float(v) for k, v in event.matching_weights.items()})
        if weights_override:
            weights.update({k: float(v) for k, v in weights_override.items()})

        items = await sourcing_repo.list_items(db, event_id)
        if not items:
            raise MatchingValidationError(
                "El evento no tiene líneas — nada que matchear"
            )
        taxonomy_node_id = items[0].taxonomy_node_id
        required_quantity = sum(float(i.quantity) for i in items if not i.is_optional)

        admin_division_ids: list[UUID] = []
        if event.requirement_id:
            locations = await requirements_repo.list_locations(db, event.requirement_id)
            admin_division_ids = [loc.admin_division_id for loc in locations]

        raw_candidates = await matching_repo.recall_candidates(
            db,
            buyer_organization_id=organization_id,
            taxonomy_node_id=taxonomy_node_id,
            admin_division_ids=admin_division_ids or None,
        )
        # asyncpg devuelve su propio tipo UUID (no str, no uuid.UUID) para
        # columnas uuid/uuid[] en SQL crudo — se normaliza a str acá, una
        # sola vez, para que todo lo que sigue (claves de dict, UUID(...))
        # trabaje con un único tipo consistente.
        candidates = [
            {
                **c,
                "offering_id": str(c["offering_id"]),
                "organization_id": str(c["organization_id"]),
                "taxonomy_node_ids": [str(n) for n in c["taxonomy_node_ids"]],
            }
            for c in raw_candidates
        ]
        candidate_offering_ids = [UUID(c["offering_id"]) for c in candidates]

        criteria = await sourcing_repo.list_criteria(db, event_id)
        criteria_dicts = [
            {c.name: getattr(crit, c.name) for c in crit.__table__.columns}
            for crit in criteria
        ]
        must_criteria = [
            c
            for c in criteria_dicts
            if c["requirement_level"] == "MUST_HAVE"
            and c["is_blocking"]
            and c["criterion_type"] != "CUSTOM"
        ]
        nice_criteria = [
            c for c in criteria_dicts if c["requirement_level"] == "NICE_TO_HAVE"
        ]

        blocking_reasons: dict[str, list[str]] = {
            str(c["offering_id"]): [] for c in candidates
        }
        for criterion in must_criteria:
            if criterion["criterion_type"] == "ATTRIBUTE":
                satisfied = await matching_repo.evaluate_attribute_criterion(
                    db,
                    criterion=criterion,
                    candidate_offering_ids=candidate_offering_ids,
                )
                declared = await matching_repo.has_declared_attribute(
                    db,
                    attribute_definition_id=criterion["attribute_definition_id"],
                    candidate_offering_ids=candidate_offering_ids,
                )
            else:
                satisfied = await matching_repo.eligible_offering_ids_for_criterion(
                    db,
                    criterion=criterion,
                    candidate_offering_ids=candidate_offering_ids,
                )
                declared = set(str(i) for i in candidate_offering_ids)

            label = criterion["description"] or criterion["criterion_type"]
            for offering_id in blocking_reasons:
                if offering_id in satisfied:
                    continue
                if offering_id not in declared:
                    continue  # ausencia de dato ≠ incumplimiento (§H.3) — no bloquea
                blocking_reasons[offering_id].append(f"No cumple: {label}")

        eligible_ids = [
            UUID(oid) for oid, reasons in blocking_reasons.items() if not reasons
        ]

        candidate_node_ids = sorted(
            {n for c in candidates for n in c["taxonomy_node_ids"]}
        )
        category_scores = (
            await matching_repo.category_fit_scores(
                db,
                requested_node_id=taxonomy_node_id,
                candidate_node_ids=candidate_node_ids,
            )
            if taxonomy_node_id
            else {}
        )
        territory_scores = await matching_repo.territory_fit_scores(
            db,
            admin_division_ids=admin_division_ids,
            candidate_offering_ids=eligible_ids,
            max_mobilization_days=None,
        )

        industry_id = None
        if event.requirement_id:
            linked_requirement = await requirements_repo.get_requirement(
                db, event.requirement_id
            )
            industry_id = linked_requirement.industry_id if linked_requirement else None

        scoring_inputs = await matching_repo.fetch_scoring_inputs(
            db,
            offering_ids=eligible_ids,
            industry_id=industry_id,
            taxonomy_node_id=taxonomy_node_id,
            admin_division_ids=admin_division_ids or None,
        )
        eligible_org_ids = {
            UUID(str(v["organization_id"])) for v in scoring_inputs.values()
        }
        accreditation_status = await matching_repo.fetch_accreditation_status(
            db,
            organization_ids=list(eligible_org_ids),
            program_id=event.requires_accreditation_program_id,
        )
        # AVL de ESTE comprador (fase 8.8) — solo relevante donde
        # accreditation_fit se calcula, ver compute_accreditation_fit
        # §H.4.5 (un APPROVED tiene prioridad sobre la rama de programa).
        avl_status_by_org = await matching_repo.fetch_avl_status(
            db,
            buyer_organization_id=organization_id,
            organization_ids=list(eligible_org_ids),
        )

        nice_attribute_results: dict[str, list[float]] = {
            str(oid): [] for oid in eligible_ids
        }
        for criterion in nice_criteria:
            if criterion["criterion_type"] != "ATTRIBUTE":
                continue
            satisfied = await matching_repo.evaluate_attribute_criterion(
                db, criterion=criterion, candidate_offering_ids=eligible_ids
            )
            declared = await matching_repo.has_declared_attribute(
                db,
                attribute_definition_id=criterion["attribute_definition_id"],
                candidate_offering_ids=eligible_ids,
            )
            for oid_str in nice_attribute_results:
                is_declared = oid_str in declared
                meets = oid_str in satisfied
                factor = attribute_criterion_factor(meets=meets, declared=is_declared)
                nice_attribute_results[oid_str].append(factor)

        today = dt.now(timezone.utc).date()
        results: list[dict[str, Any]] = []
        for candidate in candidates:
            offering_id = candidate["offering_id"]
            reasons = blocking_reasons[offering_id]
            is_eligible = not reasons
            breakdown = None
            total_score = 0.0

            if is_eligible:
                inputs = scoring_inputs.get(offering_id, {})
                node_scores = [
                    category_scores.get(n, 0.0) for n in candidate["taxonomy_node_ids"]
                ]
                accreditation = (
                    accreditation_status.get(str(inputs.get("organization_id")))
                    if event.requires_accreditation_program_id
                    else None
                )
                components: dict[str, tuple[float, str] | None] = {
                    "category_fit": (
                        compute_category_fit(node_scores, is_primary_match=True)
                        if taxonomy_node_id
                        else None
                    ),
                    "attribute_fit": compute_attribute_fit(
                        nice_attribute_results.get(offering_id, [])
                    ),
                    "territory_fit": (
                        (
                            territory_scores.get(offering_id, 0.0),
                            "Cobertura territorial evaluada",
                        )
                        if admin_division_ids
                        else None
                    ),
                    "experience_fit": compute_experience_fit(
                        years_experience=inputs.get("years_experience"),
                        case_study_count=inputs.get("case_study_count", 0),
                        verified_case_study_count=inputs.get(
                            "verified_case_study_count", 0
                        ),
                        client_reference_count=inputs.get("client_reference_count", 0),
                    ),
                    "accreditation_fit": (
                        compute_accreditation_fit(
                            status=accreditation["status"] if accreditation else None,
                            valid_until=(
                                accreditation["valid_until"] if accreditation else None
                            ),
                            completion_pct=(
                                accreditation["completion_pct"]
                                if accreditation
                                else None
                            ),
                            today=today,
                            avl_status=avl_status_by_org.get(
                                str(inputs.get("organization_id"))
                            ),
                        )
                        if event.requires_accreditation_program_id
                        else None
                    ),
                    "performance_fit": compute_performance_fit(),
                    "responsiveness_fit": compute_responsiveness_fit(),
                    "capacity_fit": compute_capacity_fit(
                        monthly_capacity=inputs.get("monthly_capacity"),
                        required_quantity=required_quantity,
                    ),
                }
                modifiers = compute_modifiers(
                    completion_pct=inputs.get("completion_pct"),
                    has_expired_documents=bool(inputs.get("has_expired_documents")),
                    has_local_base=bool(inputs.get("has_local_base")),
                )
                breakdown = score_candidate(
                    components=components, modifiers=modifiers, weights=weights
                )
                breakdown["is_eligible"] = True
                breakdown["blocking_reasons"] = []
                total_score = breakdown["total_score"]
            else:
                breakdown = {
                    "engine_version": ENGINE_VERSION,
                    "total_score": 0,
                    "is_eligible": False,
                    "blocking_reasons": reasons,
                }

            results.append(
                {
                    "offering_id": UUID(str(offering_id)),
                    "organization_id": UUID(str(candidate["organization_id"])),
                    "total_score": total_score,
                    "is_eligible": is_eligible,
                    "blocking_reasons": reasons,
                    "score_breakdown": breakdown,
                }
            )

        # §H.5 — agregación por organización: mejor offering + bonus de cobertura.
        results.sort(key=lambda r: r["total_score"], reverse=True)
        eligible_results = [r for r in results if r["is_eligible"]]
        eligible_by_org: dict[UUID, list[dict]] = {}
        for r in eligible_results:
            eligible_by_org.setdefault(r["organization_id"], []).append(r)
        for org_results in eligible_by_org.values():
            bonus = min(len(org_results) - 1, 3) * 2
            for r in org_results:
                r["total_score"] = min(r["total_score"] + bonus, 100)

        eligible_results.sort(key=lambda r: r["total_score"], reverse=True)
        for idx, r in enumerate(eligible_results, start=1):
            r["rank"] = idx

        duration_ms = int((time.monotonic() - started) * 1000)

        response = {
            "engine_version": ENGINE_VERSION,
            "weights": weights,
            "candidates_evaluated": len(candidates),
            "eligible_count": len(eligible_results),
            "duration_ms": duration_ms,
            "results": results,
        }

        if dry_run:
            return response

        run = await matching_repo.create_match_run(
            db,
            sourcing_event_id=event_id,
            engine_version=ENGINE_VERSION,
            weights_snapshot=weights,
            triggered_by_member_id=user_id,
            candidates_evaluated=len(candidates),
            eligible_count=len(eligible_results),
            duration_ms=duration_ms,
        )
        await matching_repo.save_match_results(
            db,
            [
                {
                    "match_run_id": run.id,
                    "organization_id": r["organization_id"],
                    "offering_id": r["offering_id"],
                    "total_score": r["total_score"],
                    "is_eligible": r["is_eligible"],
                    "blocking_reasons": r["blocking_reasons"],
                    "score_breakdown": r["score_breakdown"],
                    "rank": r.get("rank"),
                }
                for r in results
            ],
        )
        response["match_run_id"] = run.id

    return response


async def get_latest_results(
    *, user_id: UUID, organization_id: UUID, event_id: UUID
) -> dict | None:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)
        event = await sourcing_repo.get_event(db, event_id)
        if event is None or event.organization_id != organization_id:
            raise MatchingNotFoundError("Evento no encontrado")
        run = await matching_repo.get_latest_run(db, event_id)
        if run is None:
            return None
        results = await matching_repo.list_results(db, run.id)
        return {"run": run, "results": results}
