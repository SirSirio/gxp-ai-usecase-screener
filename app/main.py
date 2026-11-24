"""FastAPI app: intake form, quick mode and JSON API.

Run: .venv/Scripts/python -m uvicorn app.main:app --reload

Pages:
- `/`        landing page: what the tool does, how, and what it does not do;
- `/submit`  the structured intake form (main path), POSTs to `/assess`;
- `/how-it-works` the process flow and the decision tree (app/how_it_works.py), checked against the rules;
- `/sources` the official documents the knowledge base is built from (app/ingest/sources.py);
- `/quick`   the old single text box (not linked anywhere; accuracy may be lower).
"""
from __future__ import annotations

import json
import re

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, model_validator

from starlette.concurrency import run_in_threadpool

from app.assessors import get_assessor
from app.audit import AuditLog
from app.config import APP_VERSION, ROOT, get_settings
from app.icons import icon
from app.ingest.sources import SOURCES, SOURCES_BY_ID
from app.intake_form import (
    FOLLOW_UP, MAX_FOLLOW_UP, MAX_LENGTH, MAX_ROUNDS, MIN_LENGTH, QUESTIONS, QUESTIONS_BY_ID, FormError, form_to_text, normalize_form,
    option_label,
)
from app.pipeline import AssessmentFailed, run_assessment
from app.retrieval.index import get_index
from app.rules import FINAL_ROUND_LABEL, VERDICT_LABELS
from app.section_page import section_view
from app.schema import AssessmentResult

app = FastAPI(title="GxP AI Use-Case Assistant", version=APP_VERSION)
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")

# Quick mode (/quick) keeps the old single text box and its free-text examples.
QUICK_EXAMPLES = [
    "We want to use ChatGPT to write first drafts of cleaning SOPs. QA reviews and approves every SOP in the eDMS as usual.",
    "A camera system with a trained neural network inspects filled vials and automatically rejects defective ones on the line. The model is locked after validation.",
    "An AI agent writes the weekly deviation trend summary for site management and emails it out automatically every Monday; nobody checks it before it goes out.",
    "Use a large language model to decide whether a deviation is minor, major or critical, so batches can be released faster.",
    "HR wants an AI tool to screen CVs and rank candidates for operator roles.",
]

# Sections of the intake form page. Presentation only: questions, options and help texts come from
# app/intake_form.py (QUESTIONS). Every question id appears exactly once here (tested).
FORM_SECTIONS = [
    ("The use case", ["title", "what", "ai_type", "areas"]),
    ("How the output is used", ["gmp_impact", "output_use", "who_checks", "replaces_check"]),
    ("Data and supplier", ["data", "source"]),
]

# Example forms that prefill the intake form. Only option values defined in QUESTIONS (tested).
FORM_EXAMPLES = [
    {"name": "LLM drafts cleaning SOPs", "form": {
        "title": "LLM drafts of cleaning SOPs",
        "what": "A chatbot writes first drafts of cleaning SOPs for production equipment from our SOP template and the "
                "equipment manual. The author edits the draft, then it goes through the normal document review.",
        "areas": ["manufacturing", "qa"],
        "gmp_impact": {"choice": "no", "explain": "Only first drafts. The author rewrites them and the SOP becomes a GMP document only after the normal review and approval."},
        "ai_type": {"choice": "llm", "explain": "A general-purpose chatbot."},
        "output_use": {"choice": "person_approves", "explain": ""},
        "who_checks": "The SOP author edits every draft; QA reviews and approves every SOP in the eDMS before it is issued.",
        "replaces_check": {"choice": "no", "explain": "The normal document review stays as it is."},
        "data": ["internal"],
        "source": {"choice": "cloud_service", "explain": ""},
    }},
    {"name": "Vision model rejects vials", "form": {
        "title": "Camera inspection of filled vials",
        "what": "A camera system with a trained neural network inspects every filled vial on the fill-finish line and "
                "automatically rejects vials with particles, cracks or a wrong fill level.",
        "areas": ["manufacturing"],
        "gmp_impact": {"choice": "yes", "explain": "It makes the accept or reject decision for each vial."},
        "ai_type": {"choice": "trained_fixed", "explain": "The model is locked after validation. Updates come as a new, validated version."},
        "output_use": {"choice": "auto_monitored", "explain": "Rejected vials go straight to the reject bin."},
        "who_checks": "Operators check the reject rate every shift; QA reviews rejects during batch record review.",
        "replaces_check": {"choice": "yes", "explain": "It replaces the manual visual inspection of every vial."},
        "data": ["confidential"],
        "source": {"choice": "vendor_installed", "explain": ""},
    }},
    {"name": "Unchecked deviation summary", "form": {
        "title": "Weekly deviation trend email",
        "what": "An AI agent reads the deviations logged in the past week, writes a trend summary and emails it to "
                "site management every Monday.",
        "areas": ["qa"],
        "gmp_impact": {"choice": "not_sure", "explain": "Management may use it to set priorities. Each deviation is still handled in the QMS."},
        "ai_type": {"choice": "llm", "explain": ""},
        "output_use": {"choice": "auto_unchecked", "explain": ""},
        "who_checks": "Nobody reviews the summary before it is sent.",
        "replaces_check": {"choice": "no", "explain": "Each deviation is still handled in the QMS as before."},
        "data": ["confidential"],
        "source": {"choice": "cloud_service", "explain": ""},
    }},
]
REQUEST_ID = re.compile(r"^[0-9a-f]{12}$")

