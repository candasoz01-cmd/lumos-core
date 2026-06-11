# Lumos v1 — Readiness Checklist

**Status:** Living document — reflects repo state as of 2026-06-11.  
**Production panel:** `https://welockai.com/panel` (Astro `ui/` build, route `/panel`).  
**Related:** [MOBILE_PHASE_0_PWA.md](MOBILE_PHASE_0_PWA.md), [PRODUCT_SUMMARY.md](PRODUCT_SUMMARY.md), [ui_panel_gorevler_bridge.md](ui_panel_gorevler_bridge.md).

---

## 1. What Lumos v1 is

Lumos v1 is the **first shippable, user-facing panel release**: a controlled, transparent assistant surface where the user always sees **Lumos** — not internal bridge or infrastructure names.

v1 is **Faz A** scope: task list, planning visibility, chat when a bridge is configured, and honest **limited mode** when it is not. It is a **web panel** (installable PWA metadata only), not a native app, not offline-first, and not full device or mail automation.

Design principles carry from the product contract:

- User approval before permanent, risky, or irreversible actions.
- Local work remains usable without a bridge.
- Bridge-dependent actions are labeled, blocked, or deferred — never silent failures.

---

## 2. What v1 includes today

### Production surface

| Item | State |
|------|--------|
| Panel route | `/panel` via Astro `ui/` build → `welockai.com/panel` |
| User-visible brand | Lumos only (no Kando/Cando in UI copy) |
| Limited-mode badge | **Sınırlı mod** when bridge is not configured (`PUBLIC_KANDO_TOKEN` empty in prod bundle) |
| PWA Phase 0 shell | `manifest.webmanifest`, theme/mobile meta on `/` and `/panel` (commit `8247a59`, on `main`) |
| Mobile chat camera | Native file input capture on camera icon (not `getUserMedia` on icon) — PR #135 merged |

### Merged panel UX (main through PR #139)

| PR | Scope |
|----|--------|
| #135 | Mobile camera capture controls in production panel |
| #136 | Calmer UX when bridge is unconfigured |
| #137 | Limited-mode status copy alignment |
| #139 | Clearer limited-mode available vs waiting actions |

### Local / panel features

| Feature | Notes |
|---------|--------|
| **Görevler [Yerel]** | Tasks persist in browser `localStorage`; badge `[Yerel]` on data-flow |
| Görev → bridge | When bridge is up, `POST /task` after local save (Phase 1 proxy); local list is not rolled back on bridge failure |
| Chat (bridge configured) | Composer, attach, native camera attach path |
| Chat (limited mode) | Empty state: *Sınırlı mod · Yerel işlemler kullanılabilir*; send blocked with explicit hint |
| Bridge proxy (Phase 1–2) | Same-origin `/api/bridge/task` and controlled media/outbox paths on `main` |
| Landing + panel | Dark theme, manifest link, `theme-color` `#38CEFF` |

### Explicitly not in production deploy

| Item | Notes |
|------|--------|
| `panel/camera.html` | Dev/smoke test page only; **not** served on `welockai.com/panel` deploy |
| Legacy `panel/` static app | Superseded for production by Astro `ui/src/pages/panel.astro` build |

---

## 3. What is intentionally limited mode / not available yet

### Limited mode (expected when bridge not configured)

