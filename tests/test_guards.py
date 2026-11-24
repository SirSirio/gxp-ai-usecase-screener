"""Safety guards (app/guards.py): they may only turn an outcome into "Not yet". SME decisions W27 / D20."""
import pytest

from app.guards import check, tick_values
from app.intake_form import normalize_form
from app.rules import decide
from app.schema import Classification


def _form(gmp=None, ai=None, use=None, who="", areas=("qa",), what="An AI tool supports the team with its daily document work."):
    return normalize_form({"what": what, "areas": list(areas), "who_checks": who,
                           "gmp_impact": {"choice": gmp, "explain": ""}, "ai_type": {"choice": ai, "explain": ""},
                           "output_use": {"choice": use, "explain": ""}})


def _run(form, gmp, model, autonomy, in_scope=True):
    c = Classification(gmp_relevance=gmp, model_type=model, autonomy=autonomy)
    return check(form, in_scope, c, decide(True, c))


# ---------------------------------------------------------------- G1: review not stated (D035)
@pytest.mark.parametrize("who", ["", "not decided yet", "TBD", "n/a", "nobody yet", "don't know"])
def test_g1_no_assumed_review_step(who):
    g = _run(_form(ai="llm", use="not_sure", who=who), "non_critical", "generative", "recommends")
    assert g and g.rule_id == "G1-review-not-stated" and g.verdict == "needs_more_information" and g.questions


def test_g1_keeps_a_clear_no():
    """A GMP-critical LLM is 'Should not proceed' with or without review: G1 must not soften it to 'Not yet'."""
    assert _run(_form(ai="llm", use=None, who=""), "critical", "generative", "recommends") is None


def test_g1_does_not_fire_when_a_check_is_described():
    assert _run(_form(ai="llm", use="not_sure", who="QA reviews and approves each translation"), "non_critical", "generative", "recommends") is None


def test_g1_does_not_fire_when_output_use_is_ticked_and_a_check_is_described():
    assert _run(_form(ai="llm", use="person_approves", who="QA reviews every report against the raw data and signs it in the eDMS"),
                "non_critical", "generative", "recommends") is None


# ---------------------------------------------------------------- G1b: receiving is not a check (D038, SME 2026-11-23)
@pytest.mark.parametrize("who", ["QA and the area owners receive it", "it is e-mailed to QA", "QA gets it", "sent to the area owners",
                                 "QA reads it", "", "nobody"])
def test_g1b_person_approves_ticked_but_only_receiving_described(who):
    g = _run(_form(ai="llm", use="person_approves", who=who), "non_critical", "generative", "recommends")
    assert g and g.rule_id == "G1-check-not-described" and g.verdict == "needs_more_information" and g.question_fields == ("autonomy",)


@pytest.mark.parametrize("who", ["QA receives it and reviews each report before release", "the area owner gets it and approves it",
                                 "QA tjekker hver rapport", "second-person verification in LIMS"])
def test_g1b_receiving_plus_a_check_is_a_check(who):
    assert _run(_form(ai="llm", use="person_approves", who=who), "non_critical", "generative", "recommends") is None


def test_g1b_receive_wording_in_the_output_use_note_counts_too():
    f = _form(ai="llm", use="person_approves", who="")
    f["output_use"]["explain"] = "QA gets it"
    assert _run(f, "non_critical", "generative", "recommends").rule_id == "G1-check-not-described"


def test_g1b_keeps_a_clear_no():
    """D038 itself: a GMP-critical LLM stays 'Should not proceed'; the check question would not change that."""
    assert _run(_form(ai="llm", use="person_approves", who="QA receives it"), "critical", "generative", "recommends") is None


def test_g1_receive_only_also_counts_as_no_check_when_nothing_is_ticked():
    g = _run(_form(ai="llm", use="not_sure", who="QA receives it"), "non_critical", "generative", "recommends")
    assert g and g.rule_id == "G1-review-not-stated"


def test_g1_accepted_trade_off_review_written_in_the_task_text():
    """SME decision: a review step written only in the task box still gets the question (never dangerous)."""
    f = _form(ai="llm", use="not_sure", who="", what="An LLM translates SOPs; QA reviews and approves every translation.")
    assert _run(f, "non_critical", "generative", "recommends").rule_id == "G1-review-not-stated"


# ---------------------------------------------------------------- G2: ticks stricter (D032)
def test_g2_ticks_stricter_than_the_model_gives_not_yet_with_the_contradiction():
    f = _form(gmp="yes", ai="trained_fixed", use="auto_monitored", who="QA only sees the exceptions")
    g = _run(f, "critical", "non_ml", "acts_with_oversight")  # model: Annex 11 only; ticks: full Annex 22
    assert g and g.rule_id == "G2-ticks-stricter" and g.verdict == "needs_more_information"
    d = g.question_details[0]
    assert d["your_answer_means"] == "a trained model, frozen in use" and d["description_reads_as"] == "fixed rules, not ML"
    assert g.question_fields == ("model_type",)


