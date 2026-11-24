"""End-to-end assessment: retrieve → assess → validate → citation check → rules → controls → intake → audit.

Each step only trusts the previous one as far as it has been checked:
- assessor output is validated against the schema (invalid → rejected, logged, never shown);
- citations are checked against what was actually retrieved or fetched;
- the verdict comes from the rules layer, never from the model.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from app.assessors import get_assessor
from app.assessors.base import Assessor, AssessorError, ProviderFailure
from app import guards, source_map
from app.audit import AuditLog
from app.citations import cite_section, check_judgment
from app.config import APP_VERSION, get_settings
from app.controls import CONTROLS
from app.intake_form import CLASSIFICATION_INPUTS, MAX_ROUNDS
from app.models import ScoredChunk
from app.retrieval.index import KnowledgeIndex, get_index
from app.rules import RULES_VERSION, VERDICT_LABELS, adaptiveness, decide, human_in_the_loop
from app.schema import (
    AssessmentResult, Control, Decision, FollowUpItem, GridPosition, IntakeForm, ModelAssessment, RunMeta,
)
from app.tools import ToolBox

# Fixed "framework" queries run next to the user's text. A use case written in business language
# ("ChatGPT drafts our SOPs") rarely matches the regulatory wording that decides it, so these make
# sure the deciding passages are always among the candidates the assessor sees.
FRAMEWORK_QUERIES = (
    ("Annex 22 scope: AI models used in critical GMP applications with direct impact on patient safety, product quality or data integrity; static models with deterministic output", 2),
    ("Generative AI and Large Language Models should not be used in critical GMP applications; non-critical use requires human-in-the-loop", 2),
    ("dynamic models which continuously learn and adapt during use should not be used in critical GMP applications", 1),
    ("human-in-the-loop: a model gives input to a decision made by a human operator; review of every output", 2),
    ("AI generated procedures and specifications must be reviewed and cleared by the quality unit", 2),
    ("computerised system validation and risk management for GMP computerised systems", 2),
    ("AI literacy and transparency obligations for deployers of AI systems; chatbots interacting with natural persons", 2),
)
DRAFT_WARNING = "Draft Annex 22, the draft Annex 11 and the draft Chapter 4 are consultation drafts (July 2025). The final texts may differ."


MAX_TEXT_FOLLOW_UPS = 3  # the classifier's own free-text questions shown for reply


def follow_up_items(outcome, model_questions: list[str]) -> list[FollowUpItem]:
    """Questions on a "Not yet" result with the inputs that answer them: the rules' and guards'
    questions come with the matching form questions (choices), the classifier's own ones with a text box."""
    details = list(outcome.question_details) + [None] * len(outcome.questions)
    items = [FollowUpItem(kind="fields", question=q, fields=list(CLASSIFICATION_INPUTS[f]), blocking=True,
                          contradiction=details[i])
             for i, (q, f) in enumerate(zip(outcome.questions, outcome.question_fields)) if f in CLASSIFICATION_INPUTS]
    asked = {i.question for i in items}
    texts = [q for q in dict.fromkeys(model_questions) if q not in asked][:MAX_TEXT_FOLLOW_UPS]
    # the classifier's own questions do not decide the outcome: "points QA will want answered"
    return items + [FollowUpItem(kind="text", question=q, blocking=False) for q in texts]


class AssessmentFailed(Exception):
    """No result can be shown. The message is plain language for the user; `detail` is the technical reason
    (shown folded away under "details"); `kind` is the failure kind (W45)."""

    def __init__(self, request_id: str, message: str, detail: str = "", kind: str = "invalid_output"):
        super().__init__(message)
        self.request_id, self.detail, self.kind = request_id, detail, kind


# What the user reads when no result can be shown, per failure kind (W45). The technical reason goes in `detail`.
FAILURE_MESSAGES = {
    "overloaded": "Gemini is overloaded or briefly unavailable right now. Your answers are kept. Try again in a "
                  "minute, or choose the keyword baseline.",
    "rate_limit": "Too many requests were sent to Gemini in the last minute. Your answers are kept. Wait a minute and try again.",
    "quota_day": "Today's Gemini quota is used up. Your answers are kept. It resets at 09:00 Danish time. Until "
                 "then, choose the keyword baseline.",
    "daily_budget": "Today's Gemini budget for this app is used up. Your answers are kept. It resets at 09:00 Danish "
                    "time. Until then, choose the keyword baseline.",
    "auth": "Gemini did not accept the app's API key, so nothing was assessed. Your answers are kept. The key needs "
            "to be checked. Until then, choose the keyword baseline.",
    "rejected": "Gemini rejected the request. This is a problem on the app's side, not with your answers. Your "
                "answers are kept, and the issue was logged. Try again later, or choose the keyword baseline.",
    "network": "Gemini could not be reached. Your answers are kept. Check the internet connection and try again.",
    "timeout": "Gemini took too long to answer, so the request was stopped. Your answers are kept. Try again in a "
               "minute, or choose the keyword baseline.",
    "invalid_output": "The AI's answer did not pass the app's format check, so it is not shown. It was logged. Your "
                      "answers are kept. Try again, or choose the keyword baseline.",
}
RETRY_KINDS = {"network"}  # API failures worth one more assessment attempt (the HTTP layer already retries 429/5xx)


