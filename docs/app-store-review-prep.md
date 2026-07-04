# App Store review preparation — Lumos

| Field | Value |
|-------|--------|
| **Document type** | Operational / review prep (docs only) |
| **Audience** | Apple App Review + internal release ops |
| **Status** | **Prep template** — native iOS app not in `lumos-core` yet |
| **Related** | [`MOBILE_PHASE_0_PWA.md`](MOBILE_PHASE_0_PWA.md), [`lumos-mobile-approval-mvp-plan.md`](analysis/lumos-mobile-approval-mvp-plan.md), [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md), [`app-store-product-safety-privacy.md`](app-store-product-safety-privacy.md) |

---

## 1. Purpose

This document prepares **App Store Connect** materials for **Lumos Mobile** (native iOS). It is safe for the public OSS repo: **placeholders only**, no production secrets, **no real review credentials in git**.

**Current repo reality:** `lumos-core` ships a **web panel + PWA shell** and an OSS **mobile web approval UI** (`GET /relay/mobile`). A **native iOS binary is not in this repository**; engineering must implement Review Mode in the **private mobile app repo** before submission.

**Product safety & privacy positioning:** Apple summary — [`app-store-product-safety-privacy.md`](app-store-product-safety-privacy.md); full internal policy — [`internal/lumos-product-safety-privacy-policy.md`](internal/lumos-product-safety-privacy-policy.md). Do not duplicate that content here.

---

## 2. Demo account — placeholders (repo-safe)

> **REVIEW-ONLY — NOT PRODUCTION**  
> Real credentials **never** belong in this public repository. Set actual values only in **App Store Connect** (Review Notes / Sign-in required) and in a private ops vault. **Rotate after each review cycle.**

```
Username / Email: (App Store Connect Review Account — provision before submission)
Password:         (Provided only in App Store Connect Review Notes — not in git)

Account type:     Demo / App Review (pre-provisioned)
Environment:      Review Mode — hosted demo workspace (see §4)
```

**Pre-submission requirement:** The review account **must be created and seeded on the hosted demo API before submission**. Apple reviewers cannot sign in if the account does not exist.

**Sign-in notes for reviewers:**
- No email verification required for this account.
- No 2FA on the review account (or provide backup codes in Notes if 2FA is enabled in prod builds).
- Account is pre-seeded with sample data only; no real user PII.

---

## 3. App Store Connect — Review Notes (English, paste-ready)

### 3.1 Repo template (placeholders — safe for git)

Use this block as the **structure** only. Replace bracketed tokens in App Store Connect; do not commit filled values.

```
Thank you for reviewing Lumos.

DEMO ACCOUNT (full access)
Email:    [REVIEW_EMAIL]
Password: [REVIEW_PASSWORD]

This is a dedicated App Review account with a pre-provisioned Demo Workspace.
It contains synthetic sample data only — no real user emails, contacts, files,
or production credentials.

HOW TO TEST
1. Launch the app and sign in with the credentials above.
2. Review Mode starts automatically for this account (banner: "Demo Workspace").
3. Explore the main tabs:
   - Home / Dashboard — sample tasks and status
   - Chat — demo assistant replies (no live external AI key required)
   - Approvals — tap pending items to approve or reject (stub execution only)
   - Settings — profile, privacy, and permission screens

FEATURES AVAILABLE IN REVIEW MODE
- Full navigation across all primary screens
- Create, edit, and complete sample tasks (local demo store)
- Approval flow for pending actions (no real OS or device control)
- Voice/text input preview (transcription may use on-device or demo stub)

INTENTIONALLY LIMITED / NOT CONNECTED IN REVIEW BUILD
- No real email send, social post, or payment processing
- No connection to the reviewer's personal PC or home devices
- External integrations (Gmail, Slack, etc.) show "Demo — not connected" or use stubs

BACKEND
Review builds connect to our hosted demo API (not localhost).
No VPN or local bridge setup is required.

PRIVACY
The demo account uses synthetic data only. Reviewers are not asked to import
personal data. Camera/microphone, if prompted, are optional for voice/capture
demos and can be skipped.

If anything is unclear or a screen appears empty, please contact us via
App Store Connect — we respond within 24 hours.

Support contact: [SUPPORT_EMAIL — must be active before submission]

The review account is intended solely for App Store evaluation. It contains
only synthetic demonstration data and cannot access any production user
information or customer accounts.
```

### 3.2 Ops-only (App Store Connect)

> **Do not commit this subsection with real values.** Paste filled credentials **only** into App Store Connect fields (Review Notes + Sign-in required). Store the password in a private ops vault.

| Field | Where to set | Value |
|-------|----------------|-------|
| Review email | App Store Connect → Review Notes + Sign-in required | Ops-provisioned review account email |
| Review password | App Store Connect → Review Notes only | Ops-generated; rotate after each review cycle |
| Support email | App Store Connect → App Information | `[SUPPORT_EMAIL — must be active before submission]` until ops confirms an active mailbox |

