"""End-to-end pipeline with the offline assessor and with a scripted fake LLM (tool loop)."""
import json

import pytest

from app.assessors.llm import LLMAssessor
from app.assessors.offline import OfflineAssessor, classify
from app.llm.base import ChatResponse, ToolCall
from app.llm.fake import FakeChatClient
from app.pipeline import AssessmentFailed, run_assessment


@pytest.mark.parametrize("text,expected", [
    ("We want ChatGPT to write first drafts of cleaning SOPs; QA reviews and approves each one.", ("non_critical", "generative", "recommends")),
    ("A trained camera model inspects vials on the filling line and rejects defects automatically.", ("critical", "static", "acts_autonomously")),
    ("HR wants an AI tool to rank candidates for operator jobs.", ("not_gmp", None, None)),
])
def test_offline_classify(text, expected):
    in_scope, _, cls, _ = classify(text)
    assert in_scope
    got = (cls["gmp_relevance"], cls["model_type"], cls["autonomy"])
    assert all(e is None or e == g for e, g in zip(expected, got)), got


@pytest.mark.parametrize("text", ["What is Annex 22?", "Write me a poem about bioreactors.", "Are we compliant with Annex 11?"])
def test_offline_refuses(text):
    assert classify(text)[0] is False


def test_offline_end_to_end(index, audit):
    r = run_assessment("We want ChatGPT to write first drafts of cleaning SOPs; QA reviews and approves each one.",
                       assessor=OfflineAssessor(), index=index, audit=audit, save=False)
    assert r.decision.verdict == "permitted_with_hitl"
    assert all(j.supported for j in r.judgments)
    assert r.intake_form and r.intake_form.status == "draft_for_qa_review"
    assert {k.id for k in r.controls} >= {"HITL_GENAI", "QU_REVIEW"}
    rec = audit.find(r.meta.request_id)[0]
    assert rec["verdict"] == "permitted_with_hitl" and rec["corpus_version"] == index.corpus_version
    assert audit.verify()[0]


def _answer(cites):
    return json.dumps({
        "in_scope": True, "title": "LLM classifies deviations",
        "classification": {"gmp_relevance": "critical", "model_type": "generative", "autonomy": "recommends"},
        "judgments": [
            {"field": "gmp_relevance", "value": "critical", "rationale": "Deviation classification drives batch disposition.", "citations": cites[:1]},
            {"field": "model_type", "value": "generative", "rationale": "It is a large language model.", "citations": cites[1:2]},
            {"field": "autonomy", "value": "recommends", "rationale": "QA confirms each classification.", "citations": ["FAKE:1:0"]},
        ],
        "open_questions": [],
    })


def test_llm_tool_loop_and_citation_check(index, audit):
    a22 = index.section_chunks("A22", "1")
    client = FakeChatClient([
        ChatResponse(content=None, tool_calls=[ToolCall(id="t1", name="get_section", args={"document": "A22", "section": "1"})]),
        ChatResponse(content="done"),
        ChatResponse(content="```json\n" + _answer([a22[0].id, "AIA:art-50:0"]) + "\n```"),
    ])
    r = run_assessment("Use an LLM to decide whether deviations are minor, major or critical.",
                       assessor=LLMAssessor(client, use_tools=True), index=index, audit=audit, save=False)
    assert r.decision.verdict == "not_permitted_critical"  # rules decide, even though a human reviews
    assert r.meta.tool_calls[0]["tool"] == "get_section" and r.meta.tool_calls[0]["ok"]
    by_field = {j.field: j for j in r.judgments}
    assert by_field["gmp_relevance"].supported  # cited a fetched chunk that is in the map
    assert by_field["model_type"].supported  # cited the map paragraph, which is always given to the model
    assert not by_field["autonomy"].supported and by_field["autonomy"].citations == []  # invented id dropped
    tool_msg = [m for m in client.requests[1]["messages"] if m["role"] == "tool"][0]
    assert "Generative AI" in tool_msg["content"]
    assert client.requests[-1]["json_schema"] is not None  # final answer is schema-forced


