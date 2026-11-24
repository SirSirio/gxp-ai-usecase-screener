# GxP AI Use-Case Assistant — project rules

Portfolio project: a first-pass EU GMP screening tool for proposed AI use cases.
Spec: kept outside the repo.

## Data policy (non-negotiable)
- Public regulatory documents only (`data/raw/`, listed in `app/ingest/sources.py`).
- No company data, no internal company documents, no client names in code, prompts, test cases or logs.
- Personal accounts only. Secrets live in `.env` (git-ignored), never in the repo.

## Stack
- Python 3.10, FastAPI, Jinja2, Pydantic v2. Virtual env: `.venv` (`.venv/Scripts/python`).
- Retrieval: hybrid TF-IDF + dense (fastembed `BAAI/bge-small-en-v1.5`) in FAISS, fused with reciprocal rank fusion.
- LLM providers behind `app/llm/base.py::ChatClient`. `offline` = deterministic keyword baseline, needs no key.

## Architecture rules
- The **rules layer** (`app/rules.py`) decides verdicts and hard constraints. The model only classifies and explains.
- Every judgment must cite a chunk id that exists in the index; the citation check drops unsupported claims.
- Invalid model output is rejected and logged, never shown.
- Every request is written to the audit log (`data/audit/audit.jsonl`, hash-chained).
- Label definitions live in `docs/LABELING_GUIDE.md`; code enums must match it.

## Test-data independence
- `eval/testset.jsonl` is held out: do not read it while tuning the offline classifier or prompts. Tune on `eval/devset.jsonl` only.

## Commands
- Build index: `.venv/Scripts/python -m app.ingest.build_index`
- Run app: `.venv/Scripts/python -m uvicorn app.main:app --reload`
- Tests: `.venv/Scripts/python -m pytest -q`
- Eval: `.venv/Scripts/python -m eval.run_eval --set test --provider offline`

## Docs
`docs/PLAN.md` (steps + status) · `docs/WORKLOG.md` (what was done, per task: update it with every change) · `docs/DECISIONS.md` (why) · `docs/ARCHITECTURE.md` · `docs/WALKTHROUGH.md` (learning guide) · `docs/VALIDATION_NOTE.md`
