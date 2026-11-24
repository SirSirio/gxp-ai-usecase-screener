"""Keyword baseline on the structured intake form ("baseline B"): ticks first, keywords only on the
proposer's own free-text answers, never on the question wording."""
import pytest

from app.assessors.offline import classify_form, form_free_text
from app.intake_form import form_to_text, normalize_form


def _form(what="A tool supports the team with its daily work in the department.", gmp=None, ai=None, use=None,
          areas=(), explain="", who=""):
    return normalize_form({
        "title": "", "what": what, "areas": list(areas), "who_checks": who,
        "gmp_impact": {"choice": gmp, "explain": explain}, "ai_type": {"choice": ai, "explain": ""},
        "output_use": {"choice": use, "explain": ""}, "data": [], "source": {"choice": None, "explain": ""},
    })


@pytest.mark.parametrize("gmp,ai,use,expected", [
    ("yes", "trained_fixed", "auto_unchecked", ("critical", "static", "acts_autonomously")),
    ("no", "llm", "person_approves", ("non_critical", "generative", "recommends")),
    ("no", "self_learning", "auto_monitored", ("non_critical", "dynamic", "acts_with_oversight")),
    ("yes", "rules", "informs", ("critical", "non_ml", "informs")),
    ("yes", "vendor_unknown", "informs", ("critical", "unclear", "informs")),
])
def test_ticks_decide_when_answered(gmp, ai, use, expected):
    ok, _, cls, cues = classify_form(_form(gmp=gmp, ai=ai, use=use, areas=["qa"]))
    assert ok and (cls["gmp_relevance"], cls["model_type"], cls["autonomy"]) == expected
    assert cues["model_type"][0].startswith("ticked: ")


def test_question_wording_never_triggers_keywords():
    """form_to_text contains '...a QC result, a release...' in the question; baseline B must not read it."""
    f = _form(ai="llm", gmp="not_sure", use="not_sure")  # answered, so the questions appear in form_to_text
    assert "release" in form_to_text(f) and "release" not in form_free_text(f)
    ok, _, cls, _ = classify_form(f)
    assert ok and cls["gmp_relevance"] == "unclear" and cls["autonomy"] == "unclear"


def test_not_sure_falls_back_to_keywords_in_the_answers():
    f = _form(what="A camera model inspects vials and rejects defects on the filling line.", gmp="not_sure", ai="not_sure",
              use="not_sure", who="nobody checks the rejects")
    ok, _, cls, cues = classify_form(f)
    assert ok and cls == {"gmp_relevance": "critical", "model_type": "static", "autonomy": "acts_autonomously"}
    assert not any(c.startswith("ticked") for c in cues["gmp_relevance"])


def test_business_areas_only_means_not_gmp():
    ok, _, cls, _ = classify_form(_form(gmp="no", ai="llm", use="person_approves", areas=["business"]))
    assert ok and cls["gmp_relevance"] == "not_gmp"
    ok, _, cls, _ = classify_form(_form(gmp="no", ai="llm", use="person_approves", areas=["business", "qa"]))
    assert cls["gmp_relevance"] == "non_critical"


def test_scope_from_ticks_and_task_text():
    # a ticked AI type counts as an AI use even if the task text never says "AI" (e.g. a rules engine)
    assert classify_form(_form(ai="rules", gmp="yes", use="informs"))[0] is True
    assert classify_form(_form(ai=None))[0] is False  # no AI words, no tick: nothing to screen
    # a request to the tool stays out of scope even with every tick filled in (dev case D010)
    assert classify_form(_form(what="help me write my end of year self-assessment for my manager",
                               gmp="no", ai="llm", use="person_approves", areas=["business"]))[0] is False


def test_pipeline_gives_the_form_to_the_offline_classifier(index, audit):
    from app.assessors.offline import OfflineAssessor
    from app.pipeline import run_assessment

    f = _form(gmp="yes", ai="trained_fixed", use="auto_unchecked", areas=["manufacturing"])
    r = run_assessment(form_to_text(f), assessor=OfflineAssessor(), index=index, audit=audit, save=False, form=f)
    assert r.decision.verdict == "annex22_full" and r.meta.prompt_version == "offline-1.4"
    assert any("ticked" in j.rationale for j in r.judgments)


def test_form_1_2_answers_map_in_the_baseline():
    ok, _, cls, _ = classify_form(_form(gmp="not_gmp", ai="probabilistic", use="informs", areas=["regulatory"]))
    assert ok and cls["gmp_relevance"] == "not_gmp" and cls["model_type"] == "probabilistic"


def test_new_question_replaces_check_is_part_of_the_form():
    from app.intake_form import QUESTIONS_BY_ID
    from app.llm.prompts import format_form

    q = QUESTIONS_BY_ID["replaces_check"]
    assert [o["value"] for o in q["options"]] == ["yes", "no", "not_sure"]
    f = normalize_form({"what": "A camera model passes good syringes straight to packaging.",
                        "replaces_check": {"choice": "yes", "explain": "inspectors see only the rejects"}})
    assert "replaces_check (ticked): Yes, a step is dropped or reduced" in format_form(f)
