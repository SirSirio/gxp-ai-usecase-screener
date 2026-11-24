"""Build the SME review page for the evaluation cases.

Run: .venv/Scripts/python scripts/build_review_page.py
Out: review/review_cases.html (self-contained; open it in a browser, no server needed)

Everything the page shows comes from the code, so it cannot drift from the app:
- form questions, options and (i) help texts from app/intake_form.py;
- outcome labels and the outcome for every label combination from app/rules.py
  (the page recomputes the outcome live when the reviewer changes a label);
- section titles for key sources from the built index.
Decisions are saved in the browser and exported as JSON; scripts/apply_review.py applies them.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.intake_form import FORM_VERSION, QUESTIONS  # noqa: E402
from app.rules import VERDICT_LABELS, decide  # noqa: E402
from app.schema import FIELD_VALUES, Classification  # noqa: E402

CASE_FILES = [ROOT / "eval" / "v2" / "dev_cases.jsonl", ROOT / "eval" / "v2" / "test_cases.jsonl"]
TEMPLATE = ROOT / "scripts" / "review_template.html"
OUT = ROOT / "review" / "review_cases.html"

FIELD_LABELS = {
    "gmp_relevance": {"critical": "GMP-critical", "non_critical": "GMP, non-critical", "not_gmp": "Not GMP", "unclear": "Unclear"},
    "model_type": {"static": "Static ML model", "dynamic": "Dynamic / self-learning", "generative": "Generative AI / LLM",
                   "probabilistic": "Probabilistic ML", "non_ml": "Not ML (rules)", "unclear": "Unclear"},
    "autonomy": {"informs": "AI informs, person decides", "recommends": "Person approves each output",
                 "acts_with_oversight": "Acts, people monitor", "acts_autonomously": "Acts, nobody checks", "unclear": "Unclear"},
}
DOC_NAMES = {"A22": "Annex 22 (draft)", "A11": "Annex 11 (2011)", "A11D": "Annex 11 (draft)", "CH4D": "Chapter 4 (draft)",
             "Q9": "ICH Q9(R1)", "AIA": "EU AI Act", "FDA-CRED": "FDA AI credibility guidance (draft)",
             "FDA-DP": "FDA AI discussion paper", "FDA-WL": "FDA warning letter 320-26-58"}


def load_cases(files: list[Path]) -> list[dict]:
    cases = []
    for f in files:
        if f.exists():
            cases += [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    return cases


def outcome_table() -> dict:
    """Outcome code for every (gmp, model, autonomy) combination, generated from the rules layer."""
    return {"|".join(combo): decide(True, Classification(gmp_relevance=combo[0], model_type=combo[1], autonomy=combo[2])).verdict
            for combo in itertools.product(*FIELD_VALUES.values())}


def section_titles() -> dict:
    path = ROOT / "data" / "index" / "sections.json"
    if not path.exists():
        return {}
    return {f"{s['doc_id']}|{s['section']}": s["title"] for s in json.loads(path.read_text(encoding="utf-8"))}


def build(case_files: list[Path] | None = None, out: Path = OUT) -> Path:
    cases = load_cases(case_files or CASE_FILES)
    data = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "form_version": FORM_VERSION,
        "questions": QUESTIONS,
        "verdict_labels": VERDICT_LABELS,
        "field_values": {k: list(v) for k, v in FIELD_VALUES.items()},
        "field_labels": FIELD_LABELS,
        "outcomes": outcome_table(),
        "doc_names": DOC_NAMES,
        "section_titles": section_titles(),
        "cases": cases,
    }
    payload = json.dumps(data, ensure_ascii=False)
    data_hash = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()[:10]
    html = TEMPLATE.read_text(encoding="utf-8")
    # Escape sequences that could end or confuse the inline <script> ("</script>", "<!--").
    safe = payload.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = html.replace("/*__DATA__*/null", safe).replace("__DATA_HASH__", data_hash)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"{len(cases)} cases -> {out.relative_to(ROOT)} (data {data_hash})")
    return out


if __name__ == "__main__":
    files = [Path(a) for a in sys.argv[1:]] or None
    build(files)
