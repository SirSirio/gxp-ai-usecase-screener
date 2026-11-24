"""Offline baseline: classify with keyword cues, cite with evidence lookups.

Deliberately simple and transparent. It exists so that
1. the whole pipeline runs without any API key;
2. the LLM has a baseline to beat (if the LLM cannot beat keywords, it is not worth its cost);
3. the evaluation harness can be tested deterministically.

Cue lists were written from general domain knowledge and tuned on eval/devset.jsonl only.
Two modes: free text (quick mode, `classify`) and the structured intake form (`classify_form`,
"baseline B": the proposer's ticks first, keywords on their free-text answers only).
offline-1.2: form mode added (WORKLOG W22); free-text mode unchanged.
offline-1.3: follow-up answers are read as free text (WORKLOG W33).
offline-1.4: citations come from the source map (app/source_map.py, D24); classification unchanged.
"""
from __future__ import annotations

import difflib
import re

from app import source_map
from app.assessors.base import AssessorOutput
from app.models import ScoredChunk
from app.tools import ToolBox

PROMPT_VERSION = "offline-1.4"


def _rx(*patterns: str) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I)


# Generative-AI products people name instead of writing "LLM". ONE list, used by both the scope check
# and the model-type check: when these were two separate lists, "Claude" and "Gemini" were in one
# but not the other, and such cases were refused as "no AI use described".
GENAI_PRODUCTS = (
    "chatgpt", "gpt", "openai", "claude", "anthropic", "gemini", "bard", "copilot", "mistral", "llama",
    "deepseek", "grok", "perplexity", "qwen", "notebooklm",
)
TYPO_TARGETS = tuple(p for p in GENAI_PRODUCTS if len(p) >= 6)  # short names are too risky to fuzzy-match
_PRODUCTS = r"\b(?:" + "|".join(GENAI_PRODUCTS) + r")(?:[- ]?\d[\w.]*)?\b"  # also "GPT-5", "Claude 4"

# ---------------------------------------------------------------- scope
OUT_OF_SCOPE = _rx(
    r"\bare we (?:compliant|allowed|legal)\b", r"\bconfirm (?:that )?(?:we|our|it)\b.*\bcompliant\b", r"\bis (?:it|this) legal\b",
    r"\bsue\b", r"\blawsuit\b", r"\blegal advice\b", r"\bliab(?:le|ility)\b",
    r"\bpoem\b", r"\bjoke\b", r"\brecipe\b", r"\bweather\b", r"\bself-assessment\b", r"\bcover letter\b", r"\bmy (?:cv|resume)\b",
)
QUESTION_ONLY = _rx(r"^\s*(?:what|who|when|why|how|can you|could you|please)\b.*\b(?:explain|summari[sz]e|mean|changed|difference|stand for)\b",
                    r"^\s*what is\b", r"^\s*who (?:wrote|is)\b")
PROPOSAL = _rx(r"\bwe (?:want|would like|'d like|plan|are planning|are looking)\b", r"\bwants? (?:an?|to)\b", r"\bour\b",
               r"\b(?:could|can) (?:an?|the) (?:ai|model|tool|agent|llm)\b", r"\bproposal\b", r"\bpilot\b", r"\buse (?:an? )?(?:ai|llm|model)\b")
AI_CUES = _rx(_PRODUCTS, r"\bai\b", r"artificial intelligence", r"\bmodel\b", r"machine learning", r"\bml\b", r"\bllm", r"chat ?gpt",
              r"chatbot", r"\bassistant\b", r"\bagent\b", r"neural", r"algorithm", r"predict", r"classif", r"automat", r"\bsmart\b",
              r"vision", r"\bnlp\b", r"learns?\b", r"trained", r"generative", r"\bgenai\b", r"\bbot\b", r"\brpa\b", r"\bscript")

# ---------------------------------------------------------------- GMP relevance
NOT_GMP = _rx(r"\bhr\b", r"recruit", r"candidate", r"\bcv\b", r"payroll", r"finance", r"invoice", r"expense", r"marketing", r"\bsales\b",
              r"commercial forecast", r"laptop", r"\bvpn\b", r"outlook", r"printer", r"helpdesk", r"\bit (?:support|team|wants)\b",
              r"employee", r"canteen", r"travel", r"budget", r"social media", r"press release", r"customer relationship")
