"""
LAN relay — demo-safe MVP between Lumos PC bridge (loopback) and Lumos Mobile.

Forwards approval list / approve / reject to local kando_bridge without exposing
KANDO_BRIDGE_SECRET to mobile clients. Pairing uses a short-lived pairing code;
mobile receives a relay-scoped token after POST /relay/pair.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import socket
import string
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from kando_bridge.pending_approvals import is_pc_remote_pending

SCHEMA_VERSION = "lumos.lan_relay.v1"
DEFAULT_RELAY_HOST = "0.0.0.0"
DEFAULT_RELAY_PORT = 8766
DEFAULT_BRIDGE_URL = "http://127.0.0.1:8765"
DEFAULT_PAIRING_TTL_SECONDS = 600
DEFAULT_BEACON_PORT = 8767
BEACON_INTERVAL_SECONDS = 3.0
RELAY_TOKEN_HEADER = "X-Relay-Token"

BridgeRequestFn = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, Any]]]


def _read_bridge_secret() -> str:
    return (os.environ.get("KANDO_BRIDGE_SECRET") or "").strip()


def _normalize_path(path: str) -> str:
    p = path or "/"
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    return p


def _pairing_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _device_id() -> str:
    return secrets.token_hex(8)


def _relay_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass
class PairedClient:
    relay_token: str
    mobile_device_id: str
    paired_at: float
    expires_at: float


@dataclass
class RelayState:
    pairing_id: str = field(default_factory=_pairing_code)
    device_id: str = field(default_factory=_device_id)
    device_name: str = "Lumos-PC"
    pairing_expires_at: float = 0.0
    paired_clients: dict[str, PairedClient] = field(default_factory=dict)
    relay_base_url: str = ""

    def refresh_pairing(self, ttl_seconds: int) -> None:
        self.pairing_id = _pairing_code()
        self.pairing_expires_at = time.time() + max(60, ttl_seconds)

    def pairing_valid(self) -> bool:
        return time.time() < self.pairing_expires_at

    def discover_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            # Eşleştirme kodu kimlik doğrulamasız keşif yanıtında verilmez:
            # LAN'daki herhangi biri kodu alıp relay_token çıkarabilirdi.
            # Kod yalnız PC yüzeyinde gösterilir ve bant dışı taşınır.
            "device_id": self.device_id,
            "device_name": self.device_name,
            "relay_url": self.relay_base_url,
            "requires_pairing": True,
            "pairing_expires_at": int(self.pairing_expires_at),
        }

    def pair(self, pairing_code: str, mobile_device_id: str | None, ttl_seconds: int) -> tuple[str | None, str]:
        code = (pairing_code or "").strip().upper()
        if not code:
            return None, "pairing_code_required"
        if not self.pairing_valid():
            return None, "pairing_expired"
        if not hmac.compare_digest(code, self.pairing_id or ""):
            return None, "invalid_pairing_code"
        token = _relay_token()
        mobile_id = (mobile_device_id or "").strip() or f"mobile_{secrets.token_hex(4)}"
        now = time.time()
        self.paired_clients[token] = PairedClient(
            relay_token=token,
            mobile_device_id=mobile_id,
            paired_at=now,
            expires_at=now + max(3600, ttl_seconds * 6),
        )
        return token, ""

    def validate_relay_token(self, token: str) -> tuple[bool, str]:
        tok = (token or "").strip()
        if not tok:
            return False, "relay_token_required"
        client = self.paired_clients.get(tok)
        if client is None:
            return False, "invalid_relay_token"
        if time.time() > client.expires_at:
            self.paired_clients.pop(tok, None)
            return False, "relay_token_expired"
        return True, ""


def default_bridge_request(
    method: str,
    path: str,
    headers: dict[str, str],
    body: bytes | None,
    *,
    bridge_url: str,
    bridge_secret: str,
) -> tuple[int, dict[str, Any]]:
    url = bridge_url.rstrip("/") + path
    req_headers = dict(headers)
    if bridge_secret:
        req_headers["X-Kando-Token"] = bridge_secret
    req = Request(url, data=body, method=method.upper(), headers=req_headers)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw.strip() else {}
            if not isinstance(payload, dict):
                if isinstance(payload, list):
                    return resp.status, {"items": payload}
                return resp.status, {"raw": payload}
            return resp.status, payload
    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            payload = json.loads(err_body) if err_body.strip() else {"error": str(e)}
        except (OSError, json.JSONDecodeError):
            payload = {"error": str(e)}
        if not isinstance(payload, dict):
            payload = {"error": str(payload)}
        return e.code, payload
    except (URLError, OSError, json.JSONDecodeError) as e:
        from kando_bridge.relay_errors import enrich_error_payload

        return 502, enrich_error_payload(
            {"ok": False, "error": "bridge_unreachable", "detail": str(e)}
        )


def mobile_ui_path(*, token: str | None = None) -> str:
    """Relative path to the mobile approval web UI."""
    if token:
        return f"/relay/mobile?token={token}"
    return "/relay/mobile"


def build_mobile_ui_html() -> str:
    """Responsive mobile web UI for pending PC remote approvals (OSS demo)."""
    return """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Lumos Onay / Approval</title>
