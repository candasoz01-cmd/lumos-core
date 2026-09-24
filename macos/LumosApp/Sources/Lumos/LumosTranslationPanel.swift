import AppKit
import Carbon
import NaturalLanguage
import SwiftUI
@preconcurrency import Translation

private let lumosTargetLanguage = "tr"

@MainActor
final class LumosTranslationModel: ObservableObject {
    enum Phase: Equatable {
        case reading
        case translating
        case translated(String)
        case failed(String)
    }

    @Published var phase: Phase = .reading
    @Published var sourceText = ""
    @Published var sourceLanguage: String?
    @Published var note: String?
    @Published var requestID = UUID()
    @Published var showsAccessibilityButton = false
    @Published var copied = false
    @Published var shortcutLabel = LumosShortcut.defaultValue.displayName
    @Published var isRecordingShortcut = false
    @Published var shortcutMessage: String?

    var translation: String? {
        if case .translated(let text) = phase { return text }
        return nil
    }

    func beginReading() {
        phase = .reading
        sourceText = ""
        sourceLanguage = nil
        note = nil
        showsAccessibilityButton = false
        copied = false
    }

    func startTranslation(of text: String) {
        sourceText = text
        let recognizer = NLLanguageRecognizer()
        recognizer.processString(text)
        let detected = recognizer.dominantLanguage.map(\.rawValue)
        if detected == lumosTargetLanguage {
            note = "Metin zaten Türkçe görünüyor."
            phase = .translated(text)
            return
        }
        sourceLanguage = detected == NLLanguage.undetermined.rawValue ? nil : detected
        guard #available(macOS 15.0, *) else {
            fail("Lumos çevirisi için macOS 15 veya üzeri gerekir.")
            return
        }
        requestID = UUID()
        phase = .translating
    }

    func finishTranslation(_ result: Result<String, Error>) {
        guard phase == .translating else { return }
        switch result {
        case .success(let text):
            phase = .translated(text)
        case .failure(let error):
            if error is CancellationError {
                fail("Çeviri iptal edildi. Dil paketi indirilmediyse kısayola yeniden basın.")
            } else {
                fail(
                    "Çeviri yapılamadı. Bu dil çifti için macOS dil paketinin yüklü olduğunu "
                        + "Sistem Ayarları › Genel › Dil ve Bölge › Çeviri Dilleri bölümünden kontrol edin. "
                        + "(\(error.localizedDescription))"
                )
            }
        }
    }

    func fail(_ message: String, showsAccessibilityButton: Bool = false) {
        phase = .failed(message)
        self.showsAccessibilityButton = showsAccessibilityButton
    }
}

struct LumosTranslationActions {
    var copy: @MainActor () -> Void
    var openAccessibilitySettings: @MainActor () -> Void
    var startShortcutRecording: @MainActor () -> Void
    var cancelShortcutRecording: @MainActor () -> Void
    var captureShortcut: @MainActor (NSEvent) -> Void
}

