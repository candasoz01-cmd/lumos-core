# Lumos iOS Repo Rules (M0 — private repo discipline)

| Field | Value |
|-------|--------|
| **Document type** | Private repo discipline — folder rules, ownership, dependency boundaries |
| **Status** | **M0 locked** — applies from first commit in `lumos-ios` |
| **Audience** | iOS engineering, Cursor build agents |
| **Related** | [`lumos-ios-core-architecture.md`](./lumos-ios-core-architecture.md) (cross-platform contract), [`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md) (Konduktör / Orkestratör) |

---

## 1. Purpose

The private **`lumos-ios`** repo enforces module discipline **from day one**. No throwaway prototype folders, no horizontal feature imports, no ad-hoc `Utils/` sprawl.

**Contract split:**

| Layer | Repository | Role |
|-------|------------|------|
| **Cross-platform architecture** | `lumos-core` (public) | Decisions, layer rules, approval wire contracts, App Store boundaries — [`lumos-ios-core-architecture.md`](./lumos-ios-core-architecture.md) |
| **iOS implementation layout** | `lumos-ios` (private) | Physical `App/` module tree, Swift, Xcode, assets |

This document is the **private-repo enforcement guide**. The architecture doc is the **platform-agnostic spec** both iOS and future Android/macOS can mirror conceptually.

---

## 2. Canonical folder tree (locked)

All product code lives under **`App/`** as peer modules — flat, no nested `Features/` container:

```
App/
├── UI/              # Screens, navigation shell, chat thread, settings flows
├── Voice/           # Speech input, transcription preview, audio session
├── Camera/          # Capture pipeline, photo picker, preview surfaces
├── Vision/          # Image analysis, on-device vision hooks (stub in v1)
├── Memory/          # User context, tasks, local/demo store
├── Security/        # Lock state, approval inbox, trust indicators, keychain gates
├── AI/              # Conductor orchestration, routing, task envelopes, approval state machine
├── Network/         # HTTP clients, hosted demo API, relay client (not App Store v1)
├── Accessibility/   # VoiceOver labels, Dynamic Type policy, a11y audit helpers
└── Shared/          # Design tokens, reusable components, extensions, shared DTOs
```

**Also at project root (not under `App/`):**

| Path | Purpose |
|------|---------|
| `Resources/` | `Assets.xcassets`, fonts, launch assets, `Localizable.strings`, demo fixtures |
| `LumosApp/` or `@main` target | Application entry — thin; wires modules only |

Exact Xcode group names mirror this tree. First commit message when repo opens: **`Initial iOS project scaffold`**.

---

## 3. Module ownership

| Module | Owns | Must not own |
|--------|------|--------------|
| **UI** | SwiftUI views, navigation shell, tab/slot layout, Chat thread UI, Settings screens, splash/launch presentation | Raw URLSession; conductor routing logic; keychain writes |
| **Voice** | Speech recognition UI hooks, audio session lifecycle, voice feature ViewModels | Direct Security approval mutations; network calls (use Network protocols) |
| **Camera** | AVFoundation capture, photo picker, camera preview surfaces | Vision analysis logic (delegate to Vision); network upload |
| **Vision** | Image processing, on-device vision stubs, analysis results | Camera session management; UI beyond vision-specific overlays |
| **Memory** | Local/demo task store, user context models, persistence adapters | Approval gates; global navigation |
| **Security** | Lock screen, approval inbox UI, trust badges, secure-storage **calls** via protocols | Orchestration routing; raw HTTP |
| **AI** | Conductor: intent routing, task envelopes, risk/approval requirements, cross-module coordination **protocols** | SwiftUI views; concrete API clients; feature-specific business UI |
| **Network** | URLSession clients, hosted demo API, relay client, request/response mapping, logging stubs | SwiftUI; feature navigation; approval business rules |
| **Accessibility** | Centralized a11y helpers, label builders, contrast checks, audit utilities | Feature business logic |
| **Shared** | Design system (colors, typography, spacing, icons), reusable components, Swift extensions, **shared** Codable types | Feature flows; service implementations; conductor logic |

---

## 4. Dependency rules (locked)

### 4.1 Direction

```
@main (App entry)
 ↓
UI, Voice, Camera, Vision, Memory, Security   ← feature surfaces
 ↓         ↓
AI (conductor)  ←  Network (via protocols defined in AI or Shared)
 ↓
Shared, Resources
Accessibility → may be imported by any module for helpers; must not import feature modules
```

| Rule | Detail |
|------|--------|
| **No horizontal imports** | `Voice` must not import `Security` directly. Cross-module needs go through **AI** (conductor) or **Network** facades |
| **AI is UI-agnostic** | Orchestration, envelopes, routing — no SwiftUI in AI |
| **Network is infrastructure** | Concrete HTTP, keychain-backed tokens, demo API — no views |
| **Shared is dumb** | Tokens, components, extensions — no feature or service logic |
| **App entry wires only** | `@main` registers dependencies and composes root view; no business rules |
| **Fail-closed** | Missing auth, missing relay token, or review misconfiguration → user-visible stop, not silent fallback |

### 4.2 Conductor alignment (Konduktör)

Maps to [`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md) Orkestratör M0:

