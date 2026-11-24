"""Safety guards: deterministic checks that run after the rules layer, for intake-form input only.

They can only make an outcome safer, never more permissive: when one fires, the outcome becomes
"Not yet" with a question. SME decisions of 2026-11-22 (WORKLOG W27, docs/DECISIONS.md D20):

G1  Human review not stated (dev case D035). The model may not assume that a person checks the
    output. If the proposer ticked "Not sure" or nothing for what happens with the output, and
    "who checks" describes no check, a human-in-the-loop class (informs / recommends) cannot be
    claimed, wherever the review step changes the outcome (it does not for a GMP-critical LLM, which
    is "Should not proceed" with or without review, so that clear "no" is kept). Accepted trade-off: when the proposer wrote the review step in another field, the tool
    asks a needless question, which is never dangerous.
    G1b (dev case D038, SME decision 2026-11-23): the same when "a person approves each output" is
    ticked but "who checks" is empty or only says who receives the output ("QA receives it"):
    receiving or reading is not a check (form-1.2), so the tick alone does not establish a review step.
    A "who checks" text that only describes receiving also counts as no check for G1 itself.
G2  The ticks point to a stricter outcome (dev case D032). The outcome is worked out a second time
    with the proposer's ticks in place of the model's reading. Ticks may only make the outcome
    stricter: if the model's outcome would be a dangerous error compared with the tick outcome
    (app/safety.py), the answer is "Not yet" and the contradiction is the question. If the model's
    reading is the stricter one, it stands (ticks are self-assessment and are often wrong).

Guards do not run when the model judged the text out of scope ("no proposal, no assessment").
"""
from __future__ import annotations

import re

from app.rules import QUESTIONS, RuleOutcome, decide
from app.safety import is_dangerous
from app.schema import Classification

NOT_YET = "needs_more_information"

# Ticked answers that carry a classification. "vendor_unknown" and "not_sure" carry none.
TICKS = {
    "ai_type": ("model_type", {"llm": "generative", "trained_fixed": "static", "probabilistic": "probabilistic",
                               "self_learning": "dynamic", "rules": "non_ml"}),
    "output_use": ("autonomy", {"informs": "informs", "person_approves": "recommends",
                                "auto_monitored": "acts_with_oversight", "auto_unchecked": "acts_autonomously"}),
}
VALUE_TEXT = {
    "critical": "GMP-critical", "non_critical": "GMP, non-critical", "not_gmp": "not GMP",
    "static": "a trained model, frozen in use", "dynamic": "a model that keeps learning", "generative": "generative AI / an LLM",
    "probabilistic": "a probabilistic model", "non_ml": "fixed rules, not ML",
    "informs": "information only, a person decides", "recommends": "a person approves each output",
    "acts_with_oversight": "takes effect automatically, people monitor", "acts_autonomously": "takes effect automatically, nobody checks",
}
FIELD_QUESTION = {"gmp_relevance": "gmp_impact", "model_type": "ai_type", "autonomy": "output_use"}
NO_CHECK = re.compile(r"^\s*$|\b(?:not (?:yet )?(?:decided|defined|clear|sure|known)|tbd|to be (?:decided|defined)|n/?a|unknown|nobody|no one|none|don'?t know)\b", re.I)
# Words that only describe getting the output (G1b, D038). A check word anywhere means a check is described.
RECEIVE = re.compile(r"\b(?:receives?|received|receiving|gets?|getting|got|(?:is|are|gets?) sent|sent (?:to|out)|e-?mail(?:ed|s)?|"
                     r"forwarded|distributed|notified|cc'?d|copied|reads?|reading|sees?|has access|have access|can see|"
                     r"looks? at|informed|available to)\b", re.I)
CHECK = re.compile(r"\b(?:check|review|approv|verif|sign|compar|assess|confirm|inspect|validat|evaluat|correct|reject|"
                   r"accept|releas|signs? off|second[- ]person|4[- ]eyes|four[- ]eyes|tjek|kontroll|godkend)\w*", re.I)


def receive_only(text: str) -> bool:
    """True when the text says who gets the output but describes no check (form-1.2: receiving is not a check)."""
    return bool(RECEIVE.search(text or "")) and not CHECK.search(text or "")


def tick_values(form: dict) -> dict[str, str]:
    """Classification values the proposer's ticks state; fields without an informative tick are left out."""
    out = {}
    impact = (form.get("gmp_impact") or {}).get("choice")
    if impact == "yes":
        out["gmp_relevance"] = "critical"
    elif impact == "not_gmp":  # form-1.2
        out["gmp_relevance"] = "not_gmp"
    elif impact == "no":
        areas = set(form.get("areas") or [])
        out["gmp_relevance"] = "not_gmp" if areas and areas <= {"business"} else "non_critical"
    for qid, (field, mapping) in TICKS.items():
        choice = (form.get(qid) or {}).get("choice")
        if choice in mapping:
            out[field] = mapping[choice]
    return out


def _not_yet(rule_id: str, explanation: str, questions: tuple[str, ...], source: tuple[str, str], hint: str,
             fields: tuple[str, ...]) -> RuleOutcome:
    return RuleOutcome(rule_id, NOT_YET, explanation, (source,), (), questions, quote_hint=hint, question_fields=fields)


