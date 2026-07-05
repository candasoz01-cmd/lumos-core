# Lumos iOS Core Architecture (V1 locked — M0 spec)

| Field | Value |
|-------|--------|
| **Document type** | Architecture spec — V1 locked (M0 spec) |
| **Status** | **V1 locked (M0 spec)** — no Swift code in `lumos-core`; primary goal is **architecture lock**, not setup/install |
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

**Current focus:** Lock Lumos iOS V1 architecture — not Xcode setup, install guides, or repo scaffolding in this document.

---

## 2. Multi-repo ecosystem (locked)

Long-term Lumos is a **multi-repo ecosystem**. Each surface owns its native stack; shared contracts live in the public core.

| Repository | Visibility | Role | Contents |
|------------|------------|------|----------|
| **`lumos-core`** | Public OSS | Shared logic, docs, protocols, architecture, decisions | This document, [`app-store-review-prep.md`](../app-store-review-prep.md), mobile approval wire contracts, ADRs — **no native iOS source** |
| **`lumos-ios`** | Private | Swift, Xcode, iOS UI, Apple integrations | App target, assets, entitlements, TestFlight / App Store binary |
| **`lumos-android`** | Future (private) | Kotlin / Compose, Android UI | Same Core contracts; independent team |
| **`lumos-web`** | Future | Web panel / PWA (partially in core today) | Shared protocols; web-specific UI |
| **`lumos-macos`** | Future (private) | AppKit / SwiftUI macOS surface | Same Core contracts; independent team |

**Public boundary:** Native iOS app code belongs in the **private** mobile repo per [`lumos-mobile-approval-mvp-plan.md`](../analysis/lumos-mobile-approval-mvp-plan.md) §10 and [`app-store-review-prep.md`](../app-store-review-prep.md) §7 (G1). `lumos-core` holds the **architecture contract** only.

### 2.1 Repo timing decision (locked)

| Decision | Status |
|----------|--------|
| **Do NOT open `lumos-ios` GitHub repo immediately** | Locked |
| **Local development first** — fast iteration for the first few days; mature skeleton locally | Locked (user choice) |
| **Then** first commit to private `lumos-ios` when skeleton is ready | Locked |
| **First commit message** (when repo opens) | `Initial iOS project scaffold` |

Both "repo-first" and "local-first" are valid strategies; **local-first is the chosen path**. No feature code in that first commit — Xcode project, folder tree, launch screen assets, and README pointing back to this spec.

**This spec does not instruct you to create the repo now.** Local Xcode work may proceed without a remote until the skeleton is mature.

---

## 3. V1 Architecture Lock

The following decisions are **locked for Lumos iOS V1**. Changes require an explicit architecture revision in `lumos-core`, not ad-hoc drift in the private repo.

