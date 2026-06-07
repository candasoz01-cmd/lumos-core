"""Persona deferred Şimdi checkpoint items — read-only / behavior probes.

Honest gap documentation: tests may xfail or assert known gaps per
docs/lumos-persona-security-implementation-gaps.md and
docs/lumos-persona-security-checkpoint.md.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest

from kando_runtime.lumos_audit import LumosAuditCollector, append_audit_log
from kando_runtime.lumos_gate import run_lumos_gate

REPO_ROOT = Path(__file__).resolve().parents[1]
GAPS_DOC = "docs/lumos-persona-security-implementation-gaps.md"
CHECKPOINT_DOC = "docs/lumos-persona-security-checkpoint.md"

_RUNTIME_SCAN_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "packages",
    REPO_ROOT / "scripts",
    REPO_ROOT / "panel",
    REPO_ROOT / "backend",
)

_SECRET_FIELD_NAMES = frozenset(
    {
        "passphrase",
        "root_key",
        "api_key",
        "openai_api_key",
        "kando_bridge_secret",
        "authorization",
        "bearer",
        "private_key",
        "secret",
        "token",
    }
)

_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}\b", re.I),
)


def _bridge_handler_stub(*, headers: dict[str, str] | None = None) -> Any:
    from kando_bridge.server import BridgeHandler

    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = headers or {}
    handler.client_address = ("127.0.0.1", 0)
    handler.reject: tuple[int, str] | None = None
    handler.last_json: tuple[int, dict[str, Any]] | None = None

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._reject = _reject
    handler._send_json = _send_json
    return handler


# --- A1: Bridge policy blocked → rejection (checkpoint §1, gap #1) ---


def test_run_lumos_gate_policy_blocked_returns_403(tmp_path: Path) -> None:
    """Controlled bridge + agent mode → policy_ok False, HTTP 403 (gate layer)."""
    audit = LumosAuditCollector(log_id="policy-block-probe")
    out = run_lumos_gate(
        "agent",
        "do something risky",
        repo_root=tmp_path,
        audit=audit,
        controlled_context={
            "bridge_mode": "controlled",
            "controlled_permission": "file_rw",
        },
    )
    assert out.get("policy_ok") is False
    assert out.get("http_status") == 403
    assert out.get("gate_complete") is True
    hb = out.get("http_body") or {}
    assert hb.get("accepted") is False
    assert hb.get("decision_kind") == "blocked"
    assert "policy" in str(hb.get("error") or "").lower()
    audit_entry = out.get("lumos_audit_log") or {}
    assert audit_entry.get("blocked") is True
    assert audit_entry.get("execution_kind") == "rejected_policy"


def test_bridge_send_lumos_pipeline_out_maps_policy_block_to_403() -> None:
    """Bridge handler maps gate policy_ok=False to 403 + blocked by lumos."""
    from kando_bridge.server import BridgeHandler

    handler = _bridge_handler_stub()
    BridgeHandler._send_lumos_pipeline_out(
        handler,
        {"policy_ok": False, "http_status": 403},
    )
    assert handler.last_json is not None
    status, body = handler.last_json
    assert status == 403
    assert body.get("accepted") is False
    assert body.get("error") == "blocked by lumos"


# --- A2: Offline/push — agent_runner push phase trace (checkpoint §3, gap #3) ---


def test_agent_runner_pipeline_has_no_auto_push_phase() -> None:
    """Persona offline: run_agent_pipeline must not auto-invoke git push (gap #3 closed)."""
    from kando import agent_runner

    source = inspect.getsource(agent_runner.run_agent_pipeline)
    assert "push_if_possible" not in source
    assert "_push_repo" not in source


def test_persona_offline_no_auto_push_invariant() -> None:
    """Offline invariant: agent pipeline excludes automatic push phase."""
    from kando import agent_runner

    source = inspect.getsource(agent_runner.run_agent_pipeline)
    assert "push_if_possible" not in source


# --- A3: Secret — keystore/log audit, no secrets in audit logs (checkpoint §4, gap #4) ---


def _audit_blob_has_secret_leak(blob: str) -> list[str]:
    hits: list[str] = []
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError:
        parsed = None
    if parsed is not None:

        def walk(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    key = str(k).lower()
                    if key in _SECRET_FIELD_NAMES and isinstance(v, str) and len(v) > 8:
                        if key != "token" or v not in ("", "n/a"):
                            hits.append(f"field:{path}.{k}")
                    walk(v, f"{path}.{k}" if path else str(k))
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    walk(item, f"{path}[{i}]")

        walk(parsed)
    for pat in _SECRET_VALUE_PATTERNS:
        if pat.search(blob):
            hits.append(f"pattern:{pat.pattern[:40]}")
    return hits


def test_audit_log_entry_does_not_embed_raw_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit JSONL must not persist env-style secret material from collector output."""
    env_secret = "audit-scan-bridge-secret-xyzzy-99"
    monkeypatch.setenv("KANDO_BRIDGE_SECRET", env_secret)
    collector = LumosAuditCollector(log_id="secret-scan-1")
    collector.set_input("agent", "TARGET: x.py\nroutine fix\n")
    collector.set_plan({"steps": []})
    collector.set_step_results([])
    collector.set_summary(
        blocked=True,
        reason="policy blocked",
        execution_result="policy_blocked",
        execution_kind="rejected_policy",
    )
    entry = collector.to_log_entry()
    serialized = json.dumps(entry, ensure_ascii=False)
    assert env_secret not in serialized
    leaks = _audit_blob_has_secret_leak(serialized)
    assert leaks == [], f"audit log leaked secret markers: {leaks}"
    append_audit_log(tmp_path, entry)
    log_dir = tmp_path / ".lumos" / "logs"
    assert log_dir.is_dir()
    for log_file in log_dir.glob("*.log"):
        text = log_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            assert _audit_blob_has_secret_leak(line) == []


def test_keystore_module_avoids_plaintext_secret_logging() -> None:
    """Read-only: keystore loader must not log passphrase/root_key plaintext."""
    keystore_path = REPO_ROOT / "src" / "security" / "keystore.py"
    text = keystore_path.read_text(encoding="utf-8")
    assert "print(" not in text
    assert "logging." not in text
    assert "logger." not in text
    assert "passphrase" in text
    assert "root_key" in text


# --- A4: Bando — runtime absent (checkpoint §5, gap #6) ---


def test_bando_runtime_absent_in_code_tree() -> None:
    """Repo runtime tree has no Bando module/endpoint/handler (docs-only persona)."""
    hits: list[str] = []
    bando_re = re.compile(r"\bbando\b", re.I)
    for root in _RUNTIME_SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".js", ".ts", ".tsx", ".mjs"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if bando_re.search(text):
                rel = path.relative_to(REPO_ROOT)
                hits.append(str(rel))
    assert hits == [], (
        "Bando runtime references found (expected docs-only): "
        + ", ".join(hits[:10])
    )


# --- A5: Anti-taklit — bridge auth when KANDO_BRIDGE_SECRET set (checkpoint §6, gap #5) ---


def test_bridge_check_secret_rejects_missing_token_when_secret_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When KANDO_BRIDGE_SECRET is set, missing/wrong token → 401."""
    from kando_bridge.server import BridgeHandler

    monkeypatch.setenv("KANDO_BRIDGE_SECRET", "test-bridge-secret-value")
    handler = _bridge_handler_stub(headers={})
    ok = BridgeHandler._check_secret(handler)
    assert ok is False
    assert handler.reject is not None
    assert handler.reject[0] == 401


def test_bridge_check_secret_accepts_matching_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """High-level auth: correct Bearer token passes when secret configured."""
    from kando_bridge.server import BridgeHandler

    secret = "test-bridge-secret-value"
    monkeypatch.setenv("KANDO_BRIDGE_SECRET", secret)
    handler = _bridge_handler_stub(
        headers={"Authorization": f"Bearer {secret}"},
    )
    ok = BridgeHandler._check_secret(handler)
    assert ok is True
    assert handler.reject is None


def test_bridge_check_secret_rejects_when_secret_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-taklit: secret unset → 401 (persona gap #5 closed)."""
    from kando_bridge.server import BridgeHandler

    monkeypatch.delenv("KANDO_BRIDGE_SECRET", raising=False)
    handler = _bridge_handler_stub(headers={})
    ok = BridgeHandler._check_secret(handler)
    assert ok is False
    assert handler.reject is not None
    assert handler.reject[0] == 401


def test_persona_bridge_requires_auth_when_secret_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-taklit invariant: bridge rejects when KANDO_BRIDGE_SECRET unset."""
    from kando_bridge.server import BridgeHandler

    monkeypatch.delenv("KANDO_BRIDGE_SECRET", raising=False)
    handler = _bridge_handler_stub(headers={})
    ok = BridgeHandler._check_secret(handler)
    assert ok is False


def test_simdi_checkpoint_docs_exist() -> None:
    """Fixture: checkpoint and gaps docs present for xfail/skip reason links."""
    assert (REPO_ROOT / GAPS_DOC).is_file()
    assert (REPO_ROOT / CHECKPOINT_DOC).is_file()
