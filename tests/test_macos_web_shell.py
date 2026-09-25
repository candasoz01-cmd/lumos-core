"""Lumos Mac web kabuğu — giriş, medya, dosya seçici, imza ve zayıf bağ.

Swift burada derlenmez (CI `macos-app-build` derler); bu testler kabuğun repodaki
mevcut sözleşmelerle (mobil OAuth, `lumos_session` çerezi, panel masaüstü işareti)
hizalı kaldığını ve gömülü tanı betiğinin gerçekten çalıştığını doğrular.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "macos" / "LumosApp"
SOURCES = APP_DIR / "Sources" / "Lumos"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _main() -> str:
    return _read(SOURCES / "main.swift")


def _shell() -> str:
    return _read(SOURCES / "LumosWebShell.swift")


def _swift_js(anchor: str) -> str:
    """Swift çok satırlı dizesindeki JS'i JS olarak geri üretir."""
    shell = _shell()
    start = shell.index(anchor)
    start = shell.index('static let script = """', start) + len('static let script = """')
    end = shell.index('"""', start)
    body = shell[start:end]
    lines = body.splitlines()
    indent = min(len(ln) - len(ln.lstrip()) for ln in lines if ln.strip())
    return "\n".join(ln[indent:] for ln in lines).replace("\\\\", "\\")


def _diag_script() -> str:
    return _swift_js("final class LumosWebDiagnostics")


def _camera_script() -> str:
    return _swift_js("enum LumosCameraCapture")


# --- dosya seçici ve medya izni ---


def test_file_inputs_open_a_native_open_panel() -> None:
    main = _main()
    assert "@objc(webView:runOpenPanelWithParameters:initiatedByFrame:completionHandler:)" in main
    assert "NSOpenPanel()" in main
    assert "parameters.allowsMultipleSelection" in main
    assert "parameters.allowsDirectories" in main
    assert "completionHandler(urls)" in main


def test_media_capture_is_granted_only_to_trusted_main_frame() -> None:
    main = _main()
    assert "decisionHandler(.prompt)" not in main
    assert "frame.isMainFrame" in main
    assert "LumosTrust.isTrusted(scheme: origin.`protocol`" in main
    assert "decisionHandler(trusted ? .grant : .deny)" in main
    shell = _shell()
    assert 'return scheme == "http" && localHosts.contains(host)' in shell


def test_hardened_runtime_has_mic_and_camera_entitlements() -> None:
    ent = _read(APP_DIR / "Lumos.entitlements")
    assert "com.apple.security.device.audio-input" in ent
    assert "com.apple.security.device.camera" in ent
    assert "applinks:welockai.com" in ent


# --- Google girişi: mevcut mobil OAuth sözleşmesi ---


def test_google_sign_in_is_intercepted_not_sent_to_external_browser() -> None:
    main = _main()
    assert 'url.path == "/auth/google/start"' in main
    assert 'host == "accounts.google.com"' in main
    decide = main[main.index("decidePolicyFor navigationAction") :]
    assert decide.index("if isGoogleSignIn(url)") < decide.index("NSWorkspace.shared.open(url)")


def test_google_sign_in_uses_existing_mobile_oauth_contract() -> None:
    shell = _shell()
    start_js = _read(ROOT / "api" / "auth" / "google" / "start.js")
    callback_js = _read(ROOT / "api" / "auth" / "google" / "callback.js")
    session_js = _read(ROOT / "api" / "_lib" / "lumos_session.js")

    # İstek tarafı: start.js `?mobile=1&app_state=` kabul eder.
    assert 'searchParams.get("mobile") === "1"' in start_js
    assert 'URLQueryItem(name: "mobile", value: "1")' in shell
    assert 'URLQueryItem(name: "app_state", value: state)' in shell
    # Dönüş tarafı: callback `lumos://auth#…session=…&state=…` üretir.
    assert "lumos://auth#" in callback_js
    assert "session: sealed" in callback_js
    assert 'callbackScheme = "lumos"' in shell
    assert 'params["state"]' in shell and "state == expectedState" in shell
    assert 'params["session"]' in shell
    # Çerez adı web oturumuyla aynı.
    assert 'const COOKIE = "lumos_session";' in session_js
    assert 'sessionCookieName = "lumos_session"' in shell
    assert 'HTTPCookiePropertyKey("HttpOnly"): "TRUE"' in shell
    assert "properties[.secure] = \"TRUE\"" in shell
    assert "ASWebAuthenticationSession(" in shell
    # Oturum değeri log'a yazılmaz.
    for line in shell.splitlines():
        if "LumosLog." in line:
            assert "sealed" not in line


