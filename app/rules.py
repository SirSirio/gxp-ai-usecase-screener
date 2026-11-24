"""Deterministic rules layer. The model classifies and explains; these rules decide.

Why separate: a verdict like "not acceptable" must be reproducible, testable and reviewable by QA
line by line. An LLM can misread a case, but it cannot override a rule. Each rule has an id that
appears in the result and the audit log, so every verdict traces back to one rule and its source.

The table mirrors docs/LABELING_GUIDE.md §6. Rules are evaluated in order; the first match wins.
rules-1.1: wording and control changes after the independent review (docs/DECISIONS.md D16).
rules-1.2: outcome labels reworded as plain answers (docs/DECISIONS.md D18); logic unchanged.
rules-1.3: safety guards G1/G2 after these rules for form input (app/guards.py, docs/DECISIONS.md D20).
rules-1.4: guard G2 explains each contradiction (answer, reading, outcome of each, how to resolve); outcomes unchanged (W35).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.controls import ANNEX22_LIFECYCLE
from app.schema import Classification

RULES_VERSION = "rules-1.10"  # 1.10: "Non-critical ML" label (Annex 11, ICH Q9) and its sources (W57); 1.9: outcome sources (W56)
_PREV = "rules-1.6"  # 1.6: "Pending clarification" label (SME, W43); 1.5: guard G1b (D038, W41)

# Pattern (SME decision 2026-11-22): "what it is: what to do (which rule)", so proposer, builder and
# decision-maker all get a plain answer. It is a screening answer, not an approval: QA still decides.
VERDICT_LABELS = {
    "out_of_scope": "Not assessed: outside this tool's scope",
    "outside_gmp": "Not GMP: proceed under normal IT rules (no Annex 22)",
    "not_permitted_critical": "Should not proceed: not for GMP-critical use (Annex 22 §1)",
    "needs_more_information": "Pending clarification: update any missing or conflicting details below",
    "not_ai_annex11": "Not ML: proceed as a standard GMP system (Annex 11)",
    "annex22_full": "GMP-critical ML: proceed with full controls (Annex 22)",
    "hitl_required": "Not as described: add human review of each output (Annex 22 §1)",
    "permitted_with_hitl": "Generative AI: proceed if a person approves each output (Annex 22)",
    "permitted_risk_based": "Non-critical ML: proceed with risk-based controls (Annex 11, ICH Q9)",
}

HITL = {"informs", "recommends"}
NO_HITL = {"acts_with_oversight", "acts_autonomously"}

QUESTIONS = {
    "gmp_relevance": "Is the AI output used in a GMP decision, as a GMP record or in a process control (e.g. batch release, QC results, deviation impact, an issued SOP or batch record)? Or does it only support people who then follow the normal GMP process?",
    "model_type": "What kind of model is it: a trained model that is frozen before use, a model that keeps learning in operation, a generative AI / LLM, or fixed rules and scripts?",
    "autonomy": "Do trained, qualified staff review and approve each output before it is used, or does the output take effect automatically?",
}


@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    verdict: str
    explanation: str
    sources: tuple[tuple[str, str], ...]
    controls: tuple[str, ...]
    questions: tuple[str, ...] = field(default_factory=tuple)
    quote_hint: str = ""
    # For each question, the classification field it is about (or "" if none), in the same order.
    # The pipeline turns this into follow-up inputs (intake_form.CLASSIFICATION_INPUTS).
    question_fields: tuple[str, ...] = field(default_factory=tuple)
    # Optional details per question (same order), e.g. a contradiction explained by guard G2 (W35).
    question_details: tuple = field(default_factory=tuple)
    # Where a source's quote must start/stop: ((doc, section, start, end), ...) (W57).
    quote_trim: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class Rule:
    id: str
    verdict: str
    when: Callable[[Classification], bool]
    explanation: str
    sources: tuple[tuple[str, str], ...]
    controls: Callable[[Classification], tuple[str, ...]]
    # Words of the exact source sentence this rule rests on. The quote shown to the user is the
    # sentence that best matches these words, so a rule never displays a neighbouring sentence
    # that happens to share words with its explanation.
    quote_hint: str = ""
    quote_trim: tuple = ()


def _hitl_controls(c: Classification) -> tuple[str, ...]:
    return ("HUMAN_REVIEW",) if c.autonomy in HITL else ()


def _risk_based(c: Classification) -> tuple[str, ...]:
    extra = ("DYNAMIC_LIFECYCLE",) if c.model_type == "dynamic" else ()
    return ("RISK_ASSESSMENT", "CSV", "INTENDED_USE", "ACCEPTANCE", "MONITORING", "CHANGE_CONTROL", "AUDIT_TRAIL",
            "DATA_GOVERNANCE", "DATA_INTEGRITY", "SUPPLIER", "PERIODIC_REVIEW", "PERSONNEL") + extra + ("AI_ACT",)


def _genai_hitl(c: Classification) -> tuple[str, ...]:
    # A look-up assistant ("informs") produces no GMP content, so quality-unit review of output
    # applies only when the model drafts something that people then approve.
    qu = ("QU_REVIEW",) if c.autonomy == "recommends" else ()
    return ("HITL_GENAI",) + qu + ("PQS_ACCOUNTABILITY", "RISK_ASSESSMENT", "CSV", "DATA_INTEGRITY", "SECURITY", "AUDIT_TRAIL",
                                   "CHANGE_CONTROL", "SUPPLIER", "PERIODIC_REVIEW", "PERSONNEL", "AI_ACT")


RULES: tuple[Rule, ...] = (
    Rule("R1-outside-gmp", "outside_gmp",
         lambda c: c.gmp_relevance == "not_gmp",
         "The use is not part of GMP-regulated activities, so Annex 22 and Annex 11 do not apply. General IT and AI governance, the EU AI Act (check whether the use is listed as high-risk) and other obligations such as data protection or the accuracy of regulatory submissions still apply.",
         (("A11", "principle"), ("AIA", "art-6")),
         lambda c: ("AI_ACT", "PERSONNEL"),
         quote_hint="annex applies to all forms of computerised systems used as part of GMP regulated activities; AI systems referred to in Annex III shall be considered to be high-risk"),
    Rule("R2-critical-nonstatic", "not_permitted_critical",
         lambda c: c.gmp_relevance == "critical" and c.model_type in ("generative", "dynamic", "probabilistic"),
         "Draft Annex 22 §1 covers only static, deterministic models in critical GMP applications, and says that dynamic, probabilistic and generative models (including LLMs) should not be used in critical GMP applications. Its human-in-the-loop allowance applies to non-critical use only. This is a reading of the EU draft; FDA's draft credibility guidance instead scales model risk with how much the model influences the decision.",
         (("A22", "1"),),
         lambda c: ("REDESIGN", "RISK_ASSESSMENT", "AI_ACT"),
         quote_hint="Generative AI Large Language Models dynamic models probabilistic output should not be used in critical GMP applications"),
    Rule("R3-unclear", "needs_more_information",
         lambda c: c.gmp_relevance == "unclear" or c.model_type == "unclear",
         "The description does not give enough detail to decide whether the use is GMP-critical or what kind of model it is. Both change the verdict.",
         (("A22", "1"),),
         lambda c: (),
         quote_hint="Artificial Intelligence models used in critical applications with direct impact on patient safety, product quality or data integrity predict classify"),
    Rule("R4-non-ml", "not_ai_annex11",
         lambda c: c.model_type == "non_ml",
         "The logic is explicitly programmed rather than learned from data, so it is not an AI/ML model under Annex 22 §1. It is a computerised system under Annex 11. If a vendor markets it as AI, ask for evidence of how it works (Annex 22 §2.2).",
         (("A22", "1"), ("A11", "principle")),
         lambda c: ("RISK_ASSESSMENT", "CSV", "DATA_INTEGRITY", "AUDIT_TRAIL", "CHANGE_CONTROL", "SUPPLIER", "PERIODIC_REVIEW", "PERSONNEL"),
         quote_hint="machine learning models which have obtained their functionality through training with data rather than being explicitly programmed"),
    Rule("R5-critical-static", "annex22_full",
         lambda c: c.gmp_relevance == "critical" and c.model_type == "static",
         "Draft Annex 22 covers a static, deterministic model in a critical GMP application. It is acceptable with the full Annex 22 lifecycle on top of Annex 11.",
         (("A22", "1"),),
         lambda c: ANNEX22_LIFECYCLE + _hitl_controls(c) + ("RISK_ASSESSMENT", "CSV", "DATA_INTEGRITY", "AUDIT_TRAIL", "SUPPLIER",
                                                              "PQS_ACCOUNTABILITY", "PERIODIC_REVIEW", "PERSONNEL", "FDA_CREDIBILITY", "AI_ACT"),
         quote_hint="applies to static models that do not adapt their performance during use by incorporating new data"),
    Rule("R6-genai-no-hitl", "hitl_required",
         lambda c: c.gmp_relevance == "non_critical" and c.model_type == "generative" and c.autonomy in NO_HITL,
         "Draft Annex 22 §1 says that when generative AI is used in non-critical GMP applications, personnel with adequate qualification and training should always be responsible for checking that each output is suitable (a human in the loop). FDA warning letter 320-26-58 goes further for CGMP activities: AI output must be reviewed and cleared by an authorised quality-unit representative.",
         (("A22", "1"), ("FDA-WL", "ai-use")),
         lambda c: ("HITL_GENAI", "QU_REVIEW", "PQS_ACCOUNTABILITY", "RISK_ASSESSMENT", "SECURITY", "SUPPLIER", "PERSONNEL", "AI_ACT"),
         quote_hint="non-critical GMP applications personnel with adequate qualification and training should always be responsible outputs reviewed and cleared quality unit"),
    Rule("R7-genai-autonomy-unclear", "needs_more_information",
         lambda c: c.gmp_relevance == "non_critical" and c.model_type == "generative" and c.autonomy == "unclear",
         "For generative AI in a GMP context, the verdict depends on whether trained staff review each output, and the description does not state this.",
         (("A22", "1"),),
         lambda c: (),
         quote_hint="non-critical GMP applications personnel with adequate qualification and training should always be responsible human-in-the-loop"),
    Rule("R8-genai-hitl", "permitted_with_hitl",
         lambda c: c.gmp_relevance == "non_critical" and c.model_type == "generative" and c.autonomy in HITL,
         "Draft Annex 22 §1 allows generative AI in non-critical GMP applications when personnel with adequate qualification and training are responsible for checking each output; Annex 22 principles may be considered where applicable.",
         (("A22", "1"),),
         _genai_hitl,
         quote_hint="non-critical GMP applications personnel with adequate qualification and training should always be responsible human-in-the-loop"),
    Rule("R9-noncritical-ml", "permitted_risk_based",
         lambda c: c.gmp_relevance == "non_critical" and c.model_type in ("static", "dynamic", "probabilistic"),
         "A non-critical GMP use of an ML model is outside the mandatory scope of draft Annex 22, which is silent on it. Apply risk-based computerised-system controls (Annex 11, ICH Q9). Using Annex 22 practices where they fit is this tool's recommendation, not a requirement of the draft.",
         (("A22", "1"), ("A11", "1"), ("Q9", "3")),
         _risk_based,
         quote_hint="Artificial Intelligence models used in critical applications with direct impact on patient safety, product quality or data integrity; "
                    "decisions on the extent of validation and data integrity controls should be based on a justified and documented risk assessment; "
                    "level of effort, formality and documentation of the quality risk management process should be commensurate with the level of risk",
         quote_trim=(("A11", "1", "As part of a risk management system", ""), ("Q9", "3", "The level of effort", ""))),
)


# R3 names only what is unclear (feature check F03k, W50).
R3_TEXT = {
    ("gmp_relevance",): "The description does not give enough detail to decide whether the use is GMP-critical. That changes the verdict.",
    ("model_type",): "The description does not give enough detail to decide what kind of model it is. That changes the verdict.",
}
# "Should not proceed" quotes the Annex 22 §1 sentence for the model type at hand, not always the LLM one (W56).
R2_QUOTE = {
    "generative": "Generative AI and Large Language Models LLM such models should not be used in critical GMP applications",
    "dynamic": "dynamic models which continuously and automatically learn and adapt performance during use should not be used in critical GMP applications",
    "probabilistic": "Models with a probabilistic output identical inputs might not provide identical outputs should not be used in critical GMP applications",
}
# Shown instead of the "Pending clarification" label once no follow-up round is left (feature check F06b, W50;
# SME rule W33: after the last round, submit again as a new proposal with a clearer scope).
FINAL_ROUND_LABEL = "Pending clarification: no rounds left, submit again as a new proposal with a clearer scope"


def decide(in_scope: bool, c: Classification | None) -> RuleOutcome:
    if not in_scope or c is None:
        return RuleOutcome("R0-out-of-scope", "out_of_scope",
                           "This tool screens proposed AI use cases against public GMP and AI texts. It does not answer general questions, give legal advice or issue compliance decisions. To screen a specific AI use, describe what the AI does and what happens to its output.",
                           (), ())
    for rule in RULES:
        if rule.when(c):
            fields: tuple[str, ...] = ()
            if rule.verdict == "needs_more_information":
                fields = tuple(f for f in ("gmp_relevance", "model_type", "autonomy") if getattr(c, f) == "unclear")
            elif c.autonomy == "unclear" and rule.verdict in ("annex22_full", "permitted_risk_based", "not_ai_annex11"):
                fields = ("autonomy",)
            explanation = R3_TEXT.get(tuple(f for f in fields if f != "autonomy"), rule.explanation) if rule.id == "R3-unclear"                 else rule.explanation
            hint = R2_QUOTE.get(c.model_type, rule.quote_hint) if rule.id == "R2-critical-nonstatic" else rule.quote_hint
            return RuleOutcome(rule.id, rule.verdict, explanation, rule.sources, tuple(dict.fromkeys(rule.controls(c))),
                               tuple(QUESTIONS[f] for f in fields), quote_hint=hint, question_fields=fields,
                               quote_trim=rule.quote_trim)
    # Unreachable when enums match the guide; kept explicit so a gap fails loudly in tests.
    raise ValueError(f"no rule matched {c}")


def human_in_the_loop(c: Classification | None) -> str | None:
    if c is None:
        return None
    if c.autonomy in HITL:
        return "yes"
    if c.autonomy in NO_HITL:
        return "no"
    return "unclear"


def adaptiveness(c: Classification | None) -> str | None:
    if c is None:
        return None
    if c.model_type == "unclear":
        return "unclear"
    return "adaptive" if c.model_type == "dynamic" else "locked"
