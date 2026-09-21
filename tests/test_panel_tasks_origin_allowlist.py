"""
TD-24 — panel görev API'sinde Origin allowlist + Faz-2 kimlik.

Kapsam:
  * Tarayıcıdan gelen cross-origin istekler 403 (Origin kapısı auth'tan önce).
  * `Access-Control-Allow-Origin: *` yok; izinli loopback origin yankılanır.
  * API (statik panel hariç) `X-Kando-Token` / Bearer ister.
  * Token yoksa 401; yabancı Origin + geçerli token yine 403.

Kapsam DIŞI: PKCE HTTP exchange ucu; tarayıcı cookie oturumu.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER = REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py"
TEST_SECRET = "lumos-td24-faz2-test-secret"

sys.path.insert(0, str(REPO_ROOT / "panel" / "scripts"))


# --- Saf birim: origin ayrıştırma -------------------------------------------

def _is_loopback_origin(origin: str) -> bool:
    import importlib.util

    spec = importlib.util.spec_from_file_location("_pts", SERVER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.is_loopback_origin(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:8766",
        "http://127.0.0.1",
        "http://localhost:21300",
        "http://localhost",
        "http://LOCALHOST:4321",
        "http://[::1]:8766",
    ],
)
def test_loopback_origins_are_allowed(origin: str) -> None:
    assert _is_loopback_origin(origin) is True


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.com",
        "http://evil.com",
        # Son ek hilesi: hostname TAM eşleşme ile elenir.
        "http://127.0.0.1.evil.com",
        "http://localhost.evil.com",
        # Şema kilidi: panel loopback'te düz http servis edilir.
        "https://localhost:8766",
        "https://127.0.0.1",
        # Kimlik bilgisi gömülü origin.
        "http://user:pass@127.0.0.1:8766",
        # Boş / bozuk.
        "",
        "null",
        "file://",
    ],
)
def test_foreign_or_malformed_origins_are_rejected(origin: str) -> None:
    assert _is_loopback_origin(origin) is False


# --- Uçtan uca: gerçek sunucu ------------------------------------------------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    tmp = tempfile.mkdtemp(prefix="lumos-td24-")
    env = dict(os.environ)
    env.update(
        {
            "LUMOS_BASE_DIR": tmp,
            "LUMOS_PANEL_TASKS_PORT": str(port),
            "LUMOS_PANEL_TASKS_HOST": "127.0.0.1",
            "LUMOS_PANEL_TASKS_SECRET": TEST_SECRET,
            "LUMOS_MODE": "online",
            "LUMOS_PROFILE": "guvenli_yurut",
            "LUMOS_SESSION_UNLOCKED": "true",
        }
    )
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{base}/tasks")
            req.add_header("X-Kando-Token", TEST_SECRET)
            urllib.request.urlopen(req, timeout=1).read()
            break
        except Exception:
            time.sleep(0.15)
    else:
        proc.kill()
        pytest.fail("panel_tasks_server ayağa kalkmadı")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _request(
    base: str,
    path: str,
    *,
    method: str = "GET",
    origin: str | None = None,
    body: dict | None = None,
    token: str | None = TEST_SECRET,
):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}{path}", method=method, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if origin is not None:
        req.add_header("Origin", origin)
    if token is not None:
        req.add_header("X-Kando-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, dict(res.headers), res.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_request_without_origin_is_allowed_with_token(server: str) -> None:
    status, headers, _ = _request(server, "/tasks")
    assert status == 200
    assert "Access-Control-Allow-Origin" not in headers
    assert headers.get("Cache-Control") == "no-store"


def test_api_without_token_is_401(server: str) -> None:
    status, _, raw = _request(server, "/tasks", token=None)
    assert status == 401
    assert json.loads(raw)["error"] == "invalid_token"


def test_wrong_token_is_401(server: str) -> None:
    status, _, raw = _request(server, "/tasks", token="not-the-configured-secret")
    assert status == 401
    assert json.loads(raw)["error"] == "invalid_token"


def test_loopback_origin_is_echoed_not_wildcarded(server: str) -> None:
    origin = "http://127.0.0.1:21300"
    status, headers, _ = _request(server, "/tasks", origin=origin)
    assert status == 200
    assert headers.get("Access-Control-Allow-Origin") == origin
    assert headers.get("Access-Control-Allow-Origin") != "*"
    assert headers.get("Vary") == "Origin"


def test_wildcard_is_gone(server: str) -> None:
    """Regresyon kilidi: hiçbir yanıtta `*` dönmemeli."""
    for origin in (None, "http://localhost:4321", "https://evil.com"):
        _, headers, _ = _request(server, "/tasks", origin=origin)
        assert headers.get("Access-Control-Allow-Origin") != "*"


def test_foreign_origin_get_is_refused(server: str) -> None:
    status, headers, raw = _request(server, "/tasks", origin="https://evil.com")
    assert status == 403
    assert json.loads(raw)["error"] == "origin_not_allowed"
    assert "Access-Control-Allow-Origin" not in headers


def test_foreign_origin_with_valid_token_is_still_403(server: str) -> None:
    status, _, raw = _request(
        server, "/tasks", origin="https://evil.com", token=TEST_SECRET
    )
    assert status == 403
    assert json.loads(raw)["error"] == "origin_not_allowed"


def test_foreign_origin_mutation_is_refused_before_any_write(server: str) -> None:
    """Asıl tehdit: yabancı bir sayfanın doğrudan POST atması."""
    before = json.loads(_request(server, "/tasks")[2])
    status, _, raw = _request(
        server, "/tasks", method="POST", origin="https://evil.com",
        body={"title": "td24-evil-should-not-land"},
    )
    assert status == 403
    assert json.loads(raw)["error"] == "origin_not_allowed"
    after = json.loads(_request(server, "/tasks")[2])
    assert after["tasks"] == before["tasks"], "reddedilen istek yazma yapmamalı"


def test_mutation_without_token_does_not_write(server: str) -> None:
    before = json.loads(_request(server, "/tasks")[2])
    status, _, raw = _request(
        server,
        "/tasks",
        method="POST",
        token=None,
        body={"title": "td24-no-token-should-not-land"},
    )
    assert status == 401
    assert json.loads(raw)["error"] == "invalid_token"
    after = json.loads(_request(server, "/tasks")[2])
    assert after["tasks"] == before["tasks"]


def test_foreign_origin_preflight_is_refused(server: str) -> None:
    """Preflight onay verirse tarayıcı asıl isteği yollar; kapı burada da olmalı."""
    status, _, _ = _request(server, "/tasks", method="OPTIONS", origin="https://evil.com")
    assert status == 403


def test_loopback_preflight_still_works(server: str) -> None:
    origin = "http://localhost:21300"
    status, headers, _ = _request(server, "/tasks", method="OPTIONS", origin=origin, token=None)
    assert status == 204
    assert headers.get("Access-Control-Allow-Origin") == origin
    allow = headers.get("Access-Control-Allow-Headers") or ""
    assert "X-Kando-Token" in allow
    assert "Authorization" in allow
