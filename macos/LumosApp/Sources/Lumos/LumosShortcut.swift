import AppKit
import Carbon

/// Seçili metin çevirisi için genel kısayol. Carbon hot key yalnız bu tuş
/// birleşimini teslim eder; klavye sürekli dinlenmez ve ek izin gerekmez.
struct LumosShortcut: Equatable {
    var keyCode: UInt32
    var carbonModifiers: UInt32
    var keyLabel: String

    static let defaultValue = LumosShortcut(
        keyCode: UInt32(kVK_ANSI_T),
        carbonModifiers: UInt32(controlKey | optionKey | cmdKey),
        keyLabel: "T"
    )

    private static let keyCodeKey = "LumosTranslateShortcutKeyCode"
    private static let modifiersKey = "LumosTranslateShortcutModifiers"
    private static let labelKey = "LumosTranslateShortcutKey"

    var displayName: String {
        var result = ""
        if carbonModifiers & UInt32(controlKey) != 0 { result += "⌃" }
        if carbonModifiers & UInt32(optionKey) != 0 { result += "⌥" }
        if carbonModifiers & UInt32(shiftKey) != 0 { result += "⇧" }
        if carbonModifiers & UInt32(cmdKey) != 0 { result += "⌘" }
        return result + keyLabel
    }

    /// En az bir ⌘, ⌥ veya ⌃ ister; yalnız harf veya ⇧+harf yazmayı bozar.
    var hasCommandLikeModifier: Bool {
        carbonModifiers & UInt32(cmdKey | optionKey | controlKey) != 0
    }

    init(keyCode: UInt32, carbonModifiers: UInt32, keyLabel: String) {
        self.keyCode = keyCode
        self.carbonModifiers = carbonModifiers
        self.keyLabel = keyLabel
    }

    init(event: NSEvent) {
        let flags = event.modifierFlags
        var modifiers: UInt32 = 0
        if flags.contains(.command) { modifiers |= UInt32(cmdKey) }
        if flags.contains(.option) { modifiers |= UInt32(optionKey) }
        if flags.contains(.control) { modifiers |= UInt32(controlKey) }
        if flags.contains(.shift) { modifiers |= UInt32(shiftKey) }
        let label: String
        switch Int(event.keyCode) {
        case kVK_Space: label = "Space"
        case kVK_Return: label = "↩"
        case kVK_Tab: label = "⇥"
        default: label = (event.charactersIgnoringModifiers ?? "?").uppercased()
        }
        self.init(keyCode: UInt32(event.keyCode), carbonModifiers: modifiers, keyLabel: label)
    }

    static func load() -> LumosShortcut {
        let defaults = UserDefaults.standard
        guard defaults.object(forKey: keyCodeKey) != nil,
              defaults.object(forKey: modifiersKey) != nil,
              let label = defaults.string(forKey: labelKey), !label.isEmpty
        else {
            return defaultValue
        }
        let shortcut = LumosShortcut(
            keyCode: UInt32(truncatingIfNeeded: defaults.integer(forKey: keyCodeKey)),
            carbonModifiers: UInt32(truncatingIfNeeded: defaults.integer(forKey: modifiersKey)),
            keyLabel: label
        )
        return shortcut.hasCommandLikeModifier ? shortcut : defaultValue
    }

    func save() {
        let defaults = UserDefaults.standard
        defaults.set(Int(keyCode), forKey: Self.keyCodeKey)
        defaults.set(Int(carbonModifiers), forKey: Self.modifiersKey)
        defaults.set(keyLabel, forKey: Self.labelKey)
    }
}

@MainActor
final class LumosHotKey {
    private var hotKeyRef: EventHotKeyRef?
    private var handlerRef: EventHandlerRef?
    private let onPress: @MainActor () -> Void

    init(onPress: @escaping @MainActor () -> Void) {
        self.onPress = onPress
    }

    func register(_ shortcut: LumosShortcut) -> OSStatus {
        unregister()
        if handlerRef == nil {
            var spec = EventTypeSpec(
                eventClass: OSType(kEventClassKeyboard),
                eventKind: UInt32(kEventHotKeyPressed)
            )
            let status = InstallEventHandler(
                GetApplicationEventTarget(),
                lumosHotKeyHandler,
                1,
                &spec,
                Unmanaged.passUnretained(self).toOpaque(),
                &handlerRef
            )
            guard status == noErr else { return status }
        }
        // 'LMST'
        let identifier = EventHotKeyID(signature: OSType(0x4C4D_5354), id: 1)
        var reference: EventHotKeyRef?
        let status = RegisterEventHotKey(
            shortcut.keyCode,
            shortcut.carbonModifiers,
            identifier,
            GetApplicationEventTarget(),
            0,
            &reference
        )
        if status == noErr {
            hotKeyRef = reference
        }
        return status
    }

    func unregister() {
        if let hotKeyRef {
            UnregisterEventHotKey(hotKeyRef)
            self.hotKeyRef = nil
        }
    }

    fileprivate func fire() {
        onPress()
    }
}

private func lumosHotKeyHandler(
    _ nextHandler: EventHandlerCallRef?,
    _ event: EventRef?,
    _ userData: UnsafeMutableRawPointer?
) -> OSStatus {
    guard let userData else { return OSStatus(eventNotHandledErr) }
    let hotKey = Unmanaged<LumosHotKey>.fromOpaque(userData).takeUnretainedValue()
    // Uygulama olay hedefi ana iş parçacığında çağrılır.
    MainActor.assumeIsolated {
        hotKey.fire()
    }
    return noErr
}