def check(form: dict | None, in_scope: bool, c: Classification | None, outcome: RuleOutcome) -> RuleOutcome | None:
    """The guarded outcome, or None if no guard fires."""
    if form is None or not in_scope or c is None or outcome.verdict == NOT_YET:
        return None

    # G1: a human check cannot be assumed, where it decides the outcome (a critical LLM is "no" either way)
    use = (form.get("output_use") or {}).get("choice")
    check_text = " ".join(filter(None, [form.get("who_checks"), (form.get("output_use") or {}).get("explain")]))
    review_decides = (c.autonomy in ("informs", "recommends")
                      and decide(True, c.model_copy(update={"autonomy": "unclear"})).verdict != outcome.verdict)
    if review_decides and use in (None, "not_sure") and (NO_CHECK.search(form.get("who_checks") or "") or receive_only(check_text)):
        return _not_yet(
            "G1-review-not-stated",
            "The form does not state whether a person checks the output before it is used, and that decides the "
            "outcome. The tool does not assume a review step that is not described.",
            (QUESTIONS["autonomy"],), ("A22", "3.3"),
            "human-in-the-loop model used to give an input to a decision made by a human operator", ("autonomy",))
    # G1b (D038, SME 2026-11-23): "a person approves each output" is ticked, but the form only says who
    # receives the output. Receiving or reading it is not a check (form-1.2 help text), so the tick alone
    # does not establish a human in the loop.
    if review_decides and use == "person_approves" and (NO_CHECK.search(form.get("who_checks") or "") or receive_only(check_text)):
        return _not_yet(
            "G1-check-not-described",
            "You selected that a trained person checks and approves each output, but the form only states who "
            "receives it. Receiving or reading the output is not a check, and whether each output is checked decides "
            "the outcome. State who checks it, against what, and where the check is recorded.",
            ("Who checks each output before it is used, against what, and where is the check recorded?",), ("A22", "3.3"),
            "human-in-the-loop model used to give an input to a decision made by a human operator", ("autonomy",))

    # G2: the ticks point to a stricter outcome than the model's reading
    ticks = tick_values(form)
    if not ticks:
        return None
    by_ticks = Classification(**{**c.model_dump(), **ticks})
    tick_outcome = decide(True, by_ticks).verdict
    if tick_outcome == outcome.verdict or not is_dangerous(tick_outcome, outcome.verdict):
        return None
    from app.intake_form import QUESTIONS_BY_ID, option_label
    from app.rules import VERDICT_LABELS

    # The fields whose tick alone makes the outcome stricter; if none does on its own, all differing fields.
    differing = [f for f, v in ticks.items() if getattr(c, f) != v]
    single = {f: decide(True, c.model_copy(update={f: ticks[f]})).verdict for f in differing}
    conflicts = tuple(f for f in differing if is_dangerous(single[f], outcome.verdict)) or tuple(differing)
    asks, details = [], []
    for f in conflicts:
        qid = FIELD_QUESTION[f]
        label = QUESTIONS_BY_ID[qid]["label"]
        asks.append(f"Two of your answers point in different directions: \"{label}\" and your description. Which one is right?")
        details.append({
            "question_id": qid,
            "your_answer": option_label(qid, (form.get(qid) or {}).get("choice")),
            "your_answer_means": VALUE_TEXT[ticks[f]],
            "description_reads_as": VALUE_TEXT.get(getattr(c, f), getattr(c, f)),
            "outcome_if_your_answer_is_right": VERDICT_LABELS[single[f]],
            "outcome_if_the_description_is_right": VERDICT_LABELS[outcome.verdict],
            "how_to_resolve": RESOLVE[f],
        })
    return RuleOutcome(
        "G2-ticks-stricter", NOT_YET,
        "Some of your answers in the form contradict your description, and the two readings lead to different "
        "outcomes. Until you resolve this, the tool does not select the more permissive reading. Each contradiction "
        "is explained below.",
        (("A22", "1"),), (), tuple(asks),
        quote_hint="Artificial Intelligence models used in critical applications with direct impact on patient safety, product quality or data integrity",
        question_fields=conflicts, question_details=tuple(details))


# How to resolve a contradiction per field (shown to the proposer with guard G2, W35).
RESOLVE = {
    "gmp_relevance": "If the GMP decision rests on the AI output (it decides, is the evidence the decision rests on, "
                     "becomes or fills in a GMP record, sets the process, or decides which items people do not "
                     "check, even if a person confirms it), keep \"Yes, directly\" and explain how in the task "
                     "description. If people decide on their own evidence through the normal GMP process (for "
                     "example investigation and change control), choose \"No, only indirectly\". If the use has "
                     "nothing to do with GMP work, choose \"No, not used for GMP work\".",
    "model_type": "If it really is this kind of AI, state this in the task description (for example who trained the "
                  "model and on what data). If the description is right, change the answer to match it.",
    "autonomy": "If a person really checks every output before it is used, state who checks it and how in \"Who "
                "checks the output\". If the output takes effect without that check, change the answer to match.",
}