def test_invalid_llm_output_rejected_and_logged(index, audit):
    # default (no tools): each attempt is one schema-enforced call; two attempts in total -> two calls
    client = FakeChatClient([ChatResponse(content='{"in_scope": true, "verdict": "annex22_full"}')] * 4)
    with pytest.raises(AssessmentFailed) as exc:
        run_assessment("Use an LLM to approve batch records.", assessor=LLMAssessor(client, use_tools=False), index=index, audit=audit, save=False)
    rec = audit.find(exc.value.request_id)
    assert rec and rec[0]["event"] == "assessment_rejected" and len(rec[0]["errors"]) == 2
    assert len(client.requests) == 2


def test_default_llm_flow_is_one_schema_call_with_core_passages_first(index, audit):
    """prompt-1.3: core definitions always given, no tool round, fixed text first and the case last."""
    from app.intake_form import form_to_text, normalize_form
    from app.pipeline import CORE_SECTIONS

    a22 = index.section_chunks("A22", "1")
    client = FakeChatClient([ChatResponse(content=_answer([a22[0].id, "AIA:art-50:0"]))])
    form = normalize_form({"what": "An LLM proposes how to classify each new deviation; QA confirms it.",
                           "gmp_impact": {"choice": "not_sure", "explain": "QA makes the final call anyway"},
                           "ai_type": {"choice": "llm", "explain": ""}})
    r = run_assessment(form_to_text(form), assessor=LLMAssessor(client, use_tools=False), index=index, audit=audit, save=False, form=form)
    assert len(client.requests) == 1
    req = client.requests[0]
    assert req["tools"] is None and req["json_schema"] is not None
    assert "get_section" not in req["messages"][0]["content"]  # no tool instructions when there is no tool
    user = req["messages"][1]["content"]
    core_ids = [c.id for d, s in CORE_SECTIONS for c in index.section_chunks(d, s)]
    assert user.startswith("PASSAGES:\n[" + core_ids[0] + "]")  # identical prefix for every case
    assert all(f"[{cid}]" in user for cid in core_ids) and set(core_ids) <= set(r.meta.retrieved_chunk_ids)
    assert user.index("USE CASE") > user.index(f"[{core_ids[-1]}]")  # the case comes last
    assert "- gmp_impact (ticked): Not sure; explanation: \"QA makes the final call anyway\"" in user  # structured fields
    assert r.decision.verdict == "not_permitted_critical"


def test_retrieval_prefix_is_identical_for_different_cases(index):
    from app.pipeline import retrieve

    a = [p.chunk.id for p in retrieve(index, "A camera model inspects vials on the filling line.", 8)]
    b = [p.chunk.id for p in retrieve(index, "HR wants an LLM to rank job applicants.", 8)]
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    assert n >= 8  # core sections + framework queries come first, in the same order


def test_title_cut_at_word_boundary():
    from app.assessors.offline import make_title

    t = make_title("An AI agent writes the master batch records and specifications for new client products and sends them on.")
    assert t.endswith("…") and not t.endswith("pr…") and len(t) <= 81


@pytest.mark.parametrize("text", [
    "An LLM writes the weekly deviation summary and emails it to management; nobody checks it first.",
    "The chatbot answers operators without any review by QA.",
])
def test_offline_negated_review_is_not_a_review(text):
    assert classify(text)[2]["autonomy"] == "acts_autonomously"


def test_abbreviations_expanded():
    from app.assessors.offline import expand_abbreviations

    assert classify("Static ML to score fermentation runs")[2]["model_type"] == "static"
    assert classify("An LLM drafts SOPs and QA approves each one")[2]["model_type"] == "generative"
    assert "machine learning" not in expand_abbreviations("Feed 250 mL of media")  # millilitre, not ML