def test_app_state_generator_satisfies_start_js_rule() -> None:
    start_js = _read(ROOT / "api" / "auth" / "google" / "start.js")
    rule = re.search(r"/\^\[A-Za-z0-9_-\]\{(\d+),(\d+)\}\$/", start_js)
    assert rule, "start.js app_state kuralı bulunamadı"
    lo, hi = int(rule.group(1)), int(rule.group(2))
    shell = _shell()
    assert '(UUID().uuidString + UUID().uuidString).replacingOccurrences(of: "-", with: "")' in shell
    sample = ("0123456789ABCDEF" * 4)  # iki UUID, tiresiz: 64 hex
    assert lo <= len(sample) <= hi
    assert re.fullmatch(r"[A-Za-z0-9_-]+", sample)


# --- masaüstü işareti ve tanı betiği ---


def test_desktop_marker_matches_panel_contract() -> None:
    panel_page = _read(ROOT / "ui" / "src" / "pages" / "panel.astro")
    runtime = _read(ROOT / "ui" / "src" / "components" / "panel" / "PanelRuntime.astro")
    assert "document.documentElement.dataset.lumosApp = \"true\"" in panel_page
    assert 'document.documentElement.dataset.lumosApp === "true"' in runtime
    assert 'document.documentElement.dataset.lumosApp = "true"' in _diag_script()


def _node() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node yok — gömülü JS çalıştırılamıyor")
    return node


