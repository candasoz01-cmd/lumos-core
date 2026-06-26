# Lumos integrations overview

| Field | Value |
|-------|-------|
| Status | **Public foundation** — product pages live; OAuth not in OSS |
| Site | [welockai.com/integrations](https://welockai.com/integrations) |
| Charter | [`docs/analysis/welockai-charter-draft.md`](analysis/welockai-charter-draft.md) §5 (integration matrix) |
| Trust model | [`docs/analysis/welockai-trust-model-draft.md`](analysis/welockai-trust-model-draft.md) |
| Naming registry | [`docs/analysis/lumos-approved-naming-registry.md`](analysis/lumos-approved-naming-registry.md) |
| Permissions | [`docs/memory/external-integrations-permissions.md`](memory/external-integrations-permissions.md) |

This document is **demo-safe** and suitable for the public `lumos-core` repository. It does not describe production credentials, OAuth client IDs, or WeLockAI private orchestration.

---

## Product surfaces (welockai.com)

| Surface | URL | Role |
|---------|-----|------|
| Integration hub | https://welockai.com/integrations | Charter-aligned permission matrix; links to all connectors |
| GitHub | https://welockai.com/integrations/github | Issue/PR/CI read context; approved write; no default delete |
| Google | https://welockai.com/integrations/google | Drive, Calendar, Gmail — read-first policy |
| Mail (Gmail) | https://welockai.com/integrations/mail | OD-031 Dar v1 — read-only inbox summary; off by default |
| Linear | https://welockai.com/integrations/linear | OD-033 Layer 3 — planned; issue sync context (no OAuth yet) |
| Slack | https://welockai.com/slack | Workplace context and controlled notifications |
| Panel | https://welockai.com/panel | Primary web workspace |
| Mac links | https://welockai.com/connect/mac | Universal Links for future Mac client |
| Cyber | https://welockai.com/cyber | Security-focused variant (early access) |

**OAuth is not started on these static pages.** Connection flows will ship under We Lock AI controlled access when ready (Internal Alpha → official release).

---

## Permission model (charter summary)

Symbols: **Read ✅** · **Write 🔒 (approval)** · **Delete 🚫 (special permission)**

| Integration | Read | Write | Delete | Notes |
|-------------|------|-------|--------|-------|
| **GitHub** | Repo metadata, issues, PRs, diff summary, CI status summary | Comments, labels, assign; merge = high-risk approval | Repo/issue/PR delete, force-push — off by default | Manual UI shortcuts exist; connector pilot Layer 1 |
| **Slack** | Policy-scoped Topic (Konu) summary, mentions | Post, react — granular grant + approval | Message/Topic delete — rare; policy + approval | Organization private area mapping; not mail channel; use announcement topic — no fixed channel names in product copy |
| **Google Drive** | File list, metadata, scoped content summary | Create/update/share link — approved | File/folder delete — special permission | No unapproved full archive |
| **Google Calendar** | Events, availability, attendee metadata | Create/move/RSVP — approved | Cancel/delete — separate grant | Calendar ↔ contacts OD-032 |
| **Gmail** | Inbox summary, thread metadata (ADR-002) | Send/draft/reply — per-action approval | Delete/archive — off by default | **Off by default**; read needs explicit grant |

**Common rule:** Read aligns with analysis/report profile. Write needs `kisitli_otonom` + general or per-action approval. Delete and irreversible external effect are treated like `SECURITY_NEVER_AUTO` — never automatic.

### Planned connectors (OD-033 watchlist)

Decision-approved; implementation pending. No automatic connector registration.

| Platform | Layer | Status |
|----------|-------|--------|
| **Linear** | 3 | Static product page live; connector after GitHub pilot |
| **Notion** | 4 | Docs/watchlist only |
| **Asana** | 4 | Docs/watchlist only |

See [`docs/memory/work-tools-connectors-decision.md`](memory/work-tools-connectors-decision.md) and [`docs/analysis/integrations-expansion-audit.md`](analysis/integrations-expansion-audit.md).

---

## LLM providers (not integration connectors)

LLM routing lives in the **engine layer**, not the integration registry.

| Provider | Role in OSS | Notes |
|----------|-------------|-------|
| **OpenAI** | Strategic provider (OD-012) | `openai_provider` + `OPENAI_API_KEY`; Computer Use gate |
| **DeepSeek** | Router label only | `ToolRouter` auxiliary task name in `kando_core.py` — **no** API adapter, registry entry, or execution path |

Alternative LLM vendors (Groq, etc.) are **not started** in the public foundation.

---

## Closed Pilot (operations — not integration)

**Closed Pilot** (≤20 invites, P1-03) is an **operations program**: contract template, invite list, NDA — not an integration surface. Invite send automation is **not implemented** in OSS; real organization names stay in private ops vault (`lumos-approved-naming-registry.md` §C.2 OWNER_ACTION). Public demo uses `ÖrnekKuruluş-A/B/C` only.

---

## OSS vs WeLockAI private

| Lumos OSS (`lumos-core`) | WeLockAI private |
|--------------------------|------------------|
| Plugin API, stub connectors (`src/integrations/`) | Production OAuth, webhook, enterprise SLA |
| Policy engine, confirmation, gateway contract | Tenant policy sets, billing limits |
| Demo-safe mail stub (`src/integrations/mail/`) — Dar v1: `connection_status`, `list_unread`, `notify_check`; OAuth skeleton in `gmail_oauth.py` | Vault, credential bridge, multi-tenant orchestration, send/delete/archive |
| Static integration pages on welockai.com | Live connection and account linking |

See [`docs/memory/public-repo-boundary.md`](memory/public-repo-boundary.md).

---

## Code references (OSS)

- Registry: `src/integrations/registry.py`
- Mail stub: `src/integrations/mail/`
- External permissions canon: `docs/memory/external-integrations-permissions.md`
- Work tools connectors: `docs/memory/work-tools-connectors-decision.md`
- ADR mail: `docs/decisions/ADR-002-mail-inbox-intelligence.md`

---

## Data flow principle

> Each tool owns its data; Lumos processes only what is necessary under user policy.

- Source systems (GitHub, Slack, Google) remain authoritative.
- Lumos stores summaries with **provenance**, not unapproved full copies.
- Audit records **what happened**, not raw user message bodies ([`lumos-audit-log-contract.md`](analysis/lumos-audit-log-contract.md)).

---

*For architectural foundation detail, see the [WeLockAI charter draft](analysis/welockai-charter-draft.md) and [trust model draft](analysis/welockai-trust-model-draft.md). This file is the public integration index for developers and product readers.*
