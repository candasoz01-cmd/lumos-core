# Lumos

**Lumos** is the primary product. **We Lock AI** is the umbrella publisher ([welockai.com](https://welockai.com)).

Lumos is a human-centered AI control layer designed to help users understand, control and safely manage actions across devices, digital workflows and connected systems.
It does not replace the user’s judgment.
It makes context, risk and next steps more visible.
## What is Lumos?
Lumos helps users interact with devices, digital actions, home automation, vehicles, applications and connected systems through a clearer and safer control layer.
The goal is not to hide complexity, but to make complex actions easier to understand, review and approve.
In many areas, the user may express what they want through voice. Lumos can then break that intent into safer, clearer and more controlled steps.
Final approval remains with the user for actions that are permanent, sensitive, costly or affect other people.
## Core Principles
- User control comes first.
- Lumos does not decide on behalf of the user.
- Risk must be made visible before action.
- Privacy is a core principle, not a paid feature.
- Outputs created with Lumos belong to the user’s intent and decision.
- Identity, consent and authority boundaries must stay clear.
- Lumos is built to create space in the user’s life, not dependency.
## Current State
Lumos is in early active development.
The current version includes:
- A public landing page foundation
- A static panel structure
- Product-language module definitions
- Core principles for user control, privacy, identity, consent and safety
- Early backend foundations for memory, state and orchestration
The current panel defines visible modules and product direction without claiming unfinished active functionality.
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
- Quantum
- Integration
- Identity
- Security
- World
- Settings
## Technical Foundations
The system includes early working foundations for:
- Contextual memory handling
- State persistence
- Modular backend orchestration
- Feed and interaction infrastructure
- Panel and control systems
- Experimental workflow coordination
## Architecture Overview
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
## Philosophy
Lumos is built around a simple idea:
AI should not become an invisible authority between humans and their own decisions.
It should help users see what is happening, understand possible risks and move forward with clearer control.
## Open Letter
Lumos includes an open letter that explains the broader intention behind the project: building a more responsible relationship between humans, technology, identity, consent and intelligent systems.
## Development Focus
Current focus areas:
- Product language
- Panel structure
- User-control principles
- Landing page clarity
- Public presentation
- GitHub and LinkedIn readiness
- Safe orchestration foundations
## Status
Early active development.
Public-facing text, interface structure and core orchestration foundations are being shaped before deeper functional implementation.
## Developer setup

Lumos is currently available as **source code** for development and review. A packaged end-user installer is **not** available yet.

### Prerequisites

- **Node.js** >= 22.12.0 (see `ui/package.json` `engines`)

### Web UI

```bash
cd ui
npm install
npm run dev
```

The default dev URL is typically http://localhost:4321 (Astro’s default unless overridden).

### Production UI build (from repo root)

```bash
npm run build
```

### Backend API (optional)

```bash
cd backend && npm install && npm run dev
```

## License
License information will be added later.
