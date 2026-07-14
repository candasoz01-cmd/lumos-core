import AppKit
import WebKit

private let defaultLumosURL = "https://welockai.com/panel?source=desktop"

@MainActor
final class LumosNavigationDelegate: NSObject, WKNavigationDelegate, WKUIDelegate {
    private let allowedHosts = Set(["welockai.com", "www.welockai.com", "127.0.0.1", "localhost"])

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping @MainActor (WKNavigationActionPolicy) -> Void
    ) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.cancel)
            return
        }

        if url.scheme == "file" || allowedHosts.contains(url.host ?? "") {
            decisionHandler(.allow)
            return
        }

        if navigationAction.navigationType == .linkActivated {
            NSWorkspace.shared.open(url)
        }
        decisionHandler(.cancel)
    }

    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        if let url = navigationAction.request.url {
            NSWorkspace.shared.open(url)
        }
        return nil
    }

    func webView(
        _ webView: WKWebView,
        requestMediaCapturePermissionFor origin: WKSecurityOrigin,
        initiatedByFrame frame: WKFrameInfo,
        type: WKMediaCaptureType,
        decisionHandler: @escaping @MainActor (WKPermissionDecision) -> Void
    ) {
        decisionHandler(.prompt)
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
            ?? ProcessInfo.processInfo.environment["LUMOS_APP_URL"]
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
    private let navigationDelegate = LumosNavigationDelegate()

    func applicationDidFinishLaunching(_ notification: Notification) {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.preferences.isElementFullscreenEnabled = true
        configuration.applicationNameForUserAgent = "LumosMac/1.0"

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = navigationDelegate
        webView.uiDelegate = navigationDelegate
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

        let rawURL = ProcessInfo.processInfo.environment["LUMOS_APP_URL"] ?? defaultLumosURL
        guard let url = URL(string: rawURL) else {
            preconditionFailure("Invalid LUMOS_APP_URL")
        }
        webView.load(URLRequest(url: url, cachePolicy: .reloadRevalidatingCacheData))
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
