import AppKit
import AuthenticationServices
import OSLog
import WebKit

/// Birleşik log: `log stream --predicate 'subsystem == "com.welockai.Lumos"'`.
/// Token, oturum değeri veya kullanıcı içeriği yazılmaz.
enum LumosLog {
    static let web = Logger(subsystem: "com.welockai.Lumos", category: "web")
    static let auth = Logger(subsystem: "com.welockai.Lumos", category: "auth")
    static let media = Logger(subsystem: "com.welockai.Lumos", category: "media")
}

/// Uygulamanın yüklemeye yapılandırıldığı köken (`LUMOS_APP_URL` veya varsayılan).
struct LumosAppOrigin: Sendable {
    let scheme: String
    let host: String
    let port: Int?

    init?(url: URL) {
        guard
            let scheme = url.scheme?.lowercased(),
            scheme == "https" || scheme == "http",
            let host = url.host?.lowercased(),
            !host.isEmpty
        else { return nil }
        self.scheme = scheme
        self.host = host
        self.port = url.port
    }

    var isSecure: Bool { scheme == "https" }

    func url(path: String, query: [URLQueryItem] = []) -> URL? {
        var components = URLComponents()
        components.scheme = scheme
        components.host = host
        components.port = port
        components.path = path
        components.queryItems = query.isEmpty ? nil : query
        return components.url
    }

    /// Panel sayfası; `source=desktop` masaüstü giriş işaretini korur.
    var panelURL: URL? {
        url(path: "/panel", query: [
            URLQueryItem(name: "source", value: "desktop"),
            URLQueryItem(name: "door", value: "lumos"),
        ])
    }
}

/// Güvenilen kökenler: uygulamanın kendi kökeni + üretim alan adı; http yalnız yerel geliştirme.
enum LumosTrust {
    static let productionHosts: Set<String> = ["welockai.com", "www.welockai.com"]
    static let localHosts: Set<String> = ["127.0.0.1", "localhost"]

    static func allowedHosts(for origin: LumosAppOrigin) -> Set<String> {
        productionHosts.union(localHosts).union([origin.host])
    }

    static func isTrusted(scheme: String, host: String, origin: LumosAppOrigin) -> Bool {
        let scheme = scheme.lowercased()
        let host = host.lowercased()
        guard allowedHosts(for: origin).contains(host) else { return false }
        if scheme == "https" { return true }
        return scheme == "http" && localHosts.contains(host)
    }
}

/// "Google ile Giriş": Google, gömülü web görünümünde OAuth'a izin vermez; akış
/// sistem kimlik doğrulama oturumunda (ASWebAuthenticationSession) yürür ve
/// mevcut mobil OAuth sözleşmesini kullanır:
/// `/auth/google/start?mobile=1&app_state=…` → `lumos://auth#session=…&state=…`.
/// Dönen mühürlü oturum, web girişinin koyduğu `lumos_session` çereziyle aynıdır;
/// uygulamanın çerez deposuna yazılır ve panel yeniden yüklenir.
@MainActor
final class LumosGoogleSignIn: NSObject, ASWebAuthenticationPresentationContextProviding {
    private static let callbackScheme = "lumos"
    private static let sessionCookieName = "lumos_session"
    private static let sessionMaxAge: TimeInterval = 604_800

    private let origin: LumosAppOrigin
    private weak var webView: WKWebView?
    private var session: ASWebAuthenticationSession?
    private var expectedState = ""

    init(origin: LumosAppOrigin) {
        self.origin = origin
    }

    func attach(webView: WKWebView) {
        self.webView = webView
    }