# Groups on the /sources page. Presentation only; every document in SOURCES appears exactly once (tested).
SOURCE_GROUPS = [
    ("EU GMP guidelines (EudraLex Volume 4)", ["A22", "A11", "A11D", "CH4D"]),
    ("International guideline", ["Q9"]),
    ("EU law", ["AIA"]),
    ("US FDA", ["FDA-CRED", "FDA-DP", "FDA-WL"]),
]


class AssessRequest(BaseModel):
    """Either a free-text `description` (quick mode) or a structured intake `form` (app/intake_form.py)."""

    description: str | None = Field(None, min_length=20, max_length=4000)
    form: dict | None = None  # may include "follow_up": [{"question", "answer"}] in a follow-up round
    provider: str | None = None  # offline | gemini | azure_openai; default: GXP_PROVIDER
    round: int = Field(1, ge=1, le=MAX_ROUNDS)
    parent_request_id: str | None = Field(None, pattern=r"^[0-9a-f]{12}$")

    @model_validator(mode="after")
    def one_input(self) -> "AssessRequest":
        if (self.description is None) == (self.form is None):
            raise ValueError("send either 'description' or 'form'")
        if self.form is not None:
            try:
                self.form = normalize_form(self.form)
            except FormError as exc:
                raise ValueError(str(exc)) from exc
        return self


def _model_name(model_id: str) -> str:
    """'gemini-3.5-flash-lite' -> 'Gemini 3.5 Flash-Lite' (display only; the exact id is logged with every result)."""
    return "-".join(" ".join(w.capitalize() if w.isalpha() else w for w in part.split()) for part in
                    model_id.replace("-", " ", 2).split("-"))


def available_providers() -> dict[str, str]:
    """Classifiers the user can choose, with a label. Only providers with credentials are offered."""
    import os

    # Labels say what each classifier is, not how well it scored (owner feedback, W52; results are in the docs).
    options = {"offline": "Keyword baseline (a fixed checklist, no AI)"}
    if os.getenv("GEMINI_API_KEY"):
        options["gemini"] = f"{_model_name(os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'))} (AI classifier)"
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        options["azure_openai"] = f"Azure OpenAI {os.getenv('AZURE_OPENAI_DEPLOYMENT', '')} (AI classifier)"
    return options


def default_provider() -> str:
    p = get_settings().provider
    return p if p in available_providers() else "offline"


def _resolve_provider(provider: str | None) -> str:
    provider = provider or default_provider()
    if provider not in available_providers():
        raise HTTPException(status_code=422, detail=f"unknown or unconfigured provider {provider!r}")
    return provider


