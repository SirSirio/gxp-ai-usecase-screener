"""Provider-neutral chat interface. Swapping Gemini for Azure OpenAI means swapping one class.

Messages use a small neutral format:
  {"role": "system"|"user"|"assistant", "content": str}
  {"role": "assistant", "tool_calls": [ToolCall, ...]}
  {"role": "tool", "tool_call_id": str, "name": str, "content": str(JSON)}
Each client translates this to its own API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    usage: dict = field(default_factory=dict)
    raw_parts: list | None = None  # provider's own message parts, replayed unchanged on the next turn


class ChatClient(Protocol):
    name: str
    model: str

    def chat(self, messages: list[dict], tools: list[dict] | None = None, json_schema: dict | None = None) -> ChatResponse: ...
