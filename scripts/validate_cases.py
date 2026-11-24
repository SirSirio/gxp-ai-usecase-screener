"""Validate evaluation cases written as filled-in intake forms (eval/v2/*.jsonl).

Run: .venv/Scripts/python scripts/validate_cases.py eval/v2/test_cases.jsonl [more files]

Checks: JSON per line, required keys, unique ids, form answers use the values defined in
app/intake_form.py, label enums match docs/LABELING_GUIDE.md, the expected outcome equals what the
rules layer derives from the expected labels, key-source doc ids exist, out-of-scope cases carry no
classification. Prints a distribution table. Exit code 1 if any error.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.intake_form import QUESTIONS  # noqa: E402
from app.rules import decide  # noqa: E402
from app.schema import FIELD_VALUES, Classification  # noqa: E402

DOCS = {"A22", "A11", "A11D", "CH4D", "Q9", "AIA", "FDA-CRED", "FDA-DP", "FDA-WL"}
CATEGORIES = {"clear", "borderline", "out_of_scope"}
CHAOS = {"typo", "abbreviation", "vague", "rambling", "wrong_field", "contradiction", "missing_answers",
         "not_sure_everywhere", "two_use_cases", "very_short", "very_long", "danish_words", "product_name",
         "irrelevant_detail", "no_punctuation", "caps_or_lowercase"}
REQUIRED = {"id", "set", "category", "form", "expected", "key_sources", "rationale", "contested_field", "chaos", "label_status"}


def check_form(form: dict, cid: str) -> list[str]:
    errs = []
    for q in QUESTIONS:
        if q["id"] not in form:
            errs.append(f"{cid}: form missing '{q['id']}' (use an empty value if unanswered)")
            continue
        v = form[q["id"]]
        allowed = {o["value"] for o in q.get("options", [])}
        if q["type"] in ("text", "textarea") and not isinstance(v, str):
            errs.append(f"{cid}: '{q['id']}' must be a string")
        elif q["type"] == "multi":
            if not isinstance(v, list) or any(x not in allowed for x in v):
                errs.append(f"{cid}: '{q['id']}' must be a list of {sorted(allowed)}")
        elif q["type"] == "single":
            if not isinstance(v, dict) or set(v) != {"choice", "explain"}:
                errs.append(f"{cid}: '{q['id']}' must be {{'choice': value|null, 'explain': str}}")
            elif v["choice"] is not None and v["choice"] not in allowed:
                errs.append(f"{cid}: '{q['id']}'.choice {v['choice']!r} not in {sorted(allowed)}")
    extra = set(form) - {q["id"] for q in QUESTIONS}
    if extra:
        errs.append(f"{cid}: unknown form keys {sorted(extra)}")
    return errs


def validate(path: Path) -> tuple[list[dict], list[str]]:
    rows, errs = [], []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            errs.append(f"{path.name}:{n}: invalid JSON ({e})")
    for r in rows:
        cid = r.get("id", "?")
        missing = REQUIRED - set(r)
        if missing:
            errs.append(f"{cid}: missing keys {sorted(missing)}")
            continue
        if r["category"] not in CATEGORIES:
            errs.append(f"{cid}: category {r['category']!r}")
        bad_chaos = set(r["chaos"]) - CHAOS
        if bad_chaos:
            errs.append(f"{cid}: unknown chaos tags {sorted(bad_chaos)}")
        errs += check_form(r["form"], cid)
        e = r["expected"]
        if e.get("in_scope"):
            try:
                c = Classification(gmp_relevance=e["gmp_relevance"], model_type=e["model_type"], autonomy=e["autonomy"])
            except Exception as exc:
                errs.append(f"{cid}: bad labels ({exc})")
                continue
            derived = decide(True, c).verdict
            if derived != e["verdict"]:
                errs.append(f"{cid}: verdict {e['verdict']} but the rules give {derived}")
            if not r["key_sources"]:
                errs.append(f"{cid}: in-scope case without key_sources")
        else:
            if any(e.get(f) is not None for f in FIELD_VALUES) or e.get("verdict") != "out_of_scope" or r["key_sources"]:
                errs.append(f"{cid}: out-of-scope case must have null fields, verdict out_of_scope, no key_sources")
        for s in r["key_sources"]:
            if s.get("doc") not in DOCS or not s.get("section"):
                errs.append(f"{cid}: bad key source {s}")
        if r["contested_field"] not in (None, "gmp_relevance", "model_type", "autonomy", "in_scope"):
            errs.append(f"{cid}: contested_field {r['contested_field']!r}")
    ids = [r.get("id") for r in rows]
    dupes = [i for i, k in Counter(ids).items() if k > 1]
    if dupes:
        errs.append(f"duplicate ids {dupes}")
    return rows, errs


def main() -> int:
    all_errs, all_rows = [], []
    for p in sys.argv[1:]:
        rows, errs = validate(Path(p))
        all_rows += rows
        all_errs += errs
    print(f"{len(all_rows)} cases")
    print("verdicts:  ", dict(Counter(r["expected"]["verdict"] for r in all_rows)))
    print("categories:", dict(Counter(r["category"] for r in all_rows)))
    print("chaos tags:", dict(Counter(t for r in all_rows for t in r["chaos"]).most_common()))
    for e in all_errs:
        print("ERROR", e)
    print("OK" if not all_errs else f"{len(all_errs)} error(s)")
    return 1 if all_errs else 0


if __name__ == "__main__":
    sys.exit(main())