<style>
:root { color-scheme: light dark; --bg: #f4f4f5; --card: #fff; --text: #18181b; --muted: #71717a;
  --ok: #16a34a; --no: #dc2626; --accent: #2563eb; --border: #e4e4e7; --warn: #b45309; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #09090b; --card: #18181b; --text: #fafafa; --muted: #a1a1aa;
    --border: #3f3f46; --warn: #fbbf24; }
}
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: var(--bg);
  color: var(--text); min-height: 100dvh; padding-bottom: env(safe-area-inset-bottom, 0); }
header { padding: 1rem 1rem 0.5rem; position: sticky; top: 0; background: var(--bg);
  border-bottom: 1px solid var(--border); z-index: 1; }
h1 { margin: 0; font-size: 1.125rem; }
.sub { color: var(--muted); font-size: 0.8125rem; margin-top: 0.25rem; }
#status { font-size: 0.75rem; color: var(--muted); margin-top: 0.5rem; }
#error-banner { display: none; margin-top: 0.5rem; padding: 0.625rem 0.75rem;
  border-radius: 8px; background: #fef2f2; color: #991b1b; font-size: 0.8125rem; }
@media (prefers-color-scheme: dark) {
  #error-banner { background: #450a0a; color: #fecaca; }
}
#error-banner.visible { display: block; }
main { padding: 0.75rem 1rem 2rem; display: grid; gap: 0.75rem; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 16px;
  padding: 1.25rem 1rem; }
.headline { font-weight: 700; font-size: 1.125rem; line-height: 1.35; word-break: break-word; }
.detail { font-size: 0.9375rem; color: var(--muted); margin-top: 0.5rem; word-break: break-all; }
.risk { display: inline-block; padding: 0.2rem 0.625rem; border-radius: 999px;
  font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.04em;
  border: 1px solid var(--border); margin-top: 0.75rem; }
