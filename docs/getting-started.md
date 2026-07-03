# Getting started with Lumos Core

**Canonical onboarding** for new developers. For product principles and deploy details, see [README](../README.md).

| Field | Value |
|-------|--------|
| Status | Docs only — no code |
| Last updated | 2026-06-26 |

---

## Choose your path

| Path | Time | Terminals | What works |
|------|------|-----------|------------|
| **Katman A — UI only** | ~5 min | 1 | Landing + panel shell in **Limited mode** |
| **Katman B — Full local** | 10+ min | 3–4 | Bridge, tasks, chat proxy, connected panel |

**Limited mode without a bridge is normal.** Chat and bridge-backed tasks require Katman B.

---

## Katman A — First 5 minutes (UI only)

**Prerequisites:** Node.js >= 22.12.0

```bash
git clone https://github.com/candasoz01-cmd/lumos-core
cd lumos-core/ui
npm install
npm run dev
```

| URL | What you see |
|-----|----------------|
| http://127.0.0.1:4321/ | Public landing (welockai.com deploy target) |
| http://127.0.0.1:4321/panel | Panel shell — **Sınırlı mod** badge, no bridge required |

---

## Katman B — Full local dev

**Prerequisites:** Node >= 22.12, Python 3.10+ (bridge/tasks), [Vercel CLI](https://vercel.com/docs/cli) (`vercel dev` for `/api/bridge/*` proxy)

**Canonical runbook:** [Local bridge runbook](local-kando-dev-runbook.md)

**Landing walkthrough:** [welockai.com/#kurulum](https://welockai.com/#kurulum) (8 steps — same flow when running UI locally)

### Quick sequence

1. `cp ui/.env.example ui/.env.local` — set `PUBLIC_*` URLs and `PUBLIC_KANDO_TOKEN` for local bridge
2. `export KANDO_BRIDGE_SECRET='test123'` → `./scripts/bridge_start.sh` (port **8765**)
3. `python3 panel/scripts/panel_tasks_server.py` (port **8766**)
4. At repo root: `export BRIDGE_UPSTREAM_URL='http://127.0.0.1:8765'` + same secret + `LUMOS_BRIDGE_PROXY_AUTH_TOKEN` → **`vercel dev`**
5. Open http://127.0.0.1:3000/panel

For chat: Python venv + `OPENAI_API_KEY` — see runbook.

---

## Port and dev-server reference

| Process | Default port | Command / notes |
|---------|--------------|-----------------|
| Astro UI (`npm run dev`) | **4321** | `cd ui && npm run dev` — landing + panel; **no** `/api/bridge` proxy |
| Vercel dev (`vercel dev`) | **3000** | Repo root — serves Astro + **`/api/bridge/*`** serverless proxy |
| Local bridge | **8765** | `./scripts/bridge_start.sh`; override via `KANDO_BRIDGE_PORT` |
| Panel task server | **8766** | `python3 panel/scripts/panel_tasks_server.py` |

Use **`127.0.0.1`** in URLs (not `localhost`) to avoid IPv6 drift on macOS.

### `npm run dev` vs `vercel dev`

| | `cd ui && npm run dev` | `vercel dev` (repo root) |
|--|------------------------|--------------------------|
| Port | 4321 | 3000 |
| Panel URL | `/panel` on :4321 | `/panel` on :3000 |
| Task proxy `/api/bridge/task` | Not available (503 / missing) | Works when `BRIDGE_UPSTREAM_URL` + bridge secret + proxy auth are set |
| Best for | UI-only exploration (Katman A) | Full panel + bridge smoke (Katman B) |

---

## `ui/` vs `panel/` — don't mix them up

| Directory | Role |
|-----------|------|
| **`ui/`** | Primary web surface — Astro landing + `/panel`; Vercel deploy target for welockai.com |
| **`panel/`** | **Scripts only** — `panel_tasks_server.py`, legacy static assets; not the main panel UI |
| **`archive/panel/`** | Legacy — do not use for new work |

Full repo layout: [`docs/project-map.md`](project-map.md)

---

## Limited vs full panel mode

| Mode | When | UX |
|------|------|-----|
| **Limited (Sınırlı mod)** | No bridge / no env — Katman A | Panel shell loads; chat/tasks show "not configured" — **expected** |
| **Full / connected** | Bridge + env + `vercel dev` — Katman B | Chat, task proxy, file flows can reach local bridge |

---

## welockai.com'da ne görünür?

**Production commit (2026-06-26):** `690009e` — Vercel Production deploy, `main` ile hizalı (#557 dahil).

| URL | Prod'da | Not |
|-----|---------|-----|
| `/` | Landing, kurulum, ürün kartları | Statik Astro; TR/EN i18n |
| `/panel` | Panel kabuğu, modül navigasyonu, ORAA kart **markup** | Kart `hidden` — yalnızca görev API'si (`127.0.0.1:8766`) erişilebilirken JS ile açılır; prod tarayıcıda bu adres yok → **kart görünmez**, kabuk görünür |
| `/integrations` | Hub + izin matrisi | Mail / Linear kartları dahil |
| `/integrations/mail` | Gmail OD-031 read-only sayfası | OAuth yok — bilgi yüzeyi |
| `/integrations/linear` | Linear OD-033 planned sayfası | OAuth yok — bilgi yüzeyi |
| `/cyber`, `/slack` | Ürün varyant sayfaları | Statik |
| `/api/bridge/*` | **503** `bridge_proxy_unconfigured` | `BRIDGE_UPSTREAM_URL` + bridge secret + proxy auth owner adımı — bkz. [vercel-bridge-proxy-setup.md](vercel-bridge-proxy-setup.md) |

**Prod'da görünür (bugünkü merge'ler):** entegrasyon hub + mail/linear sayfaları; panel ORAA resource-mode advisor kartı HTML/i18n (#555–#556); landing ve umbrella nav; sınırlı mod panel kopyası (TR/EN).

**Yalnızca yerel (Katman B):** köprü sohbeti, görev oluşturma/tamamlama, ORAA kartının canlı veriyle açılması (görev API `127.0.0.1:8766` — tunnel/bridge gerekir), dosya/terminal akışları, kuantum/AnchorUSB Python modülleri.

---

## Optional: Python CLI

```bash
make install    # venv + editable install
lumos --help    # CLI entry (see docs/project-map.md)
make test       # CI-parity pytest
```

Python is **not** required for Katman A.

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [README](../README.md) | Product overview, deploy, modules |
| [Local bridge runbook](local-kando-dev-runbook.md) | Bridge smoke, env files, diagnostics |
| [project-map.md](project-map.md) | Repo layout, entry points, naming |
| [integrations-overview.md](integrations-overview.md) | welockai.com surfaces vs OSS boundary |
| [INTERNAL_ALPHA_OPERATIONS.md](INTERNAL_ALPHA_OPERATIONS.md) | Internal Alpha ops, P1-02 checkpoints |
| [pilot-contract-template.md](analysis/pilot-contract-template.md) | Closed Pilot sözleşme şablonu (P1-03) |
| [support-channel-alpha.md](analysis/support-channel-alpha.md) | Destek kanalı + SLA şablonu (P1-04) |
| [Bridge server README](../scripts/README_kando_bridge_server.md) | Bridge API and security |

---

*Journey quick win QW-4 — replaces scattered onboarding entry points.*
