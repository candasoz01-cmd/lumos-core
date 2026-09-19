"""Alexa+ MCP 2025-11-25 Streamable HTTP — contest slice for #854.

Runtime proof is this module imported and the HTTP handler actually invoked.
The web simulation at `/alexa-plus-simulasyon` is not this server.
"""

from __future__ import annotations

import base64
import re
import secrets
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from alexa_plus_mcp import PROTOCOL_VERSION, SERVER_NAME, TOOL_NAME, handle_jsonrpc
from alexa_plus_mcp.oauth import AuthServer, SCOPE_SERVICE, SCOPE_TOOLS, s256_challenge
from alexa_plus_mcp.protocol import Session, propose_lumos_task
from alexa_plus_mcp.server import ServerConfig, origin_allowed, serve

REPO = Path(__file__).resolve().parents[1]
TOKEN = "test-token-for-alexa-plus-mcp"
ACCEPT = "application/json, text/event-stream"
OAUTH_CLIENT_ID = "lumos-test-client"
OAUTH_CLIENT_SECRET = "lumos-test-secret"
OAUTH_REDIRECT = "https://example.test/alexa/callback"


def _serve(auth: AuthServer | None = None):
    httpd = serve(ServerConfig(token=TOKEN, host="127.0.0.1", port=0, auth=auth))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    base = f"http://{host}:{port}"
    if auth is not None:
        auth.public_url = base
    return httpd, thread, base


def _stop(httpd, thread) -> None:
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=2)


@pytest.fixture()
def mcp_http():
    httpd, thread, base = _serve()
    try:
        yield base
    finally:
        _stop(httpd, thread)


@pytest.fixture()
def mcp_oauth():
    auth = AuthServer(
        public_url="http://127.0.0.1:1",
        client_id=OAUTH_CLIENT_ID,
        client_secret=OAUTH_CLIENT_SECRET,
        redirect_uris=frozenset({OAUTH_REDIRECT}),
    )
    httpd, thread, base = _serve(auth)
    try:
        yield base, auth
    finally:
        _stop(httpd, thread)


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


def _basic_auth() -> str:
    raw = f"{OAUTH_CLIENT_ID}:{OAUTH_CLIENT_SECRET}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _token(base: str, form: dict[str, str], *, basic: bool = True) -> requests.Response:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if basic:
        headers["Authorization"] = _basic_auth()
    return requests.post(f"{base}/oauth/token", data=form, headers=headers, timeout=2)


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    return verifier, s256_challenge(verifier)


def test_oauth_metadata_has_s256_and_prm(mcp_oauth: tuple[str, AuthServer]) -> None:
    base, auth = mcp_oauth
    as_meta = requests.get(f"{base}/.well-known/oauth-authorization-server", timeout=2)
    prm = requests.get(f"{base}/.well-known/oauth-protected-resource", timeout=2)
    prm_mcp = requests.get(f"{base}/.well-known/oauth-protected-resource/mcp", timeout=2)
    assert as_meta.status_code == 200
    assert "S256" in as_meta.json()["code_challenge_methods_supported"]
    assert as_meta.json()["grant_types_supported"] == [
        "authorization_code",
        "client_credentials",
        "refresh_token",
    ]
    assert prm.status_code == 200
    assert prm.json()["resource"] == auth.resource
    assert prm.json()["authorization_servers"] == [auth.issuer]
    assert prm.json()["bearer_methods_supported"] == ["header"]
    assert prm_mcp.json() == prm.json()
    assert "WWW-Authenticate" not in as_meta.headers
    assert "WWW-Authenticate" not in prm.headers


def test_dcr_is_not_supported(mcp_oauth: tuple[str, AuthServer]) -> None:
    base, _auth = mcp_oauth
    response = requests.post(f"{base}/register", json={"redirect_uris": [OAUTH_REDIRECT]}, timeout=2)
    assert response.status_code == 404


def test_client_credentials_requires_resource_and_issues_service_token(
    mcp_oauth: tuple[str, AuthServer],
) -> None:
    base, auth = mcp_oauth
    missing = _token(base, {"grant_type": "client_credentials", "scope": SCOPE_SERVICE})
    assert missing.status_code == 400
    ok = _token(
        base,
        {
            "grant_type": "client_credentials",
            "scope": SCOPE_SERVICE,
            "resource": auth.resource,
        },
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["token_type"] == "Bearer"
    assert body["scope"] == SCOPE_SERVICE
    assert "refresh_token" not in body
    assert "WWW-Authenticate" not in ok.headers


def test_authorization_code_pkce_user_token_and_refresh_rotation(
    mcp_oauth: tuple[str, AuthServer],
) -> None:
    base, auth = mcp_oauth
    verifier, challenge = _pkce()
    authorize = requests.get(
        f"{base}/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": OAUTH_CLIENT_ID,
            "redirect_uri": OAUTH_REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": auth.resource,
            "scope": SCOPE_TOOLS,
            "state": "abc",
        },
        allow_redirects=False,
        timeout=2,
    )
    assert authorize.status_code == 302
    location = authorize.headers["Location"]
    assert location.startswith(OAUTH_REDIRECT)
    query = parse_qs(urlparse(location).query)
    assert query["state"] == ["abc"]
    code = query["code"][0]
    token = _token(
        base,
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": OAUTH_REDIRECT,
            "resource": auth.resource,
        },
    )
    assert token.status_code == 200
    body = token.json()
    assert body["scope"] == SCOPE_TOOLS
    refresh = body["refresh_token"]
    rotated = _token(
        base,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "resource": auth.resource,
        },
    )
    assert rotated.status_code == 200
    replay = _token(
        base,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "resource": auth.resource,
        },
    )
    assert replay.status_code == 400


