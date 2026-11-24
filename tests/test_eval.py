"""Evaluation harness on the v2 intake-form cases. Offline classifier only; uses dev cases only."""
import pytest

from eval import run_eval


def test_form_case_goes_through_the_same_path_as_the_web_app():
    from app.intake_form import form_to_text, normalize_form

    case = run_eval.load("dev")[0]
    text, form = run_eval.case_input(case)
    assert form == normalize_form(case["form"]) and text == form_to_text(form)
    assert run_eval.case_input({"description": "free text"}) == ("free text", None)  # v1 cases still work


def test_sample_is_reproducible_and_tagged():
    cases = run_eval.load("dev")
    a, b = run_eval.pick(cases, sample=10, seed=1), run_eval.pick(cases, sample=10, seed=1)
    assert [c["id"] for c in a] == [c["id"] for c in b] and len(a) == 10
    assert [c["id"] for c in run_eval.pick(cases, sample=10, seed=2)] != [c["id"] for c in a]
    assert run_eval.run_tag({"set": "test", "cases_version": "v2", "selection": {"sample": 10}}) == "test_v2_sample10"
    assert run_eval.run_tag({"set": "test", "cases_version": "v2", "selection": {"limit": None}}) == "test_v2"
    assert run_eval.run_tag({"set": "dev"}) == "dev"  # old results keep their names


def test_evaluate_dev_forms_offline(index, tmp_path):
    from app import config

    config.use_settings(config.Settings(provider="offline", audit_dir=tmp_path / "audit", results_dir=tmp_path / "results"))
    try:
        result = run_eval.evaluate("dev", "offline", sample=3, seed=0)
    finally:
        config.use_settings(None)
    assert result["cases_version"] == "v2" and result["metrics"]["n"] == 3
    assert result["metrics"]["schema_valid_rate"] == 1.0
    assert (tmp_path / "audit" / "eval_audit.jsonl").exists()


@pytest.mark.parametrize("set_name", ["dev", "test"])
def test_v2_files_exist(set_name):
    assert run_eval.CASE_FILES[("v2", set_name)].exists()


def test_a_form_the_app_would_reject_is_scored_not_assessed_without_crashing(index, tmp_path, monkeypatch):
    from app import config

    case = dict(run_eval.load("dev")[0])
    case["form"] = dict(case["form"], what="too short")
    monkeypatch.setattr(run_eval, "load", lambda *a, **k: [case])
    config.use_settings(config.Settings(provider="offline", audit_dir=tmp_path / "a", results_dir=tmp_path / "r"))
    try:
        result = run_eval.evaluate("dev", "offline")
    finally:
        config.use_settings(None)
    row = result["cases"][0]
    assert row["got"]["verdict"] == "out_of_scope" and row["rule_id"] == "form-validation"
    assert result["metrics"]["forms_rejected_by_validation"] == 1