.risk-high { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
.risk-medium { background: #fef3c7; color: #92400e; border-color: #fde68a; }
@media (prefers-color-scheme: dark) {
  .risk-high { background: #450a0a; color: #fecaca; }
  .risk-medium { background: #422006; color: #fde68a; }
}
.expiry { font-size: 0.8125rem; color: var(--warn); margin-top: 0.75rem; font-weight: 500; }
.expiry.urgent { color: var(--no); }
.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 0.625rem; margin-top: 1.25rem; }
button { border: none; border-radius: 12px; padding: 1rem 0.75rem; min-height: 56px;
  font-size: 1rem; font-weight: 700; cursor: pointer; }
.btn-ok { background: var(--ok); color: #fff; }
.btn-no { background: var(--no); color: #fff; }
button:disabled { opacity: 0.45; cursor: not-allowed; }
.empty { text-align: center; color: var(--muted); padding: 2.5rem 1rem; line-height: 1.5; }
.token-box { margin-top: 0.75rem; display: grid; gap: 0.5rem; }
.token-box input { width: 100%; padding: 0.625rem; border-radius: 8px; border: 1px solid var(--border);
  background: var(--card); color: var(--text); font-size: 0.875rem; }
.token-box button { background: var(--accent); color: #fff; min-height: auto; padding: 0.75rem; }
.hidden { display: none; }
.preview-toggle { margin-top: 0.5rem; font-size: 0.75rem; color: var(--accent); background: none;
  border: none; padding: 0; min-height: auto; font-weight: 500; cursor: pointer; }
.preview { margin-top: 0.5rem; font-size: 0.75rem; font-family: ui-monospace, monospace;
  background: var(--bg); padding: 0.5rem; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }
</style>
</head>
<body>
<header>
  <h1 id="device-label">Lumos-PC</h1>
  <div class="sub">Bekleyen isteği onaylayın veya reddedin / Review pending request</div>
  <div id="status">—</div>
  <div id="error-banner" role="alert"></div>
  <div id="token-setup" class="token-box hidden">
    <input id="token-input" type="text" placeholder="Relay token / eşleştirme token" autocomplete="off">
    <button type="button" id="token-save">Kaydet / Save</button>
  </div>
</header>
<main id="list"></main>
<script>
const RELAY_HEADER = "X-Relay-Token";
const TOKEN_KEY = "lumos_relay_token";
const params = new URLSearchParams(location.search);
let relayToken = params.get("token") || sessionStorage.getItem(TOKEN_KEY) || "";
let countdownTimer = null;

function setStatus(msg) { document.getElementById("status").textContent = msg; }
function showError(msg) {
  const el = document.getElementById("error-banner");
  if (!msg) { el.classList.remove("visible"); el.textContent = ""; return; }
  el.textContent = msg;
  el.classList.add("visible");
}
function showTokenSetup(show) {
  document.getElementById("token-setup").classList.toggle("hidden", !show);
}
function saveToken(tok) {
  relayToken = (tok || "").trim();
  if (relayToken) {
    sessionStorage.setItem(TOKEN_KEY, relayToken);
    showTokenSetup(false);
    poll();
  }
}
if (params.get("token")) saveToken(params.get("token"));
else if (!relayToken) showTokenSetup(true);

document.getElementById("token-save").addEventListener("click", () => {
  saveToken(document.getElementById("token-input").value);
});

function esc(s) {
  return String(s ?? "").replace(/[&<>\"']/g, c =>
    ({ "&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;" }[c]));
}

const CMD_LABELS = {
  pc_open_url: "Web adresi aç / Open web address",
  pc_open_app: "Uygulama aç / Open application",
  pc_type_text: "Metin yaz / Type text",
  pc_suggest_click: "Tıklama öner / Suggest click",
  pc_request_file_picker: "Dosya seç / Pick a file",
  pc_read_screen: "Ekranı oku / Read screen",
};

function headline(item) {
  const action = String(item.required_user_action || item.pending_summary || item.title || "").trim();
  if (action) return action.split(" / ")[0].trim() || action;
  return CMD_LABELS[item.command] || "PC isteği / PC request";
}

function detailLine(item) {
  const prev = item.arguments_preview || item.arguments || {};
  if (item.command === "pc_open_url" && prev.url) return String(prev.url);
  if (item.command === "pc_open_app" && prev.app_name) return String(prev.app_name);
  if (item.command === "pc_type_text" && prev.text) {
    const t = String(prev.text);
    return t.length > 80 ? t.slice(0, 80) + "…" : t;
  }
  if (prev.target_description) return String(prev.target_description);
  if (prev.purpose) return String(prev.purpose);
  return "";
}

function formatExpiry(expiresAt) {
  if (!expiresAt) return "";
  const end = new Date(expiresAt);
  if (isNaN(end.getTime())) return "";
  const sec = Math.max(0, Math.floor((end - Date.now()) / 1000));
  if (sec <= 0) return "Süresi doldu / Expired";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m >= 60) return "≈" + Math.floor(m / 60) + " saat kaldı / h left";
  if (m > 0) return "≈" + m + " dk " + s + " sn kaldı / left";
  return sec + " sn kaldı / sec left";
}

function riskClass(level) {
  const l = String(level || "").toLowerCase();
  if (l === "high") return "risk risk-high";
  if (l === "medium") return "risk risk-medium";
  return "risk hidden";
}

function riskLabel(level) {
  const l = String(level || "").toLowerCase();
  if (l === "high") return "Yüksek risk / High risk";
  if (l === "medium") return "Orta risk / Medium risk";
  return "";
}

async function api(method, path, body) {
  const headers = { "Accept": "application/json" };
  if (relayToken) headers[RELAY_HEADER] = relayToken;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message_en || data.message_tr || data.error || res.statusText || "request_failed");
  return data;
}

function renderFocusItem(item) {
  const card = document.createElement("article");
  card.className = "card";
  const det = detailLine(item);
  const rl = riskLabel(item.risk_level);
  card.innerHTML = `
    <div class="headline">${esc(headline(item))}</div>
    ${det ? `<div class="detail">${esc(det)}</div>` : ""}
    ${rl ? `<div class="${riskClass(item.risk_level)}">${esc(rl)}</div>` : ""}
    <div class="expiry" id="expiry-line">${esc(formatExpiry(item.expires_at))}</div>
    <button type="button" class="preview-toggle hidden" id="preview-toggle">Detayları göster / Show details</button>
    <pre class="preview hidden" id="preview-block"></pre>
    <div class="actions">
      <button type="button" class="btn-no" data-act="reject">Reddet / Reject</button>
      <button type="button" class="btn-ok" data-act="approve">Onayla / Approve</button>
    </div>`;
  const preview = item.arguments_preview || item.arguments || {};
  const previewBlock = card.querySelector("#preview-block");
  const previewToggle = card.querySelector("#preview-toggle");
  if (preview && Object.keys(preview).length) {
    previewBlock.textContent = JSON.stringify(preview, null, 2);
    previewToggle.classList.remove("hidden");
    previewToggle.addEventListener("click", () => {
      const open = previewBlock.classList.toggle("hidden");
      previewToggle.textContent = open
        ? "Detayları göster / Show details"
        : "Detayları gizle / Hide details";
    });
  }
  const expiryEl = card.querySelector("#expiry-line");
  function tickExpiry() {
    if (!expiryEl || !item.expires_at) return;
    const txt = formatExpiry(item.expires_at);
    expiryEl.textContent = txt;
    expiryEl.classList.toggle("urgent", txt.includes("dk") && parseInt(txt, 10) <= 2 || txt.includes("sn"));
  }
  tickExpiry();
  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = setInterval(tickExpiry, 1000);
  card.querySelectorAll(".actions button").forEach(btn => {
    btn.addEventListener("click", async () => {
      const approved = btn.dataset.act === "approve";
      card.querySelectorAll("button").forEach(b => b.disabled = true);
      showError("");
      try {
        await api("POST", approved ? "/relay/approve" : "/relay/reject", {
          approval_file: item.approval_file,
          approval_token: item.approval_token,
          approval_id: item.approval_id,
        });
        setStatus(approved ? "Onaylandı / Approved" : "Reddedildi / Rejected");
        poll();
      } catch (e) {
        showError("Hata / Error: " + e.message);
        card.querySelectorAll("button").forEach(b => { if (!b.classList.contains("preview-toggle")) b.disabled = false; });
      }
    });
  });
  return card;
}

async function poll() {
  if (!relayToken) {
    setStatus("Token gerekli / Token required");
    showTokenSetup(true);
    return;
  }
  setStatus("Yükleniyor… / Loading…");
  showError("");
  const root = document.getElementById("list");
  try {
    const data = await api("GET", "/relay/pending");
    const items = data.pending || [];
    root.replaceChildren();
    if (!items.length) {
      if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
      root.innerHTML = '<div class="empty"><strong>Bekleyen istek yok</strong><br>No pending requests<br><span style="font-size:0.8125rem">PC'de yeni bir işlem gelince burada görünür</span></div>';
      setStatus("Hazır / Ready");
    } else {
      const focus = items[0];
      root.appendChild(renderFocusItem(focus));
      setStatus(items.length === 1 ? "1 bekleyen istek / 1 pending" : items.length + " bekleyen — ilk gösteriliyor / showing first");
    }
  } catch (e) {
    root.replaceChildren();
    root.innerHTML = '<div class="empty">' + esc(e.message) + '</div>';
    showError("Bağlantı hatası / Connection error: " + e.message);
    setStatus("Bağlantı kesildi / Disconnected");
    if (String(e.message).includes("relay_token")) showTokenSetup(true);
  }
}

poll();
setInterval(poll, 5000);
</script>
</body>
</html>"""


def filter_pc_remote_pending(items: list[Any]) -> list[dict[str, Any]]:
    """Keep pc_remote rows; bridge list API may omit source/schema_version."""
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if is_pc_remote_pending(item):
            out.append(item)
            continue
        aid = str(item.get("approval_id") or "")
        if aid.startswith("pc_remote_") or item.get("command"):
            out.append(item)
    return out


@dataclass
class RelayConfig:
    host: str = DEFAULT_RELAY_HOST
    port: int = DEFAULT_RELAY_PORT
    bridge_url: str = DEFAULT_BRIDGE_URL
    bridge_secret: str = ""
    device_name: str = "Lumos-PC"
    pairing_ttl_seconds: int = DEFAULT_PAIRING_TTL_SECONDS
    enable_beacon: bool = True
    beacon_port: int = DEFAULT_BEACON_PORT
    beacon_interval: float = BEACON_INTERVAL_SECONDS
    state: RelayState | None = None
    bridge_request: BridgeRequestFn | None = None

    def __post_init__(self) -> None:
        if not self.bridge_secret:
            self.bridge_secret = _read_bridge_secret()
        if self.state is None:
            self.state = RelayState(device_name=self.device_name)
        self.state.device_name = self.device_name
        self.state.refresh_pairing(self.pairing_ttl_seconds)

    def relay_base_url(self) -> str:
        if self.state and self.state.relay_base_url:
            return self.state.relay_base_url
        host = self.host
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        return f"http://{host}:{self.port}"

    def make_bridge_request(self) -> BridgeRequestFn:
        if self.bridge_request is not None:
            return self.bridge_request

        bridge_url = self.bridge_url
        bridge_secret = self.bridge_secret

        def _req(
            method: str,
            path: str,
            headers: dict[str, str],
            body: bytes | None,
        ) -> tuple[int, dict[str, Any]]:
            return default_bridge_request(
                method,
                path,
                headers,
                body,
                bridge_url=bridge_url,
                bridge_secret=bridge_secret,
            )

        return _req


def build_beacon_payload(state: RelayState, relay_port: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "pairing_id": state.pairing_id,
        "relay_port": relay_port,
        "pc_name": state.device_name,
        "device_id": state.device_id,
    }


class BeaconBroadcaster:
    """UDP broadcast beacon — pairing_id only; no bridge secret."""

    def __init__(
        self,
        state: RelayState,
        relay_port: int,
        beacon_port: int = DEFAULT_BEACON_PORT,
        interval: float = BEACON_INTERVAL_SECONDS,
    ) -> None:
        self._state = state
        self._relay_port = relay_port
        self._beacon_port = beacon_port
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="lan-relay-beacon", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            while not self._stop.is_set():
                if self._state.pairing_valid():
                    payload = json.dumps(
                        build_beacon_payload(self._state, self._relay_port),
                        ensure_ascii=False,
                    ).encode("utf-8")
                    try:
                        sock.sendto(payload, ("255.255.255.255", self._beacon_port))
                        sock.sendto(payload, ("127.0.0.1", self._beacon_port))
                    except OSError:
                        pass
                self._stop.wait(self._interval)
        finally:
            sock.close()


def listen_beacon_once(
    *,
    timeout: float = 2.0,
    port: int = DEFAULT_BEACON_PORT,
) -> dict[str, Any] | None:
    """Receive one LAN beacon (CI-friendly via 127.0.0.1 loopback)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)
    try:
        sock.bind(("0.0.0.0", port))
        data, _addr = sock.recvfrom(4096)
        obj = json.loads(data.decode("utf-8"))
        return obj if isinstance(obj, dict) else None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    finally:
        sock.close()


def make_handler(config: RelayConfig) -> type[BaseHTTPRequestHandler]:
    state = config.state
    assert state is not None
    bridge_request = config.make_bridge_request()

    class LanRelayHandler(BaseHTTPRequestHandler):
        server_version = "LumosLanRelay/1.0"

        def log_message(self, fmt: str, *args: object) -> None:
            line = f"[lan_relay] {self.address_string()} — {fmt % args}\n"
            sys.stderr.write(line)

        def end_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers",
                f"Content-Type, {RELAY_TOKEN_HEADER}",
            )
            super().end_headers()

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.end_headers()

        def _read_json_body(self) -> tuple[dict[str, Any] | None, str | None]:
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
            except (TypeError, ValueError):
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            if not raw:
                return {}, None
            try:
                obj = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                return None, f"invalid_json: {e}"
            if not isinstance(obj, dict):
                return None, "json_object_required"
            return obj, None

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, status: int, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _relay_token(self) -> str:
            return (self.headers.get(RELAY_TOKEN_HEADER) or "").strip()

        def _require_relay_token(self) -> bool:
            ok, err = state.validate_relay_token(self._relay_token())
            if ok:
                return True
            from kando_bridge.relay_errors import enrich_error_payload

            self._send_json(401, enrich_error_payload({"ok": False, "error": err}))
            return False

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = _normalize_path(parsed.path)
            if path == "/relay/mobile":
                self._send_html(200, build_mobile_ui_html())
                return
            if path == "/relay/discover":
                # Kimlik doğrulamasız istek eşleştirme penceresini yenileyemez;
                # aksi halde pencere dışarıdan süresiz açık tutulabilirdi.
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "pairing_open": state.pairing_valid(),
                        **state.discover_payload(),
                    },
                )
                return
            if path == "/health":
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "service": "lumos_lan_relay",
                        "schema_version": SCHEMA_VERSION,
                        "pairing_valid": state.pairing_valid(),
                    },
                )
                return
            if path == "/relay/pending":
                if not self._require_relay_token():
                    return
                status, payload = bridge_request(
                    "GET",
                    "/pending_approvals?include_tokens=1",
                    {},
                    None,
                )
                items: list[Any]
                if isinstance(payload, list):
                    items = payload
                elif isinstance(payload.get("items"), list):
                    items = payload["items"]
                elif isinstance(payload.get("pending"), list):
                    items = payload["pending"]
                else:
                    items = []
                filtered = filter_pc_remote_pending(items)
                self._send_json(
                    status if 200 <= status < 300 else 200,
                    {"ok": True, "pending": filtered, "count": len(filtered)},
                )
                return
            self._send_json(404, {"ok": False, "error": "not_found"})

        def do_POST(self) -> None:
            path = _normalize_path(urlparse(self.path).path)
            body, err = self._read_json_body()
            if err:
                self._send_json(400, {"ok": False, "error": err})
                return
            assert body is not None

            if path == "/relay/pair":
                token, pair_err = state.pair(
                    str(body.get("pairing_code") or body.get("pairing_id") or ""),
                    str(body.get("mobile_device_id") or "") or None,
                    config.pairing_ttl_seconds,
                )
                if token is None:
                    from kando_bridge.relay_errors import enrich_error_payload

                    self._send_json(
                        403,
                        enrich_error_payload({"ok": False, "error": pair_err}),
                    )
                    return
                mobile_path = mobile_ui_path(token=token)
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "relay_token": token,
                        "device_id": state.device_id,
                        "device_name": state.device_name,
                        "schema_version": SCHEMA_VERSION,
                        "mobile_url": mobile_path,
                        "mobile_ui": mobile_path,
                    },
                )
                return

            if path in ("/relay/approve", "/relay/reject"):
                if not self._require_relay_token():
                    return
                approved = path == "/relay/approve"
                bridge_body = {
                    "approved": approved,
                    "approval_token": str(body.get("approval_token") or ""),
                }
                if body.get("approval_file"):
                    bridge_body["approval_file"] = str(body.get("approval_file"))
                if body.get("approval_id"):
                    bridge_body["task_id"] = str(body.get("approval_id"))
                if body.get("task_id"):
                    bridge_body["task_id"] = str(body.get("task_id"))
                raw = json.dumps(bridge_body, ensure_ascii=False).encode("utf-8")
                status, payload = bridge_request(
                    "POST",
                    "/approve",
                    {"Content-Type": "application/json; charset=utf-8"},
                    raw,
                )
                self._send_json(status, {"ok": 200 <= status < 300, **payload})
                return

            self._send_json(404, {"ok": False, "error": "not_found"})

    return LanRelayHandler


