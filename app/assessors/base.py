"""Assessor interface: description + retrieved passages (+ tools) in, raw ModelAssessment dict out.

Two implementations:
- OfflineAssessor: deterministic keyword baseline. No API key. Gives a floor to compare the LLM against.
- LLMAssessor: any ChatClient (Gemini, Azure OpenAI, or a scripted fake in tests).
The pipeline validates whatever comes back; an assessor is never trusted to produce valid output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import ScoredChunk
from app.tools import ToolBox


class AssessorError(Exception):
    """The assessor could not produce an answer (API error, unparseable output)."""


class ProviderFailure(AssessorError):
    """The LLM API call itself failed (no answer to check). `kind` as in app.llm.providers.ProviderError."""

    def __init__(self, message: str, kind: str, status: int | None = None):
        super().__init__(message)
        self.kind, self.status = kind, status


@dataclass
class AssessorOutput:
    raw: dict
    model: str


class Assessor(Protocol):
    name: str
    prompt_version: str

    def assess(self, description: str, passages: list[ScoredChunk], tools: ToolBox, form: dict | None = None) -> AssessorOutput:
        """`description` is the text to classify; `form` is the structured intake form it came from, or None (quick mode)."""
        ...
