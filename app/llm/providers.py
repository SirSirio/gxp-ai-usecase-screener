"""Real LLM providers over plain HTTPS (httpx), so no vendor SDK is required.

STATUS: Gemini is exercised live (WORKLOG W13, W14, W21); Azure OpenAI is written against the
public REST API but not yet tested against a live endpoint. The tool loop and parsing are
covered by tests with FakeChatClient.
"""
from __future__ import annotations

import copy
import json
import os
import re
import time
import uuid

import httpx

from app.llm.base import ChatResponse, ToolCall

TIMEOUT = httpx.Timeout(90.0, connect=10.0)  # 90 s is the longest wait *between* bytes, not for the whole answer
REQUEST_DEADLINE = float(os.getenv("LLM_REQUEST_DEADLINE", "120"))  # whole answer; one dev request once took 14 min (W48)


def _send(url: str, headers: dict, body: dict, deadline: float | None = None) -> httpx.Response:
    """POST and read the answer within a total deadline. httpx's own timeout only bounds each wait between
    bytes, so a slow trickle could hold a request open for many minutes (D017 in the W47 dev run: 851 s)."""
    deadline = REQUEST_DEADLINE if deadline is None else deadline
    t0 = time.monotonic()
    with httpx.stream("POST", url, headers=headers, json=body, timeout=TIMEOUT) as r:
        buf = bytearray()
        for chunk in r.iter_bytes():
            buf += chunk
            if time.monotonic() - t0 > deadline:
                raise httpx.ReadTimeout(f"no complete answer within {deadline:.0f} s", request=r.request)
        # iter_bytes() already decoded the body, so the encoding headers no longer apply
        headers_out = {k: v for k, v in r.headers.items() if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")}
        return httpx.Response(r.status_code, headers=headers_out, content=bytes(buf), request=r.request)


class ProviderError(Exception):
    """An LLM API call failed (HTTP error, rate limit). The message includes the provider's reason.

    `kind` says what went wrong in terms a user can act on (W45): overloaded, rate_limit, quota_day,
    daily_budget, auth, rejected, network, timeout. `status` is the HTTP status, if there was a response.
    """

    def __init__(self, message: str, kind: str = "rejected", status: int | None = None):
        super().__init__(message)
        self.kind, self.status = kind, status


def classify_http(status: int, text: str) -> str:
    """The failure kind of an HTTP error response."""
    low = text.lower()
    if status == 429:
        return "quota_day" if "per day" in low else "rate_limit"
    if status in TRANSIENT:
        return "overloaded"
    if status in (401, 403) or (status == 400 and "api key" in low):
        return "auth"
    return "rejected"


def http_error(provider: str, r: httpx.Response) -> ProviderError:
    """A ProviderError for an HTTP error response, with the provider's own message when it gives one."""
    try:
        reason = r.json().get("error", {}).get("message") or r.text
    except ValueError:
        reason = r.text
    return ProviderError(f"{provider} HTTP {r.status_code}: {reason[:500]}", classify_http(r.status_code, r.text), r.status_code)


TRANSIENT = {500, 502, 503, 504}  # server overloaded or briefly down ("high demand"): worth a short wait
# Waits before retrying a temporary server error. Short in the web app, where a person is waiting: about 15 s,
# then the plain "Gemini is overloaded" message (W55; before, a 503 kept the page waiting for over a minute).
# The evaluation sets EVAL_TRANSIENT_DELAYS, because there finishing the case matters more than speed.
TRANSIENT_DELAYS: tuple[float, ...] = (3.0, 8.0)
EVAL_TRANSIENT_DELAYS: tuple[float, ...] = (5.0, 15.0, 40.0)


class QuotaGuard:
    """Stay below the free-tier limits instead of hitting them (user request, WORKLOG W39).

    - Per minute: at most `max_rpm` requests (default 12, under Gemini's 15), by spacing them out.
    - Per day: at most `daily_budget` requests (default 450, under the 500 quota); then every further
      request is refused with a ProviderError (a logged rejection), never sent.
    Every HTTP attempt counts, including retries: failed requests also count against Google's quota.
    The day count is kept in a small file so it survives restarts and is shared by the app and the
    evaluation. Google's quota resets at 09:00 Danish time; the counter's day starts at 08:00 UTC
    (09:00 in winter, 10:00 in summer: an hour late in summer, i.e. on the safe side).
    """

    def __init__(self, max_rpm: int, daily_budget: int, usage_file, clock=time.monotonic, sleep=time.sleep, now=None):
        import threading
        from datetime import datetime, timezone

        self.interval = 60.0 / max_rpm if max_rpm > 0 else 0.0
        self.daily_budget = daily_budget
        self.usage_file = usage_file
        self.clock, self.sleep = clock, sleep
        self.now = now or (lambda: datetime.now(timezone.utc))
        self._last: float | None = None
        self._lock = threading.Lock()

    def _day(self) -> str:
        from datetime import timedelta

        return (self.now() - timedelta(hours=8)).date().isoformat()

    def used_today(self) -> int:
        try:
            data = json.loads(self.usage_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        return int(data.get(self._day(), 0))

    def before_request(self) -> None:
        with self._lock:
            used = self.used_today()
            if used >= self.daily_budget:
                raise ProviderError(f"Daily budget reached: {used} of {self.daily_budget} Gemini requests used today "
                                    "(free quota 500; resets at 09:00 Danish time). Use the keyword baseline until then.",
                                    kind="daily_budget")
            if self._last is not None and self.interval:
                wait = self.interval - (self.clock() - self._last)
                if wait > 0:
                    self.sleep(wait)
            self._last = self.clock()
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file.write_text(json.dumps({self._day(): used + 1}), encoding="utf-8")


_QUOTA: QuotaGuard | None = None


def gemini_quota() -> QuotaGuard:
    """The process-wide guard for Gemini requests (limits from GEMINI_MAX_RPM / GEMINI_DAILY_BUDGET)."""
    global _QUOTA
    if _QUOTA is None:
        from app.config import ROOT

        _QUOTA = QuotaGuard(int(os.getenv("GEMINI_MAX_RPM", "12")), int(os.getenv("GEMINI_DAILY_BUDGET", "450")),
                            ROOT / "data" / "usage" / "gemini_requests.json")
    return _QUOTA


def _post_with_rate_limit_retry(url: str, headers: dict, body: dict, attempts: int = 4,
                                before_request=None) -> httpx.Response:
    """POST, waiting and retrying the same call on a per-minute rate limit (HTTP 429) or a
    temporary server error (HTTP 500/502/503/504).

    A per-day quota is not retried: waiting a minute does not help, so the 429 is returned and
    becomes a logged rejection. For 429 the wait uses the server's suggested retryDelay when given;
    for server errors it backs off 5, 15, then 40 seconds. Without this, one 503 restarted the whole
    assessment and two in a row turned it into a rejection (WORKLOG W21).
    """
    for attempt in range(attempts):
        if before_request is not None:  # pacing and daily budget (QuotaGuard); may raise ProviderError
            before_request()
        try:
            r = _send(url, headers, body)
        except httpx.TimeoutException as exc:  # connected, but no complete answer in time (W48)
            raise ProviderError(f"timeout: {type(exc).__name__}: {exc}"[:500], kind="timeout") from exc
        except httpx.HTTPError as exc:  # no response at all: DNS, connection refused
            raise ProviderError(f"network error: {type(exc).__name__}: {exc}"[:500], kind="network") from exc
        last = attempt == attempts - 1
        if r.status_code in TRANSIENT and not last and attempt < len(TRANSIENT_DELAYS):
            time.sleep(TRANSIENT_DELAYS[attempt])
            continue
        if r.status_code != 429 or "per day" in r.text.lower() or last:
            return r
        delay = 30.0
        m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', r.text)
        if m:
            delay = float(m.group(1)) + 1
        time.sleep(min(delay, 90))
    return r


def inline_refs(schema: dict) -> dict:
    """Resolve $ref/$defs so providers with partial JSON-Schema support accept the schema."""
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})

    def walk(node, is_properties: bool = False):
        if isinstance(node, dict):
            if "$ref" in node and not is_properties:
                target = defs[node["$ref"].split("/")[-1]]
                return walk(copy.deepcopy(target))
            # Drop Pydantic's decorative "title" labels, but never a real field that is *named* "title"
            # (inside "properties"). Dropping that broke the schema: Gemini answered HTTP 400.
            return {k: walk(v, is_properties=(k == "properties")) for k, v in node.items()
                    if is_properties or k != "title"}
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