# The definitions every classification rests on (LABELING_GUIDE): always given to the assessor, so it
# needs no tool round to fetch them (prompt-1.3, WORKLOG W23).
CORE_SECTIONS = (("A22", "1"), ("A22", "3.3"), ("A22", "10.5"))


def retrieve(index: KnowledgeIndex, description: str, k: int) -> list[ScoredChunk]:
    """Core sections and the source-map paragraphs, then the framework queries, then the hits for this use case. The first two parts
    are the same for every request, so the prompt starts with an identical prefix (provider caching)."""
    seen: dict[str, ScoredChunk] = {}
    for doc, section in CORE_SECTIONS:
        for chunk in index.section_chunks(doc, section):
            seen.setdefault(chunk.id, ScoredChunk(chunk=chunk, score=1.0))
    # every paragraph the source map names, so the model can always cite the right one (map-1.0, D24)
    for cid in source_map.all_ids():
        chunk = index.get_chunk(cid)
        if chunk:
            seen.setdefault(cid, ScoredChunk(chunk=chunk, score=1.0))
    for query, n in FRAMEWORK_QUERIES:
        for hit in index.search(query, n):
            seen.setdefault(hit.chunk.id, hit)
    for hit in index.search(description, k):
        seen.setdefault(hit.chunk.id, hit)
    return list(seen.values())


def _audit() -> AuditLog:
    return AuditLog(get_settings().audit_dir / "audit.jsonl")


