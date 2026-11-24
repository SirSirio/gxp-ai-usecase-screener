"""Schemas. Enum values must match docs/LABELING_GUIDE.md.

Two layers:
- ModelAssessment: what an assessor (LLM or offline baseline) must return. Validated strictly;
  anything invalid is rejected and logged, never shown.
- AssessmentResult: what the user gets, after the rules layer and the citation check.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GmpRelevance = Literal["critical", "non_critical", "not_gmp", "unclear"]
ModelType = Literal["static", "dynamic", "generative", "probabilistic", "non_ml", "unclear"]
Autonomy = Literal["informs", "recommends", "acts_with_oversight", "acts_autonomously", "unclear"]
Verdict = Literal[
    "out_of_scope",
    "outside_gmp",
    "not_permitted_critical",
    "needs_more_information",
    "not_ai_annex11",
    "annex22_full",
    "hitl_required",
    "permitted_with_hitl",
    "permitted_risk_based",
]
JudgmentField = Literal["gmp_relevance", "model_type", "autonomy"]

FIELD_VALUES: dict[str, tuple[str, ...]] = {
    "gmp_relevance": GmpRelevance.__args__,
    "model_type": ModelType.__args__,
    "autonomy": Autonomy.__args__,
}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- assessor output
class Classification(Strict):
    gmp_relevance: GmpRelevance
    model_type: ModelType
    autonomy: Autonomy


class Judgment(Strict):
    field: JudgmentField
    value: str
    rationale: str = Field(min_length=10, max_length=800)
    citations: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("citations")
    @classmethod
    def plain_ids(cls, v: list[str]) -> list[str]:
        """Strip the brackets and quotes a model copies from the prompt ("[A22:1:1]" -> "A22:1:1"); without this,
        valid citations were dropped as unknown ids (feature check F10e, W50). Only the wrapping is removed:
        the id must still match a passage exactly in the citation check."""
        return [c.strip().strip("[]()\"'` ").strip() for c in v]


class ModelAssessment(Strict):
    """The only shape an assessor may return."""

    in_scope: bool
    out_of_scope_reason: str | None = None
    title: str = Field(min_length=3, max_length=120)
    classification: Classification | None = None
    judgments: list[Judgment] = Field(default_factory=list, max_length=6)
    open_questions: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("judgments")
    @classmethod
    def judgments_match_fields(cls, v: list[Judgment]) -> list[Judgment]:
        for j in v:
            if j.value not in FIELD_VALUES[j.field]:
                raise ValueError(f"judgment value {j.value!r} not allowed for {j.field}")
        return v

    @model_validator(mode="after")
    def consistent(self) -> "ModelAssessment":
        if self.in_scope:
            if self.classification is None:
                raise ValueError("in-scope assessments need a classification")
            fields = [j.field for j in self.judgments]
            if sorted(fields) != sorted(FIELD_VALUES):
                raise ValueError("in-scope assessments need exactly one judgment per field")
            for j in self.judgments:
                if getattr(self.classification, j.field) != j.value:
                    raise ValueError(f"judgment for {j.field} contradicts the classification")
        elif self.classification is not None or self.judgments:
            raise ValueError("out-of-scope assessments must not classify")
        return self


# ---------------------------------------------------------------- result for the user
class Citation(BaseModel):
    chunk_id: str
    doc_id: str
    ref: str  # "Annex 22 (draft) §1 Scope"
    doc_status: str
    url: str
    page: int
    quote: str  # the sentence(s) that best support the claim
    support: float  # support score from the citation check


class CheckedJudgment(BaseModel):
    field: JudgmentField
    value: str
    label: str
    rationale: str
    supported: bool
    citations: list[Citation]
    citations_proposed: int = 0  # how many ids the assessor cited before the check
    proposed_ids: list[str] = Field(default_factory=list)  # the ids it cited, before the check (scored by the eval)
    note: str | None = None  # e.g. "Not covered by the sources."


class Control(BaseModel):
    id: str
    title: str
    what: str
    why: str
    citations: list[Citation]


class GridPosition(BaseModel):
    adaptiveness: Literal["locked", "adaptive", "unclear"]
    autonomy: Autonomy
    note: str = "Simplified grid inspired by the GAMP AI adaptiveness × autonomy concept; levels defined in this project."


class Decision(BaseModel):
    verdict: Verdict
    label: str
    rule_id: str
    explanation: str
    citations: list[Citation]


class RunMeta(BaseModel):
    request_id: str
    created_at: datetime
    provider: str
    model: str
    prompt_version: str
    rules_version: str
    corpus_version: str
    app_version: str
    retrieved_chunk_ids: list[str]
    source_map_version: str = ""  # app/source_map.py: which paragraphs may back each answer
    tool_calls: list[dict] = Field(default_factory=list)
    latency_ms: int = 0
    round: int = 1  # 1 = first submission; 2-3 = follow-up rounds after "Not yet" (intake_form.MAX_ROUNDS)
    parent_request_id: str | None = None  # the request this follow-up answers


class FollowUpItem(BaseModel):
    """One question on a "Not yet" result, with the form inputs that can answer it (WORKLOG W33).

    kind "fields": show these form questions (choices with their (i) help, prefilled) next to the
    question, so the corrected ticks reach the rules and the guards. kind "text": a question from the
    classifier itself; the proposer answers in a short text box (stored in form["follow_up"])."""

    kind: Literal["fields", "text"]
    question: str
    fields: list[str] = Field(default_factory=list)  # intake_form question ids, for kind "fields"
    # True: answering it can change the outcome (questions from the rules and guards). False: a point the
    # classifier raises that QA will want answered, but that does not decide the outcome (W35).
    blocking: bool = True
    # For a contradiction (guard G2): which answer conflicts with what, where each reading leads, how to resolve.
    contradiction: dict | None = None


class IntakeForm(BaseModel):
    """Draft intake record for an IT/QA AI intake process. Always a draft: QA decides."""

    form_version: str = "1.0"
    status: Literal["draft_for_qa_review"] = "draft_for_qa_review"
    request_id: str
    created_at: datetime
    title: str
    description: str
    proposer: dict = Field(default_factory=lambda: {"name": None, "department": None, "contact": None})
    classification: dict
    verdict: dict
    required_controls: list[dict]
    open_questions: list[str]
    evidence: list[dict]
    generated_by: dict
    proposer_answers: dict | None = None  # the filled-in intake form (app/intake_form.py), if one was used
    disclaimer: str = (
        "First-pass screening generated by a decision-support tool from public regulatory texts. "
        "Not a compliance decision. The quality unit decides."
    )


class AssessmentResult(BaseModel):
    description: str
    in_scope: bool
    title: str
    out_of_scope_reason: str | None = None
    classification: Classification | None = None
    human_in_the_loop: Literal["yes", "no", "unclear"] | None = None
    grid: GridPosition | None = None
    decision: Decision
    judgments: list[CheckedJudgment] = Field(default_factory=list)
    controls: list[Control] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    intake_form: IntakeForm | None = None
    form: dict | None = None  # the proposer's answers when the structured form was used; None in quick mode
    follow_up: list[FollowUpItem] = Field(default_factory=list)  # filled for "Not yet" results on form input
    follow_up_allowed: bool = False  # True if another round is possible (meta.round < MAX_ROUNDS)
    meta: RunMeta
