"""Alexa+ MCP 2025-11-25 Streamable HTTP — contest slice for #854.

Runtime proof is this module imported and the HTTP handler actually invoked.
The web simulation at `/alexa-plus-simulasyon` is not this server.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path

import pytest
import requests

from alexa_plus_mcp import PROTOCOL_VERSION, SERVER_NAME, TOOL_NAME, handle_jsonrpc
from alexa_plus_mcp.protocol import Session, propose_lumos_task
from alexa_plus_mcp.server import ServerConfig, origin_allowed, serve

REPO = Path(__file__).resolve().parents[1]
TOKEN = "test-token-for-alexa-plus-mcp"
ACCEPT = "application/json, text/event-stream"


@pytest.fixture()
def mcp_http():
    httpd = serve(ServerConfig(token=TOKEN, host="127.0.0.1", port=0))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        yield base
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def _post(base: str, payload: dict, *, token: str = TOKEN, session: str | None = None,
          extra_headers: dict | None = None, initialized_header: bool = True) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": ACCEPT,
        "Content-Type": "application/json",
    }
    if session:
        headers["MCP-Session-Id"] = session
        if initialized_header:
            headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
    if extra_headers:
        headers.update(extra_headers)
    return requests.post(f"{base}/mcp", json=payload, headers=headers, timeout=2)


def _session(base: str) -> str:
    init = _post(
        base,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        },
        initialized_header=False,
    )
    assert init.status_code == 200, init.text
    sid = init.headers.get("MCP-Session-Id")
    assert sid
    body = init.json()
    assert body["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert body["result"]["serverInfo"]["name"] == SERVER_NAME
    ready = _post(
        base,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        session=sid,
    )
    assert ready.status_code == 202
    return sid


def test_runtime_hook_imports_and_calls_jsonrpc_handler() -> None:
    session = Session(session_id="unit")
    session.initialized = True
    outcome = handle_jsonrpc(
        {"jsonrpc": "2.0", "id": 7, "method": "tools/list"},
        session,
    )
    names = [tool["name"] for tool in outcome.body["result"]["tools"]]
    assert TOOL_NAME in names
    assert outcome.status == 200


def test_unauthenticated_post_is_401_without_www_authenticate(mcp_http: str) -> None:
    response = requests.post(
        f"{mcp_http}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Accept": ACCEPT, "Content-Type": "application/json"},
        timeout=2,
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" not in response.headers
    assert "WWW-Authenticate" not in {k.title() for k in response.headers}


def test_initialize_tools_list_and_call_over_streamable_http(mcp_http: str) -> None:
    sid = _session(mcp_http)
    listed = _post(mcp_http, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session=sid)
    assert listed.status_code == 200
    assert listed.headers["Content-Type"].startswith("application/json")
    tools = listed.json()["result"]["tools"]
    assert tools[0]["name"] == TOOL_NAME

    called = _post(
        mcp_http,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": TOOL_NAME,
                "arguments": {"request": "Yarın 14:00 için servis ziyareti görevi hazırla"},
            },
        },
        session=sid,
    )
    assert called.status_code == 200
    result = called.json()["result"]
    assert result["isError"] is False
    proposal = result["structuredContent"]
    assert proposal["requires_human_approval"] is True
    assert proposal["created"] is False
    assert proposal["writes_task"] is False
    assert proposal["title"]
    assert "14:00" in (proposal["time_note"] or "")


def test_invalid_origin_forbidden(mcp_http: str) -> None:
    response = _post(
        mcp_http,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                    "clientInfo": {"name": "x", "version": "0"}}},
        extra_headers={"Origin": "https://evil.example"},
        initialized_header=False,
    )
    assert response.status_code == 403


def test_localhost_origin_allowed(mcp_http: str) -> None:
    assert origin_allowed("http://127.0.0.1:9999", frozenset())
    assert origin_allowed(None, frozenset())
    assert not origin_allowed("https://evil.example", frozenset())
    response = _post(
        mcp_http,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                    "clientInfo": {"name": "x", "version": "0"}}},
        extra_headers={"Origin": "http://127.0.0.1:1234"},
        initialized_header=False,
    )
    assert response.status_code == 200


def test_unsupported_protocol_version_is_400(mcp_http: str) -> None:
    sid = _session(mcp_http)
    response = _post(
        mcp_http,
        {"jsonrpc": "2.0", "id": 9, "method": "ping"},
        session=sid,
        extra_headers={"MCP-Protocol-Version": "2024-11-05"},
    )
    assert response.status_code == 400


def test_get_mcp_is_405_json_mode(mcp_http: str) -> None:
    response = requests.get(f"{mcp_http}/mcp", timeout=2)
    assert response.status_code == 405


def test_health_reports_streamable_http(mcp_http: str) -> None:
    response = requests.get(f"{mcp_http}/health", timeout=2)
    assert response.status_code == 200
    body = response.json()
    assert body["protocolVersion"] == PROTOCOL_VERSION
    assert body["transport"] == "streamable-http"


def test_bind_is_localhost(mcp_http: str) -> None:
    host = mcp_http.split("://", 1)[1].rsplit(":", 1)[0]
    assert host in {"127.0.0.1", "localhost"}


def test_proposal_never_writes_task() -> None:
    proposal = propose_lumos_task("Pay the invoice tomorrow 09:00")
    assert proposal["created"] is False
    assert proposal["writes_task"] is False
    assert proposal["requires_human_approval"] is True


def test_contest_code_has_no_ring_scope() -> None:
    root = REPO / "src" / "alexa_plus_mcp"
    blob = " ".join(path.read_text(encoding="utf-8").lower() for path in root.glob("*.py"))
    assert "import ring" not in blob
    assert "from ring" not in blob
    assert "ring.com" not in blob


def test_simulation_page_is_marked_historical() -> None:
    page = (REPO / "ui" / "src" / "pages" / "alexa-plus-simulasyon.astro").read_text(encoding="utf-8")
    note = (REPO / "docs" / "analysis" / "amazon-alexa-plus-simulation-2026.md").read_text(encoding="utf-8")
    note_flat = re.sub(r"\s+", " ", note)
    assert "tarihsel" in page.lower()
    assert "tarihsel" in note.lower()
    assert "yarışma kabul kanıtı" in note_flat
    assert "python -m alexa_plus_mcp" in page
