"""The rules layer is the part QA must be able to trust, so every rule is pinned by a test."""
import itertools

import pytest

from app.controls import ANNEX22_LIFECYCLE
from app.rules import RULES, adaptiveness, decide, human_in_the_loop
from app.schema import Classification, FIELD_VALUES


def C(g, m, a):
    return Classification(gmp_relevance=g, model_type=m, autonomy=a)


@pytest.mark.parametrize("g,m,a,verdict,rule", [
    ("not_gmp", "generative", "acts_autonomously", "outside_gmp", "R1-outside-gmp"),
    ("not_gmp", "unclear", "unclear", "outside_gmp", "R1-outside-gmp"),
    ("critical", "generative", "recommends", "not_permitted_critical", "R2-critical-nonstatic"),  # HITL does not rescue critical GenAI
    ("critical", "dynamic", "acts_with_oversight", "not_permitted_critical", "R2-critical-nonstatic"),
    ("critical", "probabilistic", "informs", "not_permitted_critical", "R2-critical-nonstatic"),
    ("critical", "unclear", "recommends", "needs_more_information", "R3-unclear"),
    ("unclear", "static", "informs", "needs_more_information", "R3-unclear"),
    ("unclear", "generative", "recommends", "needs_more_information", "R3-unclear"),
    ("critical", "non_ml", "acts_autonomously", "not_ai_annex11", "R4-non-ml"),
    ("non_critical", "non_ml", "informs", "not_ai_annex11", "R4-non-ml"),
    ("critical", "static", "acts_autonomously", "annex22_full", "R5-critical-static"),
    ("non_critical", "generative", "acts_autonomously", "hitl_required", "R6-genai-no-hitl"),
    ("non_critical", "generative", "acts_with_oversight", "hitl_required", "R6-genai-no-hitl"),
    ("non_critical", "generative", "unclear", "needs_more_information", "R7-genai-autonomy-unclear"),
    ("non_critical", "generative", "recommends", "permitted_with_hitl", "R8-genai-hitl"),
    ("non_critical", "generative", "informs", "permitted_with_hitl", "R8-genai-hitl"),
    ("non_critical", "static", "acts_autonomously", "permitted_risk_based", "R9-noncritical-ml"),
    ("non_critical", "dynamic", "recommends", "permitted_risk_based", "R9-noncritical-ml"),
])
def test_rule_table(g, m, a, verdict, rule):
    out = decide(True, C(g, m, a))
    assert (out.verdict, out.rule_id) == (verdict, rule)


def test_out_of_scope():
    assert decide(False, None).verdict == "out_of_scope"


def test_every_combination_has_exactly_one_verdict():
    """No gap in the table: all 4 x 6 x 5 = 120 combinations resolve."""
    for g, m, a in itertools.product(*FIELD_VALUES.values()):
        out = decide(True, C(g, m, a))
        assert out.verdict
        assert out.sources, "every verdict cites at least one source"


def test_rule_ids_unique():
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids))


def test_critical_static_gets_full_lifecycle_and_hitl_controls():
    out = decide(True, C("critical", "static", "recommends"))
    assert set(ANNEX22_LIFECYCLE) <= set(out.controls)
    assert "HUMAN_REVIEW" in out.controls
    assert "HUMAN_REVIEW" not in decide(True, C("critical", "static", "acts_autonomously")).controls


def test_genai_controls_include_quality_unit_review():
    for a in ("recommends", "acts_autonomously"):
        assert "QU_REVIEW" in decide(True, C("non_critical", "generative", a)).controls


def test_dynamic_noncritical_gets_lifecycle_control():
    assert "DYNAMIC_LIFECYCLE" in decide(True, C("non_critical", "dynamic", "recommends")).controls
    assert "DYNAMIC_LIFECYCLE" not in decide(True, C("non_critical", "static", "recommends")).controls


def test_questions_only_for_unclear_fields():
    out = decide(True, C("unclear", "unclear", "recommends"))
    assert len(out.questions) == 2
    assert decide(True, C("critical", "static", "informs")).questions == ()


def test_derived_fields():
    assert human_in_the_loop(C("critical", "static", "recommends")) == "yes"
    assert human_in_the_loop(C("critical", "static", "acts_with_oversight")) == "no"
    assert human_in_the_loop(C("critical", "static", "unclear")) == "unclear"
    assert adaptiveness(C("critical", "dynamic", "informs")) == "adaptive"
    assert adaptiveness(C("critical", "generative", "informs")) == "locked"


def test_lookup_assistant_needs_no_quality_unit_review_of_output():
    """An LLM that only informs produces no GMP content to clear (independent review, finding 9)."""
    assert "QU_REVIEW" not in decide(True, C("non_critical", "generative", "informs")).controls
    assert "QU_REVIEW" in decide(True, C("non_critical", "generative", "recommends")).controls


def test_hosted_genai_gets_supplier_security_and_data_integrity():
    out = decide(True, C("non_critical", "generative", "recommends")).controls
    assert {"SUPPLIER", "SECURITY", "DATA_INTEGRITY"} <= set(out)
