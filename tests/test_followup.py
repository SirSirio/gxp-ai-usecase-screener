"""Follow-up loop (WORKLOG W33): on "Not yet" the proposer corrects the form and answers the tool's
questions, then resubmits; at most intake_form.MAX_ROUNDS rounds. Offline classifier only."""
import pytest
from fastapi.testclient import TestClient

from app.intake_form import FOLLOW_UP, MAX_ROUNDS, FormError, form_to_text, normalize_form

BASE = {"what": "An LLM translates the client SOPs and batch record templates for our site.",
        "ai_type": {"choice": "llm", "explain": ""}, "output_use": {"choice": "not_sure", "explain": ""},
        "who_checks": "not decided yet", "areas": ["msat"]}


# ---------------------------------------------------------------- the form carries the answers
def test_follow_up_answers_are_kept_and_empty_ones_dropped():
    f = normalize_form(BASE | {FOLLOW_UP: [{"question": "Does the vendor document the model?", "answer": "Yes, a model card."},
                                           {"question": "Unanswered?", "answer": "  "}]})
    assert f[FOLLOW_UP] == [{"question": "Does the vendor document the model?", "answer": "Yes, a model card."}]
    assert FOLLOW_UP not in normalize_form(BASE)  # a first submission keeps its exact shape


@pytest.mark.parametrize("bad", ["text", [{"q": "x"}], [{"question": "q", "answer": "a"}] * 11])
def test_follow_up_shape_is_validated(bad):
    with pytest.raises(FormError):
        normalize_form(BASE | {FOLLOW_UP: bad})


def test_answers_reach_the_llm_text_and_the_baseline_but_not_the_question_text():
    from app.assessors.offline import form_free_text
    from app.llm.prompts import format_form

    f = normalize_form(BASE | {FOLLOW_UP: [{"question": "Is a release decision involved?", "answer": "No, drafts only."}]})
    assert "Q: Is a release decision involved?\nA: No, drafts only." in form_to_text(f)
    assert 'A: "No, drafts only."' in format_form(f)
    assert "No, drafts only." in form_free_text(f) and "release decision" not in form_free_text(f)


# ---------------------------------------------------------------- which inputs come with which question
def test_follow_up_items_map_questions_to_form_inputs():
    from app.guards import check
    from app.pipeline import follow_up_items
    from app.rules import decide
    from app.schema import Classification

    c = Classification(gmp_relevance="non_critical", model_type="generative", autonomy="recommends")
    g1 = check(normalize_form(BASE), True, c, decide(True, c))  # G1: review not stated
    items = follow_up_items(g1, ["Who reviews the translations?", "Who reviews the translations?", "a", "b", "c"])
    assert items[0].kind == "fields" and items[0].fields == ["output_use", "who_checks"]
    assert [i.kind for i in items[1:]] == ["text"] * 3  # model questions deduplicated, at most 3

    unclear = decide(True, Classification(gmp_relevance="critical", model_type="unclear", autonomy="informs"))
    assert follow_up_items(unclear, [])[0].fields == ["ai_type"]

    g2_form = normalize_form(BASE | {"gmp_impact": {"choice": "yes", "explain": ""}, "ai_type": {"choice": "trained_fixed", "explain": ""},
                                     "output_use": {"choice": "auto_monitored", "explain": ""}, "who_checks": "QA sees exceptions"})
    c2 = Classification(gmp_relevance="critical", model_type="non_ml", autonomy="acts_with_oversight")
    g2 = check(g2_form, True, c2, decide(True, c2))
    assert g2.rule_id == "G2-ticks-stricter" and follow_up_items(g2, [])[0].fields == ["ai_type"]


# ---------------------------------------------------------------- the loop through the web app
@pytest.fixture(scope="module")
def client(index, tmp_path_factory):
    from app import config

    tmp = tmp_path_factory.mktemp("fu")
    config.use_settings(config.Settings(provider="offline", audit_dir=tmp / "audit", results_dir=tmp / "results"))
    from app.main import app

    yield TestClient(app)
    config.use_settings(None)


