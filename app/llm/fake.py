"""Scripted ChatClient for tests: replays a fixed list of responses and records what it was sent."""
from __future__ import annotations

from app.llm.base import ChatResponse


class FakeChatClient:
    name = "fake"
    model = "fake-1"

    def __init__(self, responses: list[ChatResponse]):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def chat(self, messages, tools=None, json_schema=None) -> ChatResponse:
        self.requests.append({"messages": [dict(m) for m in messages], "tools": tools, "json_schema": json_schema})
        if not self.responses:
            raise RuntimeError("FakeChatClient ran out of scripted responses")
        return self.responses.pop(0)