| Locked item | Reference | Notes |
|-------------|-----------|-------|
| **Folder tree** | §4 | Logical layout under `Lumos/` — App, Core, Features/*, Services, Models, Resources, Shared |
| **Layer rules** | §5 | Dependency direction, Conductor alignment, fail-closed, no horizontal Feature↔Feature |
| **First screen spec** | §6 | Black background, centered logo, «Hayal etmen yeterli.» — heartbeat, not Hello World |
| **Multi-repo split** | §2 | Core = public contracts; iOS = private native; future platforms mirror pattern |
| **Local-first repo timing** | §2.1 | Local skeleton first; private repo opens when ready — not day one |
| **v1 OUT scope** | [`app-store-review-prep.md`](../app-store-review-prep.md) §5 | Canonical boundary for what v1 does **not** ship — locked reference |

### 3.1 v1 OUT scope (locked reference)

Canonical source: [`app-store-review-prep.md`](../app-store-review-prep.md) **§5 v1 Capability boundary**. Summary — do not expand v1 without updating that doc:

| Out of scope for v1 |
|---------------------|
| Full Lumos cloud / multi-device sync |
| Sign in with Apple (unless auth path ships) |
| Push Notifications (unless approval alerts are live) |
| iCloud, App Groups, shared containers |
| Siri / Shortcuts, Background modes, Apple Intelligence hooks |
| visionOS / macOS targets |
| Unused Apple entitlements (§5.2 defaults OFF) |
| LAN relay in App Store build (review uses hosted demo API) |
| Real OS / device control (private layer; stub in review) |

---

## 4. Folder tree and responsibilities (locked)

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

### 4.1 Per-folder responsibility

| Folder | Owns | Must not own |
|--------|------|--------------|
| **App** | `@main`, scene lifecycle, root `WindowGroup`, dependency container bootstrap, feature module registration, first-launch routing | Feature UI, network calls, business rules |
| **Core** | Orchestrator/conductor **interfaces**, routing contracts, task envelope types, approval gate abstractions, shared error/result types, feature-agnostic use-case protocols | UIKit/SwiftUI views, concrete API clients, feature-specific state |
| **Features/** | Screen flows, feature ViewModels, feature-local state, user-facing copy for that domain | Direct calls to another Feature's types; raw URLSession; global singletons bypassing Services |
| **Services/** | HTTP clients, LAN relay client, secure storage, keychain, demo/review API, logging, analytics stubs | SwiftUI views; feature-specific navigation |
| **Models** | Codable structs, domain enums, API mapping types shared across Features and Services | View logic; side effects |
| **Resources** | `Assets.xcassets`, fonts, launch storyboard/SwiftUI launch, `Localizable.strings`, demo JSON fixtures | Swift code (except generated asset symbols) |
| **Shared** | Design system (colors, typography), reusable components (buttons, banners), Swift extensions | Feature business rules; service implementations |

### 4.2 Feature modules (v1 placeholders)

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

## 5. Layer rules (Conductor-aligned, locked)

Mobile architecture mirrors the **Lumos Orkestratör / Konduktör** vision ([`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md) — M0): coordination, not feature silos talking past each other.

### 5.1 Dependency direction

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

### 5.2 Conductor mapping (M0 — conceptual)

| Conductor concept | iOS layer |
|-------------------|-----------|
| Task envelope | `Core` — intent + risk + approval requirement |
| Route / lane selection | `Core` — `RoutingCoordinator` or equivalent protocol |
| Tool / bridge delegation | `Services` — relay client, hosted demo API |
| User gate (🔴 onay) | `Features/Security` + `Core` approval state |
| Audit / rationale | `Services` logging → future sync with Karar Duvarı patterns |

**Agent-to-agent on device:** forbidden — same spirit as [ADR-008](../decisions/ADR-008-agent-network-boundary.md): Features do not delegate to each other horizontally; **Core** (conductor) mediates.

---

## 6. First launch screen spec (locked, no code)

V1 deliverable when the private Xcode project is scaffolded (locally first, then in `lumos-ios`). **This section is the UI contract** — implementation is SwiftUI in the private repo, not in `lumos-core`.

### 6.1 Visual spec

| Element | Spec |
|---------|------|
| **Background** | Solid black (`#000000` or system black) — edge to edge |
| **Logo** | Lumos mark, centered (horizontal + vertical), vector asset from `Resources/` |
| **Tagline** | «Hayal etmen yeterli.» — centered below logo, readable contrast (e.g. white or brand secondary at ~70% opacity) |
| **Typography** | System or brand font; tagline one line if possible; Dynamic Type supported |
| **Chrome** | No tab bar, no navigation bar, no buttons on first paint — pure presence |
| **Animation** | Optional subtle fade-in (≤ 400ms); no splash video |

### 6.2 Behavior (M0)

| Behavior | Spec |
|----------|------|
| **Cold launch** | Shows heartbeat screen immediately |
| **Duration** | Static until user gesture or auto-advance (future: tap or 2s → home shell) — **M0 may stay static** |
| **Status bar** | Light content on dark background |
| **Safe area** | Logo + text respect safe area; no clipping on notch/Dynamic Island |

### 6.3 SwiftUI notes (optional — private repo only)

- Root: `ZStack` with `Color.black.ignoresSafeArea()` + `VStack` (logo, spacing, text)
- Logo: `Image("LumosLogo")` resizable, scaledToFit, max width ~40% of screen
- Tagline: `.font(.title3)` or design token; `.multilineTextAlignment(.center)`
- Preview: `#Preview` with iPhone 15 Pro + SE sizes
- **Accessibility:** VoiceOver reads «Lumos. Hayal etmen yeterli.»

### 6.4 Explicit non-goals (M0 screen)

- No login, no bridge pairing, no network call on launch
- No «Loading…» spinner unless app init truly blocks (prefer instant paint)
- No third-party SDK init on this screen

---

## 7. v1 scope vs future

Canonical App Store boundary: [`app-store-review-prep.md`](../app-store-review-prep.md) **§5 v1 Capability boundary** (locked reference — see §3.1).

### 7.1 In scope for v1 (iOS)

| Area | v1 |
|------|-----|
| Native iOS app (App Store) | ✓ |
| Heartbeat launch + core navigation shell | ✓ |
| Demo Workspace / Review Mode | ✓ |
| Secure **approval UX** (explicit consent) | ✓ |
| Tasks, Settings, Chat/Approvals tabs (demo content) | ✓ |
| Minimal Apple entitlements (§5.2 defaults OFF) | ✓ |

### 7.2 Out of scope for v1

See **§3.1** and [`app-store-review-prep.md`](../app-store-review-prep.md) §5 for the locked OUT list.

### 7.3 OSS vs private (mobile)

| Capability | `lumos-core` (OSS) | `lumos-ios` (private) |
|------------|-------------------|----------------------|
| Bridge / pending JSON contract | ✓ | Consumes via Services |
| LAN relay demo | ✓ | Not in App Store v1 |
| Native UI + Review Mode | — | ✓ |
| Hosted demo API client | — | ✓ |

---

## 8. Cross-references

| Topic | Document |
|-------|----------|
| **Orkestratör M0** | [`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md) — Lumos Orkestratör v1, Konduktör protokolü |
| **Storage choice** | Same draft — Depolama seçimi; Settings must disclose actual flow |
| **App Store prep** | [`app-store-review-prep.md`](../app-store-review-prep.md) |
| **Mobile approval wire** | [`lumos-mobile-approval-mvp-plan.md`](../analysis/lumos-mobile-approval-mvp-plan.md) |
| **Internal Alpha scope** | [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](../INTERNAL_ALPHA_RELEASE_SCOPE.md) — O8 native app out of Alpha OSS scope |
| **Product safety** | [`app-store-product-safety-privacy.md`](../app-store-product-safety-privacy.md) |
| **ADR-008** | Agent network boundary — no horizontal feature delegation |

### 8.1 App Store gaps (G1–G6)

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

## 9. Multi-platform note

Long-term: **Android, iOS, macOS, Vision Pro, Web** share logic via **Core + Models + Services protocols**, not duplicated feature code. See §2 for the repo map.

| Layer | Share strategy |
|-------|----------------|
| **Core, Models** | Kotlin Multiplatform / Swift shared package / future Rust core — decision deferred; **interfaces first** in this spec |
| **Services** | Platform implementations (Keychain vs Keystore, etc.) |
| **Features** | Per-platform UI (SwiftUI, Compose, AppKit) |
| **Shared** | Design tokens exported per platform |

**Principle:** Write orchestration and approval rules once in Core; UI stays native per platform. iOS V1 establishes the pattern private repos for other platforms can mirror.

---

## 10. Build phases (recommended)

| Phase | Where | Deliverable |
|-------|-------|-------------|
| **V1 lock (this doc)** | `lumos-core` | Architecture spec locked — **no Swift in public repo** |
| **M1 — local first** | Local Xcode (no remote required yet) | Folder tree, heartbeat screen, mature skeleton |
| **M1 — repo open** | Private `lumos-ios` | First commit: `Initial iOS project scaffold`; CI (lint/build) |
| **M2** | `lumos-ios` | Navigation shell, Review Mode flag, hosted demo API stub |
| **M3** | `lumos-ios` + backend | Approvals tab, G3 demo workspace |
| **M4** | Private + ops | TestFlight, App Store Connect, G5–G6 |

**Note:** M1 local work and M1 repo open are sequential, not simultaneous. Do not block local iteration on repo creation.

---

## 11. Explicit constraints (this PR)

- **NO Swift files** are added to `lumos-core` — documentation only.
- **NO Xcode project** in the public repository unless the user explicitly opts into a public scaffold (default: **private `lumos-ios`**).
- **NO production secrets**, entitlements, or review credentials in git.
- Cursor and human engineers implement against this spec in the private repo (local first, then remote).

---

## 12. Success criteria (V1 lock)

| Criterion | Met when |
|-----------|----------|
| V1 architecture locked | §3 decisions documented and marked locked |
| Folder responsibilities documented | ✓ §4 |
| Layer rules enforceable | Review checklist in §5 passes for first feature PR |
| First screen spec unambiguous | Design can implement without guessing — §6 |
| v1 boundary linked | §3.1 / §7 ↔ app-store-review-prep §5 |
| Repo placement + timing clear | §2 — local-first, private `lumos-ios` when ready |

---

## 13. Open questions (minimal)

Only unresolved items — not architecture decisions:

| Question | Notes |
|----------|-------|
| **Xcode version** | Pin when local skeleton starts (team standard TBD) |
| **Exact logo asset** | Vector source file / export spec for `Resources/` (brand asset TBD) |

---

*Son güncelleme: 2026-07-05 — V1 architecture lock; multi-repo map; local-first repo timing; docs only, no Swift.*
