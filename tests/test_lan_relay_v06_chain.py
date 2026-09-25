"""v0.6 yerel ağ zinciri — telefon → relay → köprü /task → onay → gerçek icra → kanıt.

ROADMAP "v0.6 Mobil — asgari sürüm tanımı": mevcut RB-04–07 sözleşmesi üzerinde
relay'in görev aktarımı, gerçek /task onaylarının listelenmesi ve gerçek icra
açılmadan önce kapatılan güvenlik açıkları. Köprü uçları in-process çağrılır
(canlı köprü süreci yok); relay gerçek HTTP(S) sunucusu olarak çalışır.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import socket
import ssl
import subprocess
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from kando_bridge.lan_relay import (
    KIND_PC_REMOTE,
    KIND_TASK,
    MOBILE_TASK_SOURCE,
    RELAY_TOKEN_HEADER,
    LanRelayServer,
    RelayConfig,
    RelayState,
    SlidingWindowLimiter,
    build_relay_pending_list,
    classify_relay_pending,
    redact_token_query,
    strip_mobile_secrets,
)
from kando_bridge.pc_remote_tools import CMD_OPEN_URL, execute_tool_stub

SECRET = "bridge-test-secret"


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _bridge_handler_stub(*, body: dict[str, Any]) -> Any:
    from kando_bridge.server import BridgeHandler

    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler = BridgeHandler.__new__(BridgeHandler)
    handler.headers = {"Content-Length": str(len(raw)), "X-Kando-Token": SECRET}
    handler.rfile = BytesIO(raw)
    handler.reject = None
    handler.last_json = None
    handler.client_address = ("127.0.0.1", 12345)

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._reject = _reject
    handler._send_json = _send_json
    return handler


class RecordingBridge:
    """Gerçek köprü handler'larını in-process çağırır; relay'in gönderdiğini kaydeder."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import kando_bridge.server as srv

        self.root = tmp_path
        self.pending_dir = tmp_path / ".lumos" / "pending_approvals"
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(srv, "ROOT", tmp_path)
        monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", self.pending_dir)
        monkeypatch.setenv("KANDO_BRIDGE_SECRET", SECRET)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.task_response: tuple[int, dict[str, Any]] = (
            200,
            {"accepted": True, "requires_approval": False, "message": "tamam"},
        )

    def __call__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> tuple[int, dict[str, Any]]:
        from kando_bridge.server import BridgeHandler, build_pending_approvals_list

        obj = json.loads((body or b"{}").decode("utf-8")) if body else {}
        self.calls.append((method.upper(), path, obj))
        if method.upper() == "GET" and path.startswith("/pending_approvals"):
            return 200, {
                "items": build_pending_approvals_list(
                    include_approval_token="include_tokens=1" in path
                )
            }
        if method.upper() == "POST" and path == "/approve":
            handler = _bridge_handler_stub(body=obj)
            BridgeHandler._handle_approve(handler)
            assert handler.last_json is not None
            return handler.last_json
        if method.upper() == "POST" and path == "/task":
            return self.task_response
        return 404, {"error": "not_found"}

    def posted(self, path: str) -> list[dict[str, Any]]:
        return [b for m, p, b in self.calls if m == "POST" and p == path]


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        out = {str(k) for k in value}
        for inner in value.values():
            out |= _keys(inner)
        return out
    if isinstance(value, list):
        out: set[str] = set()
        for inner in value:
            out |= _keys(inner)
        return out
    return set()


def _write_dispatch_pending(root: Path) -> dict[str, Any]:
    """Gerçek gate kodundan orta risk dispatch onay kaydı (onayda workspace'e dosya yazar)."""
    from kando_runtime.task_dispatch import attach_execution_dispatch_to_out

    out: dict[str, Any] = {
        "execution_mode": "restricted",
        "policy_ok": True,
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "medium",
            "normalized_task": {"target_body": "telefon.txt oluştur"},
        },
    }
    attach_execution_dispatch_to_out(out, repo_root=root)
    rec = out["pending_approval_record"]
    assert isinstance(rec, dict)
    rec["approval_token"] = "tok-phone-dispatch"
    (root / str(out["approval_file"])).write_text(
        json.dumps(rec, ensure_ascii=False), encoding="utf-8"
    )
    return rec


