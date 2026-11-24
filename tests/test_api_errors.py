"""API errors reach the user as a plain message, with the technical reason folded away (W45).
No real API is called: a fake client raises the provider errors."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.assessors.llm import LLMAssessor
from app.llm.providers import ProviderError, classify_http, http_error
from app.pipeline import FAILURE_MESSAGES, AssessmentFailed, run_assessment


class FailingClient:
    name, model = "gemini", "fake-model"

    def __init__(self, error: ProviderError):
        self.error, self.calls = error, 0

    def chat(self, messages, tools=None, json_schema=None):
        self.calls += 1
        raise self.error


@pytest.mark.parametrize("status,text,kind", [
    (503, "The model is overloaded", "overloaded"),
    (500, "", "overloaded"),
    (429, "Quota exceeded for metric: requests per minute", "rate_limit"),
    (429, "Quota exceeded: generate_content requests per day", "quota_day"),
    (403, "PERMISSION_DENIED", "auth"),
    (400, "API key not valid. Please pass a valid API key.", "auth"),
    (400, "Invalid JSON payload", "rejected"),
])
def test_http_errors_are_classified(status, text, kind):
    assert classify_http(status, text) == kind


def test_http_error_uses_the_providers_own_message():
    r = httpx.Response(503, json={"error": {"code": 503, "message": "The model is overloaded. Please try again later."}})
    e = http_error("Gemini", r)
    assert e.kind == "overloaded" and e.status == 503 and str(e) == "Gemini HTTP 503: The model is overloaded. Please try again later."


@pytest.mark.parametrize("kind", ["overloaded", "quota_day", "daily_budget", "auth", "rejected", "rate_limit"])
def test_api_failure_gives_a_plain_message_and_no_pointless_retry(index, audit, kind):
    client = FailingClient(ProviderError(f"Gemini HTTP 999: technical text for {kind}", kind=kind))
    with pytest.raises(AssessmentFailed) as exc:
        run_assessment("Use an LLM to draft SOPs; QA reviews each one.", assessor=LLMAssessor(client, use_tools=False),
                       index=index, audit=audit, save=False)
    assert exc.value.kind == kind and str(exc.value) == FAILURE_MESSAGES[kind]
    assert f"technical text for {kind}" in exc.value.detail and "HTTP" not in str(exc.value)
    assert client.calls == 1  # the HTTP layer already retried what can be retried
    rec = audit.find(exc.value.request_id)[0]
    assert rec["event"] == "assessment_rejected" and rec["failure_kind"] == kind


def test_network_failure_is_tried_twice(index, audit):
    client = FailingClient(ProviderError("network error: ConnectError: no route", kind="network"))
    with pytest.raises(AssessmentFailed) as exc:
        run_assessment("Use an LLM to draft SOPs; QA reviews each one.", assessor=LLMAssessor(client, use_tools=False),
                       index=index, audit=audit, save=False)
    assert exc.value.kind == "network" and client.calls == 2


def test_network_error_without_a_response_becomes_a_provider_error(monkeypatch):
    from app.llm import providers

    def boom(*a, **k):
        raise httpx.ConnectError("connection refused")
    monkeypatch.setattr(providers, "_send", boom)
    with pytest.raises(ProviderError) as exc:
        providers._post_with_rate_limit_retry("https://example.invalid", {}, {})
    assert exc.value.kind == "network"


# ---------------------------------------------------------------- the web page
@pytest.fixture
def client(index, tmp_path, monkeypatch):
    from app import config, main

    config.use_settings(config.Settings(provider="offline", audit_dir=tmp_path / "audit", results_dir=tmp_path / "results"))
    failing = FailingClient(ProviderError("Gemini HTTP 503: The model is overloaded. Please try again later.", kind="overloaded", status=503))
    monkeypatch.setattr(main, "get_assessor", lambda provider: LLMAssessor(failing, use_tools=False))
    yield TestClient(main.app)
    config.use_settings(None)


def test_form_page_shows_the_plain_message_and_the_details(client):
    data = {"provider": "offline", "what": "An LLM drafts cleaning SOPs for the filling line; QA reviews every draft.",
            "areas": ["qa"], "who_checks": "QA reviews every draft in the eDMS"}
    r = client.post("/assess", data=data)
    assert r.status_code == 502
    assert FAILURE_MESSAGES["overloaded"].split(":")[0] in r.text
    assert "Gemini HTTP 503: The model is overloaded" in r.text  # technical reason, in the details
    assert "An LLM drafts cleaning SOPs for the filling line" in r.text  # the answers are kept


def test_api_returns_kind_and_detail(client):
    r = client.post("/api/assess", json={"description": "An LLM drafts cleaning SOPs; QA reviews every draft before use.",
                                         "provider": "offline"})
    assert r.status_code == 502
    d = r.json()["detail"]
    assert d["kind"] == "overloaded" and d["message"] == FAILURE_MESSAGES["overloaded"] and "HTTP 503" in d["detail"]


def test_timeout_is_its_own_kind_and_not_retried(monkeypatch):
    from app.llm import providers

    def slow(*a, **k):
        raise httpx.ReadTimeout("no complete answer within 120 s")
    monkeypatch.setattr(providers, "_send", slow)
    with pytest.raises(ProviderError) as exc:
        providers._post_with_rate_limit_retry("https://example.invalid", {}, {})
    assert exc.value.kind == "timeout" and exc.value.kind in FAILURE_MESSAGES


def _mock_stream(monkeypatch, handler):
    """Route providers._send through an in-memory transport instead of the network."""
    from app.llm import providers

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(providers.httpx, "stream", lambda method, url, **k: client.stream(method, url, json=k.get("json"),
                                                                                        headers=k.get("headers")))
    return providers


class _Trickle(httpx.SyncByteStream):
    def __iter__(self):
        for _ in range(10):
            yield b" "


def test_send_stops_a_trickling_answer_at_the_deadline(monkeypatch):
    """A server that keeps sending a byte now and then is stopped at the total deadline (W48)."""
    providers = _mock_stream(monkeypatch, lambda request: httpx.Response(200, stream=_Trickle()))
    clock = iter(range(0, 1000, 50))  # each chunk arrives 50 s after the previous one
    monkeypatch.setattr(providers.time, "monotonic", lambda: next(clock))
    with pytest.raises(httpx.ReadTimeout):
        providers._send("https://example.invalid", {}, {}, deadline=120)


def test_send_returns_a_normal_answer(monkeypatch):
    providers = _mock_stream(monkeypatch, lambda request: httpx.Response(200, json={"ok": True}))
    r = providers._send("https://example.invalid", {}, {"q": 1})
    assert r.status_code == 200 and r.json() == {"ok": True}


@pytest.mark.parametrize("kind", sorted(FAILURE_MESSAGES))
def test_every_failure_message_says_the_answers_are_kept(kind):
    """Feature check F08b (W50): the user should never wonder whether they have to type everything again."""
    assert "answers" in FAILURE_MESSAGES[kind] and ("kept" in FAILURE_MESSAGES[kind])
