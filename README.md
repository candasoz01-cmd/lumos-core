# Lumos

**Lumos** is the primary product focus. It is a human-centered artificial intelligence **control and assistant layer**: it helps people understand, steer, and safely manage actions across devices, digital workflows, and connected systems—without replacing their judgment.

It is developed under the **We Lock AI** umbrella as an **independent** product and direction—not owned, branded, or operated by any large language model vendor as their first-party product. Learn more about the umbrella organization: **[https://welockai.com/](https://welockai.com/)**

## Principles

- **User decision** first: Lumos does not decide on behalf of the user.
- **Explicit approval** for actions that are permanent, sensitive, costly, or affect other people.
- **Risk visibility** before action: context and consequences should be easier to see, not hidden.
- **Data awareness**: clarity about what is used, where it flows, and how it is handled; privacy as a baseline, not a paid add-on.
- Identity, consent, and authority boundaries stay explicit.
- Outputs align with the user’s intent and choice; the aim is useful support, not dependency.

Where AI-assisted reasoning is useful, Lumos may use **external model services when configured**, in a straightforward, replaceable way—without centering the product on a single vendor or overstating any provider’s role.

## What is Lumos?

Lumos helps users interact with devices, digital actions, home automation, vehicles, applications, and connected systems through a clearer and safer control layer.

The goal is not to hide complexity, but to make complex actions easier to understand, review, and approve.

In many areas, the user may express what they want through voice. Lumos can then break that intent into safer, clearer, and more controlled steps.

Final approval remains with the user for actions that are permanent, sensitive, costly, or affect other people.

## Current status

Lumos is in **early active development**. Public-facing text, interface structure, and core orchestration foundations are being shaped before deeper functional implementation.

The current version includes:

- A public landing page foundation
- A static panel structure
- Product-language module definitions
- Core principles for user control, privacy, identity, consent, and safety
- Early backend foundations for memory, state, and orchestration

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

## Philosophy

Lumos is built around a simple idea:

AI should not become an invisible authority between humans and their own decisions.

It should help users see what is happening, understand possible risks, and move forward with clearer control.

## Why Lumos?

Lumos is aimed at a practical problem: keeping identity, consent, and intelligent systems understandable and steerable, with the user’s judgment in the loop rather than replaced.

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

### Kando (optional dev bridge)

From the author’s perspective, **Kando** is **early-stage** helper tooling: it wires the panel toward task, file, and chat targets during local development and experiments. It is not described here as finished product infrastructure—more as a practical starting point that may evolve. Security and behavior details: `scripts/README_kando_bridge_server.md`.

### Yerel köprü (panel görev / dosya / sohbet hedefi)

Panel varsayılanları uzak bir örnek adrese işaret edebilir; yerel deneme için köprü:

```bash
./scripts/bridge_start.sh
```

Ayrıntı ve güvenlik: `scripts/README_kando_bridge_server.md`.

## Deploy (tek yol: Vercel — statik UI)

Üretim arayüzü **Astro** ile `ui/` altında derlenir; çıktı `ui/dist/`. Önerilen yayın:

1. [Vercel](https://vercel.com) üzerinde yeni proje: **Root Directory** = `ui` (monorepo kökünde bağladıysanız), veya kökten bağlayıp bu repodaki `vercel.json` ile `outputDirectory: "ui/dist"` kullanın.
2. Build: `npm run build` (Vercel’de `ui` kökünde varsayılan `astro build` yeterli; kökten derleme için `vercel.json` içindeki `buildCommand` kullanılır).
3. Panelin sohbet / görev / dosya köprüsü için ortam değişkenleri: `PUBLIC_LUMOS_CHAT_URL`, `PUBLIC_LUMOS_PANEL_UPLOAD_URL`, `PUBLIC_KANDO_TOKEN`, isteğe bağlı `PUBLIC_LUMOS_PANEL_HEALTH_URL`. Yerel köprü yalnızca loopback kabul eder; uzak bir köprü ayrı barındırma ve güvenlik politikası gerektirir (ayrıntı: `scripts/README_kando_bridge_server.md`).

`render.yaml` bu repoda yok; eski “Render-only” talimatları kaldırıldıysa yerine bu bölüm geçerlidir. Sohbet için örnek uzak adres (`panel.astro` varsayılanı) ayrı bir dağıtımdır — token ve URL’leri kendi ortamınıza göre ayarlayın.

## Açık kaynak ve resmi kullanım sınırı

Lumos’u, geleceği kuracak gençlere ve teknolojiyi insan yararına kullanmak isteyen herkese bir başlangıç hediyesi olarak görüyoruz. Ancak We Lock AI çatısı altındaki Lumos ürün kimliği, görsel marka unsurları, resmi servisler, API erişimleri ve kullanıcı verileri kontrollü izin yapısıyla korunur.

Açık kaynak kod, resmi Lumos hizmetlerini temsil etme, We Lock AI markasını kullanma, üretim API’lerine erişme veya kullanıcı verilerine ulaşma yetkisi anlamına gelmez. Resmi entegrasyonlar açık izin, güvenli kimlik doğrulama ve tanımlı kullanım sınırları içinde çalışır.

## License

License information will be added later.
