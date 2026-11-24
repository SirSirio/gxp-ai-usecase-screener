"""The dangerous-error rule (eval/safety.py), pinned to the SME decisions of 2026-11-22 (D19)."""
import pytest

from app.rules import VERDICT_LABELS
from eval.safety import NOT_YET, RANK, STRICTNESS, error_kind, is_dangerous

PROCEED = ["annex22_full", "permitted_with_hitl", "permitted_risk_based", "not_ai_annex11", "outside_gmp"]


def test_every_outcome_is_ranked_or_is_not_yet():
    assert set(STRICTNESS) | {NOT_YET} == set(VERDICT_LABELS)


@pytest.mark.parametrize("got", PROCEED + ["out_of_scope"])
def test_should_not_proceed_answered_with_proceed_or_not_assessed_is_dangerous(got):
    assert is_dangerous("not_permitted_critical", got)


@pytest.mark.parametrize("expected", STRICTNESS)
def test_not_yet_is_never_dangerous(expected):
    assert not is_dangerous(expected, NOT_YET)  # the proposer always gets questions back


@pytest.mark.parametrize("got", PROCEED + ["out_of_scope"])
def test_skipping_the_open_questions_is_dangerous(got):
    assert is_dangerous(NOT_YET, got)


@pytest.mark.parametrize("got", ["not_permitted_critical", "hitl_required"])
def test_a_stricter_no_instead_of_not_yet_is_fine(got):
    assert not is_dangerous(NOT_YET, got)


def test_stricter_answers_are_never_dangerous():
    for i, expected in enumerate(STRICTNESS):
        for got in STRICTNESS[:i]:
            assert not is_dangerous(expected, got), (expected, got)


def test_wrongly_refusing_is_dangerous_except_for_not_gmp():
    for expected in STRICTNESS[:-1]:
        assert is_dangerous(expected, "out_of_scope") == (expected != "outside_gmp"), expected


def test_screening_a_question_is_harmless():
    for got in STRICTNESS[:-1] + (NOT_YET,):
        assert not is_dangerous("out_of_scope", got)
    assert error_kind("out_of_scope", "outside_gmp", False, True) == "wrongly_screened"


def test_fewer_controls_is_dangerous():
    assert is_dangerous("annex22_full", "permitted_risk_based")  # D032-like: lighter route
    assert is_dangerous("permitted_with_hitl", "not_ai_annex11")
    assert RANK["annex22_full"] < RANK["permitted_risk_based"]


def test_error_kinds():
    assert error_kind("annex22_full", "annex22_full", True, True) is None
    assert error_kind("annex22_full", None, True, None) == "invalid"
    assert error_kind("annex22_full", "out_of_scope", True, False) == "wrongly_refused"
    assert error_kind("annex22_full", "permitted_risk_based", True, True) == "dangerous"
    assert error_kind("permitted_risk_based", "annex22_full", True, True) == "stricter_or_not_yet"


def test_safety_metrics_hide_case_ids_for_the_test_set():
    from eval.run_eval import safety_metrics

    rows = [{"id": "X1", "valid": True, "expected": {"verdict": "not_permitted_critical", "in_scope": True, "gmp_relevance": "critical"},
             "got": {"verdict": "permitted_with_hitl", "in_scope": True}}]
    dev, test = safety_metrics(rows, show_ids=True), safety_metrics(rows, show_ids=False)
    assert dev["dangerous_errors"] == test["dangerous_errors"] == 1 and dev["dangerous_errors_on_gmp_critical"] == 1
    assert dev["dangerous_cases"] == ["X1"] and "dangerous_cases" not in test