    func start() {
        guard session == nil else {
            LumosLog.auth.info("google sign-in already in progress")
            return
        }
        let state = Self.makeState()
        guard let startURL = origin.url(path: "/auth/google/start", query: [
            URLQueryItem(name: "mobile", value: "1"),
            URLQueryItem(name: "app_state", value: state),
        ]) else {
            LumosLog.auth.error("google sign-in start url invalid")
            return
        }
        expectedState = state
        let coordinator = self
        let authSession = ASWebAuthenticationSession(
            url: startURL,
            callbackURLScheme: Self.callbackScheme
        ) { @Sendable callbackURL, error in
            Task { @MainActor in
                coordinator.finish(callbackURL: callbackURL, error: error)
            }
        }
        authSession.presentationContextProvider = self
        authSession.prefersEphemeralWebBrowserSession = false
        session = authSession
        if authSession.start() {
            LumosLog.auth.info("google sign-in session started")
        } else {
            session = nil
            LumosLog.auth.error("google sign-in session failed to start")
        }
    }

    nonisolated func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        MainActor.assumeIsolated {
            self.webView?.window ?? NSApp.keyWindow ?? NSWindow()
        }
    }

    private func finish(callbackURL: URL?, error: Error?) {
        session = nil
        if let error {
            if let authError = error as? ASWebAuthenticationSessionError,
               authError.code == .canceledLogin {
                LumosLog.auth.info("google sign-in cancelled by user")
            } else {
                LumosLog.auth.error("google sign-in failed: \(String(describing: error), privacy: .public)")
                loadAuthPage(error: "auth_session_failed")
            }
            return
        }
        guard let callbackURL, callbackURL.scheme?.lowercased() == Self.callbackScheme else {
            LumosLog.auth.error("google sign-in returned no callback")
            loadAuthPage(error: "auth_session_failed")
            return
        }
        let params = Self.fragmentParameters(of: callbackURL)
        guard let state = params["state"], !expectedState.isEmpty, state == expectedState else {
            LumosLog.auth.error("google sign-in state mismatch")
            loadAuthPage(error: "invalid_state")
            return
        }
        expectedState = ""
        if let code = params["error"], !code.isEmpty {
            LumosLog.auth.error("google sign-in server error: \(code, privacy: .public)")
            loadAuthPage(error: code)
            return
        }
        guard let sealed = params["session"], !sealed.isEmpty else {
            LumosLog.auth.error("google sign-in callback without session")
            loadAuthPage(error: "auth_session_failed")
            return
        }
        installSession(sealed)
    }

    private func installSession(_ sealed: String) {
        guard let webView else { return }
        var properties: [HTTPCookiePropertyKey: Any] = [
            .name: Self.sessionCookieName,
            .value: sealed,
            .domain: origin.host,
            .path: "/",
            .expires: Date(timeIntervalSinceNow: Self.sessionMaxAge),
            .sameSitePolicy: HTTPCookieStringPolicy.sameSiteLax.rawValue,
            HTTPCookiePropertyKey("HttpOnly"): "TRUE",
        ]
        if origin.isSecure {
            properties[.secure] = "TRUE"
        }
        guard let cookie = HTTPCookie(properties: properties) else {
            LumosLog.auth.error("google sign-in cookie could not be built")
            loadAuthPage(error: "auth_session_failed")
            return
        }
        let panelURL = origin.panelURL
        webView.configuration.websiteDataStore.httpCookieStore.setCookie(cookie) { [weak webView] in
            LumosLog.auth.info("google sign-in session installed")
            guard let webView, let panelURL else { return }
            webView.load(URLRequest(url: panelURL))
        }
    }

    private func loadAuthPage(error code: String) {
        guard let webView, let url = origin.url(path: "/auth", query: [
            URLQueryItem(name: "error", value: code),
            URLQueryItem(name: "source", value: "desktop"),
        ]) else { return }
        webView.load(URLRequest(url: url))
    }

    /// `^[A-Za-z0-9_-]{20,128}$` — `api/auth/google/start.js` mobil app_state kuralı.
    private static func makeState() -> String {
        (UUID().uuidString + UUID().uuidString).replacingOccurrences(of: "-", with: "")
    }

    /// `lumos://auth#session=…&state=…` → sözlük (fragment, sorgu biçiminde).
    static func fragmentParameters(of url: URL) -> [String: String] {
        guard
            let fragment = URLComponents(url: url, resolvingAgainstBaseURL: false)?.percentEncodedFragment,
            !fragment.isEmpty,
            let items = URLComponents(string: "lumos://auth?" + fragment)?.queryItems
        else { return [:] }
        var out: [String: String] = [:]
        for item in items {
            out[item.name] = item.value ?? ""
        }
        return out
    }
}