GMP_CONTEXT = _rx(r"\bgmp\b", r"\bbatch", r"deviation", r"\bcapa\b", r"\bqc\b", r"\bqa\b", r"\blab\b", r"laborator", r"manufactur",
                  r"production", r"\bsop", r"validation", r"cleaning", r"bioreactor", r"fermentation", r"cell culture", r"tech(?:nology)? transfer",
                  r"\bmsat\b", r"warehouse", r"\blims\b", r"\bmes\b", r"\beqms\b", r"change control", r"quality", r"excipient", r"\bmedia\b",
                  r"\bhplc\b", r"\bcds\b", r"environmental monitoring", r"aseptic", r"fill(?:ing)?\b", r"vials?\b", r"specification", r"\bcoa\b",
                  r"\bqp\b", r"inspection", r"sterile", r"client", r"sponsor")
CRITICAL = _rx(r"\brelease", r"disposition", r"\bqp\b", r"certif", r"\breject", r"accept(?:/| or )reject", r"visual inspection",
               r"in-process control", r"\bipc\b", r"real-time release", r"\brtrt\b", r"(?:qc|test|lab) results?", r"identity test", r"\bid test",
               r"sterility", r"endotoxin", r"\bcqa", r"control (?:the|our) (?:bioreactor|process|feed)", r"set ?points?", r"feed rate",
               r"sign(?:s)? off", r"approve (?:the )?batch", r"(?:batch|production) record review", r"\boos\b", r"integrat\w* (?:the )?peaks",
               r"(?:classify|classif\w*) (?:the )?(?:deviations?|defects?|containers?)", r"\bdispens", r"\bcoa results\b")
NON_CRITICAL_TASK = _rx(r"\bdraft", r"training material", r"summar", r"\bsearch", r"\bfind\b", r"look up", r"\btrend", r"dashboard", r"\bplan\b",
                        r"planning", r"schedul", r"\bsuggest", r"gap assessment", r"meeting", r"minutes", r"translat", r"knowledge", r"overview")

# ---------------------------------------------------------------- model type
NON_ML = _rx(r"rule[s-]? ?(?:based|configured|engine)?", r"\bconfigured\b", r"keywords?\b", r"if[- ]then", r"\bmacro", r"\bscript", r"\brpa\b",
             r"fixed limits?", r"control limits", r"\bspc\b", r"formula", r"lookup table", r"drop-?down")
DYNAMIC = _rx(r"learns? (?:on its own|by itself|continuously|from (?:new|every|each))", r"keeps? (?:learning|retraining)", r"continuous(?:ly)? learn",
              r"retrain\w* (?:itself|automatically|every|nightly|each|weekly|daily|on)", r"self-learning", r"\badapts?\b", r"online learning",
              r"updates? itself", r"reinforcement", r"learns? on its own every")
GENERATIVE = _rx(_PRODUCTS, r"\bllm", r"chat ?gpt", r"chatbot", r"generative", r"\bgen-?ai\b", r"\bai agent",
                 r"\bagents?\b", r"language model", r"\bdraft\w*", r"\bwrites?\b", r"summari[sz]", r"answers? (?:questions|sponsors|users)",
                 r"\bassistant\b", r"translat")
PROBABILISTIC = _rx(r"monte carlo", r"stochastic", r"sampling-based", r"non-deterministic", r"different answer each time")
STATIC = _rx(r"\btrained\b", r"\blocked\b", r"\bfrozen\b", r"classification model", r"\bvision\b", r"camera", r"neural network", r"\bcnn\b",
             r"regression", r"soft sensor", r"predictive model", r"anomaly detection", r"random forest", r"xgboost", r"machine learning",
             r"\bml model", r"\bmodel (?:predicts|classifies|detects)", r"image recognition", r"\bstatic\b", r"deep learning")