struct LumosTranslationView: View {
    @ObservedObject var model: LumosTranslationModel
    let actions: LumosTranslationActions

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Kaynak metin")
                .font(.caption)
                .foregroundStyle(.secondary)
            ScrollView {
                Text(model.sourceText.isEmpty ? "—" : model.sourceText)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(minHeight: 40, maxHeight: 110)

            Divider()

            Text("Türkçe çeviri")
                .font(.caption)
                .foregroundStyle(.secondary)
            resultView
                .frame(maxWidth: .infinity, minHeight: 60, alignment: .topLeading)

            Divider()

            shortcutRow
        }
        .padding(14)
        .frame(minWidth: 380, minHeight: 280)
        .background { translationRunner }
    }

    @ViewBuilder
    private var resultView: some View {
        switch model.phase {
        case .reading:
            ProgressView("Seçili metin okunuyor…")
                .controlSize(.small)
        case .translating:
            ProgressView("Çevriliyor…")
                .controlSize(.small)
        case .translated(let text):
            VStack(alignment: .leading, spacing: 6) {
                ScrollView {
                    Text(text)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                if let note = model.note {
                    Text(note)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        case .failed(let message):
            VStack(alignment: .leading, spacing: 8) {
                Text(message)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
                if model.showsAccessibilityButton {
                    Button("Erişilebilirlik Ayarlarını Aç") { actions.openAccessibilitySettings() }
                }
            }
        }
    }

    private var shortcutRow: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                if model.isRecordingShortcut {
                    Text("Yeni kısayola basın (Esc: vazgeç)")
                        .font(.caption)
                        .background {
                            LumosShortcutCapture(
                                onCapture: actions.captureShortcut,
                                onCancel: actions.cancelShortcutRecording
                            )
                        }
                } else {
                    Button("Kısayol: \(model.shortcutLabel)") { actions.startShortcutRecording() }
                        .buttonStyle(.link)
                        .font(.caption)
                }
                Spacer()
                Button(model.copied ? "Kopyalandı" : "Kopyala") { actions.copy() }
                    .disabled(model.translation == nil)
            }
            if let message = model.shortcutMessage {
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    @ViewBuilder
    private var translationRunner: some View {
        if #available(macOS 15.0, *) {
            if model.phase == .translating {
                LumosTranslationRunner(
                    text: model.sourceText,
                    sourceLanguage: model.sourceLanguage,
                    onFinish: { result in model.finishTranslation(result) }
                )
                .id(model.requestID)
            }
        }
    }
}

/// Apple Translation ile cihaz üzerinde çeviri; metin Lumos sunucusuna gitmez.
@available(macOS 15.0, *)
private struct LumosTranslationRunner: View {
    let text: String
    let sourceLanguage: String?
    let onFinish: @MainActor (Result<String, Error>) -> Void

    var body: some View {
        Color.clear
            .frame(width: 0, height: 0)
            .translationTask(
                source: sourceLanguage.map { Locale.Language(identifier: $0) },
                target: Locale.Language(identifier: lumosTargetLanguage)
            ) { session in
                do {
                    let response = try await session.translate(text)
                    await onFinish(.success(response.targetText))
                } catch {
                    await onFinish(.failure(error))
                }
            }
    }
}

/// Kısayol kaydı yalnız Lumos penceresi içinde, kullanıcı "Kısayol" düğmesine bastığında.
private struct LumosShortcutCapture: NSViewRepresentable {
    let onCapture: @MainActor (NSEvent) -> Void
    let onCancel: @MainActor () -> Void

    func makeNSView(context: Context) -> LumosShortcutCaptureView {
        let view = LumosShortcutCaptureView()
        view.onCapture = onCapture
        view.onCancel = onCancel
        return view
    }

    func updateNSView(_ nsView: LumosShortcutCaptureView, context: Context) {
        nsView.onCapture = onCapture
        nsView.onCancel = onCancel
    }
}

final class LumosShortcutCaptureView: NSView {
    var onCapture: (@MainActor (NSEvent) -> Void)?
    var onCancel: (@MainActor () -> Void)?

    override var acceptsFirstResponder: Bool { true }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        window?.makeFirstResponder(self)
    }

    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        guard event.type == .keyDown, window?.firstResponder === self else { return false }
        handle(event)
        return true
    }

    override func keyDown(with event: NSEvent) {
        handle(event)
    }

    private func handle(_ event: NSEvent) {
        if Int(event.keyCode) == kVK_Escape {
            onCancel?()
        } else {
            onCapture?(event)
        }
    }
}

/// Genel kısayol → seçili metni oku → küçük Lumos penceresinde Türkçe çeviri.
@MainActor
final class LumosSelectionTranslator {
    private let model = LumosTranslationModel()
    private var panel: NSPanel?
    private var hotKey: LumosHotKey?
    private var shortcut = LumosShortcut.load()
    private var isReading = false

    func start() {
        let hotKey = LumosHotKey { [weak self] in self?.trigger() }
        self.hotKey = hotKey
        model.shortcutLabel = shortcut.displayName
        let status = hotKey.register(shortcut)
        if status != noErr {
            model.shortcutMessage = registrationFailureMessage(status)
        }
    }

