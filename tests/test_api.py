"""Web app and JSON API. Tests always use the offline classifier: they must never spend the Gemini
quota or depend on the internet, even when .env makes Gemini the default."""
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def client(index, tmp_path_factory, monkeypatch_module):
    from app import config

    tmp = tmp_path_factory.mktemp("run")
    config.use_settings(config.Settings(provider="offline", audit_dir=tmp / "audit", results_dir=tmp / "results"))
    monkeypatch_module.setenv("GEMINI_API_KEY", "test-key-not-used")  # so the selector offers Gemini
    from app.main import app

    yield TestClient(app)
    config.use_settings(None)


def test_tests_never_touch_real_audit_log_or_gemini(client):
    from app.config import ROOT, get_settings

    s = get_settings()
    assert s.provider == "offline"
    assert s.audit_dir != ROOT / "data" / "audit" and s.results_dir != ROOT / "data" / "results"


def test_health(client):
    r = client.get("/api/health").json()
    assert r["chunks"] > 100 and r["default_provider"] == "offline"
    assert {"offline", "gemini"} <= set(r["available_providers"])


def test_form_page_shows_classifier_selector(client):
    html = client.get("/submit").text
    assert "Screen use case" in html and 'name="provider"' in html
    assert 'value="offline" selected' in html and 'value="gemini"' in html