Triggered when production build has **no** `PUBLIC_KANDO_TOKEN` (prod does not fall back to `test123` — PR #130).

User sees:

- Connection badge: **Sınırlı mod**
- Chat empty hint: local operations available; bridge actions waiting
- Send / bridge-dependent controls blocked with plain-language hints
- Görevler still work locally with `[Yerel]` labeling

### Not in v1 (by design)

| Area | v1 stance |
|------|-----------|
| Service worker / offline | Out of scope — see [MOBILE_PHASE_0_PWA.md](MOBILE_PHASE_0_PWA.md) |
| Android / iOS native shell | Out of scope |
| Capacitor / React Native | Out of scope |
| Full mail, calendar, device, payment automation | Panel sections may exist as placeholders; not v1 product promises |
| `panel/camera.html` on production | Dev smoke only |
| Unattended autonomous agent | Contradicts product contract |
| Production secrets in `PUBLIC_*` env | Rejected pattern; real bridge secret must stay server-side |

---

## 4. What local features work

These work **without** a configured Kando bridge (limited mode is still a valid v1 experience):

| Feature | Behavior |
|---------|----------|
| Open panel | `/panel` loads; limited badge if no token |
| Görevler | Add, list, edit meta, clear local list; `[Yerel]` badge; `localStorage` persistence |
| Görevler UI | Plan cards, local-only hints; bridge metadata shown when last bridge call succeeded |
| Settings / navigation | Panel sections reachable; non-bridge content readable |
| PWA install metadata | Manifest + icons discoverable in DevTools (no SW) |
| Mobile attach menu | Native camera/gallery pickers where OS provides them (chat icon → file input) |

**Requires bridge (not local-only):**

- Chat send to Lumos backend / Kando pipeline
- File upload to bridge outbox
- Task execution on bridge (`POST /task` acceptance and outbox updates)
- Health/capability probes that call bridge endpoints

---

## 5. What bridge-dependent features wait for later

| Feature | Waits on |
|---------|----------|
| Full chat | `PUBLIC_KANDO_TOKEN` + bridge process + chat URL (`PUBLIC_LUMOS_CHAT_URL` or default Render endpoint) |
| Bridge task execution | `kando_bridge` running; Phase 1 proxy env on UI host |
| Upload / media outbox | Bridge + Phase 2 controlled proxy paths |
| “Aktif” (non-limited) connection badge | Successful bridge health/capability probe |
| Operator full-mode on production | Server-side bridge auth strategy — not client-embedded production secrets |

Local dev reference: [local-kando-dev-runbook.md](local-kando-dev-runbook.md).

---

## 6. What must be checked before calling v1 complete

### Production smoke (`welockai.com/panel`)

- [ ] Panel loads over HTTPS; no console-breaking errors on first paint
- [ ] **Sınırlı mod** badge visible when prod env has empty `PUBLIC_KANDO_TOKEN`
- [ ] Chat composer does not send optimistically when bridge blocked; hint text is clear (PR #139 behavior)
- [ ] Görevler: add task → appears with `[Yerel]` → survives refresh
- [ ] Mobile: camera icon opens native capture, not broken `getUserMedia` on icon
- [ ] Manifest loads (`Application → Manifest` in DevTools)

### CI / repo

- [ ] `ruff check .` passes
- [ ] `pytest -q` passes
- [ ] GitHub Actions green on latest `main` commit
- [ ] No accidental commit of real `PUBLIC_KANDO_TOKEN` / bridge secrets

### Deploy boundary

- [ ] Astro `ui` build is what ships to `/panel` — not raw `panel/camera.html`
- [ ] PWA shell present (`8247a59` ancestor of release commit)

### Optional operator path (full mode, not required for public limited v1)

- [ ] Local smoke: `scripts/kando_bridge_server.py` or `python -m kando_bridge` + `ui` dev with matching token
- [ ] Task appears in `.lumos/outbox` after bridge-connected görev add

---

## 7. Smallest remaining PR list (priority order)

No open PRs at checklist time; remaining work is **verification and ops**, not large feature branches.

| Priority | Item | Type | Notes |
|----------|------|------|-------|
| 1 | **Prod limited-mode smoke sign-off** | Ops / checklist | Confirm welockai.com/panel matches §6; document date + commit hash |
| 2 | **CI green on release commit** | Verify | Required by project discipline — local pass ≠ done |
| 3 | **Operator bridge runbook link in README** | Docs (tiny) | Point operators to `local-kando-dev-runbook.md` — only if public doc gap found |
| 4 | **PWA `start_url` → `/panel` review** | Optional UX PR | Manifest currently `start_url: "/"`; change only if product wants install → panel |
| 5 | **Service worker / offline** | **Post-v1** | Explicit new phase + approval per MOBILE_PHASE_0_PWA |

**Already merged for v1 panel (no further PR required unless regression):**

- #135 camera, #136/#137 limited UX, #139 action clarity, PWA `8247a59`, bridge proxy #131–#133, prod token fallback fix #130.

---

## 8. Clear “v1 done” definition

**Lumos v1 is done when all of the following are true:**

1. **Shipped surface:** `welockai.com/panel` serves the current Astro panel build from `main`.
2. **Limited mode is correct:** With production env (no client bridge token), users see **Sınırlı mod**, can use **Görevler [Yerel]**, and bridge-dependent actions show waiting/blocked messaging — not crashes or fake success.
3. **Mobile attach works:** Chat camera icon uses native capture input on touch-primary devices (PR #135 behavior).
4. **PWA Phase 0:** Manifest + head metadata present; **no** service worker claimed or shipped.
5. **Scope honesty:** No marketing of offline, native app, or full automation beyond Faz A.
6. **Quality gate:** Latest `main` passes `ruff check .`, `pytest -q`, and CI.
7. **Documented:** This checklist §6 items checked and signed off with commit hash (e.g. `ec02026` or later).

**v1 is not done if:**

- CI is red on the release commit.
- Limited mode shows “active” bridge or sends chat optimistically without a bridge.
- Production deploy serves `panel/camera.html` as the main panel.
- Real bridge secrets are embedded in `PUBLIC_*` build variables.

---

## Revision log

| Date | Commit / PR | Change |
|------|-------------|--------|
| 2026-06-11 | (this doc) | Initial v1 readiness checklist |
| 2026-06-11 | `ec02026` / PR #139 | Limited-mode action clarity on `main` |
| 2026-06-11 | `8247a59` | PWA Phase 0 shell on `main` |