# Abbreviations are expanded before matching, so "ML" counts exactly like "machine learning".
# Case-sensitive on purpose: "ML" is machine learning, "mL" is millilitre (common in fermentation texts).
ABBREVIATIONS = {
    "ML": "machine learning", "AI/ML": "machine learning", "DL": "deep learning", "NN": "neural network",
    "LLM": "large language model", "LLMs": "large language models", "GenAI": "generative AI", "Gen AI": "generative AI",
    "NLP": "natural language processing", "RPA": "robotic process automation", "SPC": "statistical process control",
    "IPC": "in-process control", "RTRT": "real-time release testing", "PAT": "process analytical technology",
    "MBR": "master batch record", "EBR": "electronic batch record", "BMR": "batch manufacturing record",
    "BPR": "batch production record", "OOS": "out of specification", "CQA": "critical quality attribute",
    "CPP": "critical process parameter", "QU": "quality unit", "QP": "qualified person",
}
_ABBR = re.compile(r"(?<![\w/])(" + "|".join(re.escape(a) for a in sorted(ABBREVIATIONS, key=len, reverse=True)) + r")(?![\w/])")


def _product_typos(text: str) -> list[str]:
    """Product names written with a typo ('Cahtgpt', 'ChatGTP', 'Gemnini') -> the correct name.

    Only words of 6+ letters, and only very close matches (similarity >= 0.85), so ordinary words
    stay untouched: 'clause' vs 'claude' scores 0.83 and is ignored. test_offline_typo_matching_has_
    no_false_positives_in_corpus runs this over every word of the 9 regulatory documents.
    """
    found = []
    for word in re.findall(r"[A-Za-z][A-Za-z-]{5,}", text):
        w = word.lower().replace("-", "")
        if w in GENAI_PRODUCTS:
            continue
        match = difflib.get_close_matches(w, TYPO_TARGETS, n=1, cutoff=0.85)
        if match:
            found.append(match[0])
    return found


def expand_abbreviations(text: str) -> str:
    """Append the full form of abbreviations and the correct name of misspelt AI products.

    'Static ML ...' -> '... [machine learning]'; 'We use Cahtgpt ...' -> '... [chatgpt]'.
    """
    found = dict.fromkeys([ABBREVIATIONS[m.group(1)] for m in _ABBR.finditer(text)] + _product_typos(text))
    return text + (" [" + "; ".join(found) + "]" if found else "")

# ---------------------------------------------------------------- autonomy
AUTONOMOUS = _rx(r"\bautomatically\b", r"without (?:any )?(?:further|human|manual|review|check)", r"\bdirectly\b", r"straight (?:into|to)",
                 r"\bitself\b", r"no human", r"24/7", r"go(?:es)? out", r"\bauto-", r"no (?:one|review)", r"releases the")
OVERSIGHT = _rx(r"spot[- ]check", r"\bsample(?:s|d)? (?:of|the)\b", r"monitor(?:ed|s)? by", r"can override", r"intervene", r"periodic(?:ally)? review",
                r"alerts? (?:the|a) (?:supervisor|operator)")
REVIEW = _rx(r"\breview(?:s|ed)?\b", r"\bapprov", r"\bconfirm", r"\bchecks?\b", r"go(?:es)? through", r"line by line", r"\bfinali[sz]e",
             r"\badjusts?\b", r"\bdecides?\b", r"\bverif", r"\bsigns?\b(?! off)", r"\bedits?\b")
NEGATED_REVIEW = _rx(r"\b(?:nobody|no one|no-one|never|without|not)\b[^.;]{0,25}?\b(?:review|check|approv|verif|look)\w*")
INFORMS = _rx(r"\bsearch", r"\bfind\b", r"look up", r"dashboard", r"overview", r"answers? (?:questions|staff)", r"\btrend", r"for information",
              r"\bsummar")


def _hits(rx: re.Pattern, text: str) -> list[str]:
    return sorted({m.group(0).strip().lower() for m in rx.finditer(text)})


def _scope_problem(text: str) -> str | None:
    """Why the text is not a use case to screen, or None. `text` must already be expanded."""
    if OUT_OF_SCOPE.search(text):
        return "The request asks for legal advice, a compliance verdict or something unrelated to an AI use case."
    if QUESTION_ONLY.search(text) and not PROPOSAL.search(text):
        return "This is a general question, not a proposed AI use case. Describe the use you want to screen."
    return None


def _gmp_from_text(text: str) -> tuple[str, list[str]]:
    not_gmp, gmp, crit, noncrit = _hits(NOT_GMP, text), _hits(GMP_CONTEXT, text), _hits(CRITICAL, text), _hits(NON_CRITICAL_TASK, text)
    if not_gmp and not gmp:
        return "not_gmp", not_gmp
    if crit:
        return "critical", crit
    if gmp:
        return "non_critical", gmp + noncrit
    return "unclear", []


