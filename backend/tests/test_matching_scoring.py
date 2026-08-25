"""Los "25 casos de oro" del motor de matching (fase 6.8, §H.7: "cualquier
cambio de fórmula debe justificar cada diferencia") — tests puros contra
services/matching.py, sin base de datos. Cubren la matemática de cada
sub-fórmula de docs/03-MATCHING-ENGINE.md §H.4 y la agregación general.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.services import matching


# ─── category_fit (§H.4.1) ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "node_scores,is_primary,expected_score",
    [
        ([1.0], True, 1.0),  # nodo exacto
        ([0.90], True, 0.95),  # descendiente + bonus primary
        ([0.90], False, 0.90),  # descendiente sin bonus
        ([0.70], False, 0.70),  # ancestro
        ([0.50], False, 0.50),  # hermano a 1 nivel
        ([0.30], False, 0.30),  # hermano a 2 niveles
        ([], False, 0.0),  # sin categoría en común
        ([0.30, 0.90], False, 0.90),  # toma el mejor de varios nodos ligados
    ],
)
def test_category_fit(node_scores, is_primary, expected_score):
    score, _detail = matching.compute_category_fit(node_scores, is_primary)
    assert score == pytest.approx(expected_score)


# ─── attribute_fit (§H.4.2) ─────────────────────────────────────────────────────


def test_attribute_fit_none_when_no_criteria():
    assert matching.compute_attribute_fit([]) is None


def test_attribute_fit_averages_factors():
    score, detail = matching.compute_attribute_fit([1.0, 0.6, 0.3, 0.0])
    assert score == pytest.approx(0.475)
    assert "1 de 4" in detail


@pytest.mark.parametrize(
    "meets,declared,is_close,expected",
    [
        (True, True, False, 1.0),
        (False, True, True, 0.6),
        (False, False, False, 0.3),
        (False, True, False, 0.0),
    ],
)
def test_attribute_criterion_factor(meets, declared, is_close, expected):
    assert (
        matching.attribute_criterion_factor(
            meets=meets, declared=declared, is_close=is_close
        )
        == expected
    )


# ─── experience_fit (§H.4.4) ────────────────────────────────────────────────────


def test_experience_fit_no_history_is_zero():
    score, _ = matching.compute_experience_fit(
        years_experience=None,
        case_study_count=0,
        verified_case_study_count=0,
        client_reference_count=0,
    )
    assert score == 0.0


def test_experience_fit_full_marks():
    score, _ = matching.compute_experience_fit(
        years_experience=10,
        case_study_count=5,
        verified_case_study_count=1,
        client_reference_count=3,
    )
    assert score == pytest.approx(1.0)


def test_experience_fit_verified_case_study_bonus_caps_at_one():
    score, _ = matching.compute_experience_fit(
        years_experience=10,
        case_study_count=5,
        verified_case_study_count=5,
        client_reference_count=0,
    )
    # f_industria=1, f_casos=min(1*1.15,1)=1, f_clientes=0 -> 0.45+0.35 = 0.80
    assert score == pytest.approx(0.80)


# ─── accreditation_fit (§H.4.5) ─────────────────────────────────────────────────


def test_accreditation_fit_accredited_long_validity():
    score, _ = matching.compute_accreditation_fit(
        status="ACCREDITED",
        valid_until=date(2027, 1, 1),
        completion_pct=100,
        today=date(2026, 1, 1),
    )
    assert score == 1.00


def test_accreditation_fit_accredited_expiring_soon():
    score, _ = matching.compute_accreditation_fit(
        status="ACCREDITED",
        valid_until=date(2026, 2, 1),
        completion_pct=100,
        today=date(2026, 1, 1),
    )
    assert score == 0.85


def test_accreditation_fit_under_review():
    score, _ = matching.compute_accreditation_fit(
        status="UNDER_REVIEW",
        valid_until=None,
        completion_pct=50,
        today=date(2026, 1, 1),
    )
    assert score == 0.40


def test_accreditation_fit_partial_completion_no_resolution():
    score, _ = matching.compute_accreditation_fit(
        status="PENDING_DOCUMENTS",
        valid_until=None,
        completion_pct=75,
        today=date(2026, 1, 1),
    )
    assert score == 0.25


def test_accreditation_fit_no_process():
    score, _ = matching.compute_accreditation_fit(
        status=None, valid_until=None, completion_pct=None, today=date(2026, 1, 1)
    )
    assert score == 0.00


def test_accreditation_fit_avl_approved():
    """Fase 8.8 — un AVL APPROVED por este comprador puntual corta la
    evaluación antes de mirar status/completion_pct: es la señal más fuerte
    posible, más fuerte que estar acreditado en programa (§H.4.5)."""
    score, _ = matching.compute_accreditation_fit(
        status=None,
        valid_until=None,
        completion_pct=None,
        today=date(2026, 1, 1),
        avl_status="APPROVED",
    )
    assert score == 1.00


# ─── performance_fit / responsiveness_fit (§H.4.6/7 — arranque neutral) ────────


def test_performance_fit_always_neutral():
    score, _ = matching.compute_performance_fit()
    assert score == 0.55


def test_responsiveness_fit_always_neutral():
    score, _ = matching.compute_responsiveness_fit()
    assert score == 0.55


# ─── capacity_fit (§H.4.8) ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "capacity,required,expected",
    [
        (None, 100, 0.50),
        (400, 0, 1.00),
        (400, 150, 1.00),  # ratio 2.67 >= 2.0
        (200, 150, 0.80),  # ratio 1.3333 -> 0.70 + 0.30*0.3333
        (100, 130, 0.40),  # ratio 0.77 -> tramo 0.7-1.0
        (50, 150, 0.15),  # ratio 0.33
    ],
)
def test_capacity_fit(capacity, required, expected):
    score, _ = matching.compute_capacity_fit(
        monthly_capacity=capacity, required_quantity=required
    )
    assert score == pytest.approx(expected, abs=1e-4)


# ─── modificadores ──────────────────────────────────────────────────────────────


def test_modifiers_none_when_all_clean():
    modifiers = matching.compute_modifiers(
        completion_pct=100, has_expired_documents=False, has_local_base=False
    )
    assert modifiers == []


def test_modifiers_incomplete_profile():
    modifiers = matching.compute_modifiers(
        completion_pct=40, has_expired_documents=False, has_local_base=False
    )
    assert modifiers == [
        {"key": "incomplete_profile", "factor": 0.90, "label": "Perfil incompleto"}
    ]


def test_modifiers_stack_multiplicatively():
    modifiers = matching.compute_modifiers(
        completion_pct=40, has_expired_documents=True, has_local_base=True
    )
    factors = [m["factor"] for m in modifiers]
    assert factors == [0.90, 0.85, 1.05]


# ─── score_candidate — fórmula general (§H.4) ──────────────────────────────────


def test_score_candidate_excludes_non_applicable_components():
    """Sin attribute_fit ni accreditation_fit definidos (None), Σwᵢ se
    recalcula solo sobre lo aplicable — no se cuentan como 0."""
    components = {
        "category_fit": (1.0, "exacto"),
        "attribute_fit": None,
        "territory_fit": (1.0, "misma comuna"),
        "experience_fit": (1.0, "full"),
        "accreditation_fit": None,
        "performance_fit": (0.55, "neutral"),
        "responsiveness_fit": (0.55, "neutral"),
        "capacity_fit": (1.0, "sobra"),
    }
    result = matching.score_candidate(
        components=components, modifiers=[], weights=matching.DEFAULT_WEIGHTS
    )
    applicable_weight = (
        20 + 15 + 12 + 10 + 8 + 5
    )  # sin attribute_fit(20) ni accreditation_fit(10)
    weighted_sum = 20 * 1.0 + 15 * 1.0 + 12 * 1.0 + 10 * 0.55 + 8 * 0.55 + 5 * 1.0
    expected = round(100 * weighted_sum / applicable_weight, 1)
    assert result["total_score"] == expected
    assert len(result["components"]) == 6


def test_score_candidate_all_components_full_marks_is_100():
    components = {k: (1.0, "full") for k in matching.DEFAULT_WEIGHTS}
    result = matching.score_candidate(
        components=components, modifiers=[], weights=matching.DEFAULT_WEIGHTS
    )
    assert result["total_score"] == 100.0


def test_score_candidate_applies_modifiers_multiplicatively():
    components = {k: (1.0, "full") for k in matching.DEFAULT_WEIGHTS}
    modifiers = [
        {"key": "incomplete_profile", "factor": 0.90, "label": "Perfil incompleto"}
    ]
    result = matching.score_candidate(
        components=components, modifiers=modifiers, weights=matching.DEFAULT_WEIGHTS
    )
    assert result["total_score"] == 90.0


def test_score_candidate_clamped_to_100():
    """Un modificador que empujara sobre 100 (no debería pasar con los
    factores documentados, pero la fórmula no debe devolver >100)."""
    components = {k: (1.0, "full") for k in matching.DEFAULT_WEIGHTS}
    modifiers = [{"key": "boost", "factor": 1.5, "label": "boost artificial de test"}]
    result = matching.score_candidate(
        components=components, modifiers=modifiers, weights=matching.DEFAULT_WEIGHTS
    )
    assert result["total_score"] == 100.0
