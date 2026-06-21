"""LAN relay MVP — discovery, pairing, pending proxy, approve/reject E2E."""
from __future__ import annotations

import json
import socket
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from kando_bridge.lan_relay import (
    RELAY_TOKEN_HEADER,
    LanRelayServer,
    RelayConfig,
    RelayState,
    build_beacon_payload,
    build_mobile_ui_html,
    filter_pc_remote_pending,
    listen_beacon_once,
    make_handler,
    mobile_ui_path,
)
from kando_bridge.mobile_approval_client import main as mobile_cli_main
from kando_bridge.pc_remote_tools import CMD_OPEN_APP
from kando_bridge.pending_approvals import PC_REMOTE_PENDING_SCHEMA, STATUS_PENDING


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
    handler.headers = {"Content-Length": str(len(raw))}
    handler.rfile = BytesIO(raw)
    handler.reject = None
    handler.last_json: tuple[int, dict[str, Any]] | None = None
    handler.client_address = ("127.0.0.1", 12345)

    def _reject(status: int, msg: str) -> None:
        handler.reject = (status, msg)

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        handler.last_json = (status, payload)

    handler._reject = _reject
    handler._send_json = _send_json
    return handler


def _make_mock_bridge_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    import kando_bridge.server as srv
    from kando_bridge.server import BridgeHandler, build_pending_approvals_list

    pending_dir = tmp_path / ".lumos" / "pending_approvals"
    pending_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pending_dir)
    monkeypatch.setenv("KANDO_BRIDGE_SECRET", "bridge-test-secret")

    def bridge_request(
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> tuple[int, dict[str, Any]]:
        if method.upper() == "GET" and path.startswith("/pending_approvals"):
            return 200, {"items": build_pending_approvals_list(include_approval_token=True)}
        if method.upper() == "POST" and path == "/tools/execute":
            obj = json.loads((body or b"{}").decode("utf-8"))
            handler = _bridge_handler_stub(body=obj)
            handler.headers["X-Kando-Token"] = headers.get("X-Kando-Token", "bridge-test-secret")
            BridgeHandler._handle_tools_execute(handler)
            assert handler.last_json is not None
            return handler.last_json
        if method.upper() == "POST" and path == "/approve":
            obj = json.loads((body or b"{}").decode("utf-8"))
            handler = _bridge_handler_stub(body=obj)
            BridgeHandler._handle_approve(handler)
            assert handler.last_json is not None
            return handler.last_json
        return 404, {"error": "not_found"}

    return bridge_request


def _relay_get(port: int, path: str, *, token: str | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if token:
        headers[RELAY_TOKEN_HEADER] = token
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method="GET")
    with urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _relay_post(
    port: int,
    path: str,
    body: dict[str, Any],
    *,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers[RELAY_TOKEN_HEADER] = token
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raw = e.read().decode("utf-8")
        payload = json.loads(raw) if raw.strip() else {"error": str(e)}
        return e.code, payload if isinstance(payload, dict) else {"error": str(payload)}


@pytest.fixture
def relay_server(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, RelayState, RelayConfig]:
    port = _free_port()
    beacon_port = _free_port()
    bridge_request = _make_mock_bridge_request(tmp_path, monkeypatch)
    config = RelayConfig(
        host="127.0.0.1",
        port=port,
        bridge_url="http://127.0.0.1:8765",
        bridge_secret="bridge-test-secret",
        device_name="Test-PC",
        enable_beacon=True,
        beacon_port=beacon_port,
        beacon_interval=0.2,
        bridge_request=bridge_request,
    )
    server = LanRelayServer(config)
    thread = threading.Thread(target=server.start, kwargs={"block": True}, daemon=True)
    thread.start()
    time.sleep(0.15)
    assert config.state is not None
    return port, config.state, config


def test_filter_pc_remote_pending() -> None:
    items = [
        {"source": "pc_remote", "approval_id": "a1"},
        {"source": "panel", "approval_id": "a2"},
        {"schema_version": PC_REMOTE_PENDING_SCHEMA, "approval_id": "a3"},
    ]
    filtered = filter_pc_remote_pending(items)
    assert len(filtered) == 2
    assert {x["approval_id"] for x in filtered} == {"a1", "a3"}


def test_pairing_requires_valid_code(relay_server: tuple[int, RelayState, RelayConfig]) -> None:
    port, state, _ = relay_server
    status, payload = _relay_post(port, "/relay/pair", {"pairing_code": "WRONG1"})
    assert status == 403
    assert payload["error"] == "invalid_pairing_code"

    status, payload = _relay_post(port, "/relay/pair", {"pairing_code": state.pairing_id})
    assert status == 200
    assert payload.get("relay_token")


def test_pending_requires_relay_token(relay_server: tuple[int, RelayState, RelayConfig]) -> None:
    port, _, _ = relay_server
    with pytest.raises(Exception):
        _relay_get(port, "/relay/pending")


def test_discover_no_secret(relay_server: tuple[int, RelayState, RelayConfig]) -> None:
    port, state, _ = relay_server
    status, payload = _relay_get(port, "/relay/discover")
    assert status == 200
    assert payload["pairing_id"] == state.pairing_id
    assert "KANDO_BRIDGE_SECRET" not in json.dumps(payload)
    assert payload["device_name"] == "Test-PC"


def test_lan_relay_mvp_e2e(
    relay_server: tuple[int, RelayState, RelayConfig],
) -> None:
    """Create pending on bridge → mobile lists via relay → approve → re-execute stub."""
    port, state, config = relay_server
    bridge_request = config.bridge_request
    assert bridge_request is not None

    status, pending_out = bridge_request(
        "POST",
        "/tools/execute",
        {"X-Kando-Token": "bridge-test-secret", "Content-Type": "application/json"},
        json.dumps(
            {"command": CMD_OPEN_APP, "arguments": {"app_name": "Safari"}},
            ensure_ascii=False,
        ).encode("utf-8"),
    )
    assert status == 200
    assert pending_out["status"] == "pending_approval"
    approval_token = pending_out["approval_token"]
    approval_file = pending_out["approval_file"]
    approval_id = pending_out["approval_id"]

    _, pair_payload = _relay_post(
        port,
        "/relay/pair",
        {"pairing_code": state.pairing_id, "mobile_device_id": "test-phone"},
    )
    relay_token = pair_payload["relay_token"]

    _, list_payload = _relay_get(port, "/relay/pending", token=relay_token)
    assert list_payload["count"] == 1
    assert list_payload["pending"][0]["approval_id"] == approval_id
    assert list_payload["pending"][0]["status"] == STATUS_PENDING

    _, approve_payload = _relay_post(
        port,
        "/relay/approve",
        {"approval_file": approval_file, "approval_token": approval_token},
        token=relay_token,
    )
    assert approve_payload.get("accepted") is True
    assert approve_payload.get("pc_remote_approval", {}).get("status") == "approved"

    status, exec_out = bridge_request(
        "POST",
        "/tools/execute",
        {"X-Kando-Token": "bridge-test-secret", "Content-Type": "application/json"},
        json.dumps(
            {
                "command": CMD_OPEN_APP,
                "arguments": {"app_name": "Safari"},
                "approval_token": approval_token,
                "approval_id": approval_id,
            },
            ensure_ascii=False,
        ).encode("utf-8"),
    )
    assert status == 200
    assert exec_out["status"] == "stub"
    assert exec_out["ok"] is True


def test_mobile_client_discover_and_pending_cli(
    relay_server: tuple[int, RelayState, RelayConfig],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    port, state, config = relay_server
    relay_url = f"http://127.0.0.1:{port}"
    bridge_request = config.bridge_request
    assert bridge_request is not None

    bridge_request(
        "POST",
        "/tools/execute",
        {"Content-Type": "application/json"},
        json.dumps(
            {"command": CMD_OPEN_APP, "arguments": {"app_name": "Notes"}},
            ensure_ascii=False,
        ).encode("utf-8"),
    )

    assert mobile_cli_main(["--relay-url", relay_url, "discover"]) == 0
    discover_out = capsys.readouterr().out
    assert state.pairing_id in discover_out

    capsys.readouterr()
    assert mobile_cli_main(["--relay-url", relay_url, "pair", state.pairing_id]) == 0
    pair_raw = capsys.readouterr().out
    pair_out = json.loads(pair_raw[pair_raw.index("{") :])
    relay_token = pair_out["relay_token"]

    monkeypatch.setenv("LUMOS_RELAY_TOKEN", relay_token)
    assert mobile_cli_main(["--relay-url", relay_url, "pending"]) == 0
    pending_raw = capsys.readouterr().out
    pending_out = json.loads(pending_raw[pending_raw.index("{") :])
    assert pending_out["count"] >= 1


def test_udp_beacon_loopback() -> None:
    state = RelayState(device_name="BeaconPC", pairing_id="BEAC01")
    port = _free_port()
    received: list[dict[str, Any] | None] = []

    def _listen() -> None:
        received.append(listen_beacon_once(timeout=3.0, port=port))

    listener = threading.Thread(target=_listen, daemon=True)
    listener.start()
    time.sleep(0.05)
    payload = json.dumps(build_beacon_payload(state, 8766), ensure_ascii=False).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(payload, ("127.0.0.1", port))
    finally:
        sock.close()
    listener.join(timeout=3.0)
    assert received and received[0] is not None
    msg = received[0]
    assert msg["pairing_id"] == "BEAC01"
    assert msg["relay_port"] == 8766
    assert "secret" not in json.dumps(msg).lower()


def test_relay_mobile_ui_route(relay_server: tuple[int, RelayState, RelayConfig]) -> None:
    """GET /relay/mobile returns HTML with approve/reject controls."""
    port, _, _ = relay_server
    req = Request(f"http://127.0.0.1:{port}/relay/mobile", method="GET")
    with urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
    assert "Onayla / Approve" in html
    assert "Reddet / Reject" in html
    assert "PC isteği onayı" in html
    assert "/relay/pending" in html
    assert "/relay/approve" in html


def test_pair_returns_mobile_url(relay_server: tuple[int, RelayState, RelayConfig]) -> None:
    port, state, _ = relay_server
    _, payload = _relay_post(port, "/relay/pair", {"pairing_code": state.pairing_id})
    assert payload.get("relay_token")
    mobile_url = payload.get("mobile_url") or payload.get("mobile_ui")
    assert mobile_url
    assert mobile_url.startswith("/relay/mobile?token=")


def test_mobile_ui_path_helper() -> None:
    assert mobile_ui_path() == "/relay/mobile"
    assert mobile_ui_path(token="abc") == "/relay/mobile?token=abc"


def test_build_mobile_ui_html_contains_controls() -> None:
    html = build_mobile_ui_html()
    assert "btn-ok" in html
    assert "btn-no" in html
    assert 'data-act="approve"' in html
    assert 'data-act="reject"' in html
    assert "/relay/approve" in html
    assert "/relay/reject" in html
    assert "approval_token" in html


def test_relay_invalid_token_error_payload(relay_server: tuple[int, RelayState, RelayConfig]) -> None:
    port, _, _ = relay_server
    req = Request(
        f"http://127.0.0.1:{port}/relay/pending",
        headers={RELAY_TOKEN_HEADER: "bad-token", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=5) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        status = e.code
        payload = json.loads(e.read().decode("utf-8"))
    assert status == 401
    assert payload["error"] == "invalid_relay_token"
    assert payload.get("message_tr")
    assert payload.get("message_en")


def test_reject_via_relay(relay_server: tuple[int, RelayState, RelayConfig]) -> None:
    port, state, config = relay_server
    bridge_request = config.bridge_request
    assert bridge_request is not None

    _, pending_out = bridge_request(
        "POST",
        "/tools/execute",
        {"Content-Type": "application/json"},
        json.dumps(
            {"command": CMD_OPEN_APP, "arguments": {"app_name": "Mail"}},
            ensure_ascii=False,
        ).encode("utf-8"),
    )
    _, pair_payload = _relay_post(port, "/relay/pair", {"pairing_code": state.pairing_id})
    relay_token = pair_payload["relay_token"]

    _, reject_payload = _relay_post(
        port,
        "/relay/reject",
        {
            "approval_file": pending_out["approval_file"],
            "approval_token": pending_out["approval_token"],
        },
        token=relay_token,
    )
    assert reject_payload.get("accepted") is True
    assert reject_payload.get("closed") is True

    _, list_payload = _relay_get(port, "/relay/pending", token=relay_token)
    assert list_payload["count"] == 0


def test_handler_unit_pairing_expired() -> None:
    state = RelayState()
    config = RelayConfig(
        host="127.0.0.1",
        port=9999,
        enable_beacon=False,
        state=state,
        bridge_request=lambda *_a, **_k: (200, {}),
    )
    state.pairing_expires_at = time.time() - 1
    handler_cls = make_handler(config)
    handler = handler_cls.__new__(handler_cls)
    handler.headers = {"Content-Length": "28"}
    handler.path = "/relay/pair"
    handler.rfile = BytesIO(b'{"pairing_code":"ABC123"}')
    sent: list[tuple[int, dict[str, Any]]] = []

    def _send_json(status: int, payload: dict[str, Any]) -> None:
        sent.append((status, payload))

    handler._send_json = _send_json  # type: ignore[method-assign]
    handler.do_POST()
    assert sent[0][0] == 403
    assert sent[0][1]["error"] == "pairing_expired"


def test_beacon_payload_shape() -> None:
    state = RelayState(device_name="MyPC", pairing_id="ABC123")
    payload = build_beacon_payload(state, 8766)
    assert payload["pairing_id"] == "ABC123"
    assert payload["pc_name"] == "MyPC"
    assert payload["relay_port"] == 8766