def _model_from_text(text: str) -> tuple[str, list[str]]:
    # most specific signal wins
    for value, rx in (("dynamic", DYNAMIC), ("generative", GENERATIVE), ("probabilistic", PROBABILISTIC), ("static", STATIC)):
        h = _hits(rx, text)
        if h:
            return value, h
    h = _hits(NON_ML, text)
    return ("non_ml", h) if h else ("unclear", [])


def _autonomy_from_text(text: str) -> tuple[str, list[str]]:
    # an explicit human review step beats "automatically"
    rev, auto, over, inf = _hits(REVIEW, text), _hits(AUTONOMOUS, text), _hits(OVERSIGHT, text), _hits(INFORMS, text)
    neg = _hits(NEGATED_REVIEW, text)
    if neg:  # "nobody checks it" must not count as a review step
        return "acts_autonomously", neg
    if over:
        return "acts_with_oversight", over
    if rev:
        return "recommends", rev
    if auto:
        return "acts_autonomously", auto
    if inf:
        return "informs", inf
    return "unclear", []


def classify(text: str) -> tuple[bool, str | None, dict[str, str], dict[str, list[str]]]:
    """Return (in_scope, reason, classification, cues) for a free-text use-case description (quick mode)."""
    text = expand_abbreviations(text)
    problem = _scope_problem(text)
    if problem:
        return False, problem, {}, {}
    if not AI_CUES.search(text):
        return False, "No AI or automation use is described.", {}, {}
    cues: dict[str, list[str]] = {}
    gmp_rel, cues["gmp_relevance"] = _gmp_from_text(text)
    model, cues["model_type"] = _model_from_text(text)
    autonomy, cues["autonomy"] = _autonomy_from_text(text)
    return True, None, {"gmp_relevance": gmp_rel, "model_type": model, "autonomy": autonomy}, cues


# ---------------------------------------------------------------- structured intake form (baseline B)
# The proposer's ticks are read first; keywords run only on the free-text answers (never on the question
# wording, which contains trigger words such as "a QC result, a release"), and only where the tick is
# "Not sure" or blank. A static checklist: it trusts self-assessment, so it is expected to fail on the
# cases where the ticks contradict the description. Mapping agreed with the SME (WORKLOG, decision B).
TICK_MAP = {
    "ai_type": ("model_type", {"llm": "generative", "trained_fixed": "static", "probabilistic": "probabilistic",
                               "self_learning": "dynamic", "rules": "non_ml", "vendor_unknown": "unclear"}),
    "output_use": ("autonomy", {"informs": "informs", "person_approves": "recommends",
                                "auto_monitored": "acts_with_oversight", "auto_unchecked": "acts_autonomously"}),
}
NON_GMP_AREAS = {"business"}


def form_free_text(form: dict, scope_only: bool = False) -> str:
    """The proposer's own words: title, task and (unless scope_only) every explanation. No question text."""
    from app.intake_form import QUESTIONS

    parts = [form.get("title") or "", form.get("what") or ""]
    if not scope_only:
        for q in QUESTIONS:
            v = form.get(q["id"])
            if isinstance(v, dict):
                parts.append(v.get("explain") or "")
            elif q["id"] == "who_checks":
                parts.append(v or "")
        parts += [x["answer"] for x in form.get("follow_up") or []]  # answers only, never the question text
    return "\n".join(p for p in parts if p)


