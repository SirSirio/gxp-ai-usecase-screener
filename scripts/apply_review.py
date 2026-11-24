"""Apply an SME review export (from review/review_cases.html) to a case file.

Run: .venv/Scripts/python scripts/apply_review.py eval/v2/reviews/<export>.json eval/v2/dev_cases.jsonl

What each decision does:
- approved  -> label_status "sme_approved"
- rejected  -> the case is removed
- rewrite   -> edited_form / edited_expected are applied, label_status "sme_rewritten";
               a rewrite with only a comment is listed for a manual rewrite and left unchanged
Comments are never applied automatically: they are printed so each one is handled by hand.
The script refuses to run if a decision names a case id that is not in the file, and warns
when the cases changed after the review page was built (data hash mismatch).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_review_page import CASE_FILES, load_cases  # noqa: E402


def data_hash() -> str:
    """Same hash as the review page: over all case files, as they are now."""
    return hashlib.sha256(json.dumps(load_cases(CASE_FILES), sort_keys=True).encode()).hexdigest()[:10]


def apply(review: dict, cases: list[dict]) -> tuple[list[dict], dict]:
    decisions = review["decisions"]
    unknown = sorted(set(decisions) - {c["id"] for c in cases})
    if unknown:
        raise SystemExit(f"decisions for unknown case ids: {unknown}")
    out, report = [], {"approved": [], "rejected": [], "rewritten": [], "manual_rewrite": [], "comments": {}, "not_reviewed": []}
    for c in cases:
        d = decisions.get(c["id"])
        if not d or d["status"] == "open":
            report["not_reviewed"].append(c["id"])
            out.append(c)
            continue
        if d.get("comment"):
            report["comments"][c["id"]] = d["comment"]
        if d["status"] == "rejected":
            report["rejected"].append(c["id"])
            continue
        if d["status"] == "approved":
            c["label_status"] = "sme_approved"
            report["approved"].append(c["id"])
        elif d["status"] == "rewrite":
            if d.get("edited_form") or d.get("edited_expected"):
                c["form"].update(d.get("edited_form") or {})
                c["expected"].update(d.get("edited_expected") or {})
                if c["expected"].get("in_scope") is False:  # out of scope: no labels, no sources (validate_cases)
                    c["expected"].update({"gmp_relevance": None, "model_type": None, "autonomy": None, "verdict": "out_of_scope"})
                    c["key_sources"], c["category"] = [], "out_of_scope"
                c["label_status"] = "sme_rewritten"
                report["rewritten"].append(c["id"])
            else:
                report["manual_rewrite"].append(c["id"])
        out.append(c)
    return out, report


def main(review_path: Path, case_path: Path, quiet: bool = False) -> None:
    review = json.loads(review_path.read_text(encoding="utf-8"))
    current = data_hash()
    if review.get("data_hash") != current:
        print(f"WARNING: cases changed since the review page was built ({review.get('data_hash')} -> {current})")
    cases = [json.loads(line) for line in case_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    new, report = apply(review, cases)
    case_path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in new), encoding="utf-8", newline="\n")
    print(f"{case_path}: {len(cases)} -> {len(new)} cases (review {review_path.name}, exported {review.get('exported_at')})")
    for key in ("approved", "rejected", "rewritten", "manual_rewrite", "not_reviewed"):
        print(f"  {key:15} {len(report[key]):3}  {' '.join(report[key])}")
    if quiet:  # held-out test set: do not show case content to whoever tunes the tool
        print(f"  ({len(report['comments'])} comments not shown; --quiet)")
        return
    for cid, text in report["comments"].items():
        print(f"  comment {cid}: {text}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--quiet"]
    if len(args) != 2:
        raise SystemExit(__doc__)
    main(Path(args[0]), Path(args[1]), quiet="--quiet" in sys.argv)