def test_each_rule_quotes_its_own_sentence(index):
    from app.citations import cite_section
    from app.rules import RULES

    expected = {
        "R2-critical-nonstatic": "should not be used in critical GMP",
        "R3-unclear": "critical applications with direct impact",
        "R5-critical-static": "static models",
        "R8-genai-hitl": "non-critical GMP applications",
    }
    rules = {r.id: r for r in RULES}
    for rid, phrase in expected.items():
        r = rules[rid]
        quote = cite_section(index, "A22", "1", r.quote_hint or r.explanation).quote
        assert phrase in quote, (rid, quote)


def test_provider_error_is_rejected_not_crashed(index, audit):
    """An API failure (e.g. HTTP 400/429) must be logged as a rejection, not crash the app."""
    from app.llm.providers import ProviderError

    class Failing:
        name, model = "fake", "fake-1"

        def chat(self, *a, **k):
            raise ProviderError("Gemini HTTP 429: quota exceeded")

    with pytest.raises(AssessmentFailed) as exc:
        run_assessment("Use an LLM to draft SOPs.", assessor=LLMAssessor(Failing()), index=index, audit=audit, save=False)
    rec = audit.find(exc.value.request_id)[0]
    assert rec["event"] == "assessment_rejected" and "429" in rec["errors"][0]


class _Resp:
    def __init__(self, status, text="{}"):
        self.status_code, self.text = status, text


@pytest.mark.parametrize("statuses,expected_status,calls,waits", [
    ([503, 200], 200, 2, [3.0]),                 # one "high demand" 503: wait 3 s, same call succeeds
    ([503, 500, 200], 200, 3, [3.0, 8.0]),       # backoff grows
    ([503, 503, 503, 503], 503, 3, [3.0, 8.0]),  # web app gives up after 3 tries (~15 s) -> plain message (W55)
    ([400], 400, 1, []),                         # a real error is not retried
])
def test_transient_server_errors_are_retried_on_the_same_call(monkeypatch, statuses, expected_status, calls, waits):
    from app.llm import providers

    seq, slept = list(statuses), []
    monkeypatch.setattr(providers, "_send", lambda *a, **k: _Resp(seq.pop(0)))
    monkeypatch.setattr(providers.time, "sleep", slept.append)
    r = providers._post_with_rate_limit_retry("https://example.invalid", {}, {})
    assert r.status_code == expected_status and len(statuses) - len(seq) == calls and slept == waits


def test_evaluation_retries_longer(monkeypatch):
    """The evaluation waits 5, 15, 40 s: finishing the case matters more than speed there (W55)."""
    from app.llm import providers

    monkeypatch.setattr(providers, "TRANSIENT_DELAYS", providers.EVAL_TRANSIENT_DELAYS)
    seq, slept = [503, 503, 503, 503], []
    monkeypatch.setattr(providers, "_send", lambda *a, **k: _Resp(seq.pop(0)))
    monkeypatch.setattr(providers.time, "sleep", slept.append)
    assert providers._post_with_rate_limit_retry("https://example.invalid", {}, {}).status_code == 503
    assert slept == [5.0, 15.0, 40.0] and not seq


def test_slow_assessment_does_not_block_other_pages(index, tmp_path, monkeypatch):
    """W55: /assess runs the assessment in a worker thread, so the server stays responsive meanwhile."""
    import threading, time as _t
    from fastapi.testclient import TestClient
    from app import config, main
    from app.assessors.offline import OfflineAssessor

    config.use_settings(config.Settings(provider="offline", audit_dir=tmp_path / "audit", results_dir=tmp_path / "results"))

    class Slow(OfflineAssessor):
        def assess(self, *a, **k):
            _t.sleep(2.0)
            return super().assess(*a, **k)
    monkeypatch.setattr(main, "get_assessor", lambda provider: Slow())
    try:
        with TestClient(main.app) as client:
            data = {"provider": "offline", "what": "An LLM drafts cleaning SOPs for the filling line; QA reviews every draft."}
            t = threading.Thread(target=lambda: client.post("/assess", data=data))
            t.start()
            _t.sleep(0.3)
            t0 = _t.perf_counter()
            assert client.get("/static/style.css").status_code == 200
            assert _t.perf_counter() - t0 < 1.0  # answered while the slow assessment is still running
            t.join()
    finally:
        config.use_settings(None)


