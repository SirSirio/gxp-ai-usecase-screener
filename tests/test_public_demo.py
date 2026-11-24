"""GXP_PUBLIC_DEMO: the hosted demo shows a data notice on both forms, an audit-log line on the result page
and a badge in the header. Off by default, so local runs look as before. Offline classifier only."""
import dataclasses

import pytest
from fastapi.testclient import TestClient

DESCRIPTION = "We want ChatGPT to draft SOPs and QA approves each one before release in the eDMS."
MARKERS = ("data-demo-notice", "data-demo-audit", "data-demo-badge")


@pytest.fixture(scope="module")
def settings(index, tmp_path_factory):
    from app import config

    tmp = tmp_path_factory.mktemp("demo")
    s = config.Settings(provider="offline", audit_dir=tmp / "audit", results_dir=tmp / "results")
    yield s
    config.use_settings(None)


@pytest.fixture(scope="module")
def client(settings):
    from app.main import app

    return TestClient(app)


def _use(settings, on: bool):
    from app import config

    config.use_settings(dataclasses.replace(settings, public_demo=on))


def _result_html(client) -> str:
    r = client.post("/quick", data={"description": DESCRIPTION, "provider": "offline"})
    assert r.status_code == 200
    return r.text


def test_setting_is_off_unless_the_env_var_is_1():
    import os

    from app import config

    if os.getenv("GXP_PUBLIC_DEMO"):
        pytest.skip("GXP_PUBLIC_DEMO is set in this shell")
    assert config.Settings().public_demo is False


def test_no_demo_notices_by_default(client, settings):
    _use(settings, False)
    pages = [client.get("/submit").text, client.get("/quick").text, _result_html(client)]
    for html in pages:
        for m in MARKERS:
            assert m not in html
        assert "Public demo" not in html


def test_demo_notice_on_both_forms(client, settings):
    _use(settings, True)
    for path in ("/submit", "/quick"):
        html = client.get(path).text
        assert "data-demo-notice" in html, path
        assert "Do not enter confidential or company information. Use made-up or public examples." in html, path
        assert "data-demo-badge" in html, path


def test_demo_audit_line_on_result_page(client, settings):
    _use(settings, True)
    html = _result_html(client)
    assert "data-demo-audit" in html
    assert "the audit log is not kept" in html and "for demonstration only" in html
    assert "data-demo-notice" not in html  # the form notice belongs to the forms only
