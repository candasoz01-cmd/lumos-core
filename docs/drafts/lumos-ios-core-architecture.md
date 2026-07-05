# Lumos iOS Core Architecture (V1 locked — M0 spec)

| Field | Value |
|-------|--------|
| **Document type** | Architecture spec — V1 locked (M0 spec) |
| **Status** | **V1 locked (M0 spec)** — Hello World era **ended**; architecture lock complete. Next work: design system → splash → nav skeleton (see §14). No Swift in `lumos-core`. |
| **Audience** | iOS engineering (private repo), Cursor build agents, release ops |
| **Related** | [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md), [`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md), [`app-store-review-prep.md`](../app-store-review-prep.md), [`lumos-mobile-approval-mvp-plan.md`](../analysis/lumos-mobile-approval-mvp-plan.md), [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](../INTERNAL_ALPHA_RELEASE_SCOPE.md) |

---

## 1. Purpose — first heartbeat, not Hello World

Lumos iOS is not a template app. The first shipped screen is a **heartbeat**: proof that the shell exists, the brand is present, and the product philosophy is visible before any feature module loads.

| Principle | Meaning |
|-----------|---------|
| **First heartbeat** | App launches → user sees Lumos identity and one intentional line of copy — not Xcode defaults |
| **Not Hello World** | No placeholder navigation, no debug menus, no «Lorem ipsum» in v0 scaffold |
| **Architecture first** | Folder tree, layer rules, and service boundaries are defined **before** Swift files land |
| **Clean skeleton** | Real features attach to this tree later — no throwaway prototype structure |

**One-line intent:** *«Hayal etmen yeterli.»* — the app opens on black, centered Lumos logo, that line. Everything else comes later on the same skeleton.

**Hello World era ended:** The M0 spec lock is complete. Future sessions implement against this skeleton — not exploratory scaffolding.

**Current focus:** Cross-platform architecture contract in `lumos-core`; physical module tree and enforcement in private `lumos-ios` per [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md).

---

## 2. Multi-repo ecosystem (locked)

Long-term Lumos is a **multi-repo ecosystem**. Each surface owns its native stack; shared contracts live in the public core.

| Repository | Visibility | Role | Contents |
|------------|------------|------|----------|
| **`lumos-core`** | Public OSS | Shared logic, docs, protocols, architecture, decisions | This document, [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md), [`app-store-review-prep.md`](../app-store-review-prep.md), mobile approval wire contracts, ADRs — **no native iOS source** |
| **`lumos-ios`** | Private | Swift, Xcode, iOS UI, Apple integrations | `App/` module tree, assets, entitlements, TestFlight / App Store binary |
| **`lumos-android`** | Future (private) | Kotlin / Compose, Android UI | Same conceptual contracts; independent physical layout |
| **`lumos-web`** | Future | Web panel / PWA (partially in core today) | Shared protocols; web-specific UI |
| **`lumos-macos`** | Future (private) | AppKit / SwiftUI macOS surface | Same conceptual contracts; independent team |

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
| **Two-level model** | §4 | Conceptual (cross-platform) vs physical (`App/` flat modules in private repo) |
| **Physical folder tree** | §4.2, [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md) | `App/UI`, `Voice`, `Camera`, `Vision`, `Memory`, `Security`, `AI`, `Network`, `Accessibility`, `Shared` |
| **Layer rules** | §5 | Dependency direction, Conductor alignment, fail-closed, no horizontal module imports |
| **Xcode reference** | §13 | Xcode 26.6, Build 17F113 — canonical dev reference |
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

## 4. Two-level model: conceptual vs iOS physical

Architecture uses **two complementary views**. They are not contradictory — the conceptual layer is the cross-platform contract; the physical layer is how **`lumos-ios`** implements it.

### 4.1 Conceptual layout (cross-platform contract)

Use these names when discussing Lumos mobile architecture across iOS, Android, macOS, and in ADRs:

```
Lumos/  (conceptual)
├── App/                    # Application entry, lifecycle, root composition
├── Core/                   # Cross-cutting orchestration, routing, task envelopes
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
└── Shared/                 # UI primitives, extensions, design tokens
```

This tree remains valid for **platform-agnostic documentation**, wire contracts, and future Android/macOS repos that may choose their own physical grouping.

### 4.2 Physical layout (locked for `lumos-ios` v1)

The private iOS repo uses a **flat `App/` module tree** — no nested `Features/` container. Discipline from day one per [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md):

```
App/
├── UI/              # Screens, navigation shell, chat, settings
├── Voice/
├── Camera/          # Capture pipeline (split from Vision for v1 clarity)
├── Vision/
├── Memory/
├── Security/
├── AI/              # Conductor orchestration (conceptual Core)
├── Network/         # HTTP, demo API, relay (conceptual Services)
├── Accessibility/
└── Shared/          # Design tokens, components, shared DTOs (conceptual Models + Shared)

Resources/           # At project root — assets, localization, launch assets
```

**User decision (locked):** iOS v1 prefers this flat `App/` layout over a `Core/` + `Features/*` split. Orchestration lives in **AI**; infrastructure in **Network**; screens in **UI**.

### 4.3 Conceptual → physical mapping

| Conceptual (this spec) | Physical (`lumos-ios` under `App/`) | Notes |
|------------------------|-------------------------------------|-------|
| **App** (entry) | `@main` target + root composition in **UI** | Thin wiring only |
| **Core** (orchestration) | **AI** | Task envelopes, routing, approval state machine — UI-agnostic |
| **Features/Chat** | **UI** | Assistant thread, chat surfaces |
| **Features/Voice** | **Voice** | Speech input, transcription preview |
| **Features/Vision** | **Vision** + **Camera** | Camera = capture; Vision = analysis |
| **Features/Memory** | **Memory** | User context, tasks, local/demo store |
| **Features/Settings** | **UI** (flows) + **Shared** (tokens) | Settings screens in UI; disclosure copy tokens in Shared |
| **Features/Security** | **Security** | Lock, approval inbox, trust indicators |
| **Services** | **Network** | HTTP clients, hosted demo API, relay |
| **Models** | **Shared** (shared DTOs) | Module-local types stay in owning module |
| **Shared** | **Shared** | Design system, reusable components, extensions |
| **Resources** | `Resources/` (project root) | Outside `App/` |
| *(iOS-only)* | **Accessibility** | Centralized a11y policy — no conceptual equivalent required on other platforms yet |

### 4.4 Per-module responsibility (physical)

| Module | Owns | Must not own |
|--------|------|--------------|
| **UI** | SwiftUI views, navigation shell, Chat thread, Settings flows, splash presentation | Raw URLSession; conductor logic; keychain writes |
| **Voice** | Speech UI hooks, audio session, voice ViewModels | Direct Security mutations; network (use Network via AI) |
| **Camera** | AVFoundation capture, photo picker, preview | Vision analysis; network upload |
| **Vision** | Image analysis, on-device vision stubs | Camera session; general UI |
| **Memory** | Local/demo store, user context | Approval gates; global navigation |
| **Security** | Lock screen, approval inbox, trust badges | Orchestration; raw HTTP |
| **AI** | Conductor interfaces, routing, task envelopes, approval abstractions | SwiftUI views; concrete API clients |
| **Network** | HTTP clients, demo/review API, logging stubs | SwiftUI; feature navigation |
| **Accessibility** | VoiceOver helpers, Dynamic Type policy, audit utilities | Feature business logic |
| **Shared** | Design system, reusable components, shared Codable types | Feature flows; service implementations |

Full enforcement rules: [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md) §3–§6.

---

## 5. Layer rules (Conductor-aligned, locked)

Mobile architecture mirrors the **Lumos Orkestratör / Konduktör** vision ([`lumos-2040-vision-draft.md`](./lumos-2040-vision-draft.md) — M0): coordination, not feature silos talking past each other.

### 5.1 Dependency direction (physical modules)

```
@main
 ↓
UI, Voice, Camera, Vision, Memory, Security
 ↓              ↓
AI (conductor) ← Network (infrastructure)
 ↓
Shared, Resources
Accessibility → importable by any module; must not import feature modules
```

| Rule | Detail |
|------|--------|
| **No horizontal imports** | `Voice` does not import `Security` directly. Cross-module needs go through **AI** or **Network** facades |
| **Feature modules → AI / Network** | Features depend on protocols defined in **AI** or **Shared**; concrete HTTP in **Network** |
| **AI is UI-agnostic** | Orchestration contracts, not SwiftUI |
| **App entry wires everything** | Composition root registers services and injects into feature entry points |
| **Fail-closed** | Missing auth, missing relay token, or review/demo misconfiguration → stop with user-visible state, not silent fallback |

### 5.2 Conductor mapping (M0 — conceptual)

| Conductor concept | iOS module (physical) | Conceptual layer |
|-------------------|----------------------|------------------|
| Task envelope | **AI** | Core |
| Route / lane selection | **AI** | Core |
| Tool / bridge delegation | **Network** | Services |
| User gate (🔴 onay) | **Security** + **AI** approval state | Features/Security + Core |
| Audit / rationale | **Network** logging → future Karar Duvarı sync | Services |

**Agent-to-agent on device:** forbidden — same spirit as [ADR-008](../decisions/ADR-008-agent-network-boundary.md): feature modules do not delegate to each other horizontally; **AI** (conductor) mediates.

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
- **Accessibility:** VoiceOver reads «Lumos. Hayal etmen yeterli.» — use **Accessibility** module helpers

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
| Bridge / pending JSON contract | ✓ | Consumes via Network |
| LAN relay demo | ✓ | Not in App Store v1 |
| Native UI + Review Mode | — | ✓ |
| Hosted demo API client | — | ✓ |

---

## 8. Cross-references

| Topic | Document |
|-------|----------|
| **Private repo discipline** | [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md) — folder rules, ownership, import checklist |
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
| **G1** Native iOS app | Private `lumos-ios` | Module tree, layer rules, heartbeat screen |
| **G2** Cloud auth | Backend + identity | Network layer placeholder; not M0 |
| **G3** Review Mode + Demo API | Backend + mobile | UI routing + Network contract |
| **G4** Hosted demo env | DevOps | Network base URL config |
| **G5** Review account provisioning | Ops | Out of architecture doc |
| **G6** Full-path QA | Mobile QA | After G1–G3 |

---

## 9. Multi-platform note

Long-term: **Android, iOS, macOS, Vision Pro, Web** share logic via conceptual **Core + Models + Services** contracts, not duplicated feature code. See §2 for the repo map.

| Layer | Share strategy |
|-------|----------------|
| **Core, Models** (conceptual) | Kotlin Multiplatform / Swift shared package / future Rust core — decision deferred; **interfaces first** in this spec |
| **Services** (conceptual) | Platform implementations (Keychain vs Keystore, etc.) → **Network** on iOS |
| **Features** (conceptual) | Per-platform UI and physical modules |
| **Shared** | Design tokens exported per platform |

**Principle:** Write orchestration and approval rules once (conceptual Core → iOS **AI**); UI stays native per platform. iOS V1 establishes the pattern private repos for other platforms can mirror.

---

## 10. Build phases (recommended)

| Phase | Where | Deliverable |
|-------|-------|-------------|
| **V1 lock (this doc)** | `lumos-core` | Architecture spec + repo rules locked — **no Swift in public repo** |
| **M1 — local first** | Local Xcode (no remote required yet) | `App/` module tree, design system, heartbeat screen, nav skeleton |
| **M1 — repo open** | Private `lumos-ios` | First commit: `Initial iOS project scaffold`; CI (lint/build) |
| **M2** | `lumos-ios` | Review Mode flag, hosted demo API stub |
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
| Two-level model documented | §4 — conceptual vs physical, mapping table |
| Repo rules linked | [`lumos-ios-repo-rules.md`](./lumos-ios-repo-rules.md) |
| Layer rules enforceable | Review checklist in repo rules passes for first feature PR |
| First screen spec unambiguous | Design can implement without guessing — §6 |
| v1 boundary linked | §3.1 / §7 ↔ app-store-review-prep §5 |
| Repo placement + timing clear | §2 — local-first, private `lumos-ios` when ready |
| Xcode reference pinned | §13 — 26.6 / 17F113 |

---

## 13. Xcode reference (locked)

| Field | Value |
|-------|--------|
| **Xcode version** | **26.6** |
| **Build** | **17F113** |
| **Role** | Canonical dev reference for local skeleton and `lumos-ios` CI — team builds should match unless an ADR revises |

---

## 14. Next session roadmap (document only — not implement now)

After this architecture lock, the next implementation sessions stack in order:

| # | Session focus | Module touchpoints | Outcome |
|---|---------------|-------------------|---------|
| **1** | **Lumos Design System** | **Shared** (+ **Accessibility** for contrast/type policy) | Colors, typography, spacing, icon logic — tokens usable by all modules |
| **2** | **First launch / Splash** | **UI** + `Resources/` | Black screen, centered logo, «Hayal etmen yeterli.» — §6 spec |
| **3** | **Main navigation skeleton** | **UI** | Tab or slot layout reserving Chat, Voice, Camera, Memory module entry points — empty placeholders OK |

**After these three:** feature work stacks on the existing architecture — no structural rewrites.

---

## 15. Open questions (minimal)

Only unresolved items — not architecture decisions:

| Question | Notes |
|----------|-------|
| **Exact logo asset** | Vector source file / export spec for `Resources/` (brand asset TBD) |

---

*Son güncelleme: 2026-07-05 — Hello World era ended; Xcode 26.6 locked; App/ flat modules; two-level conceptual/physical model; next-session roadmap §14.*