/// Panel ile kabuk arası tanı köprüsü + masaüstü işareti.
///
/// - `data-lumos-app="true"`: panel, masaüstü girişini yalnız `?source=desktop`
///   sorgusundan tanıyordu; uygulama içinde başka bir sayfaya/sorguya gidildiğinde
///   işaret kayboluyor ve panel "Sınırlı mod"a düşüyordu (ses metne çeviri kapalı).
///   Kabuk işareti her belge yüklenişinde koyar — panelin mevcut sözleşmesi.
/// - Tanı: JS hataları, getUserMedia sonucu, MediaRecorder biçim desteği,
///   transcribe/session HTTP durumları ve mikrofon/kamera ipucu metinleri birleşik
///   log'a gider (yalnız durum/ad; ses, metin içeriği, token yok).
@MainActor
final class LumosWebDiagnostics: NSObject, WKScriptMessageHandler {
    static let handlerName = "lumosDiag"

    func install(on controller: WKUserContentController) {
        controller.add(self, name: Self.handlerName)
        controller.addUserScript(WKUserScript(
            source: Self.script,
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        ))
        controller.addUserScript(WKUserScript(
            source: LumosCameraCapture.script,
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        ))
    }

    func userContentController(
        _ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage
    ) {
        guard let body = message.body as? [String: Any] else { return }
        let kind = String(String(describing: body["kind"] ?? "").prefix(64))
        let detail = String(String(describing: body["detail"] ?? "").prefix(300))
        if Self.isFailure(kind: kind, detail: detail) {
            // error düzeyi kalıcıdır: `log show --last 1h --predicate 'subsystem == "com.welockai.Lumos"'`
            LumosLog.web.error("\(kind, privacy: .public) \(detail, privacy: .public)")
        } else {
            LumosLog.web.info("\(kind, privacy: .public) \(detail, privacy: .public)")
        }
    }

    /// `http <yol> <durum> [hata_kodu]` ≥ 400, JS hataları, kamera/medya hataları.
    static func isFailure(kind: String, detail: String) -> Bool {
        if kind.hasPrefix("js.") || kind.hasSuffix(".fail") || kind.hasSuffix(".error")
            || kind.hasSuffix(".missing") {
            return true
        }
        guard kind == "http" else { return false }
        let parts = detail.split(separator: " ")
        guard parts.count >= 2, let status = Int(parts[1]) else { return false }
        return status >= 400
    }

