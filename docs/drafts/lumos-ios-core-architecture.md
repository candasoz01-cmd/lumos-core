# Lumos iOS Core Architecture (M0)

| Field | Value |
|-------|--------|
| **Document type** | Architecture spec — M0 Concept |
| **Status** | **Draft / M0** — no Swift code in `lumos-core` |
| **Audience** | iOS engineering (private repo), Cursor build agents, release ops |
| **Related** | [`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md), [`app-store-review-prep.md`](../app-store-review-prep.md), [`lumos-mobile-approval-mvp-plan.md`](../analysis/lumos-mobile-approval-mvp-plan.md), [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](../INTERNAL_ALPHA_RELEASE_SCOPE.md) |

---

## 1. Purpose — first heartbeat, not Hello World

Lumos iOS is not a template app. The first shipped screen is a **heartbeat**: proof that the shell exists, the brand is present, and the product philosophy is visible before any feature module loads.

| Principle | Meaning |
|-----------|---------|
| **First heartbeat** | App launches → user sees Lumos identity and one intentional line of copy — not Xcode defaults |
| **Not Hello World** | No placeholder navigation, no debug menus, no «Lorem ipsum» in v0 scaffold |
| **Architecture first** | Folder tree, layer rules, and service boundaries are defined **before** Swift files land |
| **Clean skeleton** | Real features (Chat, Voice, Vision, Memory, Settings, Security) attach to this tree later — no throwaway prototype structure |

**One-line intent:** *«Hayal etmen yeterli.»* — the app opens on black, centered Lumos logo, that line. Everything else comes later on the same skeleton.

---

## 2. Repository placement

| Repository | Role | Contents |
|------------|------|----------|
| **`lumos-core`** (public OSS) | Spec + App Store prep | This document, [`app-store-review-prep.md`](../app-store-review-prep.md), mobile approval wire contracts — **no native iOS source** |
| **`lumos-ios`** (recommended **private**) | Xcode project + Swift/SwiftUI | App target, assets, entitlements, TestFlight / App Store binary |

**Public boundary:** Native iOS app code belongs in the **private** mobile repo per [`lumos-mobile-approval-mvp-plan.md`](../analysis/lumos-mobile-approval-mvp-plan.md) §10 and [`app-store-review-prep.md`](../app-store-review-prep.md) §7 (G1). `lumos-core` holds the **architecture contract** only.

**First commit (when `lumos-ios` is created):**

```
Initial iOS project scaffold
```

No feature code in that commit — Xcode project, folder tree, launch screen assets, and README pointing back to this spec.

---

## 3. Folder tree and responsibilities

Target Xcode / Swift package layout (logical names; physical groups mirror this tree):

```
Lumos/
├── App/                    # Application entry, lifecycle, root composition
├── Core/                   # Cross-cutting domain logic, orchestration hooks, protocols
├── Features/
│   ├── Chat/
│   ├── Voice/
│   ├── Vision/
│   ├── Memory/
│   ├── Settings/
│   └── Security/
├── Services/               # Infrastructure adapters (network, storage, relay, auth)
├── Models/                 # Shared value types, DTOs, domain enums
├── Resources/              # Assets, localization, bundled fixtures
└── Shared/                 # UI primitives, extensions, design tokens — no feature logic
```

### 3.1 Per-folder responsibility

| Folder | Owns | Must not own |
|--------|------|--------------|
| **App** | `@main`, scene lifecycle, root `WindowGroup`, dependency container bootstrap, feature module registration, first-launch routing | Feature UI, network calls, business rules |
| **Core** | Orchestrator/conductor **interfaces**, routing contracts, task envelope types, approval gate abstractions, shared error/result types, feature-agnostic use-case protocols | UIKit/SwiftUI views, concrete API clients, feature-specific state |
| **Features/** | Screen flows, feature ViewModels, feature-local state, user-facing copy for that domain | Direct calls to another Feature's types; raw URLSession; global singletons bypassing Services |
| **Services/** | HTTP clients, LAN relay client, secure storage, keychain, demo/review API, logging, analytics stubs | SwiftUI views; feature-specific navigation |
| **Models** | Codable structs, domain enums, API mapping types shared across Features and Services | View logic; side effects |
| **Resources** | `Assets.xcassets`, fonts, launch storyboard/SwiftUI launch, `Localizable.strings`, demo JSON fixtures | Swift code (except generated asset symbols) |
| **Shared** | Design system (colors, typography), reusable components (buttons, banners), Swift extensions | Feature business rules; service implementations |

### 3.2 Feature modules (v1 placeholders)

Each `Features/*` folder starts as an **empty module boundary** with a README or `FeaturePlaceholder.swift` stub in the **private repo only** — not in `lumos-core`. Responsibilities when implemented:

| Feature | Future scope (not M0) |
|---------|------------------------|
| **Chat** | Assistant thread, demo/review canned replies |
| **Voice** | Speech input preview, on-device or stub transcription |
| **Vision** | Camera/photo preview for capture demos |
| **Memory** | User context, tasks, local/demo store |
| **Settings** | Profile, privacy, permissions, storage choice disclosure |
| **Security** | Lock state, approval inbox, trust indicators |

---

## 4. Layer rules (Conductor-aligned)

Mobile architecture mirrors the **Lumos Orkestratör / Konduktör** vision ([`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md) — M0): coordination, not feature silos talking past each other.

### 4.1 Dependency direction

```
App
 ↓
Features  →  Core (protocols, routing, envelopes)
 ↓              ↑
Services  ←  Models
 ↓
Shared, Resources
```

| Rule | Detail |
|------|--------|
| **Features ↛ Features** | `Chat` does not import `Security` directly. Cross-feature needs go through **Core** routing or a **Service** facade |
| **Features → Services** | Features depend on service **protocols** defined in Core; concrete implementations live in Services |
| **Core is UI-agnostic** | Core holds orchestration contracts, not SwiftUI |
| **App wires everything** | Composition root registers services and injects into feature entry points |
| **Fail-closed** | Missing auth, missing relay token, or review/demo misconfiguration → stop with user-visible state, not silent fallback |

### 4.2 Conductor mapping (M0 — conceptual)

| Conductor concept | iOS layer |
|-------------------|-----------|
| Task envelope | `Core` — intent + risk + approval requirement |
| Route / lane selection | `Core` — `RoutingCoordinator` or equivalent protocol |
| Tool / bridge delegation | `Services` — relay client, hosted demo API |
| User gate (🔴 onay) | `Features/Security` + `Core` approval state |
| Audit / rationale | `Services` logging → future sync with Karar Duvarı patterns |

**Agent-to-agent on device:** forbidden — same spirit as [ADR-008](../decisions/ADR-008-agent-network-boundary.md): Features do not delegate to each other horizontally; **Core** (conductor) mediates.

---

## 5. First launch screen spec (no code)

M0 deliverable when the private Xcode repo is scaffolded. **This section is the UI contract** — implementation is SwiftUI in `lumos-ios`, not in `lumos-core`.

### 5.1 Visual spec

| Element | Spec |
|---------|------|
| **Background** | Solid black (`#000000` or system black) — edge to edge |
| **Logo** | Lumos mark, centered (horizontal + vertical), vector asset from `Resources/` |
| **Tagline** | «Hayal etmen yeterli.» — centered below logo, readable contrast (e.g. white or brand secondary at ~70% opacity) |
| **Typography** | System or brand font; tagline one line if possible; Dynamic Type supported |
| **Chrome** | No tab bar, no navigation bar, no buttons on first paint — pure presence |
| **Animation** | Optional subtle fade-in (≤ 400ms); no splash video |

### 5.2 Behavior (M0)

| Behavior | Spec |
|----------|------|
| **Cold launch** | Shows heartbeat screen immediately |
| **Duration** | Static until user gesture or auto-advance (future: tap or 2s → home shell) — **M0 may stay static** |
| **Status bar** | Light content on dark background |
| **Safe area** | Logo + text respect safe area; no clipping on notch/Dynamic Island |

### 5.3 SwiftUI notes (optional — private repo only)

- Root: `ZStack` with `Color.black.ignoresSafeArea()` + `VStack` (logo, spacing, text)
- Logo: `Image("LumosLogo")` resizable, scaledToFit, max width ~40% of screen
- Tagline: `.font(.title3)` or design token; `.multilineTextAlignment(.center)`
- Preview: `#Preview` with iPhone 15 Pro + SE sizes
- **Accessibility:** VoiceOver reads «Lumos. Hayal etmen yeterli.»

### 5.4 Explicit non-goals (M0 screen)

- No login, no bridge pairing, no network call on launch
- No «Loading…» spinner unless app init truly blocks (prefer instant paint)
- No third-party SDK init on this screen

---

## 6. v1 scope vs future

Canonical App Store boundary: [`app-store-review-prep.md`](../app-store-review-prep.md) **§5 v1 Capability boundary**.

### 6.1 In scope for v1 (iOS)

| Area | v1 |
|------|-----|
| Native iOS app (App Store) | ✓ |
| Heartbeat launch + core navigation shell | ✓ |
| Demo Workspace / Review Mode | ✓ |
| Secure **approval UX** (explicit consent) | ✓ |
| Tasks, Settings, Chat/Approvals tabs (demo content) | ✓ |
| Minimal Apple entitlements (§5.2 defaults OFF) | ✓ |

### 6.2 Out of scope for v1

| Area | Deferred |
|------|----------|
| Full cloud / multi-device sync | Post-v1 |
| Sign in with Apple | Unless auth path ships |
| Push notifications | Unless approval alerts live |
| iCloud, App Groups | Post-v1 |
| LAN relay in App Store build | Review uses hosted demo API ([§4.3](../app-store-review-prep.md)) |
| visionOS / macOS targets | Separate surfaces |
| Real OS / device control | Private layer; stub in review |

### 6.3 OSS vs private (mobile)

| Capability | `lumos-core` (OSS) | `lumos-ios` (private) |
|------------|-------------------|----------------------|
| Bridge / pending JSON contract | ✓ | Consumes via Services |
| LAN relay demo | ✓ | Not in App Store v1 |
| Native UI + Review Mode | — | ✓ |
| Hosted demo API client | — | ✓ |

---

## 7. Cross-references

| Topic | Document |
|-------|----------|
| **Orkestratör M0** | [`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md) — Lumos Orkestratör v1, Konduktör protokolü |
| **Storage choice** | Same draft — Depolama seçimi; Settings must disclose actual flow |
| **App Store prep** | [`app-store-review-prep.md`](../app-store-review-prep.md) |
| **Mobile approval wire** | [`lumos-mobile-approval-mvp-plan.md`](../analysis/lumos-mobile-approval-mvp-plan.md) |
| **Internal Alpha scope** | [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](../INTERNAL_ALPHA_RELEASE_SCOPE.md) — O8 native app out of Alpha OSS scope |
| **Product safety** | [`app-store-product-safety-privacy.md`](../app-store-product-safety-privacy.md) |
| **ADR-008** | Agent network boundary — no horizontal feature delegation |

### 7.1 App Store gaps (G1–G6)

From [`app-store-review-prep.md`](../app-store-review-prep.md) §7 — architecture acknowledges; implementation is private:

| Gap | Owner | This spec addresses |
|-----|-------|---------------------|
| **G1** Native iOS app | Private `lumos-ios` | Folder tree, layer rules, heartbeat screen |
| **G2** Cloud auth | Backend + identity | Services layer placeholder; not M0 |
| **G3** Review Mode + Demo API | Backend + mobile | App routing + Services contract |
| **G4** Hosted demo env | DevOps | Services base URL config |
| **G5** Review account provisioning | Ops | Out of architecture doc |
| **G6** Full-path QA | Mobile QA | After G1–G3 |

---

## 8. Multi-platform note

Long-term: **Android, iOS, macOS, Vision Pro** share logic via **Core + Models + Services protocols**, not duplicated feature code.

| Layer | Share strategy |
|-------|----------------|
| **Core, Models** | Kotlin Multiplatform / Swift shared package / future Rust core — decision deferred; **interfaces first** in this spec |
| **Services** | Platform implementations (Keychain vs Keystore, etc.) |
| **Features** | Per-platform UI (SwiftUI, Compose, AppKit) |
| **Shared** | Design tokens exported per platform |

**Principle:** Write orchestration and approval rules once in Core; UI stays native per platform. iOS M0 establishes the pattern private repos for other platforms can mirror.

---

## 9. Build phases (recommended)

| Phase | Repo | Deliverable |
|-------|------|-------------|
| **M0 (this doc)** | `lumos-core` | Architecture spec only — **no Swift in public repo** |
| **M1** | `lumos-ios` | Xcode scaffold, folder tree, heartbeat screen, CI (lint/build) |
| **M2** | `lumos-ios` | Navigation shell, Review Mode flag, hosted demo API stub |
| **M3** | `lumos-ios` + backend | Approvals tab, G3 demo workspace |
| **M4** | Private + ops | TestFlight, App Store Connect, G5–G6 |

---

## 10. Explicit constraints (this PR)

- **NO Swift files** are added to `lumos-core` in the architecture PR — documentation only.
- **NO Xcode project** in the public repository unless the user explicitly opts into a public scaffold (default: **private `lumos-ios`**).
- **NO production secrets**, entitlements, or review credentials in git.
- Cursor and human engineers implement against this spec in the private repo.

---

## 11. Success criteria (M0)

| Criterion | Met when |
|-----------|----------|
| Folder responsibilities documented | ✓ this doc |
| Layer rules enforceable | Review checklist in §4 passes for first feature PR |
| First screen spec unambiguous | Design can implement without guessing |
| v1 boundary linked | §6 ↔ app-store-review-prep §5 |
| Repo placement clear | `lumos-ios` private recommended |

---

*Son güncelleme: 2026-07-05 — M0 architecture spec; docs only, no Swift.*
