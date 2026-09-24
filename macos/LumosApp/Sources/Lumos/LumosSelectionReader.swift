import AppKit
import ApplicationServices
import Carbon

enum LumosSelectionError: Error, Equatable {
    case accessibilityPermissionMissing
    case secureInput
    case noSelection
    case tooLong(limit: Int)

    var message: String {
        switch self {
        case .accessibilityPermissionMissing:
            return "Lumos’un seçili metni okuyabilmesi için Erişilebilirlik izni gerekli. "
                + "Sistem Ayarları › Gizlilik ve Güvenlik › Erişilebilirlik bölümünde Lumos’u açın, "
                + "ardından kısayola yeniden basın."
        case .secureInput:
            return "Parola veya güvenli giriş alanlarından metin alınmaz."
        case .noSelection:
            return "Seçili metin bulunamadı. Metni seçip kısayola yeniden basın."
        case .tooLong(let limit):
            return "Seçim çok uzun. En fazla \(limit) karakter çevrilebilir."
        }
    }
}

/// Seçili metni yalnız kısayol anında okur. Önce Erişilebilirlik; metin
/// alınamazsa (ör. Google Docs) bir kez ⌘C gönderir ve panoyu eski haline getirir.
@MainActor
enum LumosSelectionReader {
    static let maxCharacters = 5000

    static func readSelection() async -> Result<String, LumosSelectionError> {
        // İzin istemi açılmaz; kullanıcı Sistem Ayarları'ndan kendisi verir.
        guard AXIsProcessTrusted() else { return .failure(.accessibilityPermissionMissing) }
        if IsSecureEventInputEnabled() { return .failure(.secureInput) }

        let targetApp = NSWorkspace.shared.frontmostApplication
        let focused = focusedElement(pid: targetApp?.processIdentifier)
        if let focused, isSecure(focused) { return .failure(.secureInput) }

        if let focused, let text = selectedText(of: focused), hasContent(text) {
            return validate(text)
        }

        guard let targetApp,
              targetApp.processIdentifier != ProcessInfo.processInfo.processIdentifier
        else {
            return .failure(.noSelection)
        }

        await waitForModifierRelease()
        // Kısayol basılıyken odak güvenli alana geçmiş olabilir.
        if IsSecureEventInputEnabled() { return .failure(.secureInput) }
        guard let copied = await copySelectionPreservingPasteboard(pid: targetApp.processIdentifier),
              hasContent(copied)
        else {
            return .failure(.noSelection)
        }
        return validate(copied)
    }

    private static func validate(_ text: String) -> Result<String, LumosSelectionError> {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count <= maxCharacters else { return .failure(.tooLong(limit: maxCharacters)) }
        return .success(trimmed)
    }

    private static func hasContent(_ text: String) -> Bool {
        !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private static func attribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, name as CFString, &value) == .success else {
            return nil
        }
        return value
    }

    private static func focusedElement(pid: pid_t?) -> AXUIElement? {
        var candidates = [AXUIElementCreateSystemWide()]
        if let pid {
            candidates.append(AXUIElementCreateApplication(pid))
        }
        for container in candidates {
            AXUIElementSetMessagingTimeout(container, 0.5)
            if let value = attribute(container, kAXFocusedUIElementAttribute),
               CFGetTypeID(value) == AXUIElementGetTypeID() {
                return unsafeDowncast(value, to: AXUIElement.self)
            }
        }
        return nil
    }

    private static func isSecure(_ element: AXUIElement) -> Bool {
        let subrole = attribute(element, kAXSubroleAttribute) as? String
        let role = attribute(element, kAXRoleAttribute) as? String
        return subrole == kAXSecureTextFieldSubrole || role == kAXSecureTextFieldSubrole
    }

    private static func selectedText(of element: AXUIElement) -> String? {
        attribute(element, kAXSelectedTextAttribute) as? String
    }

    /// Kısayoldaki ⌃⌥⌘ basılı kalırsa gönderilen ⌘C başka bir komuta dönüşür.
    private static func waitForModifierRelease() async {
        let held: CGEventFlags = [.maskCommand, .maskAlternate, .maskControl, .maskShift]
        for _ in 0..<40 {
            if CGEventSource.flagsState(.combinedSessionState).intersection(held).isEmpty {
                return
            }
            try? await Task.sleep(for: .milliseconds(25))
        }
    }

    private static func copySelectionPreservingPasteboard(pid: pid_t) async -> String? {
        let pasteboard = NSPasteboard.general
        let snapshot = LumosPasteboardSnapshot(pasteboard)
        let changeCountBefore = pasteboard.changeCount

        guard postCopyShortcut(to: pid) else { return nil }

        var copied: String?
        for _ in 0..<40 {
            try? await Task.sleep(for: .milliseconds(25))
            if pasteboard.changeCount != changeCountBefore {
                copied = pasteboard.string(forType: .string)
                break
            }
        }
        if pasteboard.changeCount != changeCountBefore {
            snapshot.restore(to: pasteboard)
        }
        return copied
    }

    private static func postCopyShortcut(to pid: pid_t) -> Bool {
        let source = CGEventSource(stateID: .privateState)
        let keyC = CGKeyCode(kVK_ANSI_C)
        guard let down = CGEvent(keyboardEventSource: source, virtualKey: keyC, keyDown: true),
              let up = CGEvent(keyboardEventSource: source, virtualKey: keyC, keyDown: false)
        else {
            return false
        }
        down.flags = .maskCommand
        up.flags = .maskCommand
        down.postToPid(pid)
        up.postToPid(pid)
        return true
    }
}

/// Kontrollü kopyalamadan önce panonun tüm öğe ve türlerini bellekte tutar.
struct LumosPasteboardSnapshot {
    private let items: [[(NSPasteboard.PasteboardType, Data)]]

    init(_ pasteboard: NSPasteboard) {
        items = (pasteboard.pasteboardItems ?? []).map { item in
            item.types.compactMap { type in
                item.data(forType: type).map { (type, $0) }
            }
        }
    }

    func restore(to pasteboard: NSPasteboard) {
        pasteboard.clearContents()
        let restored: [NSPasteboardItem] = items.map { entries in
            let item = NSPasteboardItem()
            for (type, data) in entries {
                item.setData(data, forType: type)
            }
            return item
        }
        if !restored.isEmpty {
            pasteboard.writeObjects(restored)
        }
    }
}
