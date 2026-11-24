"""Evaluate the assistant on a labelled set and store the result per version.

Run:
  .venv/Scripts/python -m eval.run_eval --set dev --provider offline     # prints per-case details
  .venv/Scripts/python -m eval.run_eval --set test --provider offline    # held out: aggregates only
  .venv/Scripts/python -m eval.run_eval --set dev --provider gemini --sample 10 --seed 1   # smoke run

Cases: v2 (default) are filled-in intake forms in eval/v2/. Each form is validated, rendered with
form_to_text and passed to the pipeline together with the form, exactly as the web app does.
v1 (--cases v1) are the old single-text sets eval/devset.jsonl and eval/testset.jsonl.
Results and reports are named by set and case version, e.g. dev_v2_gemini_latest.md.

Metrics
- schema_valid_rate: assessments that passed validation (invalid output is never shown)
- field accuracy: in_scope, gmp_relevance, model_type, autonomy (over cases labelled in scope)
- verdict accuracy: overall and per category (clear / borderline / out_of_scope)
- refusal: precision and recall of out_of_scope; wrongly refused clear in-scope cases
- key-source recall: expected (doc, section) found among retrieved passages, and among cited passages
- citation keep rate: citations proposed by the assessor that survived the citation check
- model citations in map: the assessor's own citations (before the check) scored against the source map
  (app/source_map.py): in the map, known wrong, or outside the map; judgments with source: answers other
  than "unclear" that show at least one source after the check (W46, D24)
Every run is saved with prompt, rules, corpus, app and git versions so changes can be compared.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.assessors import get_assessor
from app.audit import AuditLog
from app import source_map
from app.config import APP_VERSION, ROOT, get_settings
from app.intake_form import FormError, form_to_text, normalize_form
from app.pipeline import AssessmentFailed, run_assessment
from app.retrieval.index import get_index
from app.rules import RULES_VERSION
from eval.safety import error_kind, is_dangerous

EVAL_DIR = ROOT / "eval"
FIELDS = ("gmp_relevance", "model_type", "autonomy")


CASE_FILES = {
    ("v1", "dev"): EVAL_DIR / "devset.jsonl", ("v1", "test"): EVAL_DIR / "testset.jsonl",
    ("v2", "dev"): EVAL_DIR / "v2" / "dev_cases.jsonl", ("v2", "test"): EVAL_DIR / "v2" / "test_cases.jsonl",
}


def load(set_name: str, version: str = "v2") -> list[dict]:
    path = CASE_FILES[(version, set_name)]
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def case_input(case: dict) -> tuple[str, dict | None]:
    """What the pipeline gets, the same way the web app does it: (text for the classifier, form or None)."""
    if "form" in case:
        form = normalize_form(case["form"])
        return form_to_text(form), form
    return case["description"], None


def pick(cases: list[dict], limit: int | None = None, sample: int | None = None, seed: int = 0) -> list[dict]:
    """A reproducible random sample (same seed, same cases), or the first `limit` cases."""
    if sample:
        return sorted(random.Random(seed).sample(cases, min(sample, len(cases))), key=lambda c: c["id"])
    return cases[:limit]


def run_tag(result: dict) -> str:
    """dev / test for the old sets, dev_v2 / test_v2 for the form cases, plus _sampleN for a sample run,
    so a smoke run is never mistaken for a full run (used in file names, reports and history)."""
    v = result.get("cases_version", "v1")
    tag = result["set"] if v == "v1" else f"{result['set']}_{v}"
    sample = (result.get("selection") or {}).get("sample")
    return f"{tag}_sample{sample}" if sample else tag


def _matches(chunk_section: str, expected: str) -> bool:
    return chunk_section == expected or chunk_section.startswith(expected + ".")


def source_hit(chunk_ids: list[str], src: dict) -> bool:
    for cid in chunk_ids:
        doc, section, _ = cid.split(":", 2)
        if doc == src["doc"] and _matches(section, src["section"]):
            return True
    return False


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def evaluate(set_name: str, provider: str, limit: int | None = None, version: str = "v2",
             sample: int | None = None, seed: int = 0) -> dict:
    cases = pick(load(set_name, version), limit, sample, seed)
    index = get_index()
    assessor = get_assessor(provider)
    audit = AuditLog(get_settings().audit_dir / "eval_audit.jsonl")
    rows = [assess_case(case, assessor, index, audit) for case in cases]
    result = summarise(rows, set_name, provider, index.corpus_version, assessor)
    result["cases_version"] = version
    result["selection"] = {"sample": sample, "seed": seed} if sample else {"limit": limit}
    return result


def assess_case(case: dict, assessor, index, audit) -> dict:
    """One case through the full pipeline, scored. Never raises: a failed assessment is a row with valid=False."""
    exp = case["expected"]
    t0 = time.perf_counter()
    row = {"id": case["id"], "category": case["category"], "expected": exp, "valid": True}
    try:
        text, form = case_input(case)
    except FormError as exc:
        # The web app rejects such a form before any classification ("please describe the task in at
        # least 20 characters"), so nothing is assessed: scored as "Not assessed", no API call made.
        row.update(got={"in_scope": False, "verdict": "out_of_scope", **{f: None for f in FIELDS}},
                   rule_id="form-validation", form_rejected=str(exc), latency_ms=0, retrieved_hits=[], cited_hits=[],
                   judgments_supported=[], citations_kept=0, citations_proposed=0, tool_calls=0,
                   model_citations=[], judgments_sourced=[])
        return row
    try:
        r = run_assessment(text, assessor=assessor, index=index, audit=audit, save=False, form=form)
    except AssessmentFailed as exc:
        row.update(valid=False, error=str(exc), failure_kind=exc.kind, latency_ms=int((time.perf_counter() - t0) * 1000))
        return row
    c = r.classification
    got = {"in_scope": r.in_scope, "verdict": r.decision.verdict,
           **{f: (getattr(c, f) if c else None) for f in FIELDS}}
    cited = sorted({x.chunk_id for j in r.judgments for x in j.citations} | {x.chunk_id for x in r.decision.citations}
                   | {x.chunk_id for k in r.controls for x in k.citations})
    proposed = sum(j.citations_proposed for j in r.judgments)
    row.update(
        got=got, latency_ms=r.meta.latency_ms, rule_id=r.decision.rule_id,
        retrieved_hits=[source_hit(r.meta.retrieved_chunk_ids + [cid for t in r.meta.tool_calls for cid in t.get("chunk_ids", [])], s) for s in case["key_sources"]],
        cited_hits=[source_hit(cited, s) for s in case["key_sources"]],
        judgments_supported=[j.supported for j in r.judgments],
        citations_kept=sum(len(j.citations) for j in r.judgments), citations_proposed=proposed,
        tool_calls=len(r.meta.tool_calls),
        model_citations=[source_map.judge(j.value, cid) for j in r.judgments if j.value != "unclear"
                         for cid in dict.fromkeys(j.proposed_ids)],
        judgments_sourced=[bool(j.citations) for j in r.judgments if j.value != "unclear"],
    )
    return row


# Failures caused by the provider, not by the model's answer: the case was never assessed, so it may be run again
# (owner decision, W51: answers lost to HTTP 503 are discarded and those cases re-run). An invalid model answer is a
# real result and is never retried.
PROVIDER_FAILURES = {"overloaded", "network", "timeout", "rate_limit"}


def retry_unanswered(path: Path) -> dict:
    """Re-run only the cases of a saved run that got no answer because of the provider, on the same versions."""
    result = json.loads(path.read_text(encoding="utf-8"))
    index = get_index()
    assessor = get_assessor(result["provider"])
    now = {"prompt": assessor.prompt_version, "rules": RULES_VERSION, "corpus": index.corpus_version,
           "source_map": source_map.SOURCE_MAP_VERSION}
    changed = {k: (result["versions"].get(k), v) for k, v in now.items() if result["versions"].get(k) != v}
    if changed:
        raise SystemExit(f"Refused: the system changed since this run {changed}; a retry must use the same versions.")
    cases = {c["id"]: c for c in load(result["set"], result.get("cases_version", "v2"))}
    audit = AuditLog(get_settings().audit_dir / "eval_audit.jsonl")
    todo = [i for i, r in enumerate(result["cases"]) if not r["valid"] and r.get("failure_kind") in PROVIDER_FAILURES]
    for i in todo:
        result["cases"][i] = {**assess_case(cases[result["cases"][i]["id"]], assessor, index, audit), "retried": True}
    new = summarise(result["cases"], result["set"], result["provider"], index.corpus_version, assessor)
    still = sum(1 for i in todo if not result["cases"][i]["valid"])
    result["metrics"], result["confusion"] = new["metrics"], new["confusion"]
    result.setdefault("retries", []).append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                             "cases_retried": len(todo), "still_unanswered": still})
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    append_history({**result, "run_at": result["retries"][-1]["at"]}, run_tag(result))
    write_report(result, run_tag(result))
    return result


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 3) if den else None


def safety_metrics(rows: list[dict], show_ids: bool) -> dict:
    """The primary acceptance numbers (eval/safety.py, D19): dangerous errors must be 0.
    Case ids are listed only when show_ids (dev set); for the held-out test set, counts only."""
    kinds = {r["id"]: error_kind(r["expected"]["verdict"], r["got"]["verdict"] if r["valid"] else None,
                                 r["expected"]["in_scope"], r["got"]["in_scope"] if r["valid"] else None) for r in rows}
    dangerous = [r["id"] for r in rows if r["valid"] and is_dangerous(r["expected"]["verdict"], r["got"]["verdict"])]
    critical = [i for i in dangerous if next(r for r in rows if r["id"] == i)["expected"].get("gmp_relevance") == "critical"]
    m = {
        "dangerous_errors": len(dangerous),
        "dangerous_errors_on_gmp_critical": len(critical),
        "wrongly_refused": sum(k == "wrongly_refused" for k in kinds.values()),
        "wrongly_refused_dangerous": sum(kinds[i] == "wrongly_refused" for i in dangerous),
        "wrongly_screened": sum(k == "wrongly_screened" for k in kinds.values()),
        "stricter_or_not_yet": sum(k == "stricter_or_not_yet" for k in kinds.values()),
    }
    if show_ids:
        m["dangerous_cases"] = dangerous
    return m


def summarise(rows: list[dict], set_name: str, provider: str, corpus_version: str, assessor) -> dict:
    valid = [r for r in rows if r["valid"]]
    in_scope = [r for r in valid if r["expected"]["in_scope"]]
    m: dict = {"n": len(rows), **safety_metrics(rows, show_ids=set_name == "dev"),
               "forms_rejected_by_validation": sum(1 for r in rows if r.get("form_rejected")),
               "schema_valid_rate": _rate(len(valid), len(rows)),
               "unanswered_provider_failures": sum(1 for r in rows if not r["valid"] and r.get("failure_kind") in PROVIDER_FAILURES)}
    m["verdict_accuracy"] = _rate(sum(r["got"]["verdict"] == r["expected"]["verdict"] for r in valid), len(rows))
    m["in_scope_accuracy"] = _rate(sum(r["got"]["in_scope"] == r["expected"]["in_scope"] for r in valid), len(rows))
    for f in FIELDS:
        m[f"{f}_accuracy"] = _rate(sum(r["got"][f] == r["expected"][f] for r in in_scope), len([r for r in rows if r["expected"]["in_scope"]]))
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    m["verdict_accuracy_by_category"] = {k: _rate(sum(x["valid"] and x["got"]["verdict"] == x["expected"]["verdict"] for x in v), len(v)) for k, v in sorted(by_cat.items())}
    oos_pred = [r for r in valid if not r["got"]["in_scope"]]
    oos_true = [r for r in rows if not r["expected"]["in_scope"]]
    m["refusal_precision"] = _rate(sum(not r["expected"]["in_scope"] for r in oos_pred), len(oos_pred))
    m["refusal_recall"] = _rate(sum(r["valid"] and not r["got"]["in_scope"] for r in oos_true), len(oos_true))
    m["clear_cases_wrongly_refused"] = sum(1 for r in oos_pred if r["expected"]["in_scope"] and r["category"] == "clear")
    ks_ret = [h for r in valid for h in r.get("retrieved_hits", [])]
    ks_cit = [h for r in valid for h in r.get("cited_hits", [])]
    m["key_source_recall_retrieved"] = _rate(sum(ks_ret), len(ks_ret))
    m["key_source_recall_cited"] = _rate(sum(ks_cit), len(ks_cit))
    primary = [r["retrieved_hits"][0] for r in valid if r.get("retrieved_hits")]
    m["primary_source_recall_retrieved"] = _rate(sum(primary), len(primary))
    sup = [s for r in valid for s in r.get("judgments_supported", [])]
    m["judgments_supported_rate"] = _rate(sum(sup), len(sup))
    m["citation_keep_rate"] = _rate(sum(r.get("citations_kept", 0) for r in valid), sum(r.get("citations_proposed", 0) for r in valid))
    mc = Counter(x for r in valid for x in r.get("model_citations", []))
    m["model_citations_in_map_rate"] = _rate(mc["in_map"], sum(mc.values()))
    m["model_citations_known_wrong"] = mc["known_wrong"]
    m["model_citations_outside_map"] = mc["outside_map"]
    sourced = [s for r in valid for s in r.get("judgments_sourced", [])]
    m["judgments_with_source_rate"] = _rate(sum(sourced), len(sourced))
    m["mean_latency_ms"] = int(sum(r["latency_ms"] for r in rows) / max(len(rows), 1))
    confusion = Counter((r["expected"]["verdict"], r["got"]["verdict"] if r["valid"] else "INVALID") for r in rows)
    return {
        "set": set_name, "provider": provider, "model": getattr(getattr(assessor, "client", None), "model", "keyword-rules"),
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": {"prompt": assessor.prompt_version, "rules": RULES_VERSION, "corpus": corpus_version, "source_map": source_map.SOURCE_MAP_VERSION,
                     "app": APP_VERSION, "git": git_commit()},
        "metrics": m,
        "confusion": [{"expected": e, "got": g, "count": n} for (e, g), n in sorted(confusion.items())],
        "cases": rows,
    }


def save(result: dict) -> Path:
    out_dir = EVAL_DIR / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = result["run_at"].replace(":", "").replace("-", "")[:15]
    tag = run_tag(result)
    path = out_dir / f"{tag}_{result['provider']}_{stamp}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    append_history(result, tag)
    write_report(result, tag)
    return path


HISTORY_KEYS = ["run_at", "set", "provider", "model", "prompt", "rules", "corpus", "source_map", "app", "git", "n",
                "dangerous_errors", "dangerous_errors_on_gmp_critical", "wrongly_refused", "schema_valid_rate", "verdict_accuracy",
                "in_scope_accuracy", "gmp_relevance_accuracy", "model_type_accuracy", "autonomy_accuracy", "refusal_precision",
                "refusal_recall", "primary_source_recall_retrieved", "key_source_recall_retrieved", "key_source_recall_cited",
                "judgments_supported_rate", "model_citations_in_map_rate", "model_citations_known_wrong",
                "judgments_with_source_rate", "mean_latency_ms"]


def append_history(result: dict, tag: str) -> None:
    """One row per run. If the columns changed since older runs, the file is rewritten with the new
    header (older rows keep their values; new columns stay empty for them)."""
    hist = EVAL_DIR / "results" / "history.csv"
    rows = []
    if hist.exists():
        with open(hist, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            same_header = reader.fieldnames == HISTORY_KEYS
    else:
        same_header = False
    row = {**{k: result[k] for k in ("run_at", "provider", "model")}, "set": tag, **result["versions"],
           **{k: v for k, v in result["metrics"].items() if k in HISTORY_KEYS}}
    if same_header:
        with open(hist, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HISTORY_KEYS).writerow(row)
        return
    with open(hist, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HISTORY_KEYS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows + [row])


def rescore(path: Path) -> dict:
    """Recompute the metrics of a saved run from its stored per-case rows (no API calls), e.g. after a
    new metric is added or an SME changed a label. Labels (expected, category) are refreshed from the
    current case file; the tool's answers are not touched. If a case's key sources changed, its source
    hits are dropped (they cannot be recomputed without the retrieved ids). The file and its report are
    updated; history.csv is not (it is not a new run)."""
    result = json.loads(path.read_text(encoding="utf-8"))
    current = {c["id"]: c for c in load(result["set"], result.get("cases_version", "v1"))}
    changed = []
    for row in result["cases"]:
        case = current.get(row["id"])
        if case is None:
            continue
        if row["expected"] != case["expected"] or row["category"] != case["category"]:
            changed.append(row["id"])
            row["expected"], row["category"] = case["expected"], case["category"]
            if len(row.get("retrieved_hits", [])) != len(case["key_sources"]):
                row["retrieved_hits"], row["cited_hits"] = [], []
    result["labels_refreshed"] = changed

    class _Stored:  # summarise() reads the prompt version and model from the assessor
        prompt_version = result["versions"]["prompt"]
        client = type("C", (), {"model": result["model"]})()

    new = summarise(result["cases"], result["set"], result["provider"], result["versions"]["corpus"], _Stored())
    result["metrics"], result["confusion"] = new["metrics"], new["confusion"]
    result["rescored_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(result, run_tag(result))
    return result


def write_report(result: dict, tag: str) -> None:
    m = result["metrics"]
    lines = [
        f"# Evaluation report: {tag}, provider `{result['provider']}`",
        "",
        f"Cases: {result.get('cases_version', 'v1')}, {m['n']} evaluated, selection {result.get('selection')}",
        "",
        f"Run {result['run_at']} · model `{result['model']}` · " + " · ".join(f"{k} `{v}`" for k, v in result["versions"].items()),
        "",
        "| Metric | Value |", "|---|---|",
    ]
    for k, v in m.items():
        if isinstance(v, dict):
            v = ", ".join(f"{a}: {b}" for a, b in v.items())
        lines.append(f"| {k.replace('_', ' ')} | {v} |")
    lines += ["", "## Verdict confusion (expected → got)", "", "| expected | got | n |", "|---|---|---|"]
    lines += [f"| {c['expected']} | {c['got']} | {c['count']} |" for c in result["confusion"]]
    out = EVAL_DIR / "reports"
    out.mkdir(exist_ok=True)
    (out / f"{tag}_{result['provider']}_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    from app.llm import providers  # evaluation: patient retries on temporary server errors (W55)

    providers.TRANSIENT_DELAYS = providers.EVAL_TRANSIENT_DELAYS
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["dev", "test"], default="dev")
    ap.add_argument("--provider", default="offline")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sample", type=int, help="random sample of N cases, reproducible with --seed")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cases", choices=["v1", "v2"], default="v2", help="v2 = intake-form cases (default), v1 = old text sets")
    ap.add_argument("--rescore", type=Path, help="recompute the metrics of a saved result file (no API calls) and exit")
    ap.add_argument("--retry-unanswered", type=Path,
                    help="re-run only the cases of a saved run that got no answer because of the provider (503, network, timeout)")
    args = ap.parse_args()
    if args.retry_unanswered:
        r = retry_unanswered(args.retry_unanswered)
        print(json.dumps(r["metrics"], indent=2))
        print("retries:", json.dumps(r["retries"]))  # counts only, no case ids (the test set stays held out)
        return
    if args.rescore:
        r = rescore(args.rescore)
        print(json.dumps(r["metrics"], indent=2))
        return
    result = evaluate(args.set, args.provider, args.limit, args.cases, args.sample, args.seed)
    path = save(result)
    print(json.dumps(result["metrics"], indent=2))
    if args.set == "dev":  # per-case detail only for the dev set (test set stays held out)
        for r in result["cases"]:
            got = r.get("got", {})
            flag = "OK " if got.get("verdict") == r["expected"]["verdict"] else "XX "
            diff = {f: (r["expected"][f], got.get(f)) for f in ("in_scope",) + FIELDS if r["expected"][f] != got.get(f)}
            print(flag, r["id"], r["expected"]["verdict"], "->", got.get("verdict"), diff or "")
    print(f"saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