**Security:** Real credentials **never** in public git. After each App Review cycle, rotate the demo password and optionally reset the demo tenant.

---

## 4. Review Mode / Demo Workspace — engineering spec

### 4.1 Goals

| Requirement | Detail |
|-------------|--------|
| **Privacy-safe** | Zero real PII; seeded fixtures only |
| **Full feature access** | Reviewers see all primary flows — not "Limited mode" |
| **No reviewer setup** | No local bridge, tunnel, or passphrase required |
| **Deterministic** | Same seed → same tasks, approvals, chat stubs |
| **Clearly labeled** | Persistent "Demo Workspace" / "App Review" indicator |

### 4.2 Activation (implement in native app + backend)

1. **Account flag:** `is_review_account=true` on the ops-provisioned review account (server-side).
2. **Client flag:** On login, app enters `reviewMode` — ignores local bridge discovery.
3. **Hosted demo API:** Review builds use `LUMOS_REVIEW_API_BASE` (staging/demo host), not user PC.
4. **Bootstrap payload:** Server returns pre-built workspace:
   - 5–10 sample tasks (mixed statuses)
   - 2–3 pending approvals (approve/reject demo)
   - Chat thread with 3–5 canned exchanges
   - Empty or stub integrations (mail, calendar, devices)
5. **Write isolation:** Demo writes stay in review tenant; TTL reset nightly (optional).

### 4.3 Mapping to existing OSS concepts

| OSS concept | Review Mode use |
|-------------|-----------------|
| Panel **Limited mode** | **Disabled** for review account — reviewers must not hit "bridge required" dead ends |
| Panel **demo / fixture** data | **Reuse patterns** from `fixtures.js` / UI demo i18n — port to mobile API responses |
| **`sandbox_mode`** (Python core) | Analog: review tenant cannot touch production Lumos state |
| **LAN relay `/relay/mobile`** | **Not used** in App Store build — replace with hosted approval API |

### 4.4 Sample data rules

- Names: fictional (e.g. "Alex Demo", "Sample Task")
- Email/content: lorem or `[Demo]`-prefixed strings
- No real phone numbers, addresses, or API keys in responses
- Media: bundled demo assets only

### 4.5 Permissions (iOS)

| Permission | Review behavior |
|------------|-----------------|
| Camera / Photos | Optional; demo capture shows preview only, no upload to prod |
| Microphone | Optional; voice demo may use on-device stub |
| Notifications | Demo local notifications for approval prompts |
| Local Network | **Not required** in review build (no LAN relay) |

---

## 5. v1 Capability boundary (Apple services)

Apple entitlements and capabilities are **not** “enable just in case.” App Review asks: **“Why does this entitlement exist?”** Every capability in the binary must have a **visible, honest user-facing reason** and match Privacy Nutrition Labels and in-app copy. Claims ↔ implementation: [`app-store-product-safety-privacy.md`](app-store-product-safety-privacy.md).

### 5.1 This release (v1 Lumos)