# ---------------------------------------------------------------- form helpers
def _fields_to_form(data) -> dict:
    """HTML form fields -> form dict (not yet validated). A single choice posts `<id>` and `<id>_explain`."""
    form: dict = {}
    for q in QUESTIONS:
        qid = q["id"]
        if q["type"] in ("text", "textarea"):
            form[qid] = data.get(qid) or ""
        elif q["type"] == "multi":
            form[qid] = [v for v in data.getlist(qid) if v]
        else:
            form[qid] = {"choice": data.get(qid) or None, "explain": data.get(f"{qid}_explain") or ""}
    # follow-up answers: pairs fu_q_<n> (the question, sent back as a hidden field) and fu_a_<n> (the reply);
    # earlier rounds' answers are posted again the same way, so they accumulate
    numbers = sorted({int(k[5:]) for k in data.keys() if k.startswith("fu_q_") and k[5:].isdigit()})
    answers = [{"question": data.get(f"fu_q_{n}") or "", "answer": data.get(f"fu_a_{n}") or ""} for n in numbers]
    if any(a["answer"].strip() for a in answers):
        form[FOLLOW_UP] = answers
    return form


def _round_info(data) -> tuple[int, str | None]:
    """The follow-up round (hidden field `round`, default 1) and the request it answers (`parent_request_id`)."""
    try:
        rnd = int(data.get("round") or 1)
    except ValueError:
        rnd = 1
    parent = data.get("parent_request_id") or None
    if parent is not None and not REQUEST_ID.match(parent):
        parent = None
    return rnd, parent


def _safe_form(raw: dict | None = None) -> dict:
    """A form to show again after an error: known values kept, unknown ones dropped."""
    raw, out = raw or {}, {}
    for q in QUESTIONS:
        v, allowed = raw.get(q["id"]), {o["value"] for o in q.get("options", [])}
        if q["type"] in ("text", "textarea"):
            out[q["id"]] = v.strip() if isinstance(v, str) else ""
        elif q["type"] == "multi":
            out[q["id"]] = [x for x in (v or []) if x in allowed]
        else:
            v = v if isinstance(v, dict) else {}
            out[q["id"]] = {"choice": v.get("choice") if v.get("choice") in allowed else None,
                            "explain": v.get("explain") if isinstance(v.get("explain"), str) else ""}
    # Answers to the tool's follow-up questions are kept too, so a failed follow-up round loses nothing
    # (open item from W33). Only well-formed text pairs, cut to the form's limits.
    fu = raw.get(FOLLOW_UP)
    if isinstance(fu, list):
        out[FOLLOW_UP] = [{"question": a["question"][:600], "answer": a["answer"][:MAX_LENGTH["explain"]]}
                          for a in fu[:MAX_FOLLOW_UP] if isinstance(a, dict)
                          and isinstance(a.get("question"), str) and isinstance(a.get("answer"), str) and a["question"].strip()]
    return out


def _page_context(provider: str | None = None, **extra) -> dict:
    return {"providers": available_providers(), "selected": provider or default_provider(),
            "error": None, "error_detail": None, "field_errors": {}, **extra}


def _answered(q: dict, v) -> bool:
    return bool(v.get("choice") or v.get("explain")) if q["type"] == "single" else bool(v)


def _form_page(request: Request, form: dict | None = None, status_code: int = 200, round: int = 1,
               parent_request_id: str | None = None, **extra):
    """The intake form. On an error in a follow-up round, `round` and `parent_request_id` are carried as hidden
    fields and the follow-up answers (form["follow_up"]) are shown again, so a resubmission stays in the same round."""
    form = _safe_form(form)
    ctx = _page_context(form=form, questions=QUESTIONS_BY_ID, sections=FORM_SECTIONS, examples=FORM_EXAMPLES,
                        follow_up=form.get(FOLLOW_UP, []), round=round, parent_request_id=parent_request_id,
                        answered={q["id"]: _answered(q, form[q["id"]]) for q in QUESTIONS}, page="submit", **extra)
    return templates.TemplateResponse(request, "submit.html", ctx, status_code=status_code)


def _quick_page(request: Request, description: str = "", status_code: int = 200, **extra):
    ctx = _page_context(description=description, examples=QUICK_EXAMPLES, **extra)
    return templates.TemplateResponse(request, "quick.html", ctx, status_code=status_code)