def test_diag_script_parses(tmp_path: Path) -> None:
    node = _node()
    js = tmp_path / "diag.js"
    js.write_text(_diag_script(), encoding="utf-8")
    result = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_diag_script_marks_desktop_and_reports_status_only(tmp_path: Path) -> None:
    """Sahte tarayıcı ortamında: işaret, getUserMedia, recorder desteği, HTTP durumu."""
    node = _node()
    harness = tmp_path / "run.js"
    harness.write_text(
        """
const posts = [];
const listeners = {};
global.window = globalThis;
window.webkit = { messageHandlers: { lumosDiag: { postMessage: (m) => posts.push(m) } } };
window.addEventListener = (name, fn) => { (listeners[name] = listeners[name] || []).push(fn); };
global.document = {
  documentElement: { dataset: {} },
  addEventListener: () => {},
  getElementById: () => null,
};
Object.defineProperty(globalThis, "navigator", {
  value: { mediaDevices: { getUserMedia: async () => ({ id: "stream" }) } },
  configurable: true,
  writable: true,
});
global.MediaRecorder = { isTypeSupported: (t) => t === "audio/mp4" };
global.fetch = async (url) => ({
  status: String(url).includes("transcribe") ? 503 : 401,
  ok: false,
  clone: () => ({ json: async () => ({ error: "bridge_proxy_unconfigured", text: "gizli transkript" }) }),
});
require(process.argv[2]);
(async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  await fetch("/api/bridge/transcribe?token=secret-should-not-leak");
  await fetch("/api/bridge/task");
  listeners.error.forEach((fn) => fn({ message: "boom", filename: "https://x/a.js?v=1", lineno: 7 }));
  await new Promise((r) => setTimeout(r, 10));
  console.log(JSON.stringify({ posts, marker: document.documentElement.dataset.lumosApp, stream }));
})();
""",
        encoding="utf-8",
    )
    script = tmp_path / "diag.js"
    script.write_text(_diag_script(), encoding="utf-8")
    result = subprocess.run(
        [node, str(harness), str(script)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["marker"] == "true"
    assert out["stream"] == {"id": "stream"}  # sarmalayıcı akışı olduğu gibi döndürür
    by_kind = {p["kind"]: p["detail"] for p in out["posts"]}
    assert by_kind["media.getUserMedia.ok"] == "audio"
    assert "audio/mp4=true" in by_kind["media.recorder.support"]
    assert by_kind["http"] == "/api/bridge/transcribe 503 bridge_proxy_unconfigured"
    assert by_kind["js.error"] == "boom @https://x/a.js:7"
    raw = json.dumps(out["posts"])
    assert "secret-should-not-leak" not in raw
    assert "gizli transkript" not in raw  # yanıttan yalnız `error` kodu alınır
    assert "/api/bridge/task" not in raw  # yalnız izlenen uçlar


# --- imza ve zayıf bağ ---


def test_adhoc_build_strips_associated_domains_release_keeps_it() -> None:
    script = _read(APP_DIR / "build-app.sh")
    adhoc = script[script.index('if [[ "${SIGNING_IDENTITY}" == "-" ]]; then') : script.index("\nelse\n")]
    release = script[script.index("\nelse\n") : script.index("codesign --verify --deep --strict")]
    assert 'Delete :com.apple.developer.associated-domains' in adhoc
    assert '--entitlements "${ADHOC_ENTITLEMENTS}"' in adhoc
    assert "associated-domains kaldı" in adhoc
    assert '--entitlements "${ENTITLEMENTS}"' in release
    assert "--options runtime --timestamp" in release
    assert "applinks:welockai.com" in release


def test_translation_framework_is_weak_linked_and_verified() -> None:
    package = _read(APP_DIR / "Package.swift")
    script = _read(APP_DIR / "build-app.sh")
    assert '"-weak_framework", "-Xlinker", "Translation"' in package
    assert '"-disable-autolink-framework", "-Xfrontend", "Translation"' in package
    assert "LC_LOAD_WEAK_DYLIB" in script and "Translation.framework" in script
    assert 'grep -A2 "cmd LC_LOAD_DYLIB"' in script
    panel = _read(SOURCES / "LumosTranslationPanel.swift")
    assert "guard #available(macOS 15.0, *) else {" in panel


# --- panel: artı menüsü kaydı gerçek biçimle adlandırılır ---


def test_record_preview_transcript_filename_follows_recorder_mime() -> None:
    runtime = _read(ROOT / "ui" / "src" / "components" / "panel" / "PanelRuntime.astro")
    assert "filenameFromBlob: true" in runtime
    assert "audioRecordingFilenameForMime(blobMime)" in runtime
    fn = runtime[runtime.index("function audioRecordingFilenameForMime(") :]
    fn = fn[: fn.index("\n      }\n")]
    assert 'return "recording.mp4"' in fn and 'return "recording.webm"' in fn


def test_diag_failures_are_logged_at_persisted_error_level() -> None:
    shell = _shell()
    assert "LumosLog.web.error(" in shell
    fn = shell[shell.index("static func isFailure(") :]
    fn = fn[: fn.index("\n    }\n")]
    assert 'kind.hasPrefix("js.")' in fn and "status >= 400" in fn


# --- kamera: gerçek kamera, dosya seçici değil ---


def test_camera_capture_intercepts_capture_inputs_only() -> None:
    js = _camera_script()
    assert 'el.hasAttribute("capture")' in js
    assert "e.preventDefault();" in js
    assert "getUserMedia({ video:" in js
    assert 'new File([blob], "Lumos-Kamera-"' in js
    assert 'input.dispatchEvent(new Event("change", { bubbles: true }))' in js
    assert "getTracks().forEach((t) => t.stop())" in js
    # Swift dizesine kaçışsız gömülür.
    assert "\\" not in js
    shell = _shell()
    assert "source: LumosCameraCapture.script" in shell
    # Panel sözleşmesi: Kamera `capture` koyar, Fotoğraf seç kaldırır; change → files[0].
    runtime = _read(ROOT / "ui" / "src" / "components" / "panel" / "PanelRuntime.astro")
    assert 'cameraPhotoInput.setAttribute("capture", "environment");' in runtime
    assert 'cameraPhotoInput.removeAttribute("capture");' in runtime
    assert "cameraPhotoInput.files && cameraPhotoInput.files[0]" in runtime
    readme = _read(APP_DIR / "README.md")
    assert "dosya seçiciyi açar" not in readme.split("## Web kabuğu")[1].split("## Yerel build")[0]


def test_camera_script_parses(tmp_path: Path) -> None:
    node = _node()
    js = tmp_path / "camera.js"
    js.write_text(_camera_script(), encoding="utf-8")
    result = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