def run_assessment(description: str, assessor: Assessor | None = None, index: KnowledgeIndex | None = None,
                   audit: AuditLog | None = None, save: bool = True, form: dict | None = None,
                   round: int = 1, parent_request_id: str | None = None) -> AssessmentResult:
    """Assess one use case. `description` is what the assessor classifies; `form` (optional) is the
    structured intake form it was rendered from (app.intake_form.form_to_text). The form is stored,
    audited and exported with the result. `round` / `parent_request_id`: a follow-up submission after a
    "Not yet" result (at most intake_form.MAX_ROUNDS rounds), linked to the request it answers."""
    if not 1 <= round <= MAX_ROUNDS:
        raise ValueError(f"round must be 1 to {MAX_ROUNDS}")
    settings = get_settings()
    index = index or get_index()
    assessor = assessor or get_assessor(settings.provider)
    audit = audit or _audit()
    request_id = uuid.uuid4().hex[:12]
    created = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    description = description.strip()

    passages = retrieve(index, description, settings.top_k)
    tools = ToolBox(index)
    base_log = {
        "request_id": request_id, "description": description,
        "description_sha256": hashlib.sha256(description.encode()).hexdigest(),
        "provider": assessor.name, "prompt_version": assessor.prompt_version, "rules_version": RULES_VERSION,
        "corpus_version": index.corpus_version, "source_map_version": source_map.SOURCE_MAP_VERSION, "app_version": APP_VERSION,
        "retrieved_chunk_ids": [p.chunk.id for p in passages],
        "round": round, "parent_request_id": parent_request_id,
    }
    if form is not None:
        base_log["form"] = form

    # ---- assess + validate (one retry for LLMs; invalid output is never shown) ----
    ma, raw, model, errors, failure = None, None, "", [], None
    for attempt in range(1 if assessor.name == "offline" else 2):
        try:
            out = assessor.assess(description, passages, tools, form=form)
            raw, model = out.raw, out.model
            ma = ModelAssessment.model_validate(raw)
            break
        except ProviderFailure as exc:  # the API call failed: retrying rarely helps (quota, key, overload already retried)
            errors.append(str(exc)[:2000])
            failure = exc
            if exc.kind not in RETRY_KINDS:
                break
        except (ValidationError, AssessorError) as exc:
            errors.append(str(exc)[:2000])
            failure = None
    if ma is None:
        kind = failure.kind if failure is not None else "invalid_output"
        audit.append("assessment_rejected", {**base_log, "model": model, "raw_output": raw, "errors": errors,
                                             "failure_kind": kind, "tool_calls": tools.calls})
        raise AssessmentFailed(request_id, FAILURE_MESSAGES.get(kind, FAILURE_MESSAGES["rejected"]),
                               detail=(errors[-1] if errors else "")[:600], kind=kind)

    # ---- citation check ----
    allowed = {p.chunk.id for p in passages} | tools.fetched_ids
    judgments = [check_judgment(index, j, allowed) for j in ma.judgments]

    # ---- rules decide ----
    outcome = decide(ma.in_scope, ma.classification)
    # ---- safety guards (form input): may only turn the outcome into "Not yet" (app/guards.py) ----
    outcome = guards.check(form, ma.in_scope, ma.classification, outcome) or outcome
    quote_claim = outcome.quote_hint or outcome.explanation  # steer each quote to the sentence the rule rests on
    trims = {(t[0], t[1]): (t[2], t[3]) for t in outcome.quote_trim}
    decision_cits = [c for c in (cite_section(index, d, s, quote_claim, *trims.get((d, s), ("", "")))
                                 for d, s in outcome.sources) if c]
    decision = Decision(verdict=outcome.verdict, label=VERDICT_LABELS[outcome.verdict], rule_id=outcome.rule_id,
                        explanation=outcome.explanation, citations=decision_cits)

    controls = []
    for cid in outcome.controls:
        cdef = CONTROLS[cid]
        cits = [c for c in (cite_section(index, d, s, cdef.quote_hint or cdef.what) for d, s in cdef.refs) if c]
        controls.append(Control(id=cid, title=cdef.title, what=cdef.what,
                                why="Source: " + "; ".join(c.ref for c in cits) if cits else "Source: none resolved",
                                citations=cits))

    questions = list(dict.fromkeys(ma.open_questions + list(outcome.questions)))
    warnings = []
    shown = decision_cits + [c for j in judgments for c in j.citations] + [c for k in controls for c in k.citations]
    if any(c.doc_status == "draft" for c in shown):
        warnings.append(DRAFT_WARNING)
    unsupported = [j.field for j in judgments if not j.supported]
    if unsupported:
        warnings.append(f"No supporting passage found for: {', '.join(unsupported)}. Treat those judgments with care.")

    c = ma.classification
    meta = RunMeta(request_id=request_id, created_at=created, provider=assessor.name, model=model,
                   prompt_version=assessor.prompt_version, rules_version=RULES_VERSION,
                   corpus_version=index.corpus_version, app_version=APP_VERSION,
                   source_map_version=source_map.SOURCE_MAP_VERSION, retrieved_chunk_ids=[p.chunk.id for p in passages], tool_calls=tools.calls,
                   latency_ms=int((time.perf_counter() - t0) * 1000), round=round, parent_request_id=parent_request_id)
    title = (form or {}).get("title") or ma.title  # the proposer's own title wins over a generated one
    follow_up = follow_up_items(outcome, ma.open_questions) if form is not None and decision.verdict == "needs_more_information" else []
    result = AssessmentResult(
        description=description, in_scope=ma.in_scope, title=title, out_of_scope_reason=ma.out_of_scope_reason,
        classification=c, human_in_the_loop=human_in_the_loop(c),
        grid=GridPosition(adaptiveness=adaptiveness(c), autonomy=c.autonomy) if c else None,
        decision=decision, judgments=judgments, controls=controls, open_questions=questions, warnings=warnings,
        form=form, follow_up=follow_up, follow_up_allowed=bool(follow_up) and round < MAX_ROUNDS, meta=meta,
    )
    if ma.in_scope:
        result.intake_form = build_intake(result)

    audit.append("assessment", {
        **base_log, "model": model, "tool_calls": tools.calls, "raw_output": raw, "validation_errors": errors,
        "verdict": decision.verdict, "rule_id": decision.rule_id,
        "classification": c.model_dump() if c else None,
        "cited_chunk_ids": sorted({x.chunk_id for x in shown}),
        "unsupported_judgments": unsupported, "latency_ms": meta.latency_ms,
    })
    if save:
        settings.results_dir.mkdir(parents=True, exist_ok=True)
        (settings.results_dir / f"{request_id}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def build_intake(r: AssessmentResult) -> IntakeForm:
    c = r.classification
    return IntakeForm(
        request_id=r.meta.request_id, created_at=r.meta.created_at, title=r.title, description=r.description,
        classification={
            "gmp_relevance": c.gmp_relevance, "model_type": c.model_type, "autonomy": c.autonomy,
            "human_in_the_loop": r.human_in_the_loop,
            "grid": {"adaptiveness": r.grid.adaptiveness, "autonomy": r.grid.autonomy} if r.grid else None,
        },
        verdict={"code": r.decision.verdict, "label": r.decision.label, "rule_id": r.decision.rule_id,
                 "explanation": r.decision.explanation},
        required_controls=[{"id": k.id, "title": k.title, "what": k.what, "sources": [x.ref for x in k.citations], "status": "open"}
                           for k in r.controls],
        open_questions=r.open_questions,
        evidence=[{"field": j.field, "value": j.value, "supported": j.supported,
                   "sources": [{"ref": x.ref, "chunk_id": x.chunk_id, "quote": x.quote} for x in j.citations]}
                  for j in r.judgments],
        generated_by={"provider": r.meta.provider, "model": r.meta.model, "prompt_version": r.meta.prompt_version,
                      "rules_version": r.meta.rules_version, "corpus_version": r.meta.corpus_version,
                      "source_map_version": r.meta.source_map_version,
                      "app_version": r.meta.app_version},
        proposer_answers=r.form,
    )


def result_to_json(r: AssessmentResult) -> str:
    return json.dumps(json.loads(r.model_dump_json()), indent=2, ensure_ascii=False)
