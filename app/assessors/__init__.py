"""Assessor factory: pick the assessor from GXP_PROVIDER (offline | gemini | azure_openai)."""
from __future__ import annotations

from app.assessors.base import Assessor


def get_assessor(provider: str) -> Assessor:
    if provider == "offline":
        from app.assessors.offline import OfflineAssessor

        return OfflineAssessor()
    from app.assessors.llm import LLMAssessor
    from app.llm.providers import AzureOpenAIClient, GeminiClient

    if provider == "gemini":
        return LLMAssessor(GeminiClient())
    if provider == "azure_openai":
        return LLMAssessor(AzureOpenAIClient())
    raise ValueError(f"unknown provider {provider!r}")
