# App Store review preparation — Lumos

| Field | Value |
|-------|--------|
| **Document type** | Operational / review prep (docs only) |
| **Audience** | Apple App Review + internal release ops |
| **Status** | **Prep template** — native iOS app not in `lumos-core` yet |
| **Related** | [`MOBILE_PHASE_0_PWA.md`](MOBILE_PHASE_0_PWA.md), [`lumos-mobile-approval-mvp-plan.md`](analysis/lumos-mobile-approval-mvp-plan.md), [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md) |

---

## 1. Purpose

This document prepares **App Store Connect** materials for **Lumos Mobile** (native iOS). It is safe for the public OSS repo: **example credentials only**, no production secrets.

**Current repo reality:** `lumos-core` ships a **web panel + PWA shell** and an OSS **mobile web approval UI** (`GET /relay/mobile`). A **native iOS binary is not in this repository**; engineering must implement Review Mode in the **private mobile app repo** before submission.

---

## 2. Demo account — App Store Connect (copy-paste block)

> **REVIEW-ONLY — NOT PRODUCTION**  
> Do not reuse these values in production. Rotate after each review cycle.

```
Username / Email: review@lumos.ai
Password:         Review2026!

Account type:     Demo / App Review (pre-provisioned)
Environment:      Review Mode — hosted demo workspace (see §4)
```

**Sign-in notes for reviewers:**
- No email verification required for this account.
- No 2FA on the review account (or provide backup codes in Notes if 2FA is enabled in prod builds).
- Account is pre-seeded with sample data only; no real user PII.

---

## 3. App Store Connect — Review Notes (English, paste-ready)

```
Thank you for reviewing Lumos.

DEMO ACCOUNT (full access)
Email:    review@lumos.ai
Password: Review2026!

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

Support contact: support@welockai.com
```

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

1. **Account flag:** `is_review_account=true` on `review@lumos.ai` (server-side).
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

## 5. Pre-submission checklist

### App Store Connect
- [ ] Demo account created and tested on physical device
- [ ] Review Notes pasted (§3)
- [ ] Demo credentials in "Sign-in required" section (§2)
- [ ] Privacy Nutrition Labels match demo behavior (no real data collection in review path)
- [ ] Export compliance / encryption questionnaire completed
- [ ] Support URL and privacy policy URL live

### Engineering (native app — not in this repo yet)
- [ ] `reviewMode` bypasses Limited mode and local bridge
- [ ] Hosted demo API deployed and stable
- [ ] `review@lumos.ai` seeded; login works without extra steps
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

## 6. Gaps — what must be built (not in `lumos-core`)

| # | Gap | Owner |
|---|-----|--------|
| G1 | **Native iOS app** (SwiftUI / Capacitor wrapper) | Private mobile repo |
| G2 | **Cloud auth** (email/password or Sign in with Apple for review account) | Backend / identity service |
| G3 | **Review Mode + Demo Workspace API** | Backend + mobile |
| G4 | **Hosted demo environment** (not localhost bridge) | DevOps |
| G5 | **Review account provisioning** (`review@lumos.ai`) | Ops — **rotate `Review2026!` before each cycle** |
| G6 | **Full-path QA** on review account (no Limited mode dead ends) | Mobile QA |

**OSS repo today:** PWA + panel + LAN mobile web UI only. Treat this doc as the **submission template** until G1–G6 are done.

---

## 7. Security reminder

- Never commit real review passwords or API keys to git.
- Example credentials in this doc are **placeholders**; set actual values in App Store Connect and private ops vault only.
- After review, rotate demo password and optionally reset demo tenant data.

---

## Appendix — minimum viable Review Notes (short excerpt)

Use the full block in §3 above. Minimum viable paste:

```
Demo account (full access): review@lumos.ai / Review2026!
Pre-provisioned Demo Workspace with synthetic data only — no real PII.
Sign in → explore Dashboard, Chat, Approvals, Settings. No local PC or VPN needed.
External send/payments/device control are stubbed or labeled "Demo — not connected."
Contact: support@welockai.com
```