def test_service_token_can_list_tools_but_cannot_call(
    mcp_oauth: tuple[str, AuthServer],
) -> None:
    base, auth = mcp_oauth
    issued = _token(
        base,
        {
            "grant_type": "client_credentials",
            "scope": SCOPE_SERVICE,
            "resource": auth.resource,
        },
    ).json()["access_token"]
    init = requests.post(
        f"{base}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "alexa+", "version": "0"},
            },
        },
        headers={
            "Authorization": f"Bearer {issued}",
            "Accept": ACCEPT,
            "Content-Type": "application/json",
        },
        timeout=2,
    )
    assert init.status_code == 200
    sid = init.headers["MCP-Session-Id"]
    ready = requests.post(
        f"{base}/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={
            "Authorization": f"Bearer {issued}",
            "Accept": ACCEPT,
            "Content-Type": "application/json",
            "MCP-Session-Id": sid,
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        },
        timeout=2,
    )
    assert ready.status_code == 202
    listed = requests.post(
        f"{base}/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        headers={
            "Authorization": f"Bearer {issued}",
            "Accept": ACCEPT,
            "Content-Type": "application/json",
            "MCP-Session-Id": sid,
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        },
        timeout=2,
    )
    assert listed.status_code == 200
    called = requests.post(
        f"{base}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": TOOL_NAME, "arguments": {"request": "prep a visit"}},
        },
        headers={
            "Authorization": f"Bearer {issued}",
            "Accept": ACCEPT,
            "Content-Type": "application/json",
            "MCP-Session-Id": sid,
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        },
        timeout=2,
    )
    assert called.status_code == 200
    assert called.json()["result"]["isError"] is True


def test_user_token_tools_call_does_not_write_task(
    mcp_oauth: tuple[str, AuthServer],
) -> None:
    base, auth = mcp_oauth
    verifier, challenge = _pkce()
    authorize = requests.get(
        f"{base}/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": OAUTH_CLIENT_ID,
            "redirect_uri": OAUTH_REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": auth.resource,
            "scope": SCOPE_TOOLS,
        },
        allow_redirects=False,
        timeout=2,
    )
    code = parse_qs(urlparse(authorize.headers["Location"]).query)["code"][0]
    access = _token(
        base,
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": OAUTH_REDIRECT,
            "resource": auth.resource,
        },
    ).json()["access_token"]
    init = requests.post(
        f"{base}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "alexa+", "version": "0"},
            },
        },
        headers={
            "Authorization": f"Bearer {access}",
            "Accept": ACCEPT,
            "Content-Type": "application/json",
        },
        timeout=2,
    )
    sid = init.headers["MCP-Session-Id"]
    requests.post(
        f"{base}/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={
            "Authorization": f"Bearer {access}",
            "Accept": ACCEPT,
            "Content-Type": "application/json",
            "MCP-Session-Id": sid,
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        },
        timeout=2,
    )
    called = requests.post(
        f"{base}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": TOOL_NAME, "arguments": {"request": "Yarın 14:00 servis"}},
        },
        headers={
            "Authorization": f"Bearer {access}",
            "Accept": ACCEPT,
            "Content-Type": "application/json",
            "MCP-Session-Id": sid,
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        },
        timeout=2,
    )
    proposal = called.json()["result"]["structuredContent"]
    assert called.json()["result"]["isError"] is False
    assert proposal["created"] is False
    assert proposal["writes_task"] is False
    assert proposal["requires_human_approval"] is True


def test_invalid_pkce_is_rejected(mcp_oauth: tuple[str, AuthServer]) -> None:
    base, auth = mcp_oauth
    _verifier, challenge = _pkce()
    authorize = requests.get(
        f"{base}/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": OAUTH_CLIENT_ID,
            "redirect_uri": OAUTH_REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": auth.resource,
            "scope": SCOPE_TOOLS,
        },
        allow_redirects=False,
        timeout=2,
    )
    code = parse_qs(urlparse(authorize.headers["Location"]).query)["code"][0]
    token = _token(
        base,
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": "this-verifier-does-not-match-the-challenge-value-xx",
            "redirect_uri": OAUTH_REDIRECT,
            "resource": auth.resource,
        },
    )
    assert token.status_code == 400


def test_oauth_401_has_no_www_authenticate(mcp_oauth: tuple[str, AuthServer]) -> None:
    base, _auth = mcp_oauth
    response = requests.post(
        f"{base}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Accept": ACCEPT, "Content-Type": "application/json"},
        timeout=2,
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" not in response.headers
    assert "WWW-Authenticate" not in {k.title() for k in response.headers}
