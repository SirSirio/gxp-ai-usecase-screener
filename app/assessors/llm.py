"""LLM assessor: retrieval-augmented classification with a tool loop and schema-forced output.

Flow (default, prompt-1.3): system prompt + passages (each tagged with its chunk id, the fixed core
passages first) + the use case, then ONE call with the JSON schema enforced.
With tools switched on (GXP_LLM_TOOLS=1 or use_tools=True):
1. tool phase: the model may call get_section up to MAX_TOOL_ROUNDS times;
2. answer phase: one final call with the JSON schema enforced and no tools
   (some providers cannot combine function calling and JSON mode in one request).
The returned dict is validated by the pipeline, not here.
"""
from __future__ import annotations

import json
import re

from app.assessors.base import AssessorError, AssessorOutput, ProviderFailure
from app.llm.base import ChatClient
from app.config import get_settings
from app.llm.prompts import PROMPT_VERSION, system_prompt, user_message
from app.llm.providers import ProviderError
from app.models import ScoredChunk
from app.schema import ModelAssessment
from app.tools import GET_SECTION_SPEC, ToolBox

MAX_TOOL_ROUNDS = 3


def response_schema() -> dict:
    """JSON schema sent to the provider. Pydantic generates it from the same model we validate with."""
    return ModelAssessment.model_json_schema()


def parse_json(text: str) -> dict:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise AssessorError("model returned no JSON object")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise AssessorError(f"model returned invalid JSON: {exc}") from exc


class LLMAssessor:
    prompt_version = PROMPT_VERSION

    def __init__(self, client: ChatClient, use_tools: bool | None = None):
        self.client = client
        self.name = client.name
        # Default: no tool round. The core definitions are always among the passages (pipeline.CORE_SECTIONS),
        # and in the W21 live runs the model never used the tool, so the extra call only cost quota.
        self.use_tools = get_settings().llm_tools if use_tools is None else use_tools

    def assess(self, description: str, passages: list[ScoredChunk], tools: ToolBox, form: dict | None = None) -> AssessorOutput:
        messages: list[dict] = [
            {"role": "system", "content": system_prompt(self.use_tools)},
            {"role": "user", "content": user_message(description, passages, form)},
        ]
        model = self.client.model
        try:
            if not self.use_tools:  # one call, schema enforced
                final = self.client.chat(messages, tools=None, json_schema=response_schema())
                if not final.content:
                    raise AssessorError("model returned an empty answer")
                return AssessorOutput(parse_json(final.content), model=final.model or model)
            for _ in range(MAX_TOOL_ROUNDS):
                resp = self.client.chat(messages, tools=[GET_SECTION_SPEC])
                model = resp.model or model
                # keep the model's own message parts: Gemini 3 needs its thought signatures back
                messages.append({"role": "assistant", "content": resp.content, "tool_calls": resp.tool_calls, "raw_parts": resp.raw_parts})
                if not resp.tool_calls:
                    direct = _valid_or_none(resp.content)
                    if direct is not None:  # answered directly in the right shape: done
                        return AssessorOutput(direct, model=model)
                    break  # otherwise ask again with the schema enforced
                for call in resp.tool_calls:
                    result = tools.run(call.name, call.args)
                    messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name, "content": json.dumps(result)})
            messages.append({"role": "user", "content": "Now return the final JSON object only, in exactly the required schema."})
            final = self.client.chat(messages, tools=None, json_schema=response_schema())
        except ProviderError as exc:  # API failure: logged by the pipeline; the user gets a plain message (W45)
            raise ProviderFailure(str(exc), exc.kind, exc.status) from exc
        if not final.content:
            raise AssessorError("model returned an empty answer")
        return AssessorOutput(parse_json(final.content), model=final.model or model)


def _valid_or_none(text: str | None) -> dict | None:
    """Parse and schema-check a direct answer; None if it is missing or has the wrong shape."""
    if not text or "{" not in text:
        return None
    try:
        data = parse_json(text)
        ModelAssessment.model_validate(data)
        return data
    except (AssessorError, ValueError):
        return None