class GeminiClient:
    """Google Gemini generateContent API (AI Studio key)."""

    name = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

    @staticmethod
    def _to_contents(messages: list[dict]) -> tuple[str, list[dict]]:
        system, contents = "", []
        for m in messages:
            if m["role"] == "system":
                system += m["content"]
            elif m["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
            elif m["role"] == "assistant":
                if m.get("raw_parts"):  # replay the model's own parts unchanged (keeps Gemini 3 thought signatures)
                    contents.append({"role": "model", "parts": m["raw_parts"]})
                    continue
                parts = [{"text": m["content"]}] if m.get("content") else []
                parts += [{"functionCall": {"name": c.name, "args": c.args}} for c in m.get("tool_calls", [])]
                contents.append({"role": "model", "parts": parts})
            elif m["role"] == "tool":
                contents.append({"role": "user", "parts": [{"functionResponse": {"name": m["name"], "response": json.loads(m["content"])}}]})
        return system, contents

    def chat(self, messages, tools=None, json_schema=None) -> ChatResponse:
        system, contents = self._to_contents(messages)
        body: dict = {"contents": contents, "generationConfig": {"temperature": 0}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = [{"functionDeclarations": tools}]
        if json_schema:
            body["generationConfig"]["responseMimeType"] = "application/json"
            body["generationConfig"]["responseJsonSchema"] = inline_refs(json_schema)
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        # No silent fallback to "JSON without schema": that fallback once hid a broken schema (WORKLOG W13).
        r = _post_with_rate_limit_retry(self.URL.format(model=self.model), headers, body,
                                        before_request=gemini_quota().before_request)
        if r.status_code >= 400:
            raise http_error("Gemini", r)
        data = r.json()
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if "text" in p and not p.get("thought")) or None
        calls = [ToolCall(id=uuid.uuid4().hex[:8], name=p["functionCall"]["name"], args=p["functionCall"].get("args", {}))
                 for p in parts if "functionCall" in p]
        return ChatResponse(content=text, tool_calls=calls, model=data.get("modelVersion", self.model),
                            usage=data.get("usageMetadata", {}), raw_parts=parts)


class AzureOpenAIClient:
    """Azure OpenAI / AI Foundry chat completions (deployment-based)."""

    name = "azure_openai"

    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        if not (self.endpoint and self.api_key and self.model):
            raise RuntimeError("AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT must be set")

    @staticmethod
    def _to_messages(messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                out.append({"role": "assistant", "content": m.get("content"), "tool_calls": [
                    {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.args)}} for c in m["tool_calls"]]})
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def chat(self, messages, tools=None, json_schema=None) -> ChatResponse:
        url = f"{self.endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"
        body: dict = {"messages": self._to_messages(messages), "temperature": 0}
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in tools]
        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "model_assessment", "schema": inline_refs(json_schema), "strict": False}}
        try:
            r = httpx.post(url, headers={"api-key": self.api_key, "Content-Type": "application/json"}, json=body, timeout=TIMEOUT)
        except httpx.HTTPError as exc:
            raise ProviderError(f"network error: {type(exc).__name__}: {exc}"[:500], kind="network") from exc
        if r.status_code >= 400:
            raise http_error("Azure OpenAI", r)
        data = r.json()
        msg = data["choices"][0]["message"]
        calls = [ToolCall(id=c["id"], name=c["function"]["name"], args=json.loads(c["function"]["arguments"] or "{}"))
                 for c in msg.get("tool_calls") or []]
        return ChatResponse(content=msg.get("content"), tool_calls=calls, model=data.get("model", self.model), usage=data.get("usage", {}))
