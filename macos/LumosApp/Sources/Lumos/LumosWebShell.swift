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
    }

    func userContentController(
        _ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage
    ) {
        guard let body = message.body as? [String: Any] else { return }
        let kind = String(String(describing: body["kind"] ?? "").prefix(64))
        let detail = String(String(describing: body["detail"] ?? "").prefix(300))
        LumosLog.web.info("\(kind, privacy: .public) \(detail, privacy: .public)")
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
              (res) => post("http", path + " " + res.status),
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