def _asset_version() -> str:
    """Cache-busting ?v= for the stylesheet and script: changes whenever either file changes (checked on
    every page render, so a CSS edit shows up even without a server restart)."""
    static = ROOT / "app" / "static"
    return format(max((static / f).stat().st_mtime_ns for f in ("style.css", "app.js", "how_it_works.js")) // 1_000_000, "x")


def _verdict_tone(verdict: str) -> str:
    return {"not_permitted_critical": "stop", "hitl_required": "stop", "needs_more_information": "ask",
            "out_of_scope": "neutral", "outside_gmp": "neutral"}.get(verdict, "go")


def _public_demo() -> bool:
    """Read at render time (not import time), so tests can switch it with config.use_settings."""
    return get_settings().public_demo


templates.env.globals.update(verdict_tone=_verdict_tone, verdict_labels=VERDICT_LABELS, final_round_label=FINAL_ROUND_LABEL, icon=icon,
                             option_label=option_label, all_questions=QUESTIONS, questions_by_id=QUESTIONS_BY_ID,
                             min_length=MIN_LENGTH, max_length=MAX_LENGTH, max_rounds=MAX_ROUNDS,
                             sources_by_id=SOURCES_BY_ID, asset_v=_asset_version, public_demo=_public_demo)


def _result_page(request: Request, result: AssessmentResult, provider: str):
    others = {k: v for k, v in available_providers().items() if k != provider}
    return templates.TemplateResponse(request, "result.html", {"r": result, "provider": provider,
                                                               "provider_label": available_providers()[provider],
                                                               "other_providers": others})


def _failure(exc: AssessmentFailed) -> dict:
    """Page context for a failed assessment: a plain message, and the technical reason for "details" (W45)."""
    return {"error": str(exc), "error_detail": f"{exc.detail} (request {exc.request_id})" if exc.detail
            else f"Request {exc.request_id}"}


# ---------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Landing page: what the tool does, for whom, how, and what it does not do."""
    return templates.TemplateResponse(request, "landing.html", {"page": "home"})


@app.get("/how-it-works", response_class=HTMLResponse)
def how_it_works(request: Request):
    """The process flow and the decision tree. The tree is checked against rules.decide() (tests)."""
    from app import how_it_works as hiw

    view = hiw.build()
    view["data"]["icons"] = {k: str(icon(k, v)) for k, v in (("info-circle", ""), ("check", ""), ("arrow-right", "crumb-sep"),
                                                             ("circle-check", "outcome-icon"), ("ban", "outcome-icon"),
                                                             ("help-circle", "outcome-icon"), ("circle-minus", "outcome-icon"))}
    return templates.TemplateResponse(request, "how_it_works.html", {
        "page": "how", **view, "steps": hiw.flow(), "audit": hiw.AUDIT, "loop_info": hiw.LOOP_INFO, "presets": hiw.PRESETS})


@app.get("/submit", response_class=HTMLResponse)
def submit(request: Request):
    return _form_page(request)


@app.get("/sources", response_class=HTMLResponse)
def sources(request: Request):
    """The official documents behind every citation, with their status and the official source link."""
    groups = [(title, [SOURCES_BY_ID[d] for d in ids]) for title, ids in SOURCE_GROUPS]
    return templates.TemplateResponse(request, "sources.html", {"page": "sources", "groups": groups,
                                                                "count": len(SOURCES)})


@app.get("/section", response_class=HTMLResponse)
def section_page(request: Request, doc: str = "", section: str = "", q: str | None = None):
    """One regulatory section as a readable page (the JSON form stays at /api/section). `q` is the
    quoted passage from a result; the sentences it covers are highlighted."""
    view = section_view(get_index(), doc, section, q)
    if view is None:
        return templates.TemplateResponse(request, "section.html", {"page": "section", "view": None, "doc": doc,
                                                                    "section": section}, status_code=404)
    return templates.TemplateResponse(request, "section.html", {"page": "section", "view": view})


@app.post("/assess", response_class=HTMLResponse)
async def assess_form(request: Request):
    """Main path. The form is validated against QUESTIONS, rendered to labelled text with
    form_to_text() for the classifier, and stored, audited and exported with the result."""
    data = await request.form()
    provider = _resolve_provider(data.get("provider"))
    raw = _fields_to_form(data)
    rnd, parent = _round_info(data)
    if not 1 <= rnd <= MAX_ROUNDS:
        return _form_page(request, raw, 422, provider=provider,
                          error=f"This use case has already had {MAX_ROUNDS} rounds of questions. Please submit it again "
                                "as a new proposal with a clearer scope: describe what the AI does and what happens with its output.")
    same_round = {"round": rnd, "parent_request_id": parent}  # an error page keeps the follow-up round
    try:
        form = normalize_form(raw)
    except FormError as exc:
        q = QUESTIONS_BY_ID.get(exc.field or "")
        if q and q["type"] in ("text", "textarea"):
            return _form_page(request, raw, 422, provider=provider, field_errors={exc.field: str(exc)}, **same_round)
        if exc.field == FOLLOW_UP:
            return _form_page(request, raw, 422, provider=provider, field_errors={FOLLOW_UP: str(exc)}, **same_round)
        return _form_page(request, raw, 422, provider=provider, **same_round,
                          error=f"The form contained an answer this tool does not know ({exc}). Please choose again.")
    try:
        # In a worker thread: the assessment waits on the LLM for seconds (and on retries), and running it on
        # the event loop froze every other page, even the stylesheet, until it finished (W55).
        result = await run_in_threadpool(run_assessment, form_to_text(form), assessor=get_assessor(provider), form=form,
                                         round=rnd, parent_request_id=parent)
    except AssessmentFailed as exc:
        return _form_page(request, form, 502, provider=provider, **same_round, **_failure(exc))
    return _result_page(request, result, provider)


@app.get("/quick", response_class=HTMLResponse)
def quick(request: Request):
    """Quick mode: the old single text box. Deliberately not linked from the main page."""
    return _quick_page(request)


@app.post("/quick", response_class=HTMLResponse)
def assess_quick(request: Request, description: str = Form(...), provider: str | None = Form(None)):
    description = description.strip()
    provider = _resolve_provider(provider)
    if not 20 <= len(description) <= 4000:
        return _quick_page(request, description, 422, provider=provider,
                           error="Please describe the use case in 20 to 4000 characters.")
    try:
        result = run_assessment(description, assessor=get_assessor(provider))
    except AssessmentFailed as exc:
        return _quick_page(request, description, 502, provider=provider, **_failure(exc))
    return _result_page(request, result, provider)


# ---------------------------------------------------------------- API
@app.post("/api/assess", response_model=AssessmentResult)
def assess_api(body: AssessRequest):
    provider = _resolve_provider(body.provider)
    description = form_to_text(body.form) if body.form is not None else body.description
    try:
        return run_assessment(description, assessor=get_assessor(provider), form=body.form,
                              round=body.round, parent_request_id=body.parent_request_id)
    except AssessmentFailed as exc:
        raise HTTPException(status_code=502, detail={"message": str(exc), "kind": exc.kind, "detail": exc.detail,
                                                     "request_id": exc.request_id})


def _load_result(request_id: str) -> dict:
    if not REQUEST_ID.match(request_id):
        raise HTTPException(status_code=400, detail="invalid request id")
    path = get_settings().results_dir / f"{request_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="result not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/results/{request_id}")
def get_result(request_id: str):
    return _load_result(request_id)


@app.get("/api/results/{request_id}/intake.json")
def get_intake(request_id: str):
    intake = _load_result(request_id).get("intake_form")
    if not intake:
        raise HTTPException(status_code=404, detail="no intake form for out-of-scope requests")
    return Response(json.dumps(intake, indent=2, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="ai-intake-{request_id}.json"'})


@app.get("/api/section")
def get_section(doc: str, section: str):
    sec = get_index().get_section(doc, section)
    if sec is None:
        raise HTTPException(status_code=404, detail="section not found")
    return sec


@app.get("/api/health")
def health():
    ix = get_index()
    return {"status": "ok", "app_version": APP_VERSION, "default_provider": default_provider(),
            "available_providers": list(available_providers()),
            "corpus_version": ix.corpus_version, "chunks": len(ix.chunks), "documents": ix.doc_ids,
            "dense_retrieval": ix.faiss is not None}


@app.get("/api/audit/verify")
def audit_verify():
    ok, bad = AuditLog(get_settings().audit_dir / "audit.jsonl").verify()
    return JSONResponse({"ok": ok, "first_bad_line": bad})