def test_landing_page_links_to_the_form_and_the_sources(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'href="/submit"' in html and "Submit your idea" in html and 'href="/sources"' in html
    assert 'action="/assess"' not in html  # the form itself lives on /submit
    assert "QA decides" in html and "confidential" in html  # what the tool does not do


def test_every_page_links_to_the_sources(client):
    for path in ("/", "/submit", "/sources", "/quick"):
        assert 'href="/sources"' in client.get(path).text, path


def test_sources_page_lists_every_document_with_its_official_url(client):
    from markupsafe import escape

    from app.ingest.sources import SOURCES
    from app.main import SOURCE_GROUPS

    grouped = [d for _, ids in SOURCE_GROUPS for d in ids]
    assert sorted(grouped) == sorted(s.doc_id for s in SOURCES) and len(grouped) == len(set(grouped))
    r = client.get("/sources")
    assert r.status_code == 200
    for s in SOURCES:
        assert str(escape(s.title)) in r.text
        assert f'href="{escape(s.url)}"' in r.text
        assert s.status.capitalize() in r.text


def test_assess_api_and_intake(client):
    r = client.post("/api/assess", json={"description": "A trained camera model inspects vials and rejects defects automatically on the line."})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["verdict"] == "annex22_full" and body["meta"]["provider"] == "offline"
    rid = body["meta"]["request_id"]
    intake = client.get(f"/api/results/{rid}/intake.json")
    assert intake.status_code == 200 and intake.json()["status"] == "draft_for_qa_review"
    assert "attachment" in intake.headers["content-disposition"]
    assert client.get("/api/audit/verify").json()["ok"]


def test_quick_mode_flow_with_explicit_provider(client):
    r = client.post("/quick", data={"description": "We want ChatGPT to draft SOPs and QA approves each one before release in the eDMS.",
                                    "provider": "offline"})
    assert r.status_code == 200 and "Classification" in r.text and "Download JSON" in r.text
    assert "Classified by: Keyword baseline" in r.text
    assert 'name="provider" value="gemini"' in r.text  # "screen again with" the other classifier
    assert 'action="/quick"' in r.text and 'name="description" value="We want ChatGPT' in r.text  # resubmits the same text


def test_quick_page_exists_but_is_not_linked(client):
    r = client.get("/quick")
    assert r.status_code == 200 and "Quick mode: accuracy may be lower than in the full form." in r.text
    assert 'name="description"' in r.text
    for path in ("/", "/submit", "/sources"):
        assert "/quick" not in client.get(path).text, path
    assert client.post("/quick", data={"description": "too short", "provider": "offline"}).status_code == 422


# ---------------------------------------------------------------- structured intake form
def _example_form() -> dict:
    from app.main import FORM_EXAMPLES

    return FORM_EXAMPLES[0]["form"]


def _as_fields(form: dict, provider: str = "offline") -> dict:
    """The form dict as HTML form fields, the way the browser posts it."""
    from app.intake_form import QUESTIONS

    data = {"provider": provider}
    for q in QUESTIONS:
        v = form[q["id"]]
        if q["type"] == "single":
            data[q["id"]] = v["choice"] or ""
            data[f"{q['id']}_explain"] = v["explain"]
        else:
            data[q["id"]] = v
    return data


def _request_id(html: str) -> str:
    import re

    return re.search(r"/api/results/([0-9a-f]{12})/intake\.json", html).group(1)


def test_form_page_renders_every_question_and_option_from_the_form_definition(client):
    from markupsafe import escape

    from app.intake_form import QUESTIONS

    html = client.get("/submit").text
    assert 'action="/assess"' in html
    for q in QUESTIONS:
        assert str(escape(q["label"])) in html and str(escape(q["help"])) in html
        assert f'name="{q["id"]}"' in html
        for o in q.get("options", []):
            assert f'name="{q["id"]}" value="{o["value"]}"' in html
            assert str(escape(o["label"])) in html and str(escape(o["help"])) in html
            assert f'aria-describedby="tip-{q["id"]}-{o["value"]}"' in html  # (i) help reachable by keyboard
        if q.get("explain"):
            assert f'name="{q["id"]}_explain"' in html
    assert f"0 of {len(QUESTIONS)} questions answered" in html


def test_sections_and_examples_match_the_form_definition():
    from app.intake_form import QUESTIONS, normalize_form
    from app.main import FORM_EXAMPLES, FORM_SECTIONS

    ids = [qid for _, qids in FORM_SECTIONS for qid in qids]
    assert sorted(ids) == sorted(q["id"] for q in QUESTIONS) and len(ids) == len(set(ids))
    assert len(FORM_EXAMPLES) == 3
    for ex in FORM_EXAMPLES:
        assert normalize_form(ex["form"]) == ex["form"]  # only known option values, canonical shape


def test_form_submission_returns_result_with_the_answers(client):
    from app.config import get_settings
    from app.intake_form import option_label

    form = _example_form()
    r = client.post("/assess", data=_as_fields(form))
    assert r.status_code == 200 and "Classification" in r.text and "Download JSON" in r.text
    assert "What you submitted" in r.text and form["title"] in r.text
    assert option_label("output_use", "person_approves") in r.text
    # "screen again" resubmits the same form, not a text box
    assert 'action="/assess"' in r.text and 'name="output_use" value="person_approves"' in r.text
    assert 'name="areas" value="manufacturing"' in r.text and 'name="areas" value="qa"' in r.text

    rid = _request_id(r.text)
    saved = client.get(f"/api/results/{rid}").json()
    assert saved["form"] == form and saved["title"] == form["title"]  # the proposer's title, not a generated one
    assert "What should the AI do?" in saved["description"]  # the classifier got form_to_text(form)
    assert client.get(f"/api/results/{rid}/intake.json").json()["proposer_answers"] == form
    import json

    last = json.loads((get_settings().audit_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last["request_id"] == rid and last["form"] == form
    assert client.get("/api/audit/verify").json()["ok"]


def test_form_rejects_unknown_option_values(client):
    form = _example_form()
    bad_multi = _as_fields(form) | {"areas": ["manufacturing", "moon_base"]}
    r = client.post("/assess", data=bad_multi)
    assert r.status_code == 422 and "moon_base" in r.text
    bad_single = _as_fields(form) | {"ai_type": "crystal_ball"}
    assert client.post("/assess", data=bad_single).status_code == 422


def test_form_requires_what(client):
    r = client.post("/assess", data=_as_fields(_example_form() | {"what": "too short"}))
    assert r.status_code == 422
    assert 'aria-invalid="true"' in r.text and "at least 20 characters" in r.text
    assert "LLM drafts of cleaning SOPs" in r.text  # other answers are kept


def test_api_accepts_form(client):
    form = _example_form()
    r = client.post("/api/assess", json={"form": form, "provider": "offline"})
    assert r.status_code == 200
    body = r.json()
    assert body["form"] == form and body["intake_form"]["proposer_answers"] == form
    assert body["meta"]["provider"] == "offline"
    partial = client.post("/api/assess", json={"form": {"what": "A chatbot drafts cleaning SOPs; QA approves each one."}})
    assert partial.status_code == 200 and partial.json()["form"]["areas"] == []
    assert partial.json()["form"]["source"] == {"choice": None, "explain": ""}


def test_api_form_validation(client):
    form = _example_form()
    assert client.post("/api/assess", json={"form": form | {"areas": ["moon_base"]}}).status_code == 422
    assert client.post("/api/assess", json={"form": form | {"source": {"choice": "teleport", "explain": ""}}}).status_code == 422
    assert client.post("/api/assess", json={"form": form | {"favourite_colour": "blue"}}).status_code == 422
    assert client.post("/api/assess", json={"form": form | {"what": "short"}}).status_code == 422
    assert client.post("/api/assess", json={"form": form, "description": "A chatbot drafts cleaning SOPs for QA."}).status_code == 422
    assert client.post("/api/assess", json={"provider": "offline"}).status_code == 422


def test_quick_mode_result_has_no_form(client):
    r = client.post("/api/assess", json={"description": "A trained camera model inspects vials and rejects defects automatically on the line."})
    body = r.json()
    assert body["form"] is None and body["intake_form"]["proposer_answers"] is None


def test_unknown_provider_rejected(client):
    assert client.post("/api/assess", json={"description": "We want ChatGPT to draft SOPs for the QC lab.", "provider": "gpt-99"}).status_code == 422


def test_validation(client):
    assert client.post("/api/assess", json={"description": "too short"}).status_code == 422
    assert client.get("/api/results/../../etc").status_code in (400, 404)
    assert client.get("/api/section", params={"doc": "A22", "section": "3.3"}).json()["title"] == "Human-in-the-loop"


def test_section_page_is_readable_html(client):
    r = client.get("/section", params={"doc": "A22", "section": "3.3"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html = r.text
    assert "Human-in-the-loop" in html and "EU GMP Annex 22: Artificial Intelligence" in html
    assert "consultation drafts (July 2025)" in html  # the same draft wording as the result page
    assert 'href="/sources#doc-A22"' in html  # the way back
    from app.ingest.sources import SOURCES_BY_ID
    assert SOURCES_BY_ID["A22"].url.replace("&", "&amp;") in html  # the official document
    assert "<mark" not in html  # nothing quoted, nothing highlighted


def test_section_page_shows_subsections_and_no_draft_notice_for_final_texts(client):
    html = client.get("/section", params={"doc": "A11", "section": "4"}).text
    assert "§4.1" in html and "consultation drafts" not in html


def test_section_page_highlights_the_quoted_passage(client, index):
    chunk = index.section_chunks("A22", "1")[0]
    from app.citations import best_quote
    quote = best_quote(chunk, "generative AI large language models non-critical human in the loop")
    html = client.get("/section", params={"doc": "A22", "section": "1", "q": quote}).text
    assert '<mark id="quoted">' in html and html.count('id="quoted"') == 1
    missing = client.get("/section", params={"doc": "A22", "section": "1", "q": "A sentence that is not in the text."}).text
    assert "<mark" not in missing and "could not be found" in missing



def test_section_page_does_not_repeat_a_run_in_title(client):
    """F11c: the PDF text opens subsections with the title as a run-in heading; the page shows the heading once."""
    html = client.get("/section", params={"doc": "A11D", "section": "10"}).text
    assert "Input verification</h2>" in html and "Input verification. " not in html
    assert "<p>Where critical data is" in html  # the text itself starts right after the heading
    # a title that merely opens a sentence is text, not a heading: it stays
    q9 = client.get("/section", params={"doc": "Q9", "section": "4.3"}).text
    assert "Risk assessment consists of" in q9

def test_section_page_unknown_section_is_404_and_escapes_input(client):
    assert client.get("/section", params={"doc": "A22", "section": "99.9"}).status_code == 404
    r = client.get("/section", params={"doc": "<script>alert(1)</script>", "section": "1"})
    assert r.status_code == 404 and "<script>alert(1)" not in r.text and "Section not found" in r.text


def test_result_page_links_citations_to_the_section_page(client):
    r = client.post("/quick", data={"description": "We want ChatGPT to draft SOPs and QA approves each one before release in the eDMS.",
                                    "provider": "offline"})
    assert 'href="/section?doc=' in r.text and "/api/section" not in r.text
    assert "&amp;q=" in r.text  # the quote travels along, so the section page can highlight it


def test_stylesheet_link_is_cache_busted(client):
    assert re.search(r'href="/static/style\.css\?v=[0-9a-f]+"', client.get("/").text)



def test_run_details_show_rules_and_source_map_versions(client):
    """F04b: every version that shaped the result is listed under Run details."""
    from app.rules import RULES_VERSION
    from app.source_map import SOURCE_MAP_VERSION

    r = client.post("/quick", data={"description": "We want ChatGPT to draft SOPs and QA approves each one before release in the eDMS.",
                                    "provider": "offline"})
    meta = r.text[r.text.index('<details class="meta">'):]
    assert f"<dt>Rules</dt><dd>{RULES_VERSION}</dd>" in meta and f"<dt>Source map</dt><dd>{SOURCE_MAP_VERSION}</dd>" in meta


def test_run_details_omit_an_empty_source_map_version(client):
    from app.main import templates
    from app.schema import AssessmentResult

    r = client.post("/quick", data={"description": "We want ChatGPT to draft SOPs and QA approves each one before release in the eDMS.",
                                    "provider": "offline"})
    rid = re.search(r"/api/results/([0-9a-f]{12})", r.text).group(1)
    saved = AssessmentResult.model_validate(client.get(f"/api/results/{rid}").json())
    old = saved.model_copy(update={"meta": saved.meta.model_copy(update={"source_map_version": ""})})
    html = templates.get_template("result.html").render(r=old, provider="offline", provider_label="Keyword baseline", other_providers={})
    assert "<dt>Rules</dt>" in html and "<dt>Source map</dt>" not in html


def test_grid_has_a_phone_layout_that_marks_the_same_cell(client):
    """F11b: a transposed copy of the grid for phones (CSS shows one), both marking the same position."""
    r = client.post("/quick", data={"description": "We want ChatGPT to draft SOPs and QA approves each one before release in the eDMS.",
                                    "provider": "offline"})
    html = r.text
    if 'class="grid-block"' not in html:
        pytest.skip("no grid for this result")
    wide = html[html.index('class="table-scroll grid-wide"'):html.index('class="grid-tall"')]
    tall = html[html.index('class="grid-tall"'):html.index("</table>", html.index('class="grid-tall"'))]
    assert wide.count('class="here"') == tall.count('class="here"') <= 1
    assert tall.count("<th scope=\"row\">") == 4 and tall.count("<th scope=\"col\">") == 2


def test_landing_question_count_matches_the_form():
    """F02b: the landing page names the number of questions the form has."""
    from pathlib import Path

    from app.intake_form import QUESTIONS

    words = {9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
    text = (Path(__file__).resolve().parents[1] / "app" / "templates" / "landing.html").read_text(encoding="utf-8").lower()
    n = words[len(QUESTIONS)]
    assert text.count(f"{n} questions") + text.count(f"{n} short questions") == 3
    assert not [w for k, w in words.items() if k != len(QUESTIONS) and f"{w} questions" in text]


def test_landing_rotates_three_example_cards_that_follow_the_rules(client):
    """W52: three example results in the hero, each label verbatim from VERDICT_LABELS and each outcome the one
    the rules give for the classification shown on the card. Only the first card is visible without JavaScript."""
    from app.citations import LABELS
    from app.rules import VERDICT_LABELS, decide
    from app.schema import Classification

    html = client.get("/").text
    cards = re.findall(r'<div class="sample outcome tone-(\w+)[^"]*" data-card(.*?)</dl>', html, re.S)
    assert len(cards) == 3
    by_label = {v: k for k, v in VERDICT_LABELS.items()}
    by_text = {v: k for k, v in LABELS.items()}
    autonomy = {"Acts, people monitor": "acts_with_oversight", "QA approves each output": "recommends"}
    verdicts = []
    for tone, body in cards:
        label = re.search(r'class="outcome-label">.*?<span>(.*?)</span>', body, re.S).group(1)
        verdict = by_label[label.replace("&amp;", "&")]  # KeyError = a label not taken verbatim from the rules
        cls = dict(re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", body))
        c = Classification(gmp_relevance=by_text[cls["GMP relevance"]], model_type=by_text[cls["Model type"]],
                           autonomy=autonomy[cls["Autonomy"]])
        assert decide(True, c).verdict == verdict, (label, cls)
        assert tone == ("stop" if verdict == "not_permitted_critical" else "go")
        verdicts.append(verdict)
    assert verdicts == ["annex22_full", "permitted_with_hitl", "not_permitted_critical"]
    assert html.count('data-card\n            role="group"') == 3 and html.count(" is-active\" data-card") == 1
    # controls: one labelled button per card, plus pause; hidden until the script runs
    assert len(re.findall(r'<button type="button" class="deck-dot" data-deck-go="\d" aria-label="Example \d: ', html)) == 3
    assert "data-deck-toggle" in html and "data-deck-controls hidden" in html


def test_landing_testing_section_is_general(client):
    """W52 owner feedback: no 'SME', no test scores or case counts on user-facing pages; a link to the details."""
    html = client.get("/").text
    tested = html[html.index('class="tested"'):html.index('class="closing"')]
    assert "reviewed manually" in tested or "manually reviewed" in tested
    assert "more permissive than the correct one" in tested and "keyword checklist" in tested
    assert "docs/VALIDATION_NOTE.md" in tested
    assert not re.search(r"\d", re.sub(r"<[^>]+>", " ", tested).replace("VALIDATION_NOTE", ""))
    for path in ("/", "/submit", "/quick", "/sources"):
        page = client.get(path).text
        assert "SME" not in page and "dangerous error" not in page, path
        assert not re.search(r"\d+ ?% right", page), path


def test_every_busy_form_has_a_progress_region(client):
    """W52: each form that screens (intake, quick mode, follow-up, screen again) carries the progress display:
    a hidden panel with a real progressbar and the steps, and a polite status region for screen readers."""
    pages = {"/submit": client.get("/submit").text, "/quick": client.get("/quick").text}
    pages["result"] = client.post("/assess", data={"what": "We want to use an AI tool to help people with documents in the production area.",
                                                   "provider": "offline"}).text
    for name, html in pages.items():
        forms = re.findall(r"<form [^>]*data-busy.*?</form>", html, re.S)
        assert forms, name
        for f in forms:
            assert f.count("data-progress hidden") == 1, name
            assert re.search(r'role="progressbar" aria-label="Screening progress" aria-valuemin="0" aria-valuemax="100"', f), name
            assert 'role="status" aria-live="polite" data-status' in f, name
            assert f.count("data-step>") == 4, name
    assert "followup-form" in pages["result"] and "form method=\"post\" action=\"/assess\" class=\"again\"" in pages["result"]
