"""--retry-unanswered (W59): cases lost to the provider (503, network, timeout) are re-run on the same versions;
invalid model answers are real results and are not retried. No API is called: a fake assessor is used."""
import json

import pytest

from app.assessors.base import ProviderFailure
from app.assessors.offline import OfflineAssessor


class Flaky(OfflineAssessor):
    """Fails with a provider error on its first `fails` calls, then answers like the keyword baseline."""

    def __init__(self, fails: int, kind: str = "overloaded"):
        super().__init__()
        self.fails, self.kind, self.calls = fails, kind, 0

    def assess(self, *a, **k):
        self.calls += 1
        if self.calls <= self.fails:
            raise ProviderFailure("Gemini HTTP 503: high demand", self.kind, 503)
        return super().assess(*a, **k)


@pytest.fixture
def eval_env(index, tmp_path, monkeypatch):
    from app import config
    from eval import run_eval

    config.use_settings(config.Settings(provider="offline", audit_dir=tmp_path / "audit", results_dir=tmp_path / "results"))
    monkeypatch.setattr(run_eval, "EVAL_DIR", tmp_path)
    (tmp_path / "results").mkdir()
    yield run_eval
    config.use_settings(None)


def test_unanswered_cases_are_retried_and_counted(eval_env, monkeypatch):
    run_eval = eval_env
    first = Flaky(fails=2)
    monkeypatch.setattr(run_eval, "get_assessor", lambda provider: first)
    result = run_eval.evaluate("dev", "offline", limit=4)
    assert result["metrics"]["unanswered_provider_failures"] == 2
    path = run_eval.save(result)

    monkeypatch.setattr(run_eval, "get_assessor", lambda provider: Flaky(fails=0))
    after = run_eval.retry_unanswered(path)
    assert after["metrics"]["unanswered_provider_failures"] == 0 and after["metrics"]["schema_valid_rate"] == 1.0
    assert after["retries"][-1]["cases_retried"] == 2 and after["retries"][-1]["still_unanswered"] == 0
    assert sum(1 for r in after["cases"] if r.get("retried")) == 2
    assert json.loads(path.read_text(encoding="utf-8"))["retries"]  # saved


def test_retry_refused_when_the_system_changed(eval_env, monkeypatch):
    run_eval = eval_env
    monkeypatch.setattr(run_eval, "get_assessor", lambda provider: Flaky(fails=1))
    path = run_eval.save(run_eval.evaluate("dev", "offline", limit=2))
    data = json.loads(path.read_text(encoding="utf-8"))
    data["versions"]["rules"] = "rules-0.0"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="Refused"):
        run_eval.retry_unanswered(path)


def test_invalid_model_answers_are_not_retried(eval_env, monkeypatch):
    run_eval = eval_env
    monkeypatch.setattr(run_eval, "get_assessor", lambda provider: Flaky(fails=0))
    result = run_eval.evaluate("dev", "offline", limit=2)
    result["cases"][0].update(valid=False, failure_kind="invalid_output")
    path = run_eval.save(result)
    after = run_eval.retry_unanswered(path)
    assert after["retries"][-1]["cases_retried"] == 0