def test_daily_quota_is_not_retried(monkeypatch):
    from app.llm import providers

    seq = [_Resp(429, "Quota exceeded for requests per day"), _Resp(200)]
    monkeypatch.setattr(providers, "_send", lambda *a, **k: seq.pop(0))
    monkeypatch.setattr(providers.time, "sleep", lambda s: pytest.fail("must not wait for a daily quota"))
    assert providers._post_with_rate_limit_retry("https://example.invalid", {}, {}).status_code == 429


def test_gemini_replays_raw_parts():
    """Gemini 3 needs its own message parts (with thought signatures) sent back unchanged."""
    from app.llm.base import ToolCall
    from app.llm.providers import GeminiClient

    raw = [{"functionCall": {"name": "get_section", "args": {"document": "A22", "section": "1"}}, "thoughtSignature": "sig123"}]
    _, contents = GeminiClient._to_contents([
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": None, "tool_calls": [ToolCall("t1", "get_section", {})], "raw_parts": raw},
    ])
    assert contents[1] == {"role": "model", "parts": raw}


def test_provider_schema_keeps_field_named_title():
    """inline_refs drops Pydantic's decorative 'title' labels but must keep our real 'title' field."""
    from app.assessors.llm import response_schema
    from app.llm.providers import inline_refs

    s = inline_refs(response_schema())
    assert "title" in s["properties"] and set(s["required"]) <= set(s["properties"])
    assert "$defs" not in s and "$ref" not in str(s)


@pytest.mark.parametrize("name", ["ChatGPT", "chatgpt", "Chat GPT", "Cahtgpt", "ChatGTP", "GPT-5", "Claude", "CLAUDE",
                                  "Claude 4", "Gemini", "Gemnini", "Copliot", "Mistral", "Llama", "DeepSeek", "OpenAI", "a Llm"])
def test_offline_recognises_ai_products_case_and_typos(name):
    ok, _, cls, _ = classify(f"We want to use {name} to write first drafts of cleaning SOPs; QA approves each one.")
    assert ok and cls["model_type"] == "generative"


def test_offline_typo_matching_has_no_false_positives_in_corpus(index):
    """Fuzzy matching of product names must not fire on ordinary words: none of the 9 regulatory
    documents names an AI product, so any match in them is a false positive (e.g. 'clause' -> 'claude')."""
    import re

    from app.assessors.offline import _product_typos

    words = {w for c in index.chunks for w in re.findall(r"[A-Za-z][A-Za-z-]{5,}", c.text)}
    hits = {w: _product_typos(w) for w in words if _product_typos(w)}
    assert not hits, hits


def test_quota_guard_spaces_requests_and_stops_at_the_daily_budget(tmp_path):
    from datetime import datetime, timezone

    from app.llm.providers import ProviderError, QuotaGuard

    t, slept = [0.0], []
    g = QuotaGuard(max_rpm=12, daily_budget=3, usage_file=tmp_path / "u.json", clock=lambda: t[0],
                   sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)),
                   now=lambda: datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc))
    g.before_request(); t[0] += 1.0; g.before_request(); g.before_request()
    assert slept == [4.0, 5.0]  # 60 s / 12 = 5 s between requests, never faster
    assert g.used_today() == 3
    with pytest.raises(ProviderError, match="Daily budget reached"):
        g.before_request()  # the 4th is refused, not sent
    tomorrow = QuotaGuard(12, 3, tmp_path / "u.json", now=lambda: datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc))
    assert tomorrow.used_today() == 0  # a new quota day (after 08:00 UTC)


def test_every_http_attempt_passes_the_quota_guard(monkeypatch):
    from app.llm import providers

    seq, calls = [_Resp(503), _Resp(200)], []
    monkeypatch.setattr(providers, "_send", lambda *a, **k: seq.pop(0))
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    providers._post_with_rate_limit_retry("https://example.invalid", {}, {}, before_request=lambda: calls.append(1))
    assert len(calls) == 2  # the retry counts against the quota too