    static let script = """
    (() => {
      if (window.__lumosMacShell) return;
      window.__lumosMacShell = true;
      const markDesktop = () => {
        if (document.documentElement) document.documentElement.dataset.lumosApp = "true";
      };
      markDesktop();
      document.addEventListener("readystatechange", markDesktop);
      const post = (kind, detail) => {
        try {
          window.webkit.messageHandlers.lumosDiag.postMessage({
            kind: String(kind),
            detail: String(detail == null ? "" : detail).slice(0, 300),
          });
        } catch (_) {}
      };
      window.addEventListener("error", (e) => {
        post("js.error", (e.message || "") + " @" + String(e.filename || "").split("?")[0] + ":" + (e.lineno || 0));
      });
      window.addEventListener("unhandledrejection", (e) => {
        const r = e.reason;
        post("js.rejection", r && r.name ? r.name + ": " + (r.message || "") : r);
      });
      const md = navigator.mediaDevices;
      if (md && typeof md.getUserMedia === "function") {
        const original = md.getUserMedia.bind(md);
        md.getUserMedia = (constraints) => original(constraints).then(
          (stream) => {
            post("media.getUserMedia.ok", constraints && constraints.video ? "video" : "audio");
            return stream;
          },
          (err) => {
            post("media.getUserMedia.fail", (err && err.name) + ": " + (err && err.message));
            throw err;
          },
        );
      } else {
        post("media.getUserMedia.missing", "navigator.mediaDevices yok");
      }
      if (window.MediaRecorder && typeof MediaRecorder.isTypeSupported === "function") {
        post("media.recorder.support", ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"]
          .map((t) => t + "=" + MediaRecorder.isTypeSupported(t)).join(" "));
      }
      if (typeof window.fetch === "function") {
        const originalFetch = window.fetch;
        window.fetch = function (input, init) {
          const url = typeof input === "string" ? input : (input && input.url) || "";
          const pending = originalFetch.apply(this, arguments);
          if (/\\/api\\/(bridge\\/transcribe|auth\\/session)/.test(url)) {
            const path = url.replace(/[?#].*$/, "");
            pending.then(
              (res) => {
                if (res.ok || typeof res.clone !== "function") {
                  post("http", path + " " + res.status);
                  return;
                }
                res.clone().json().then(
                  (data) => post("http", path + " " + res.status + " " + String((data && data.error) || "-").slice(0, 64)),
                  () => post("http", path + " " + res.status + " -"),
                );
              },
              (err) => post("http.fail", path + " " + (err && err.name)),
            );
          }
          return pending;
        };
      }
      const watchHint = (id) => {
        const el = document.getElementById(id);
        if (!el) return;
        new MutationObserver(() => {
          const text = (el.textContent || "").trim();
          if (text) post("hint." + id, text);
        }).observe(el, { childList: true, characterData: true, subtree: true });
      };
      document.addEventListener("DOMContentLoaded", () => {
        ["panel-voice-hint", "panel-audio-record-hint", "panel-camera-hint"].forEach(watchHint);
      });
    })();
    """
}

