"""PR #974: consent credential checks through the real loopback HTTP handler.

Place in tests/ of the revision under review. All state and credentials are
temporary. Replay success documents the containment's remaining limitation;
it is not evidence of independent human approval or replay protection.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import threading
from http.server import HTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
PANEL_SECRET = "synthetic-panel-credential-for-consent-tests"
CONSENT_SECRET = "synthetic-separate-consent-credential-974"


@pytest.fixture
def consent_server(tmp_path, monkeypatch):
    base = tmp_path / "state"
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    monkeypatch.delenv("LUMOS_CONSENT_PASSPHRASE", raising=False)
    monkeypatch.syspath_prepend(str(ROOT / "panel" / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "_panel_consent_auth_test", ROOT / "panel/scripts/panel_tasks_server.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    clock = [0.0]
    auth = module.PanelTasksAuth(secret=PANEL_SECRET, now=lambda: clock[0])
    monkeypatch.setattr(module, "_PANEL_TASKS_AUTH", auth)
    monkeypatch.setattr(module, "_base_dir", lambda: base)
    server = HTTPServer(("127.0.0.1", 0), module.Handler)
    thread = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.01), daemon=True
    )
    thread.start()

    def post(body, *, token=PANEL_SECRET, origin=None):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if origin is not None:
            headers["Origin"] = origin
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        try:
            connection.request("POST", "/lumos-consent", json.dumps(body), headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    try:
        yield SimpleNamespace(post=post, base=base, auth=auth, clock=clock)
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
        assert not thread.is_alive()


@pytest.mark.parametrize("configured", [None, "", "a" * 31])
def test_missing_or_short_configuration_does_not_create_state(
    consent_server, monkeypatch, configured
):
    if configured is not None:
        monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", configured)
    status, body = consent_server.post({"passphrase": CONSENT_SECRET})
    assert (status, body["error"]) == (503, "consent_auth_unconfigured")
    assert not consent_server.base.exists()


@pytest.mark.parametrize("body", [{}, {"passphrase": ""}, {"passphrase": "   "}])
def test_empty_passphrase_is_rejected_before_configuration_check(consent_server, body):
    status, response = consent_server.post(body)
    assert (status, response["error"]) == (400, "passphrase_required")
    assert not consent_server.base.exists()


def test_wrong_passphrase_does_not_create_consent(consent_server, monkeypatch):
    monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", CONSENT_SECRET)
    status, body = consent_server.post({"passphrase": "not-the-consent-credential"})
    assert (status, body["error"]) == (403, "consent_auth_failed")
    assert not consent_server.base.exists()


@pytest.mark.parametrize("configured", [None, CONSENT_SECRET])
def test_rejection_preserves_existing_consent(consent_server, monkeypatch, configured):
    if configured is not None:
        monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", configured)
    consent_server.base.mkdir()
    target = consent_server.base / "consent.json"
    original = b'{"granted": true, "source": "existing-consent"}\n'
    target.write_bytes(original)
    status, _ = consent_server.post({"passphrase": "wrong"})
    assert status == (503 if configured is None else 403)
    assert target.read_bytes() == original


@pytest.mark.parametrize("secret", ["a" * 32, CONSENT_SECRET, "ş" * 32])
def test_matching_credential_writes_consent_without_storing_secret(
    consent_server, monkeypatch, secret
):
    monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", secret)
    status, body = consent_server.post({"passphrase": secret})
    assert status == 200 and body["ok"] is True
    text = (consent_server.base / "consent.json").read_text(encoding="utf-8")
    record = json.loads(text)
    assert record["granted"] is True
    assert record["source"] == "panel_tasks_server"
    assert record["ts"]
    assert secret not in text and "passphrase" not in record


@pytest.mark.parametrize("token", [None, "invalid-panel-token"])
def test_consent_credential_does_not_replace_panel_auth(consent_server, monkeypatch, token):
    monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", CONSENT_SECRET)
    status, body = consent_server.post({"passphrase": CONSENT_SECRET}, token=token)
    assert (status, body["error"]) == (401, "invalid_token")
    assert not consent_server.base.exists()


def test_service_token_alone_cannot_grant_consent(consent_server, monkeypatch):
    monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", CONSENT_SECRET)
    token = consent_server.auth.mint_service_token()
    status, body = consent_server.post({"passphrase": "wrong"}, token=token)
    assert (status, body["error"]) == (403, "consent_auth_failed")
    assert not consent_server.base.exists()


def test_service_token_and_credential_can_be_replayed(consent_server, monkeypatch):
    """Characterization: neither request proves a fresh human approval."""
    monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", CONSENT_SECRET)
    token = consent_server.auth.mint_service_token()
    for _ in range(2):
        status, body = consent_server.post({"passphrase": CONSENT_SECRET}, token=token)
        assert status == 200 and body["ok"] is True
    consent_server.clock[0] = 901.0
    before = (consent_server.base / "consent.json").read_bytes()
    status, body = consent_server.post({"passphrase": CONSENT_SECRET}, token=token)
    assert (status, body["error"]) == (401, "invalid_token")
    assert (consent_server.base / "consent.json").read_bytes() == before


def test_foreign_origin_remains_blocked_with_both_credentials(consent_server, monkeypatch):
    monkeypatch.setenv("LUMOS_CONSENT_PASSPHRASE", CONSENT_SECRET)
    status, body = consent_server.post(
        {"passphrase": CONSENT_SECRET}, origin="https://untrusted.example"
    )
    assert (status, body["error"]) == (403, "origin_not_allowed")
    assert not consent_server.base.exists()