def _start_relay(config: RelayConfig) -> LanRelayServer:
    server = LanRelayServer(config)
    thread = threading.Thread(target=server.start, kwargs={"block": True}, daemon=True)
    thread.start()
    time.sleep(0.15)
    return server


def _http(
    port: int,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if token:
        headers[RELAY_TOKEN_HEADER] = token
    req = Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, json.loads(raw) if raw.strip() else {}


def _pair(port: int, state: RelayState) -> str:
    status, payload = _http(port, "POST", "/relay/pair", {"pairing_code": state.pairing_id})
    assert status == 200, payload
    return str(payload["relay_token"])


@pytest.fixture
def relay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[int, RelayState, RelayConfig, RecordingBridge]:
    bridge = RecordingBridge(tmp_path, monkeypatch)
    config = RelayConfig(
        host="127.0.0.1",
        port=_free_port(),
        bridge_secret=SECRET,
        enable_beacon=False,
        bridge_request=bridge,
    )
    server = _start_relay(config)
    yield config.port, config.state, config, bridge  # type: ignore[misc]
    server.stop()


# --- zincir: gerçek /task onayı telefonda görünür → token'sız onay → gerçek icra ---


def test_phone_sees_real_task_approval_without_token_and_approval_executes(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, _, bridge = relay
    rec = _write_dispatch_pending(bridge.root)
    token = _pair(port, state)

    status, listing = _http(port, "GET", "/relay/pending", token=token)
    assert status == 200
    assert listing["count"] == 1
    row = listing["pending"][0]
    assert row["kind"] == KIND_TASK
    assert row["executes_on_approve"] is True
    assert row["approval_file"] == rec["approval_file"]
    assert row["expires_at"]
    assert "approval_token" not in _keys(listing)
    assert "tok-phone-dispatch" not in json.dumps(listing)

    # Telefon token göndermez; relay köprü listesinden çözer.
    status, out = _http(
        port, "POST", "/relay/approve", {"approval_file": row["approval_file"]}, token=token
    )
    assert status == 200, out
    assert out["kind"] == KIND_TASK
    assert out["ok"] is True
    assert out["accepted"] is True
    assert out["applied"] is True
    assert "execution_dispatch" in out  # kanıt telefona döner
    assert "tok-phone-dispatch" not in json.dumps(out)
    assert (bridge.root / "workspace" / "telefon.txt").is_file()

    forwarded = bridge.posted("/approve")[-1]
    assert forwarded["approval_token"] == "tok-phone-dispatch"
    assert forwarded["approval_file"] == rec["approval_file"]

    # Kayıt tüketildi; ikinci onay bulunamaz, icra tekrar etmez.
    status, again = _http(
        port, "POST", "/relay/approve", {"approval_file": row["approval_file"]}, token=token
    )
    assert status == 404
    assert again["error"] == "approval_not_found"


def test_bridge_refusal_is_reported_as_failure_not_approved(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    """Canlı dumanda görülen: LLM'siz kapı boş planlı kayıt yazar; köprü icrayı reddeder
    (200 + accepted:false). Relay bunu ok:false diye iletmeli, telefon 'onaylandı' demez."""
    port, state, _, bridge = relay
    rel = ".lumos/pending_approvals/approval_empty_plan.json"
    rec = {
        "schema_version": "lumos.pending_approval.v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "approval_file": rel,
        "approval_token": "tok-empty",
        "task_id": "t-empty",
        "risk_level": "unknown",
        "execution_mode": "pending_approval",
        "final_decision": "await_user_approval",
        "policy_ok": True,
        "execution_plan": {"steps": []},
        "reasoning_snapshot": {"source": "heuristic"},
        "normalized_task": {},
        "title": "LLM yokken yazılmış görev",
    }
    (bridge.root / rel).write_text(json.dumps(rec), encoding="utf-8")
    token = _pair(port, state)
    status, out = _http(port, "POST", "/relay/approve", {"approval_file": rel}, token=token)
    assert status == 200
    assert out["ok"] is False
    assert out["accepted"] is False
    assert "execution_plan" in out["error"]
    assert "tok-empty" not in json.dumps(out)


def test_phone_supplied_token_is_ignored(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, _, bridge = relay
    rec = _write_dispatch_pending(bridge.root)
    token = _pair(port, state)
    status, out = _http(
        port,
        "POST",
        "/relay/approve",
        {"approval_file": rec["approval_file"], "approval_token": "attacker-guess"},
        token=token,
    )
    assert status == 200, out
    assert bridge.posted("/approve")[-1]["approval_token"] == "tok-phone-dispatch"


def test_reject_real_task_closes_without_execution(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, _, bridge = relay
    rec = _write_dispatch_pending(bridge.root)
    token = _pair(port, state)
    status, out = _http(
        port, "POST", "/relay/reject", {"approval_file": rec["approval_file"]}, token=token
    )
    assert status == 200
    assert out.get("closed") is True
    assert not (bridge.root / "workspace" / "telefon.txt").exists()
    _, listing = _http(port, "GET", "/relay/pending", token=token)
    assert listing["count"] == 0


def test_unknown_or_foreign_approval_file_is_not_forwarded(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, _, bridge = relay
    token = _pair(port, state)
    for ref in (
        {"approval_file": ".lumos/pending_approvals/nope.json"},
        {"approval_file": "../../etc/passwd"},
        {},
    ):
        status, out = _http(port, "POST", "/relay/approve", ref, token=token)
        assert status == 404
        assert out["error"] == "approval_not_found"
    assert bridge.posted("/approve") == []


def test_stale_task_approval_is_hidden_and_not_approvable(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, config, bridge = relay
    rec = _write_dispatch_pending(bridge.root)
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(
        seconds=config.task_approval_ttl_seconds + 5
    )
    rec["created_at"] = old.isoformat()
    (bridge.root / rec["approval_file"]).write_text(json.dumps(rec), encoding="utf-8")
    token = _pair(port, state)
    _, listing = _http(port, "GET", "/relay/pending", token=token)
    assert listing["count"] == 0
    status, _ = _http(
        port, "POST", "/relay/approve", {"approval_file": rec["approval_file"]}, token=token
    )
    assert status == 404
    assert not (bridge.root / "workspace" / "telefon.txt").exists()


def test_pc_remote_stub_flow_still_works_without_phone_token(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, _, bridge = relay
    pending = execute_tool_stub(CMD_OPEN_URL, {"url": "https://example.com"}, repo_root=bridge.root)
    secret = str(pending["approval_token"])
    token = _pair(port, state)
    _, listing = _http(port, "GET", "/relay/pending", token=token)
    assert listing["pending"][0]["kind"] == KIND_PC_REMOTE
    assert listing["pending"][0]["executes_on_approve"] is False
    assert "approval_token" not in _keys(listing)
    assert secret not in json.dumps(listing)
    status, out = _http(
        port, "POST", "/relay/approve", {"approval_file": pending["approval_file"]}, token=token
    )
    assert status == 200, out
    assert out["pc_remote_approval"]["status"] == "approved"
    assert "approval_token" not in _keys(out)
    assert secret not in json.dumps(out)


# --- /relay/task ---


def test_relay_task_forwards_only_goal_and_source(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, _, bridge = relay
    bridge.task_response = (
        200,
        {
            "accepted": True,
            "requires_approval": True,
            "approval_file": ".lumos/pending_approvals/x.json",
            "approval_token": "leak-me-not",
            "lumos_gate": {"pending_approval_record": {"approval_token": "nested-leak"}},
            "pending_summary": "özet",
        },
    )
    token = _pair(port, state)
    status, out = _http(
        port,
        "POST",
        "/relay/task",
        {
            "text": "  Masaüstündeki notları özetle  ",
            "auto_approve_safe": True,
            "bridge_mode": "controlled",
            "permission": "file_rw",
            "task_type": "shell",
            "file": "src/main.py",
            "approval_granted": True,
        },
        token=token,
    )
    assert status == 200, out
    assert bridge.posted("/task") == [
        {"goal": "Masaüstündeki notları özetle", "source": MOBILE_TASK_SOURCE}
    ]
    assert out["kind"] == KIND_TASK
    assert out["requires_approval"] is True
    assert out["approval_file"] == ".lumos/pending_approvals/x.json"
    raw = json.dumps(out)
    assert "leak-me-not" not in raw and "nested-leak" not in raw


@pytest.mark.parametrize(
    "body,error",
    [({}, "task_text_required"), ({"text": "   "}, "task_text_required"), ({"text": 5}, "task_text_required")],
)
def test_relay_task_requires_text(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
    body: dict[str, Any],
    error: str,
) -> None:
    port, state, _, bridge = relay
    token = _pair(port, state)
    status, out = _http(port, "POST", "/relay/task", body, token=token)
    assert status == 400
    assert out["error"] == error
    assert bridge.posted("/task") == []


def test_relay_task_length_limit(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, config, bridge = relay
    token = _pair(port, state)
    status, out = _http(
        port, "POST", "/relay/task", {"text": "x" * (config.task_max_chars + 1)}, token=token
    )
    assert status == 400
    assert out["error"] == "task_text_too_long"
    assert bridge.posted("/task") == []


def test_relay_task_requires_relay_token(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, _, _, bridge = relay
    status, out = _http(port, "POST", "/relay/task", {"text": "merhaba"})
    assert status == 401
    assert bridge.posted("/task") == []


def test_relay_task_rate_limited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = RecordingBridge(tmp_path, monkeypatch)
    config = RelayConfig(
        host="127.0.0.1",
        port=_free_port(),
        bridge_secret=SECRET,
        enable_beacon=False,
        bridge_request=bridge,
        task_rate_limit=2,
        task_rate_window_seconds=60,
    )
    server = _start_relay(config)
    try:
        assert config.state is not None
        token = _pair(config.port, config.state)
        codes = [
            _http(config.port, "POST", "/relay/task", {"text": f"görev {i}"}, token=token)[0]
            for i in range(3)
        ]
        assert codes == [200, 200, 429]
        assert len(bridge.posted("/task")) == 2
    finally:
        server.stop()


# --- şifresiz LAN'da gerçek icra kapalı ---


def test_plain_http_lan_bind_blocks_real_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bridge = RecordingBridge(tmp_path, monkeypatch)
    config = RelayConfig(
        host="0.0.0.0",
        port=_free_port(),
        bridge_secret=SECRET,
        enable_beacon=False,
        bridge_request=bridge,
    )
    assert config.execution_transport_ok() is False
    server = _start_relay(config)
    try:
        assert config.state is not None
        rec = _write_dispatch_pending(bridge.root)
        stub = execute_tool_stub(CMD_OPEN_URL, {"url": "https://example.com"}, repo_root=tmp_path)
        token = _pair(config.port, config.state)

        _, listing = _http(config.port, "GET", "/relay/pending", token=token)
        assert listing["task_execution_enabled"] is False

        status, out = _http(config.port, "POST", "/relay/task", {"text": "x"}, token=token)
        assert status == 403 and out["error"] == "insecure_transport"
        status, out = _http(
            config.port, "POST", "/relay/approve", {"approval_file": rec["approval_file"]}, token=token
        )
        assert status == 403 and out["error"] == "insecure_transport"
        assert bridge.posted("/task") == [] and bridge.posted("/approve") == []
        assert not (tmp_path / "workspace" / "telefon.txt").exists()

        # Gerçek icraya gitmeyen yollar açık kalır: stub onayı ve red.
        status, _ = _http(
            config.port, "POST", "/relay/approve", {"approval_file": stub["approval_file"]}, token=token
        )
        assert status == 200
        status, _ = _http(
            config.port, "POST", "/relay/reject", {"approval_file": rec["approval_file"]}, token=token
        )
        assert status == 200
    finally:
        server.stop()


def test_transport_policy_matrix() -> None:
    def ok(**kw: Any) -> bool:
        return RelayConfig(enable_beacon=False, bridge_request=lambda *_a: (200, {}), **kw).execution_transport_ok()

    assert ok(host="127.0.0.1") is True
    assert ok(host="::1") is True
    assert ok(host="localhost") is True
    assert ok(host="0.0.0.0") is False
    assert ok(host="192.168.1.20") is False
    assert ok(host="0.0.0.0", allow_insecure_execution=True) is True


def test_default_bind_is_loopback() -> None:
    assert RelayConfig(enable_beacon=False).host == "127.0.0.1"


# --- eşleştirme sertleştirmesi ---


def test_pairing_code_is_single_use(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, _, _ = relay
    code = state.pairing_id
    status, _ = _http(port, "POST", "/relay/pair", {"pairing_code": code})
    assert status == 200
    assert state.pairing_id != code
    status, out = _http(port, "POST", "/relay/pair", {"pairing_code": code})
    assert status == 403
    assert out["error"] == "invalid_pairing_code"


def test_pairing_code_rotates_after_failed_attempts(
    relay: tuple[int, RelayState, RelayConfig, RecordingBridge],
) -> None:
    port, state, config, _ = relay
    rotated: list[str] = []
    state.on_pairing_rotated = rotated.append
    code = state.pairing_id
    errors = [
        _http(port, "POST", "/relay/pair", {"pairing_code": f"BAD{i:03d}"})[1]["error"]
        for i in range(config.max_pairing_failures)
    ]
    assert errors[:-1] == ["invalid_pairing_code"] * (config.max_pairing_failures - 1)
    assert errors[-1] == "pairing_code_rotated"
    assert rotated and rotated[-1] == state.pairing_id != code
    # Yakılan eski kod artık işe yaramaz.
    status, _ = _http(port, "POST", "/relay/pair", {"pairing_code": code})
    assert status == 403


def test_relay_logs_redact_token_query() -> None:
    line = redact_token_query('"GET /relay/mobile?token=abcDEF123&x=1 HTTP/1.1" 200 -')
    assert "abcDEF123" not in line
    assert "token=[redacted]&x=1" in line


# --- TLS ---


def _self_signed(tmp_path: Path) -> tuple[Path, Path, str]:
    openssl = shutil.which("openssl")
    if not openssl:
        pytest.skip("openssl CLI yok — self-signed sertifika üretilemiyor")
    cert_path = tmp_path / "relay.crt"
    key_path = tmp_path / "relay.key"
    subprocess.run(
        [
            openssl, "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
            "-nodes", "-days", "1", "-subj", "/CN=lumos-relay-test",
            "-keyout", str(key_path), "-out", str(cert_path),
        ],
        check=True,
        capture_output=True,
    )
    der = ssl.PEM_cert_to_DER_cert(cert_path.read_text(encoding="ascii"))
    return cert_path, key_path, hashlib.sha256(der).hexdigest()


def test_tls_relay_enables_lan_execution_and_exposes_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert, key, fingerprint = _self_signed(tmp_path)
    bridge = RecordingBridge(tmp_path, monkeypatch)
    config = RelayConfig(
        host="0.0.0.0",
        port=_free_port(),
        bridge_secret=SECRET,
        enable_beacon=False,
        bridge_request=bridge,
        tls_certfile=str(cert),
        tls_keyfile=str(key),
    )
    assert config.execution_transport_ok() is True
    assert config.relay_base_url().startswith("https://")
    server = _start_relay(config)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # self-signed: pin ile doğrulanır
        with socket.create_connection(("127.0.0.1", config.port), timeout=5) as raw:
            with ctx.wrap_socket(raw) as tls:
                peer = tls.getpeercert(binary_form=True)
                assert peer is not None
                assert hashlib.sha256(peer).hexdigest() == fingerprint

        def https(method: str, path: str, body: dict[str, Any] | None = None, token: str = "") -> tuple[int, dict[str, Any]]:
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            if token:
                headers[RELAY_TOKEN_HEADER] = token
            data = json.dumps(body).encode("utf-8") if body is not None else None
            req = Request(
                f"https://127.0.0.1:{config.port}{path}", data=data, headers=headers, method=method
            )
            try:
                with urlopen(req, timeout=5, context=ctx) as resp:
                    return resp.status, json.loads(resp.read().decode("utf-8"))
            except HTTPError as e:
                return e.code, json.loads(e.read().decode("utf-8"))

        status, disc = https("GET", "/relay/discover")
        assert status == 200
        assert disc["tls"] is True
        assert disc["tls_fingerprint_sha256"] == fingerprint

        assert config.state is not None
        status, paired = https("POST", "/relay/pair", {"pairing_code": config.state.pairing_id})
        assert status == 200
        assert paired["task_execution_enabled"] is True
        status, out = https("POST", "/relay/task", {"text": "rapor hazırla"}, paired["relay_token"])
        assert status == 200, out
        assert bridge.posted("/task") == [{"goal": "rapor hazırla", "source": MOBILE_TASK_SOURCE}]

        # Düz HTTP ile konuşan istemci hizmet alamaz.
        with pytest.raises(Exception):
            urlopen(f"http://127.0.0.1:{config.port}/relay/discover", timeout=3)
    finally:
        server.stop()


def test_tls_requires_both_cert_and_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        RelayConfig(enable_beacon=False, tls_certfile=str(tmp_path / "a.crt"))


# --- saf yardımcılar ---


def test_classify_relay_pending_matrix() -> None:
    now = dt.datetime(2026, 9, 25, 12, 0, tzinfo=dt.timezone.utc)
    fresh = (now - dt.timedelta(minutes=1)).isoformat()
    base = {"schema_version": "lumos.dispatch_pending_approval.v1", "created_at": fresh}
    assert classify_relay_pending(base, now=now)[0] == KIND_TASK
    assert classify_relay_pending({**base, "schema_version": "lumos.pending_approval.v1"}, now=now)[0] == KIND_TASK
    assert classify_relay_pending({**base, "used": True}, now=now)[0] is None
    assert classify_relay_pending({**base, "status": "approved"}, now=now)[0] is None
    assert classify_relay_pending({**base, "created_at": ""}, now=now)[0] is None
    assert classify_relay_pending({**base, "created_at": "dün"}, now=now)[0] is None
    assert classify_relay_pending({**base, "schema_version": "lumos.payment.v1"}, now=now)[0] is None
    old = (now - dt.timedelta(hours=1)).isoformat()
    assert classify_relay_pending({**base, "created_at": old}, now=now)[0] is None
    assert classify_relay_pending({"source": "pc_remote", "approval_id": "a"}, now=now)[0] == KIND_PC_REMOTE


def test_strip_mobile_secrets_is_recursive() -> None:
    out = strip_mobile_secrets(
        {
            "approval_token": "a",
            "keep": 1,
            "nested": [{"relay_token": "b", "x_secret": "c", "ok": True}],
            "pc_remote_approval": {"approval_token": "d", "status": "approved"},
        }
    )
    assert out == {"keep": 1, "nested": [{"ok": True}], "pc_remote_approval": {"status": "approved"}}


def test_build_relay_pending_list_never_returns_tokens() -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    rows = build_relay_pending_list(
        [
            {"schema_version": "lumos.dispatch_pending_approval.v1", "created_at": now, "approval_token": "t1"},
            {"source": "pc_remote", "approval_id": "pc_remote_1", "approval_token": "t2"},
        ]
    )
    assert len(rows) == 2
    assert "t1" not in json.dumps(rows) and "t2" not in json.dumps(rows)


def test_sliding_window_limiter() -> None:
    lim = SlidingWindowLimiter(2, 10)
    assert lim.allow("a", now=0) and lim.allow("a", now=1)
    assert not lim.allow("a", now=2)
    assert lim.allow("b", now=2)
    assert lim.allow("a", now=11)


def test_mobile_web_ui_can_pair_with_code_and_send_tasks() -> None:
    """Geçici yüzey (iPhone Safari) CLI'sız eşleşebilir ve görev gönderebilir."""
    from kando_bridge.lan_relay import build_mobile_ui_html

    html = build_mobile_ui_html()
    assert 'id="pair-code-input"' in html
    assert '"/relay/pair"' in html
    assert '"/relay/task"' in html
    assert "location.hash" in html
    assert "history.replaceState" in html
    assert "approval_token" not in html


def test_mobile_web_ui_script_parses(tmp_path: Path) -> None:
    """Regresyon: tek tırnaklı dizedeki "PC'de" tüm betiği bozuyordu (sayfa hiç çalışmıyordu)."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node yok — JS sözdizimi kontrolü yapılamıyor")
    from kando_bridge.lan_relay import build_mobile_ui_html

    script = build_mobile_ui_html().split("<script>", 1)[1].split("</script>", 1)[0]
    js = tmp_path / "mobile_ui.js"
    js.write_text(script, encoding="utf-8")
    result = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