def test_g2_explains_the_contradiction_the_sme_ran_into():
    """The SME's live case (W35): 'Yes' ticked for GMP impact, but improvement ideas go through change control."""
    f = _form(gmp="yes", ai="llm", use="informs", who="scientists review the suggestions",
              what="An LLM analyses fermentation data and suggests process improvements; changes go through change control.")
    g = _run(f, "non_critical", "generative", "informs")
    assert g.rule_id == "G2-ticks-stricter" and g.question_fields == ("gmp_relevance",)
    d = g.question_details[0]
    assert d["question_id"] == "gmp_impact" and d["your_answer"] == "Yes, directly"
    assert d["your_answer_means"] == "GMP-critical" and d["description_reads_as"] == "GMP, non-critical"
    assert d["outcome_if_your_answer_is_right"].startswith("Should not proceed")
    assert d["outcome_if_the_description_is_right"].startswith("Generative AI: proceed")
    assert "No, only indirectly" in d["how_to_resolve"] and "change control" in d["how_to_resolve"]


def test_g2_model_stricter_than_the_ticks_stands():
    f = _form(gmp="no", ai="llm", use="person_approves", who="QA")
    assert _run(f, "critical", "generative", "acts_autonomously") is None  # model says stricter: no guard


def test_g2_agreement_or_harmless_difference_does_not_fire():
    assert _run(_form(gmp="yes", ai="trained_fixed", use="auto_unchecked", who="nobody"), "critical", "static", "acts_autonomously") is None
    # vendor_unknown and not_sure carry no classification, so they cannot trigger G2
    assert tick_values(_form(ai="vendor_unknown", use="not_sure")) == {}


def test_guards_never_run_on_out_of_scope_or_quick_mode():
    c = Classification(gmp_relevance="critical", model_type="non_ml", autonomy="acts_with_oversight")
    f = _form(gmp="yes", ai="trained_fixed", use="auto_monitored", who="x")
    assert check(f, False, c, decide(True, c)) is None  # "no proposal, no assessment"
    assert check(None, True, c, decide(True, c)) is None  # quick mode has no ticks


def test_guards_only_ever_produce_not_yet():
    """Exhaustive: whatever the model says and whatever is ticked, a guard can only return Not yet."""
    import itertools

    from app.schema import FIELD_VALUES

    forms = [_form(gmp=g, ai=a, use=u, who=w) for g in (None, "yes", "no") for a in (None, "llm", "rules", "trained_fixed")
             for u in (None, "not_sure", "person_approves", "auto_unchecked") for w in ("", "QA checks each one")]
    for f, combo in itertools.product(forms, itertools.product(*FIELD_VALUES.values())):
        g = _run(f, *combo)
        assert g is None or g.verdict == "needs_more_information"


def test_pipeline_applies_the_guard(index, audit):
    from app.assessors.llm import LLMAssessor
    from app.intake_form import form_to_text
    from app.llm.base import ChatResponse
    from app.llm.fake import FakeChatClient
    from app.pipeline import run_assessment
    import json

    a22 = index.section_chunks("A22", "1")[0].id
    answer = {"in_scope": True, "title": "Translation", "open_questions": [],
              "classification": {"gmp_relevance": "non_critical", "model_type": "generative", "autonomy": "recommends"},
              "judgments": [{"field": f, "value": v, "rationale": "Scripted for the test.", "citations": [a22]}
                            for f, v in (("gmp_relevance", "non_critical"), ("model_type", "generative"), ("autonomy", "recommends"))]}
    f = _form(ai="llm", use="not_sure", who="not decided yet")
    r = run_assessment(form_to_text(f), assessor=LLMAssessor(FakeChatClient([ChatResponse(content=json.dumps(answer))]), use_tools=False),
                       index=index, audit=audit, save=False, form=f)
    assert r.decision.verdict == "needs_more_information" and r.decision.rule_id == "G1-review-not-stated"
    assert r.open_questions and audit.find(r.meta.request_id)[0]["verdict"] == "needs_more_information"


def test_not_gmp_answer_closes_the_loop_found_by_the_regulation_review():
    """W37: a non-GMP idea forced into 'No, only indirectly' made G2 loop; the new 'not GMP' answer must not."""
    looping = _form(gmp="no", ai="llm", use="person_approves", who="I review it", areas=("regulatory",))
    assert _run(looping, "not_gmp", "generative", "recommends").rule_id == "G2-ticks-stricter"  # the old trap still explained
    fixed = _form(gmp="not_gmp", ai="llm", use="person_approves", who="I review it", areas=("regulatory",))
    assert _run(fixed, "not_gmp", "generative", "recommends") is None
    assert "No, not used for GMP work" in _run(looping, "not_gmp", "generative", "recommends").question_details[0]["how_to_resolve"]


def test_probabilistic_tick_is_informative():
    assert tick_values(_form(ai="probabilistic"))["model_type"] == "probabilistic"