def classify_form(form: dict) -> tuple[bool, str | None, dict[str, str], dict[str, list[str]]]:
    """Baseline B: (in_scope, reason, classification, cues) for a filled-in intake form."""
    from app.intake_form import option_label

    text = expand_abbreviations(form_free_text(form))
    problem = _scope_problem(expand_abbreviations(form_free_text(form, scope_only=True)))
    if problem:
        return False, problem, {}, {}
    ai_tick = (form.get("ai_type") or {}).get("choice")
    if not AI_CUES.search(text) and ai_tick not in TICK_MAP["ai_type"][1]:
        return False, "No AI or automation use is described.", {}, {}

    def ticked(qid: str) -> str | None:
        choice = (form.get(qid) or {}).get("choice")
        return None if choice in (None, "not_sure") else choice

    def tick_cue(qid: str) -> list[str]:
        return [f"ticked: {option_label(qid, ticked(qid))}"]

    cls, cues = {}, {}
    impact = ticked("gmp_impact")
    if impact == "yes":
        cls["gmp_relevance"], cues["gmp_relevance"] = "critical", tick_cue("gmp_impact")
    elif impact == "not_gmp":  # form-1.2
        cls["gmp_relevance"], cues["gmp_relevance"] = "not_gmp", tick_cue("gmp_impact")
    elif impact == "no":
        areas = set(form.get("areas") or [])
        if areas and areas <= NON_GMP_AREAS:
            cls["gmp_relevance"], cues["gmp_relevance"] = "not_gmp", tick_cue("gmp_impact") + ["area: business functions only"]
        elif not areas and _gmp_from_text(text)[0] == "not_gmp":
            cls["gmp_relevance"], cues["gmp_relevance"] = _gmp_from_text(text)
        else:
            cls["gmp_relevance"], cues["gmp_relevance"] = "non_critical", tick_cue("gmp_impact")
    else:
        cls["gmp_relevance"], cues["gmp_relevance"] = _gmp_from_text(text)

    for qid, fallback in (("ai_type", _model_from_text), ("output_use", _autonomy_from_text)):
        field, mapping = TICK_MAP[qid]
        choice = ticked(qid)
        if choice in mapping:
            cls[field], cues[field] = mapping[choice], tick_cue(qid)
        else:
            cls[field], cues[field] = fallback(text)
    return True, None, {k: cls[k] for k in ("gmp_relevance", "model_type", "autonomy")}, cues


WHY = {
    "critical": "the AI output feeds a GMP decision, record or control ({cues})",
    "non_critical": "the use is in a GMP setting ({cues}) but the output supports people rather than deciding",
    "not_gmp": "the use is outside GMP-regulated activities ({cues})",
    "static": "the description points to a trained model used as is ({cues})",
    "dynamic": "the model keeps learning or retraining in operation ({cues})",
    "generative": "it is a generative AI / LLM-type tool ({cues})",
    "probabilistic": "the output can differ for identical inputs ({cues})",
    "non_ml": "the logic is configured or programmed rather than learned ({cues})",
    "informs": "the tool provides information and people decide ({cues})",
    "recommends": "a person reviews or approves each output ({cues})",
    "acts_with_oversight": "outputs take effect while people monitor ({cues})",
    "acts_autonomously": "outputs take effect without a human check ({cues})",
}


def _pick_evidence(value: str, passages: list[ScoredChunk]) -> str | None:
    """The source map's main paragraph for this answer that is among the passages ("unclear": none)."""
    shown = {p.chunk.id for p in passages}
    return next((cid for cid in source_map.allowed(value) if cid in shown), None)


def make_title(text: str, limit: int = 80) -> str:
    """First sentence of the description, cut at a word boundary."""
    first = re.split(r"(?<=[.!?])\s", re.sub(r"\s+", " ", text.strip()), maxsplit=1)[0].rstrip(" .")
    if len(first) <= limit:
        return first or "Untitled use case"
    return first[:limit].rsplit(" ", 1)[0].rstrip(" ,;") + "…"


class OfflineAssessor:
    name = "offline"
    prompt_version = PROMPT_VERSION

    def assess(self, description: str, passages: list[ScoredChunk], tools: ToolBox, form: dict | None = None) -> AssessorOutput:
        if form is not None:  # structured intake form: ticks first (baseline B)
            in_scope, reason, cls, cues = classify_form(form)
            title = make_title(form.get("what") or description)
        else:  # quick mode: free text
            in_scope, reason, cls, cues = classify(description)
            title = make_title(description)
        if not in_scope:
            return AssessorOutput({"in_scope": False, "out_of_scope_reason": reason, "title": title}, model="keyword-rules")
        judgments = []
        for field, value in cls.items():
            cid = _pick_evidence(value, passages)
            found = ", ".join(f"'{c}'" for c in cues.get(field, [])[:4])
            why = WHY.get(value, "").format(cues=found) if found else ""
            rationale = f"Keyword baseline: {why}." if why else "Keyword baseline: the description does not give enough information for this field."
            judgments.append({"field": field, "value": value, "rationale": rationale, "citations": [cid] if cid else []})
        return AssessorOutput(
            {"in_scope": True, "title": title, "classification": cls, "judgments": judgments, "open_questions": []},
            model="keyword-rules",
        )