| Conductor concept | iOS module |
|-------------------|------------|
| Task envelope | **AI** |
| Route / lane selection | **AI** |
| Tool / bridge delegation | **Network** |
| User gate (🔴 onay) | **Security** UI + **AI** approval state |
| Audit / rationale | **Network** logging → future Karar Duvarı sync |

**Agent-to-agent on device:** forbidden — same spirit as [ADR-008](../decisions/ADR-008-agent-network-boundary.md). Feature modules do not delegate to each other; **AI** mediates.

---

## 5. Conceptual ↔ physical mapping

The architecture spec ([§4 of lumos-ios-core-architecture](./lumos-ios-core-architecture.md#4-two-level-model-conceptual-vs-ios-physical)) uses cross-platform names. This repo uses the physical layout below.

| Conceptual (lumos-core) | Physical (`lumos-ios` under `App/`) |
|-------------------------|-------------------------------------|
| `App` (entry) | `@main` target + root composition in UI |
| `Core` (orchestration) | **AI** |
| `Features/Chat` | **UI** (chat thread) |
| `Features/Voice` | **Voice** |
| `Features/Vision` | **Vision** (+ **Camera** for capture) |
| `Features/Memory` | **Memory** |
| `Features/Settings` | **UI** (settings flows) + tokens in **Shared** |
| `Features/Security` | **Security** |
| `Services` | **Network** |
| `Models` | **Shared** (cross-cutting DTOs); module-local types stay in owning module |
| `Shared` | **Shared** |
| `Resources` | Project `Resources/` (outside `App/`) |
| *(new in iOS layout)* | **Accessibility**, **Camera** |

---

## 6. Import checklist (PR review)

Before merging any PR in `lumos-ios`:

- [ ] No `import` from one feature module (`Voice`, `Camera`, …) into another feature module
- [ ] Cross-module coordination goes through **AI** protocols or **Network** facades
- [ ] **AI** contains no SwiftUI / UIKit views
- [ ] **Network** contains no SwiftUI / UIKit views
- [ ] New shared types land in **Shared** only if used by ≥2 modules; otherwise keep local
- [ ] Design tokens added to **Shared**, not duplicated in feature modules
- [ ] Accessibility labels use **Accessibility** helpers where centralized policy applies
- [ ] No secrets, production URLs, or review credentials in git

---

## 7. Xcode reference (locked)

| Field | Value |
|-------|--------|
| **Xcode** | 26.6 |
| **Build** | 17F113 |
| **Role** | Canonical dev reference for `lumos-ios` — CI and local builds should match unless an ADR says otherwise |

---

## 8. Repo timing (reaffirmed)

| Step | Status |
|------|--------|
| Architecture + rules locked in `lumos-core` | ✓ (this doc + architecture spec) |
| Local Xcode skeleton first | Locked |
| Private `lumos-ios` when skeleton mature | Locked |
| First commit | `Initial iOS project scaffold` |

---

## 9. Explicit constraints

- Rules apply **from first commit** — no grace period for flat `Utils/` or cross-imports
- **`lumos-core` holds no Swift** — only contracts and discipline docs
- Changes to module boundaries require updating **both** this doc and [`lumos-ios-core-architecture.md`](./lumos-ios-core-architecture.md) in `lumos-core`

---

*Son güncelleme: 2026-07-05 — M0 private repo rules; App/ flat modules; Xcode 26.6 reference.*