def _fields(form: dict, **extra) -> dict:
    from app.intake_form import QUESTIONS

    f = normalize_form(form)
    data = {"provider": "offline", **extra}
    for q in QUESTIONS:
        v = f[q["id"]]
        if q["type"] == "single":
            data[q["id"]], data[f"{q['id']}_explain"] = v["choice"] or "", v["explain"]
        else:
            data[q["id"]] = v
    return data


def test_not_yet_then_answered_in_round_two(client):
    from app.config import get_settings
    import json
    import re

    r1 = client.post("/assess", data=_fields(BASE))
    assert r1.status_code == 200
    rid = re.search(r"/api/results/([0-9a-f]{12})", r1.text).group(1)
    first = client.get(f"/api/results/{rid}").json()
    assert first["decision"]["verdict"] == "needs_more_information" and first["follow_up_allowed"]
    assert any(i["fields"] == ["output_use", "who_checks"] for i in first["follow_up"])

    answered = BASE | {"output_use": {"choice": "person_approves", "explain": ""}, "who_checks": "QA approves every translation before use."}
    r2 = client.post("/assess", data=_fields(answered, round="2", parent_request_id=rid,
                                             fu_q_0="Who reviews the translations?", fu_a_0="A bilingual QA specialist."))
    rid2 = re.search(r"/api/results/([0-9a-f]{12})", r2.text).group(1)
    second = client.get(f"/api/results/{rid2}").json()
    assert second["decision"]["verdict"] == "permitted_with_hitl" and not second["follow_up"]
    assert second["meta"]["round"] == 2 and second["meta"]["parent_request_id"] == rid
    assert second["form"][FOLLOW_UP] == [{"question": "Who reviews the translations?", "answer": "A bilingual QA specialist."}]
    last = json.loads((get_settings().audit_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last["round"] == 2 and last["parent_request_id"] == rid


def test_no_further_round_after_the_last_one(client):
    import re

    r = client.post("/assess", data=_fields(BASE, round=str(MAX_ROUNDS), parent_request_id="0" * 12))
    rid = re.search(r"/api/results/([0-9a-f]{12})", r.text).group(1)
    res = client.get(f"/api/results/{rid}").json()
    assert res["decision"]["verdict"] == "needs_more_information" and res["follow_up"] and not res["follow_up_allowed"]
    too_many = client.post("/assess", data=_fields(BASE, round=str(MAX_ROUNDS + 1)))
    assert too_many.status_code == 422 and "clearer scope" in too_many.text


# ---------------------------------------------------------------- the follow-up section on the result page
def _followup_form(html: str) -> str:
    start = html.index('class="followup-form"')
    return html[start:html.index("</form>", start)]


def _rid(html: str) -> str:
    import re

    return re.search(r"/api/results/([0-9a-f]{12})", html).group(1)


def test_not_yet_result_renders_the_inputs_of_each_follow_up_item(client):
    import re

    r = client.post("/assess", data=_fields(BASE))
    assert "Answer to continue" in r.text and f"Round 1 of {MAX_ROUNDS}" in r.text
    fu = _followup_form(r.text)
    # the item's form questions as real inputs, prefilled with the proposer's current answers
    assert 'name="output_use" value="not_sure" aria-describedby="tip-output_use-not_sure" checked' in fu
    assert 'name="output_use" value="person_approves" aria-describedby="tip-output_use-person_approves">' in fu
    assert 'id="tip-output_use-person_approves"' in fu  # (i) help reachable by keyboard
    assert 'name="output_use_explain"' in fu
    assert re.search(r'<textarea id="f-who_checks" name="who_checks"[^>]*>not decided yet</textarea>', fu)
    # ... and not also as hidden duplicates; everything else is re-posted unchanged
    assert 'type="hidden" name="output_use"' not in fu and 'type="hidden" name="output_use_explain"' not in fu
    assert 'type="hidden" name="who_checks"' not in fu
    assert '<input type="hidden" name="what" value="An LLM translates the client SOPs' in fu
    assert '<input type="hidden" name="areas" value="msat">' in fu
    assert '<input type="hidden" name="round" value="2">' in fu
    assert f'<input type="hidden" name="parent_request_id" value="{_rid(r.text)}">' in fu
    assert '<input type="hidden" name="provider" value="offline">' in fu
    assert "Send answers and screen again" in fu


def test_text_items_and_earlier_answers_are_posted_as_pairs(client):
    from app.main import templates
    from app.schema import AssessmentResult, FollowUpItem

    parent = "b" * 12
    r = client.post("/assess", data=_fields(BASE, round="2", parent_request_id=parent,
                                            fu_q_0="Who reviews the translations?", fu_a_0="A bilingual QA specialist."))
    saved = AssessmentResult.model_validate(client.get(f"/api/results/{_rid(r.text)}").json())
    result = saved.model_copy(update={"follow_up_allowed": True, "follow_up": [
        FollowUpItem(kind="fields", question="Who approves each translation?", fields=["output_use", "who_checks"]),
        FollowUpItem(kind="text", question="Does the vendor document the model?")]})
    html = templates.get_template("result.html").render(r=result, provider="offline", provider_label="Keyword baseline",
                                                        other_providers={})
    fu = _followup_form(html)
    assert '<input type="hidden" name="fu_q_0" value="Does the vendor document the model?">' in fu
    assert 'name="fu_a_0"' in fu and '<textarea id="fu_a_0"' in fu
    # the earlier round's answer is re-posted after the new question, so the answers accumulate
    assert '<input type="hidden" name="fu_q_1" value="Who reviews the translations?">' in fu
    assert '<input type="hidden" name="fu_a_1" value="A bilingual QA specialist.">' in fu
    assert '<input type="hidden" name="round" value="3">' in fu
    assert f"Round 2 of {MAX_ROUNDS}" in html and f"Follow-up to request {parent}" in html
    assert "A bilingual QA specialist." in html.split("What you submitted")[1]  # shown with the answers too


def test_no_follow_up_inputs_after_the_last_round(client):
    r = client.post("/assess", data=_fields(BASE, round=str(MAX_ROUNDS), parent_request_id="0" * 12))
    assert 'class="followup-form"' not in r.text and 'name="fu_a_' not in r.text
    assert f'name="round" value="{MAX_ROUNDS + 1}"' not in r.text
    assert "clearer scope" in r.text and 'href="/submit"' in r.text
    assert f"Round {MAX_ROUNDS} of {MAX_ROUNDS}" in r.text and "Follow-up to request 000000000000" in r.text



def _render_saved(client, data: dict) -> tuple[str, object]:
    """Post the form, then render the saved result with another classifier offered (so the "Screen again" form can show)."""
    from app.main import templates
    from app.schema import AssessmentResult

    r = client.post("/assess", data=data)
    saved = AssessmentResult.model_validate(client.get(f"/api/results/{_rid(r.text)}").json())
    html = templates.get_template("result.html").render(r=saved, provider="offline", provider_label="Keyword baseline",
                                                        other_providers={"gemini": "Gemini test-model (LLM)"})
    return html, saved


def test_last_round_label_points_to_a_new_proposal_not_to_this_page(client):
    """F06b (owner decision a): no round left -> the final-round label, one primary way to a new proposal,
    the open questions still listed, and no offer to screen the same proposal again."""
    from markupsafe import escape

    from app.rules import FINAL_ROUND_LABEL, VERDICT_LABELS

    html, saved = _render_saved(client, _fields(BASE, round=str(MAX_ROUNDS), parent_request_id="0" * 12))
    assert saved.decision.verdict == "needs_more_information" and not saved.follow_up_allowed
    assert str(escape(FINAL_ROUND_LABEL)) in html and str(escape(VERDICT_LABELS["needs_more_information"])) not in html
    assert 'class="again"' not in html and "Screen again with" not in html
    assert '<a class="btn btn-primary" href="/submit">' in html
    assert html.count("btn btn-primary") == 1  # the new proposal is the only primary action
    assert '<a class="btn btn-secondary" href="/api/results/' in html  # Download JSON steps back
    assert all(str(escape(item.question)) in html for item in saved.follow_up)  # what was unclear stays visible


def test_earlier_rounds_keep_the_pending_label_and_the_compare_form(client):
    from markupsafe import escape

    from app.rules import FINAL_ROUND_LABEL, VERDICT_LABELS

    html, saved = _render_saved(client, _fields(BASE))
    assert saved.follow_up_allowed and saved.meta.round == 1
    assert str(escape(VERDICT_LABELS["needs_more_information"])) in html and str(escape(FINAL_ROUND_LABEL)) not in html
    assert 'class="followup-form"' in html and "Screen again with: Gemini test-model" in html
    assert '<a class="btn btn-primary" href="/api/results/' in html

def test_api_accepts_round_and_follow_up(client):
    body = {"form": BASE | {FOLLOW_UP: [{"question": "q?", "answer": "an answer"}]}, "provider": "offline",
            "round": 2, "parent_request_id": "a" * 12}
    r = client.post("/api/assess", json=body)
    assert r.status_code == 200 and r.json()["meta"]["round"] == 2
    assert client.post("/api/assess", json=body | {"round": MAX_ROUNDS + 1}).status_code == 422
    assert client.post("/api/assess", json=body | {"parent_request_id": "../etc"}).status_code == 422


def test_contradiction_and_blocking_reach_the_follow_up_items():
    from app.guards import check
    from app.pipeline import follow_up_items
    from app.rules import decide
    from app.schema import Classification

    f = normalize_form(BASE | {"gmp_impact": {"choice": "yes", "explain": ""}, "output_use": {"choice": "informs", "explain": ""},
                               "who_checks": "scientists review the ideas"})
    c = Classification(gmp_relevance="non_critical", model_type="generative", autonomy="informs")
    items = follow_up_items(check(f, True, c, decide(True, c)), ["How are prompts archived?"])
    assert items[0].blocking and items[0].fields == ["gmp_impact"] and items[0].contradiction["your_answer"] == "Yes, directly"
    assert items[1].kind == "text" and not items[1].blocking and items[1].contradiction is None


# ---------------------------------------------------------------- blocking vs QA points, and the G2 explanation (W35)
G2_FORM = BASE | {"what": "An AI tool reads the fermentation batch data and suggests process improvements; the team investigates "
                          "and changes go through change control.",
                  "gmp_impact": {"choice": "yes", "explain": ""}, "output_use": {"choice": "informs", "explain": ""},
                  "who_checks": "scientists review the suggestions"}


def _render(client, form: dict, follow_up: list, decision: dict | None = None) -> str:
    """A saved offline result with a hand-built follow-up (the keyword baseline reads ticks first, so it never meets G2)."""
    from app.main import templates
    from app.schema import AssessmentResult

    r = client.post("/assess", data=_fields(form))
    saved = AssessmentResult.model_validate(client.get(f"/api/results/{_rid(r.text)}").json())
    update = {"follow_up_allowed": True, "follow_up": follow_up}
    if decision:
        update["decision"] = saved.decision.model_copy(update=decision)
    return templates.get_template("result.html").render(r=saved.model_copy(update=update), provider="offline",
                                                        provider_label="Keyword baseline", other_providers={})


def test_g2_result_explains_the_contradiction_and_puts_blocking_first(client):
    from markupsafe import escape

    from app.guards import check
    from app.pipeline import follow_up_items
    from app.rules import VERDICT_LABELS, decide
    from app.schema import Classification

    f = normalize_form(G2_FORM)
    c = Classification(gmp_relevance="non_critical", model_type="generative", autonomy="informs")
    g2 = check(f, True, c, decide(True, c))
    items = follow_up_items(g2, ["How are the suggestions archived?"])
    con = items[0].contradiction
    html = _render(client, G2_FORM, items, {"verdict": g2.verdict, "label": VERDICT_LABELS[g2.verdict],
                                            "rule_id": g2.rule_id, "explanation": g2.explanation})
    fu = _followup_form(html)
    assert con["your_answer"] == "Yes, directly" and f"“{con['your_answer']}”" in fu
    assert con["your_answer_means"] in fu and con["description_reads_as"] in fu
    assert escape(con["outcome_if_your_answer_is_right"]) in fu and escape(con["outcome_if_the_description_is_right"]) in fu
    assert 'class="outcome-pill tone-stop"' in fu and 'class="outcome-pill tone-go"' in fu  # tone from the label
    # "How to resolve" sits between the comparison and the prefilled input of the question involved
    resolve_at = fu.index("How to resolve")
    assert fu.index("Your description reads as") < resolve_at < fu.index(escape(con["how_to_resolve"])) \
        < fu.index(f'name="{con["question_id"]}" value="yes"')
    assert 'name="gmp_impact" value="yes" aria-describedby="tip-gmp_impact-yes" checked' in fu
    # blocking group first, then the QA points, each with its own heading; the text box keeps its fu_q_0 name
    assert fu.index("Answer these to get a result") < fu.index("Points QA will want answered") \
        < fu.index('name="fu_q_0" value="How are the suggestions archived?"')
    assert "does not change the screening result" in fu and "Send answers and screen again" in fu
    assert "Each contradiction is explained below." in html


def test_only_qa_points_say_so_and_still_allow_resubmitting(client):
    from app.schema import FollowUpItem

    html = _render(client, BASE, [FollowUpItem(kind="text", question="Does the vendor document the model?", blocking=False)])
    fu = _followup_form(html)
    assert "Answer these to get a result" not in fu and "No question here decides the outcome" in fu
    assert "Points QA will want answered" in fu and "helps QA but does not change the screening result" in fu
    assert '<input type="hidden" name="fu_q_0" value="Does the vendor document the model?">' in fu
    assert '<input type="hidden" name="round" value="2">' in fu and "Send answers and screen again" in fu


# ---------------------------------------------------------------- a failed follow-up round loses nothing (W44)
def test_safe_form_keeps_well_formed_follow_up_answers():
    from app.main import _safe_form

    out = _safe_form({FOLLOW_UP: [{"question": "Who checks?", "answer": "QA, every report"}, {"question": 3}, "junk",
                                  {"question": "  ", "answer": "x"}]})
    assert out[FOLLOW_UP] == [{"question": "Who checks?", "answer": "QA, every report"}]


def test_validation_error_in_a_follow_up_round_keeps_answers_and_round(client):
    parent = "a1b2c3d4e5f6"
    data = _fields(BASE, round="2", parent_request_id=parent,
                   fu_q_0="Who reviews the translations?", fu_a_0="A bilingual QA specialist, every translation.")
    data["what"] = "too short"  # fails MIN_LENGTH
    r = client.post("/assess", data=data)
    assert r.status_code == 422
    form = r.text[r.text.index('id="intake"'):]
    assert 'name="round" value="2"' in form and f'name="parent_request_id" value="{parent}"' in form
    assert 'name="fu_q_0" value="Who reviews the translations?"' in form
    assert "A bilingual QA specialist, every translation." in form  # shown again in an editable fu_a_0 field
    assert 'name="fu_a_0"' in form


def test_resubmitting_the_error_page_stays_in_the_same_round(client):
    import re

    parent = "0f0f0f0f0f0f"
    data = _fields(BASE, round="2", parent_request_id=parent, fu_q_0="Who reviews?", fu_a_0="QA reviews each one.")
    r = client.post("/assess", data=data)
    saved = client.get(f"/api/results/{re.search(r'/api/results/([0-9a-f]{12})', r.text).group(1)}").json()
    assert saved["meta"]["round"] == 2 and saved["meta"]["parent_request_id"] == parent
    assert saved["form"][FOLLOW_UP] == [{"question": "Who reviews?", "answer": "QA reviews each one."}]


def test_first_round_error_page_has_no_follow_up_fields(client):
    data = _fields(BASE)
    data["what"] = "too short"
    form = client.post("/assess", data=data).text
    form = form[form.index('id="intake"'):]
    assert 'name="fu_q_0"' not in form and 'name="parent_request_id"' not in form
