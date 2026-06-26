# Lumos

Turkish: [README.tr.md](README.tr.md) · [docs/tr/](docs/tr/)

**Lumos** is the primary product focus. It is a human-centered artificial intelligence **control and assistant layer**: it helps people understand, steer, and safely manage actions across devices, digital workflows, and connected systems—without replacing their judgment.

Developed under the **We Lock AI** umbrella as an **independent** product and direction—not owned, branded, or operated by any large language model vendor as their first-party product. Learn more: **[https://welockai.com/](https://welockai.com/)**

## Principles

- **User decision first:** Lumos does not decide on behalf of the user.
- **Explicit approval** for actions that are permanent, sensitive, costly, or affect other people.
- **Risk visibility** before action: context and consequences should be easier to see, not hidden.
- **Data awareness:** clarity about what is used, where it flows, and how it is handled; privacy as a baseline, not a paid add-on.
- Identity, consent, and authority boundaries stay explicit.
- Outputs align with the user's intent and choice; the aim is useful support, not dependency.

Where AI-assisted reasoning is useful, Lumos may use **external model services when configured**, in a straightforward, replaceable way—without centering the product on a single vendor or overstating any provider's role.

## What is Lumos?

Lumos helps users interact with devices, digital actions, home automation, vehicles, applications, and connected systems through a clearer and safer control layer.

The goal is not to hide complexity, but to make complex actions easier to understand, review, and approve.

In many areas, the user may express what they want through voice. Lumos can then break that intent into safer, clearer, and more controlled steps.

Final approval remains with the user for actions that are permanent, sensitive, costly, or affect other people.

## Current Status

Lumos is in **early active development**. Public-facing text, interface structure, and core orchestration foundations are being shaped before deeper functional implementation.

The current version includes:

- A public landing page foundation
- A static panel structure
- Product-language module definitions
- Core principles for user control, privacy, identity, consent, and safety
- Early backend foundations for memory, state, and orchestration

The current panel defines visible modules and product direction without claiming unfinished active functionality.

## Open Source Status

- Lumos Core is in early active development.
- The repository is open source under the Apache-2.0 license.
- The project is not yet a stable, fully contribution-ready open source product. External contributions are reviewed on a controlled basis; CONTRIBUTING.md will be added later.
- Visual brand assets, the Lumos / We Lock AI names, official services, production API access, and user data are **not** covered by the Apache-2.0 license. See [NOTICE](NOTICE).

## Quick Start

```bash
git clone https://github.com/candasoz01-cmd/lumos-core
cd lumos-core/ui
npm install
npm run dev
```

Product summary: [`docs/PRODUCT_SUMMARY.md`](docs/PRODUCT_SUMMARY.md). Release checklist: [`docs/GITHUB_RELEASE_CHECKLIST.md`](docs/GITHUB_RELEASE_CHECKLIST.md). Internal Alpha scope: [`docs/INTERNAL_ALPHA_RELEASE_SCOPE.md`](docs/INTERNAL_ALPHA_RELEASE_SCOPE.md). Branch strategy: [`docs/repo-branches.md`](docs/repo-branches.md).

## Integrations (We Lock AI)

Official integration pages live under **[welockai.com](https://welockai.com/)** — static, charter-aligned; **no OAuth in the open-source repo**.

| Surface | URL |
|---------|-----|
| Integration hub | https://welockai.com/integrations |
| GitHub | https://welockai.com/integrations/github |
| Google (Drive, Calendar, Gmail) | https://welockai.com/integrations/google |
| Slack | https://welockai.com/slack |
| Panel | https://welockai.com/panel |
| Mac / Universal Links | https://welockai.com/connect/mac |
| Cyber | https://welockai.com/cyber |

Technical and product overview: [`docs/integrations-overview.md`](docs/integrations-overview.md). Architecture foundation: [`docs/analysis/welockai-charter-draft.md`](docs/analysis/welockai-charter-draft.md) (§5 integration matrix), [`docs/analysis/welockai-trust-model-draft.md`](docs/analysis/welockai-trust-model-draft.md). Permission canon: [`docs/memory/external-integrations-permissions.md`](docs/memory/external-integrations-permissions.md). OSS stubs: `src/integrations/`.

Live OAuth, production connectors, and enterprise policy enforcement ship in the **WeLockAI private layer** — not in this public repository.

## Release Tracks

### Open-source development build

Source code is available for local review, running, and contribution. This track is intended for local development and experimentation only.

### Official / professional release

The official Lumos release under We Lock AI—including the panel, service connections, secure API access, integrations, and user approval flows—is not published yet. Download and access terms will be announced when ready.

Paid or official service access is managed separately from open-source code, via authentication, user consent, and defined usage limits.

## Modules

### Work Modules

- Chat
- Tasks
- Voice
- Media
- Social
- Mail
- Files

### Core Modules

- Publishing
- Artificial Intelligence
- Quantum *(research / placeholder — not active production; [Quantum Readiness](docs/decisions/ADR-013-lumos-quantum-security-readiness.md) local read-only scanner — Faz-2 partial; CLI: `lumos quantum-readiness`; see [ADR-001](docs/decisions/ADR-001-lumos-quantum-modules.md))*
- Integration
- Identity
- Security
- World
- Settings

## Philosophy

AI should not become an invisible authority between humans and their own decisions.

It should help users see what is happening, understand possible risks, and move forward with clearer control.

## Why Lumos?

Lumos is aimed at a practical problem: keeping identity, consent, and intelligent systems understandable and steerable, with the user's judgment in the loop rather than replaced.

## Development Focus

Current focus areas:

- Product language
- Panel structure
- User-control principles
- Landing page clarity
- Public presentation
- GitHub and LinkedIn readiness
- Safe orchestration foundations

## Technical Foundations

The system includes early working foundations for:

- Contextual memory handling
- State persistence
- Modular backend orchestration
- Feed and interaction infrastructure
- Panel and control systems
- Experimental workflow coordination

## Architecture Overview

```
User
↓
Lumos Gateway Layer
↓
Context Engine
↓
Memory / State Layer
↓
Workflow Orchestrator
↓
Modules / UI / Feed / Automation / External Systems
```

## Developer Setup

Lumos is currently available as **source code** for development and review. A packaged end-user installer is **not** available yet.

### Prerequisites

- **Node.js** >= 22.12.0 (see `ui/package.json` `engines`)

### Web UI

```bash
cd ui
npm install
npm run dev
```

The default dev URL is typically http://localhost:4321 (Astro's default unless overridden).

### Production UI build (from repo root)

```bash
npm run build
```

Output is written to `ui/dist/`.

### Backend API (optional)

```bash
cd backend && npm install && npm run dev
```

### Kando bridge (optional dev bridge)

**Kando** is early-stage helper tooling that wires the panel toward task, file, and chat targets during local development and experiments. It is not finished product infrastructure—more a practical starting point that may evolve. Security and behavior details: `scripts/README_kando_bridge_server.md`.

To start the local bridge:

```bash
./scripts/bridge_start.sh
```

See `scripts/README_kando_bridge_server.md` for details and security notes.

## Deploy

Production setup has **two separate layers**: the static panel (UI) and the optional chat / task / file bridge (backend). These do not need to run on the same platform.

### UI — Vercel (static Astro)

The production UI is built with Astro under `ui/`; output goes to `ui/dist/`.

1. Create a new project on [Vercel](https://vercel.com). Set **Root Directory** to `ui`, or connect from the repo root and use the `vercel.json` in this repo (`outputDirectory: "ui/dist"`).
2. Build command: `npm run build` (in the `ui` root, `astro build` is the default; building from the repo root uses the `buildCommand` in `vercel.json`).
3. Only the **static UI** is published on Vercel; the bridge server does not run there.

### Chat / bridge — separate service (e.g. Render)

The **Kando bridge** (or equivalent backend) for the panel's chat, task, and file targets must be hosted **separately** from the UI—for example on [Render](https://render.com), Railway, Fly.io, or your own VPS. In local development `./scripts/bridge_start.sh` accepts only loopback connections; a remote bridge requires a separate security policy and hosting (see `scripts/README_kando_bridge_server.md`).

Provide bridge addresses to the UI via Vercel (or other static host) environment variables; run the bridge process on that service. The example remote addresses in `panel.astro` are references only—use your own URLs and token policy.

**Task bridge proxy (Phase 1):** Panel `POST /task` calls go to same-origin `/api/bridge/task`. Configure **server-side** `BRIDGE_UPSTREAM_URL` (e.g. `http://127.0.0.1:8765`) and `KANDO_BRIDGE_SECRET` on Vercel or `vercel dev`—not `PUBLIC_*`. See [docs/local-kando-dev-runbook.md](docs/local-kando-dev-runbook.md).

### Environment variables (`PUBLIC_*`)

In Astro, the `PUBLIC_` prefix means the value is **embedded into the client (browser)**. Typical examples for production UI:

- `PUBLIC_LUMOS_CHAT_URL`
- `PUBLIC_LUMOS_PANEL_UPLOAD_URL`
- `PUBLIC_KANDO_TOKEN` (chat / upload / controlled only in Phase 1; task uses server-side proxy)
- Optional: `PUBLIC_LUMOS_PANEL_HEALTH_URL`

**Security warning:** Do **not** put real secret keys, production tokens, or long-lived secrets into `PUBLIC_KANDO_TOKEN`, `PUBLIC_LUMOS_PANEL_TOKEN_HINT`, or any other `PUBLIC_*` variable. These values are visible in the build output and readable from the browser. Use temporary, low-risk values for local experimentation; in production, protect the bridge with server-side authentication, short-lived tokens, and network restrictions. Sensitive secrets must only be kept in **server-side** environment variables (on the bridge / backend host).

## Open Source and Official Use Boundary

The open-source code in this repository does **not** grant the right to represent official Lumos services, use the We Lock AI brand, access production APIs, or reach user data from official services. Official integrations operate under explicit permission, secure authentication, and defined usage limits.

The Lumos and We Lock AI **names**, **logos**, and other **brand and visual identity**; official hosted **services**; production **API access**; and **user data** from official services are not covered by the Apache-2.0 license and are not granted for reuse under this repository. See [NOTICE](NOTICE).

## License

**Source code** in this repository is licensed under the [Apache License, Version 2.0](LICENSE). See also [NOTICE](NOTICE).

**Not covered by this license:** The Lumos and We Lock AI names, logos, and other brand and visual identity; official Lumos / We Lock AI hosted services; production API access; and user data from official services are not granted for reuse under this repository license.

Cloning, building, or self-hosting this open-source code does **not** grant the right to use official Lumos or We Lock AI branding, to access official production APIs, or to use user data from official services. Official integrations and services are governed separately, with explicit user consent, secure authentication, and defined usage limits.