    private func trigger() {
        guard !isReading else { return }
        isReading = true
        model.beginReading()
        Task { [weak self] in
            // Seçim, Lumos penceresi öne gelmeden hedef uygulamadan okunur.
            let result = await LumosSelectionReader.readSelection()
            guard let self else { return }
            self.isReading = false
            switch result {
            case .success(let text):
                self.model.startTranslation(of: text)
            case .failure(let error):
                self.model.fail(
                    error.message,
                    showsAccessibilityButton: error == .accessibilityPermissionMissing
                )
            }
            self.showPanel()
        }
    }

    private func showPanel() {
        let panel = self.panel ?? makePanel()
        self.panel = panel
        if !panel.isVisible {
            position(panel)
        }
        panel.orderFrontRegardless()
    }

    private func makePanel() -> NSPanel {
        let panel = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 420, height: 320),
            styleMask: [.titled, .closable, .resizable, .utilityWindow, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.title = "Lumos Çeviri"
        panel.isFloatingPanel = true
        panel.level = .floating
        panel.hidesOnDeactivate = false
        panel.becomesKeyOnlyIfNeeded = true
        panel.isReleasedWhenClosed = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        let actions = LumosTranslationActions(
            copy: { [weak self] in self?.copyTranslation() },
            openAccessibilitySettings: { Self.openAccessibilitySettings() },
            startShortcutRecording: { [weak self] in self?.startShortcutRecording() },
            cancelShortcutRecording: { [weak self] in self?.stopShortcutRecording(message: nil) },
            captureShortcut: { [weak self] event in self?.captureShortcut(event) }
        )
        panel.contentView = NSHostingView(
            rootView: LumosTranslationView(model: model, actions: actions)
        )
        return panel
    }

    private func position(_ panel: NSPanel) {
        let mouse = NSEvent.mouseLocation
        let screen = NSScreen.screens.first { NSMouseInRect(mouse, $0.frame, false) } ?? NSScreen.main
        guard let visible = screen?.visibleFrame else {
            panel.center()
            return
        }
        let size = panel.frame.size
        let x = min(max(mouse.x - size.width / 2, visible.minX), visible.maxX - size.width)
        let y = min(max(mouse.y - size.height - 16, visible.minY), visible.maxY - size.height)
        panel.setFrameOrigin(NSPoint(x: x, y: y))
    }

    private func copyTranslation() {
        guard let translation = model.translation else { return }
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(translation, forType: .string)
        model.copied = true
    }

    private static func openAccessibilitySettings() {
        let link = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        if let url = URL(string: link) {
            NSWorkspace.shared.open(url)
        }
    }

    private func startShortcutRecording() {
        // Kayıt sırasında eski kısayol tetiklenmesin.
        hotKey?.unregister()
        model.shortcutMessage = nil
        model.isRecordingShortcut = true
        panel?.makeKey()
    }

    private func stopShortcutRecording(message: String?) {
        model.isRecordingShortcut = false
        let status = hotKey?.register(shortcut) ?? noErr
        model.shortcutLabel = shortcut.displayName
        model.shortcutMessage = status == noErr ? message : registrationFailureMessage(status)
    }

    private func captureShortcut(_ event: NSEvent) {
        let candidate = LumosShortcut(event: event)
        guard candidate.hasCommandLikeModifier else {
            model.shortcutMessage = "Kısayol en az ⌘, ⌥ veya ⌃ tuşlarından birini içermeli."
            return
        }
        guard let hotKey else { return }
        let status = hotKey.register(candidate)
        guard status == noErr else {
            stopShortcutRecording(message: registrationFailureMessage(status))
            return
        }
        shortcut = candidate
        candidate.save()
        model.isRecordingShortcut = false
        model.shortcutLabel = candidate.displayName
        model.shortcutMessage = "Kısayol kaydedildi."
    }

    private func registrationFailureMessage(_ status: OSStatus) -> String {
        if status == OSStatus(eventHotKeyExistsErr) {
            return "Bu kısayol başka bir uygulama tarafından kullanılıyor. Farklı bir kısayol seçin."
        }
        return "Lumos kısayolu kaydedilemedi (kod \(status))."
    }
}