| In scope for v1 | Out of scope for v1 |
|-----------------|---------------------|
| Native **iOS app** (App Store launch) | Full Lumos cloud / multi-device sync |
| Core **user flow** (navigation, tasks, settings) | Sign in with Apple (unless auth path is implemented) |
| **Secure approval** UX (explicit user consent for effective actions) | Push Notifications (unless approval alerts are live) |
| **Demo Workspace** / Review Mode ([§4](#4-review-mode--demo-workspace--engineering-spec)) | iCloud, App Groups, shared containers |
| Honest **App Store metadata** and privacy labels | Siri / Shortcuts, Background modes, Apple Intelligence hooks |
| | visionOS / macOS targets |

**v1 goal:** A **clean first release** — minimal surface area, no unused entitlements, no “future-proofing” switches left on in Xcode or App Store Connect.

### 5.2 Keep OFF unless actively used

Do **not** enable in the v1 target unless the feature is **implemented, testable, and disclosed**:

| Apple service / capability | Default for v1 | Enable only when |
|----------------------------|----------------|------------------|
| **Sign in with Apple** | OFF | Auth product path ships; review notes explain demo/real sign-in |
| **Push Notifications** | OFF | Remote/local approval alerts are live; usage strings + label updated |
| **iCloud** (CloudKit, documents, KVS) | OFF | User-visible sync feature ships; data flow documented |
| **App Groups** | OFF | Extension or widget shares data with main app |
| **Siri / App Intents / Shortcuts** | OFF | Voice or shortcut flows are implemented and reviewable |
| **Background modes** | OFF | Justified background work exists (not “maybe later”) |
| **Apple Intelligence** / Writing Tools hooks | OFF | Explicit product integration with disclosed behavior |
| **Associated Domains / Universal Links** | OFF | Hosted links are live and match entitlements |
| **HealthKit, HomeKit, etc.** | OFF | Not in Lumos product scope |

**Review build rule:** If Review Mode does not need a capability, the **App Store submission build must not declare it**.

### 5.3 Future integrated Lumos (after v1)

Add Apple services **one at a time**, each with:

1. **Real product need** (not speculative)
2. **Engineering evidence** (working path in TestFlight)
3. **Privacy label + in-app copy update** (claim matches implementation)
4. **Review Notes** paragraph explaining why the entitlement exists

**Candidate future integrations** (not v1 commitments):

- Sign in with Apple
- Push Notifications (approval / task prompts)
- iCloud or user-chosen cloud sync (align with storage-choice vision — see [`drafts/lumos-2040-vision-draft.md`](drafts/lumos-2040-vision-draft.md))
- App Groups (widgets, share extension)
- Siri / Shortcuts
- Apple Intelligence alignment (when product scope is clear)
- visionOS / macOS (platform expansion — separate review surface)

**Principle:** **Closed now ≠ never.** v1 stays narrow so App Review sees a coherent story; services open **incrementally and transparently**.

> **TR (özet):** İlk sürüm sade çıkar; Apple servisleri ihtiyaç doğunca, tek tek, şeffaf açılır.

### 5.4 Pre-submission capability check

- [ ] Xcode **Signing & Capabilities** matches §5.2 (no unused toggles)
- [ ] **Info.plist usage descriptions** exist only for permissions the app requests
- [ ] **App Privacy** details match actual data collection (no “just in case” categories)
- [ ] Review Notes do not claim integrations that are stubbed or off ([§3](#3-app-store-connect--review-notes-english-paste-ready))
- [ ] Product safety summary aligned — [`app-store-product-safety-privacy.md`](app-store-product-safety-privacy.md)

---

## 6. Pre-submission checklist

### App Store Connect
- [ ] Demo account **created on hosted demo API** and tested on physical device
- [ ] Review Notes pasted (§3) with real credentials set **in Connect only**
- [ ] Demo credentials in "Sign-in required" section (§3.2 — Connect, not git)
- [ ] Support email active and listed in App Information
- [ ] Privacy Nutrition Labels match demo behavior (no real data collection in review path)
- [ ] Export compliance / encryption questionnaire completed
- [ ] Support URL and privacy policy URL live

### Engineering (native app — not in this repo yet)
- [ ] Apple capabilities match §5 — no unused entitlements
- [ ] `reviewMode` bypasses Limited mode and local bridge
- [ ] Hosted demo API deployed and stable
- [ ] Review account seeded; login works without extra steps
- [ ] All primary tabs reachable with sample content
- [ ] Approve/reject flow works end-to-end (stub execution)
- [ ] No production secrets in review build
- [ ] "Demo Workspace" banner visible
- [ ] TestFlight internal pass before App Store submission

### Privacy / compliance
- [ ] No real user data in review tenant
- [ ] Analytics in review build: off or anonymized demo-only
- [ ] Third-party SDKs disclosed in App Privacy details

---

## 7. Gaps — what must be built (not in `lumos-core`)

| # | Gap | Owner |
|---|-----|--------|
| G1 | **Native iOS app** (SwiftUI / Capacitor wrapper) | Private mobile repo |
| G2 | **Cloud auth** (email/password or Sign in with Apple for review account) | Backend / identity service |
| G3 | **Review Mode + Demo Workspace API** | Backend + mobile |
| G4 | **Hosted demo environment** (not localhost bridge) | DevOps |
| G5 | **Review account provisioning** (ops-provisioned email; password in Connect + vault only) | Ops — **rotate after each review cycle** |
| G6 | **Full-path QA** on review account (no Limited mode dead ends) | Mobile QA |

**OSS repo today:** PWA + panel + LAN mobile web UI only. Treat this doc as the **submission template** until G1–G6 are done.

---

## 8. Security reminder

- **Never** commit real review passwords, API keys, or support credentials to git.
- Placeholders in this doc are intentional; set actual values in **App Store Connect** and private ops vault only.
- After each review cycle: rotate demo password and optionally reset demo tenant data.
- For product safety, privacy labels, and Apple risk framing, see [`app-store-product-safety-privacy.md`](app-store-product-safety-privacy.md).

---

## Appendix — minimum viable Review Notes (short excerpt)

Use the full block in §3.1 above. Minimum viable paste (fill tokens in Connect only):

```
Demo account (full access): [REVIEW_EMAIL] / [REVIEW_PASSWORD]
Pre-provisioned Demo Workspace with synthetic data only — no real PII.
Sign in → explore Dashboard, Chat, Approvals, Settings. No local PC or VPN needed.
External send/payments/device control are stubbed or labeled "Demo — not connected."
Contact: [SUPPORT_EMAIL — must be active before submission]

The review account is intended solely for App Store evaluation. It contains
only synthetic demonstration data and cannot access any production user
information or customer accounts.
```
