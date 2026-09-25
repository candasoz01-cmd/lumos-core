import AppKit
import WebKit

private let defaultLumosURL = "https://welockai.com/panel?source=desktop"

@MainActor
final class LumosNavigationDelegate: NSObject, WKNavigationDelegate, WKUIDelegate {
    private let origin: LumosAppOrigin
    private let allowedHosts: Set<String>
    private let onGoogleSignIn: @MainActor () -> Void

    init(origin: LumosAppOrigin, onGoogleSignIn: @escaping @MainActor () -> Void) {
        self.origin = origin
        self.allowedHosts = LumosTrust.allowedHosts(for: origin)
        self.onGoogleSignIn = onGoogleSignIn
    }

    /// Panelin "Google ile Giriş" bağlantısı (`/auth/google/start`) ya da Google'ın
    /// kendi sayfası. Dış tarayıcıda biten giriş oturumu uygulamaya geri getiremez;
    /// akış ASWebAuthenticationSession'a (mobil OAuth sözleşmesi) alınır.
    private func isGoogleSignIn(_ url: URL) -> Bool {
        let host = (url.host ?? "").lowercased()
        if host == "accounts.google.com" { return true }
        guard allowedHosts.contains(host) else { return false }
        guard url.path == "/auth/google/start" || url.path == "/api/auth/google/start" else {
            return false
        }
        let query = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
        return !query.contains { $0.name == "mobile" && $0.value == "1" }
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping @MainActor (WKNavigationActionPolicy) -> Void
    ) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.cancel)
            return
        }

        if isGoogleSignIn(url) {
            decisionHandler(.cancel)
            onGoogleSignIn()
            return
        }

        if url.scheme == "file" || allowedHosts.contains((url.host ?? "").lowercased()) {
            decisionHandler(.allow)
            return
        }

        NSWorkspace.shared.open(url)
        decisionHandler(.cancel)
    }

    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        if let url = navigationAction.request.url {
            if isGoogleSignIn(url) {
                onGoogleSignIn()
                return nil
            }
            NSWorkspace.shared.open(url)
        }
        return nil
    }

    /// Mikrofon/kamera: yalnız güvenilen kökenin ana çerçevesine izin; macOS TCC
    /// izni (Info.plist kullanım açıklamaları) yine ayrıca sorulur. `.prompt`
    /// her kayıtta ikinci bir WebKit onayı açıyordu.
    func webView(
        _ webView: WKWebView,
        requestMediaCapturePermissionFor origin: WKSecurityOrigin,
        initiatedByFrame frame: WKFrameInfo,
        type: WKMediaCaptureType,
        decisionHandler: @escaping @MainActor (WKPermissionDecision) -> Void
    ) {
        let trusted = frame.isMainFrame
            && LumosTrust.isTrusted(scheme: origin.`protocol`, host: origin.host, origin: self.origin)
        LumosLog.media.info(
            "capture request type=\(type.rawValue, privacy: .public) host=\(origin.host, privacy: .public) decision=\(trusted ? "grant" : "deny", privacy: .public)"
        )
        decisionHandler(trusted ? .grant : .deny)
    }

    /// `<input type="file">` (Artı › Fotoğraf seç / Kamera / Ses dosyası, Dosyalar).
    /// macOS WKWebView bu metot olmadan dosya seçici açmaz; tıklama sessizce boşa gider.
    @objc(webView:runOpenPanelWithParameters:initiatedByFrame:completionHandler:)
    func webView(
        _ webView: WKWebView,
        runOpenPanelWith parameters: WKOpenPanelParameters,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping @MainActor ([URL]?) -> Void
    ) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = parameters.allowsDirectories
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.resolvesAliases = true
        LumosLog.web.info("file chooser opened multiple=\(parameters.allowsMultipleSelection, privacy: .public)")
        // Kapanışsız modal: WebKit seçimi completionHandler ile bekler.
        let urls = panel.runModal() == .OK ? panel.urls : nil
        LumosLog.web.info("file chooser closed selected=\(urls?.count ?? 0, privacy: .public)")
        completionHandler(urls)
    }

    func webView(
        _ webView: WKWebView,
        didFail navigation: WKNavigation!,
        withError error: Error
    ) {
        showConnectionError(in: webView)
    }

    func webView(
        _ webView: WKWebView,
        didFailProvisionalNavigation navigation: WKNavigation!,
        withError error: Error
    ) {
        showConnectionError(in: webView)
    }

    private func showConnectionError(in webView: WKWebView) {
        let target = webView.url?.absoluteString
            ?? origin.panelURL?.absoluteString
            ?? defaultLumosURL
        let safeTarget = target
            .replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "\"", with: "&quot;")
            .replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
        let html = """
        <!doctype html>
        <html lang="tr">
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <style>
          :root { color-scheme: dark; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
          body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0a0e14; color: #e8edf4; }
          main { width: min(520px, calc(100% - 48px)); text-align: center; }
          h1 { font-size: 28px; margin-bottom: 12px; }
          p { color: #9aa8b8; line-height: 1.55; }
          a { display: inline-block; margin-top: 16px; padding: 10px 16px; border: 1px solid #b9975b; border-radius: 10px; color: #f0d6a5; text-decoration: none; }
        </style>
        <main>
          <h1>Lumos’a ulaşılamadı</h1>
          <p>Bağlantıyı kontrol edip yeniden deneyin. Lumos herhangi bir işlemi arka planda başlatmadı.</p>
          <a href="\(safeTarget)">Yeniden dene</a>
        </main>
        </html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }
}

@MainActor
final class LumosAppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow?
    private var webView: WKWebView?
    private var navigationDelegate: LumosNavigationDelegate?
    private var googleSignIn: LumosGoogleSignIn?
    private let webDiagnostics = LumosWebDiagnostics()
    private let selectionTranslator = LumosSelectionTranslator()

    func applicationDidFinishLaunching(_ notification: Notification) {
        let rawURL = ProcessInfo.processInfo.environment["LUMOS_APP_URL"] ?? defaultLumosURL
        guard let url = URL(string: rawURL), let origin = LumosAppOrigin(url: url) else {
            preconditionFailure("Invalid LUMOS_APP_URL")
        }

        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.preferences.isElementFullscreenEnabled = true
        configuration.applicationNameForUserAgent = "LumosMac/1.0"
        webDiagnostics.install(on: configuration.userContentController)

        let googleSignIn = LumosGoogleSignIn(origin: origin)
        let navigationDelegate = LumosNavigationDelegate(origin: origin) { [weak googleSignIn] in
            googleSignIn?.start()
        }

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = navigationDelegate
        webView.uiDelegate = navigationDelegate
        googleSignIn.attach(webView: webView)
        self.googleSignIn = googleSignIn
        self.navigationDelegate = navigationDelegate
        webView.allowsMagnification = false

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1180, height: 820),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Lumos"
        window.minSize = NSSize(width: 820, height: 620)
        window.center()
        window.contentView = webView
        webView.frame = window.contentLayoutRect
        webView.autoresizingMask = [.width, .height]
        window.isReleasedWhenClosed = false
        window.makeKeyAndOrderFront(nil)

        self.window = window
        self.webView = webView

        webView.load(URLRequest(url: url, cachePolicy: .reloadRevalidatingCacheData))
        selectionTranslator.start()
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }
}

let application = NSApplication.shared
let appDelegate = LumosAppDelegate()
application.delegate = appDelegate
application.setActivationPolicy(.regular)
application.run()
