"""The intake form: the one definition of every question, option and help text.

Used by the review page (scripts/build_review_page.py), the test-case writers (eval cases are
filled-in forms) and, later, the web app's form. Keep it the single source of truth: two copies
of the same list drift apart (see WORKLOG W16).

Design rules agreed with the SME (2026-11-22):
- open answers where they help, choices where they make the user think about the right parameter;
- every option has a plain-language explanation, shown behind an (i) icon;
- "Not sure" is always allowed: it maps to "unclear" and to a question back to the proposer;
- the answers are evidence for the classifier, never the classification itself (self-assessment bias).
"""
from __future__ import annotations

FORM_VERSION = "form-1.2"  # 1.2: regulation review (W37): not-GMP and probabilistic options, clearer wording, new question replaces_check

QUESTIONS: list[dict] = [
    {
        "id": "title",
        "label": "Short title",
        "type": "text",
        "help": "A few words, for example 'LLM drafts of cleaning SOPs'. Enter one use case per form.",
        "feeds": ["intake form"],
    },
    {
        "id": "what",
        "label": "What should the AI do?",
        "type": "textarea",
        # A22 §3.1 ("the specific tasks it is designed to assist or automate"); FDA-CRED IV.A.1-2 (the question
        # addressed, and other information used besides the model output): feeds the direct/indirect reading (W37).
        "help": "Describe the task in your own words: what goes in, what comes out, who uses it, which question or decision it helps with, and what else people use alongside the AI output (their own data, tests, investigation).",
        "feeds": ["all fields"],
    },
    {
        "id": "areas",
        "label": "Where will it be used?",
        "type": "multi",
        "help": "Select every area that applies.",
        "options": [
            {"value": "manufacturing", "label": "Manufacturing / production", "help": "Upstream, downstream, fill-finish, the production floor, and the records created there."},
            {"value": "qc_lab", "label": "QC laboratory", "help": "Testing of raw materials, in-process samples, and finished product; laboratory data and results."},
            {"value": "qa", "label": "QA / quality systems", "help": "Deviations, CAPA, change control, batch record review, release, audits, and document control."},
            {"value": "msat", "label": "MSAT / tech transfer / process development", "help": "Bringing client processes into the facility, scale-up, and process characterisation."},
            {"value": "engineering", "label": "Engineering / maintenance / facilities", "help": "Equipment, utilities, calibration, maintenance planning, and environmental monitoring systems."},
            {"value": "supply_chain", "label": "Supply chain / warehouse", "help": "Planning, purchasing, receiving, storage, and dispatch of materials and product."},
            {"value": "regulatory", "label": "Regulatory affairs", "help": "Submissions, regulatory correspondence, dossier, and CMC documentation."},
            {"value": "business", "label": "Business functions (HR, finance, IT, sales, legal)", "help": "Functions outside GMP-regulated activities. IT work on GMP systems and GMP training count as GMP: tick the GMP area too."},
            {"value": "other", "label": "Other", "help": "Describe it in the task description."},
        ],
        "feeds": ["gmp_relevance (context)"],
    },
    {
        "id": "gmp_impact",
        # Wording follows draft Annex 22 §1: critical = "direct impact on patient safety, product quality or data
        # integrity"; non-critical = "do not have direct impact" (SME decision W35). The line is what the decision is
        # based on, not whether a person looks at the output (D017).
        "label": "Does the AI output directly affect a batch, a GMP record, a QC result, a release or a process setting?",
        "type": "single",
        "explain": True,
        # form-1.2 (W37, regulation review): "directly" also covers deciding what is NOT checked (A22 §3.2 decision
        # output "accept"/"reject"; A11D 8.1 relying on the system to notify) and filling in a GMP record (CH4D 4.24);
        # a separate "not GMP" answer, so non-GMP ideas are not forced into "indirectly" (that caused a G2 loop).
        "help": "Ask yourself what the GMP decision is based on. If it rests on the AI output, the impact is direct, even when a person confirms it. It is indirect only if people base the decision on their own evidence.",
        "options": [
            {"value": "yes", "label": "Yes, directly", "help": "The output decides a GMP decision or is the evidence it rests on, becomes or fills in a GMP record, sets the process, or decides which items people do not check, even if a person confirms it. For example: accept/reject (including units the AI passes without a human look), release, a deviation classification that QA confirms, results copied into LIMS, an AI-written SOP issued as is, or a setpoint."},
            {"value": "no", "label": "No, only indirectly", "help": "The output gives ideas or information. Before anything changes, people check it against their own evidence (data, experiments, investigation) through the normal GMP process. For example: improvement ideas that go through investigation and change control, search, summaries, or drafts that people rewrite and approve."},
            {"value": "not_gmp", "label": "No, not used for GMP work", "help": "The use has nothing to do with GMP-regulated activities. For example: HR, finance, sales, or IT helpdesk."},
            {"value": "not_sure", "label": "Not sure", "help": "That is fine. Explain what you know, and QA will help decide."},
        ],
        "feeds": ["gmp_relevance"],
    },
    {
        "id": "ai_type",
        "label": "What kind of AI is it?",
        "type": "single",
        "explain": True,
        "help": "Select the closest match. If it is a supplier's product, describe what they told you.",
        "options": [
            # form-1.2 (W37): wording from A22 §1 and the glossary ("Static - Frozen model", "identical inputs, identical
            # outputs", "continuously and automatically learn ... during use"); a probabilistic option, which A22 §1 names.
            {"value": "llm", "label": "Generative AI: writes or creates text, images or code (LLM)", "help": "Writes, summarises, translates, or answers questions. Examples: ChatGPT, Microsoft Copilot, Gemini, Claude, or an 'AI assistant' or 'AI agent' built on them."},
            {"value": "trained_fixed", "label": "Trained model, frozen: same input, same result", "help": "Learned from historical data, then frozen and used as is; new versions are tested and released. Examples: camera inspection of vials, a soft sensor predicting cell density, or anomaly detection on sensor data."},
            {"value": "probabilistic", "label": "Trained model whose answer can differ for the same input", "help": "Running it twice on exactly the same data can give a different result (for example, it uses random sampling). Ask the builder or supplier if you are unsure."},
            {"value": "self_learning", "label": "Updates itself in use: new versions go live without a test-and-release step", "help": "It retrains or adapts automatically from new data during use, and the new behaviour is used straight away. A model that is retrained but only goes live after testing and approval is a frozen model."},
            {"value": "rules", "label": "Rules or automation (not learning)", "help": "Follows fixed if-then rules written by people: scripts, robotic process automation (RPA), or statistical control limits. It is sometimes marketed as 'AI' although nothing is learned."},
            {"value": "vendor_unknown", "label": "A supplier's 'AI feature', details unknown", "help": "The supplier calls it AI, but you do not know how it works or whether it learns. Ask the supplier whether it was trained on data and how new versions are released."},
            {"value": "not_sure", "label": "Not sure", "help": "Describe what it does; the tool and QA will work out the type."},
        ],
        "feeds": ["model_type"],
    },
    {
        "id": "output_use",
        "label": "What happens with the output?",
        "type": "single",
        "explain": True,
        # form-1.2 (W37): dev cases showed "QA gets it" ticked as "a person approves"; A22 §1 (qualified personnel
        # responsible for each output), FDA-WL ("reviewed and cleared"), AIA art-14(4)(a, d).
        "help": "Describe the normal day-to-day flow, not the exception. Think of every output, including the ones the AI passes. Receiving or reading the output is not a check.",
        "options": [
            {"value": "informs", "label": "Information only: our own staff then do the task themselves", "help": "Search results, summaries, dashboards, or suggestions that a person may or may not use. Do not select this if the output goes directly to a client, a system, or a document."},
            {"value": "person_approves", "label": "A trained person checks and approves each output before it is used", "help": "Nothing is used until a qualified person has checked that specific output; they can change or reject it."},
            {"value": "auto_monitored", "label": "Used automatically; people spot-check or watch trends and alerts", "help": "The output goes straight into a system, a document, to a client, or into the process; people look at samples, alerts, or trends."},
            {"value": "auto_unchecked", "label": "Takes effect automatically; nobody checks individual outputs", "help": "The output is used directly and no one reviews it before or after."},
            {"value": "not_sure", "label": "Not sure", "help": "Explain what you expect; this decides which controls apply."},
        ],
        "feeds": ["autonomy"],
    },
    {
        "id": "who_checks",
        "label": "Who checks the output, and how?",
        "type": "textarea",
        # A22 §3.3 (responsibility of the operator), §10.5 (records), AIA art-26(2) (competence, training, authority).
        "help": "Name the role, whether they check every output, what they check it against, and where the check is recorded. For example: 'QA reviews every SOP in the eDMS', 'the analyst re-integrates if needed', 'monthly spot check of 5 %', or 'nobody'.",
        "feeds": ["autonomy"],
    },
    {
        # form-1.2 (W37, SME decision): Annex 11 Principle ("no resultant decrease in product quality, process control
        # or quality assurance" when a system replaces a manual operation); A22 §4.3 (at least as good as the process
        # it replaces); A11D 8.1. Catches review by exception, units passed without a look, reduced sampling.
        "id": "replaces_check",
        "label": "Does the AI replace or reduce a check or step that people do today?",
        "type": "single",
        "explain": True,
        "help": "If yes, name the step that is dropped or reduced.",
        "options": [
            {"value": "yes", "label": "Yes, a step is dropped or reduced", "help": "For example: QA reviews only the items the AI flags, a second test is skipped, inspectors see only the rejects, or fewer samples are taken."},
            {"value": "no", "label": "No, everything done today stays; the AI adds to it", "help": "All existing checks and steps continue as before."},
            {"value": "not_sure", "label": "Not sure", "help": "Describe what changes in the current process."},
        ],
        "feeds": ["gmp_relevance", "autonomy", "acceptance criteria"],
    },
    {
        "id": "data",
        "label": "What data goes into it?",
        "type": "multi",
        "help": "Select every type of data the AI will receive.",
        "options": [
            {"value": "public", "label": "Public information", "help": "Published guidelines, public websites, and open literature."},
            {"value": "internal", "label": "Internal, not confidential", "help": "General internal information without business or product secrets."},
            {"value": "confidential", "label": "Confidential company data", "help": "SOPs, batch and process data, QC results, deviations, and internal reports."},
            {"value": "client", "label": "Client data", "help": "A sponsor's process descriptions, batch records, specifications, or results."},
            {"value": "personal", "label": "Personal data", "help": "Names, employee data, CVs, patient or donor data, or data on how individual staff perform. If the AI evaluates people or assigns them work, state this: it can be high-risk under the EU AI Act."},
            {"value": "not_sure", "label": "Not sure", "help": "Describe the inputs in the task description."},
        ],
        "feeds": ["security, AI Act, data policy controls"],
    },
    {
        "id": "source",
        "label": "Who provides it?",
        "type": "single",
        "explain": True,
        "help": "This decides which supplier controls apply.",
        "options": [
            {"value": "in_house", "label": "Built in-house", "help": "Developed by our own team, on our own infrastructure."},
            {"value": "vendor_installed", "label": "Bought from a supplier, installed with us", "help": "Software or equipment from a vendor, running on our systems (for example, a CDS add-on or an inspection machine)."},
            {"value": "cloud_service", "label": "Cloud or online service", "help": "Runs on the provider's servers, for example ChatGPT, Microsoft Copilot, or a SaaS platform. It is useful to know who decides when the model version changes, and whether we can test it first."},
            {"value": "not_sure", "label": "Not sure", "help": "Describe what you know."},
        ],
        "feeds": ["supplier controls"],
    },
]

QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONS}


def option_label(question_id: str, value: str) -> str:
    q = QUESTIONS_BY_ID[question_id]
    return next((o["label"] for o in q.get("options", []) if o["value"] == value), value)


class FormError(ValueError):
    """A filled-in form does not match QUESTIONS. `field` names the question (None: the whole form)."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


MIN_LENGTH = {"what": 20}  # the only required answer; everything else is optional but helps
MAX_LENGTH = {"text": 200, "textarea": 4000, "explain": 1000}


def _text(value, qid: str, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise FormError(f"'{qid}' must be text", qid)
    value = value.replace("\r\n", "\n").strip()
    if len(value) > limit:
        raise FormError(f"'{qid}' is longer than {limit} characters", qid)
    return value


def normalize_form(form: dict) -> dict:
    """Validate a filled-in form and return it in the canonical shape used across the project.

    Missing answers become "", [] or {"choice": None, "explain": ""}. Unknown questions or option
    values raise FormError. Multi-choice answers are returned in the order of QUESTIONS.
    """
    if not isinstance(form, dict):
        raise FormError("the form must be an object")
    unknown = sorted(set(form) - set(QUESTIONS_BY_ID) - {FOLLOW_UP})
    if unknown:
        raise FormError(f"unknown question(s): {', '.join(unknown)}")
    out: dict = {}
    for q in QUESTIONS:
        qid, v = q["id"], form.get(q["id"])
        allowed = [o["value"] for o in q.get("options", [])]
        if q["type"] in ("text", "textarea"):
            out[qid] = _text(v, qid, MAX_LENGTH[q["type"]])
        elif q["type"] == "multi":
            v = [] if v is None else v
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise FormError(f"'{qid}' must be a list of option values", qid)
            bad = [x for x in v if x not in allowed]
            if bad:
                raise FormError(f"'{qid}': unknown option(s) {bad}; allowed: {allowed}", qid)
            out[qid] = [x for x in allowed if x in v]
        else:
            v = {} if v is None else v
            if not isinstance(v, dict) or set(v) - {"choice", "explain"}:
                raise FormError(f"'{qid}' must be {{'choice': value or null, 'explain': text}}", qid)
            choice = v.get("choice") or None
            if choice is not None and choice not in allowed:
                raise FormError(f"'{qid}': unknown option {choice!r}; allowed: {allowed}", qid)
            out[qid] = {"choice": choice, "explain": _text(v.get("explain"), qid, MAX_LENGTH["explain"])}
    for qid, n in MIN_LENGTH.items():
        if len(out[qid]) < n:
            raise FormError(f"Please describe the task in at least {n} characters.", qid)
    answers = _follow_up(form.get(FOLLOW_UP))
    if answers:  # only present after a follow-up round, so first-round forms keep their exact shape
        out[FOLLOW_UP] = answers
    return out


# ---------------------------------------------------------------- follow-up answers (WORKLOG W33)
# After a "Not yet" result the proposer can correct the form and answer the tool's free-text
# questions, then resubmit. The free-text answers travel inside the form, so the classifier, the
# result, the intake record and the audit log all see them. Corrections to ticked answers are made in
# the form fields themselves, so the rules and the safety guards see the corrected ticks.
FOLLOW_UP = "follow_up"
# Which form questions can settle each classification field (used to show the right inputs next to a question).
CLASSIFICATION_INPUTS = {"gmp_relevance": ("gmp_impact",), "model_type": ("ai_type",), "autonomy": ("output_use", "who_checks")}
MAX_FOLLOW_UP = 10
MAX_ROUNDS = 3  # the first submission plus two follow-up rounds; then "resubmit with a clearer scope"


def _follow_up(v) -> list[dict]:
    if v in (None, []):
        return []
    if not isinstance(v, list) or len(v) > MAX_FOLLOW_UP:
        raise FormError(f"'{FOLLOW_UP}' must be a list of at most {MAX_FOLLOW_UP} answers", FOLLOW_UP)
    out = []
    for item in v:
        if not isinstance(item, dict) or set(item) - {"question", "answer"}:
            raise FormError(f"each '{FOLLOW_UP}' item must be {{'question': text, 'answer': text}}", FOLLOW_UP)
        q = _text(item.get("question"), FOLLOW_UP, 600)
        a = _text(item.get("answer"), FOLLOW_UP, MAX_LENGTH["explain"])
        if q and a:  # an unanswered question is simply left out
            out.append({"question": q, "answer": a})
    return out


def form_to_text(form: dict) -> str:
    """Render a filled-in form as labelled text for the classifier (keeps question context)."""
    lines = []
    for q in QUESTIONS:
        v = form.get(q["id"])
        if v in (None, "", [], {}):
            continue
        if q["type"] == "multi":
            v = ", ".join(option_label(q["id"], x) for x in v)
        elif q["type"] == "single":
            choice = option_label(q["id"], v.get("choice", "")) if v.get("choice") else ""
            v = choice + (f". {v['explain']}" if v.get("explain") else "")
            if not v:  # unanswered single choice: {"choice": None, "explain": ""}
                continue
        lines.append(f"{q['label']}\n{v}")
    if form.get(FOLLOW_UP):
        lines.append("Answers to the tool's follow-up questions\n" + "\n".join(
            f"Q: {x['question']}\nA: {x['answer']}" for x in form[FOLLOW_UP]))
    return "\n\n".join(lines)