/// Artı › Kamera: panel `capture` öznitelikli fotoğraf girişini tıklar. iOS
/// WebKit bunu kamerayla karşılar; macOS WebKit yok sayıp dosya seçici açar.
/// Kabuk bu tıklamayı yakalar, gerçek Mac kamerasını (getUserMedia, macOS kamera
/// izni) önizleme + "Fotoğraf çek" ile açar ve çekilen JPEG'i **aynı girişe**
/// dosya olarak verip `change` tetikler — panelin mevcut fotoğraf yolu
/// (`bindCameraPhotoFromFile`) sohbete ekler. `capture` olmayan girişler
/// (Artı › Fotoğraf seç, Dosyalar) dokunulmadan macOS dosya seçicisine gider.
enum LumosCameraCapture {
    static let script = """
    (() => {
      if (window.__lumosMacCamera) return;
      window.__lumosMacCamera = true;
      const post = (kind, detail) => {
        try {
          window.webkit.messageHandlers.lumosDiag.postMessage({
            kind: String(kind),
            detail: String(detail == null ? "" : detail).slice(0, 300),
          });
        } catch (_) {}
      };
      const wantsCamera = (el) =>
        el instanceof HTMLInputElement &&
        el.type === "file" &&
        el.hasAttribute("capture") &&
        /image/i.test(el.accept || "image/*");
      let open = false;

      function stamp() {
        const d = new Date();
        const p = (n) => String(n).padStart(2, "0");
        return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + "-" + p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds());
      }

      function deliver(input, file) {
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }

      function openCamera(input) {
        if (open) return;
        open = true;
        let stream = null;
        const previousFocus = document.activeElement;
        const root = document.createElement("div");
        root.setAttribute("role", "dialog");
        root.setAttribute("aria-modal", "true");
        root.setAttribute("aria-label", "Kamera");
        root.dataset.lumosCamera = "open";
        root.style.cssText =
          "position:fixed;inset:0;z-index:2147483647;display:grid;place-items:center;" +
          "background:rgba(3,7,20,0.86);font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#e8edf4";
        const card = document.createElement("div");
        card.style.cssText =
          "width:min(720px,calc(100vw - 32px));background:#0a0e14;border:1px solid #1f2a37;" +
          "border-radius:16px;padding:16px;display:grid;gap:12px";
        const video = document.createElement("video");
        video.autoplay = true;
        video.muted = true;
        video.playsInline = true;
        video.setAttribute("playsinline", "");
        video.style.cssText = "width:100%;aspect-ratio:16/9;max-height:60vh;object-fit:cover;background:#000;border-radius:12px;transform:scaleX(-1)";
        const status = document.createElement("p");
        status.setAttribute("role", "status");
        status.style.cssText = "margin:0;font-size:14px;color:#9aa8b8;min-height:1.2em";
        status.textContent = "Kamera açılıyor…";
        const row = document.createElement("div");
        row.style.cssText = "display:flex;gap:10px;justify-content:flex-end";
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.textContent = "Vazgeç";
        cancel.dataset.lumosCameraAction = "cancel";
        cancel.style.cssText =
          "padding:10px 16px;border-radius:10px;border:1px solid #334155;background:transparent;color:#e8edf4;font-size:15px;cursor:pointer";
        const shoot = document.createElement("button");
        shoot.type = "button";
        shoot.textContent = "Fotoğraf çek";
        shoot.disabled = true;
        shoot.dataset.lumosCameraAction = "shoot";
        shoot.style.cssText =
          "padding:10px 18px;border-radius:10px;border:none;background:#38ceff;color:#030714;font-weight:700;font-size:15px;cursor:pointer";
        row.append(cancel, shoot);
        card.append(video, status, row);
        root.append(card);
        document.body.append(root);

        function close(reason) {
          if (stream) stream.getTracks().forEach((t) => t.stop());
          stream = null;
          root.remove();
          document.removeEventListener("keydown", onKey, true);
          open = false;
          post("camera.close", reason);
          if (previousFocus && typeof previousFocus.focus === "function") previousFocus.focus();
        }
        function onKey(e) {
          if (e.key === "Escape") {
            e.preventDefault();
            close("escape");
          }
        }
        document.addEventListener("keydown", onKey, true);
        cancel.addEventListener("click", () => close("cancel"));

        shoot.addEventListener("click", () => {
          const w = video.videoWidth;
          const h = video.videoHeight;
          if (!w || !h) {
            status.textContent = "Görüntü henüz hazır değil, tekrar deneyin.";
            return;
          }
          const canvas = document.createElement("canvas");
          canvas.width = w;
          canvas.height = h;
          canvas.getContext("2d").drawImage(video, 0, 0, w, h);
          shoot.disabled = true;
          canvas.toBlob(
            (blob) => {
              if (!blob) {
                status.textContent = "Fotoğraf oluşturulamadı.";
                shoot.disabled = false;
                post("camera.error", "toBlob_failed");
                return;
              }
              const file = new File([blob], "Lumos-Kamera-" + stamp() + ".jpg", { type: "image/jpeg" });
              post("camera.captured", w + "x" + h + " " + blob.size);
              close("captured");
              deliver(input, file);
            },
            "image/jpeg",
            0.92,
          );
        });

        const md = navigator.mediaDevices;
        if (!md || typeof md.getUserMedia !== "function") {
          status.textContent = "Bu cihazda kamera kullanılamıyor.";
          post("camera.error", "getUserMedia_missing");
          return;
        }
        md.getUserMedia({ video: { width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false }).then(
          (s) => {
            if (!open) {
              s.getTracks().forEach((t) => t.stop());
              return;
            }
            stream = s;
            video.srcObject = s;
            status.textContent = "";
            shoot.disabled = false;
            shoot.focus();
          },
          (err) => {
            const name = (err && err.name) || "Error";
            status.textContent =
              name === "NotAllowedError"
                ? "Kamera izni verilmedi. Sistem Ayarları › Gizlilik ve Güvenlik › Kamera › Lumos."
                : "Kamera açılamadı (" + name + ").";
            post("camera.error", name + ": " + ((err && err.message) || ""));
          },
        );
      }

      document.addEventListener(
        "click",
        (e) => {
          const el = e.target;
          if (!wantsCamera(el)) return;
          e.preventDefault();
          e.stopImmediatePropagation();
          post("camera.request", "capture=" + el.getAttribute("capture"));
          openCamera(el);
        },
        true,
      );
    })();
    """
}