class LanRelayServer:
    def __init__(self, config: RelayConfig) -> None:
        self.config = config
        self._httpd: ThreadingHTTPServer | None = None
        self._beacon: BeaconBroadcaster | None = None

    def start(self, *, block: bool = True) -> None:
        state = self.config.state
        assert state is not None
        state.relay_base_url = self.config.relay_base_url()
        handler = make_handler(self.config)
        self._httpd = ThreadingHTTPServer((self.config.host, self.config.port), handler)
        self._httpd.allow_reuse_address = True
        if self.config.enable_beacon:
            self._beacon = BeaconBroadcaster(
                state,
                self.config.port,
                beacon_port=self.config.beacon_port,
                interval=self.config.beacon_interval,
            )
            self._beacon.start()
        print(
            f"lan_relay: {state.relay_base_url} pairing={state.pairing_id} "
            f"mobile={state.relay_base_url}{mobile_ui_path()} → bridge {self.config.bridge_url}",
            flush=True,
        )
        if block:
            try:
                assert self._httpd is not None
                self._httpd.serve_forever()
            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        if self._beacon is not None:
            self._beacon.stop()
            self._beacon = None
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


def main() -> None:
    ap = argparse.ArgumentParser(description="Lumos LAN relay (mobile approval MVP)")
    ap.add_argument("--host", default=os.environ.get("LAN_RELAY_HOST", DEFAULT_RELAY_HOST))
    ap.add_argument("--port", type=int, default=int(os.environ.get("LAN_RELAY_PORT", str(DEFAULT_RELAY_PORT))))
    ap.add_argument("--bridge-url", default=os.environ.get("BRIDGE_URL", DEFAULT_BRIDGE_URL))
    ap.add_argument("--device-name", default=os.environ.get("LAN_RELAY_DEVICE_NAME", "Lumos-PC"))
    ap.add_argument(
        "--pairing-ttl",
        type=int,
        default=int(os.environ.get("LAN_RELAY_PAIRING_TTL", str(DEFAULT_PAIRING_TTL_SECONDS))),
    )
    ap.add_argument("--no-beacon", action="store_true")
    ap.add_argument("--beacon-port", type=int, default=int(os.environ.get("LAN_RELAY_BEACON_PORT", str(DEFAULT_BEACON_PORT))))
    args = ap.parse_args()

    config = RelayConfig(
        host=args.host,
        port=args.port,
        bridge_url=args.bridge_url,
        device_name=args.device_name,
        pairing_ttl_seconds=args.pairing_ttl,
        enable_beacon=not args.no_beacon,
        beacon_port=args.beacon_port,
    )
    LanRelayServer(config).start(block=True)


if __name__ == "__main__":
    main()
