# Entegrasyon genişleme denetimi (integrations expansion audit)

| Alan | Değer |
|------|-------|
| Tarih | 2026-06-26 |
| Kapsam | Public `lumos-core` — docs, UI yüzeyleri, OSS stub katmanı |
| Kaynak oturum | Subagent dced330a (integrations audit) |
| İlgili | [`integrations-overview.md`](../integrations-overview.md), [`lumos-approved-naming-registry.md`](./lumos-approved-naming-registry.md) |

Bu belge **demo-safe** denetim çıktısıdır. Üretim OAuth, credential veya pilot müşteri adları içermez.

---

## Özet

**Gemi durumu:** Internal Alpha'da entegrasyon **ürün yüzeyi canlı**, **OAuth/connector üretimi yok**. `welockai.com/integrations` hub'ı + GitHub/Google/Slack statik sayfaları yayında; hepsinde açıkça «OAuth burada başlatılmaz» yazıyor.

**DeepSeek / Groq / «gorror»:** Repoda **Groq, Gopher, gorror** yok (yalnızca `package-lock.json` içinde tesadüfi `OgroQ` alt dizisi). **DeepSeek** yalnızca `src/kando/kando_core.py` içinde `ToolRouter`'da `AUXILIARY` görevler için **isimlendirilmiş yönlendirme etiketi**; API adapter'ı, registry kaydı veya yürütme yolu **yok**. Stratejik LLM sağlayıcı kararı **OpenAI** (OD-012, [`computer-use-permission-gate-decision.md`](../memory/computer-use-permission-gate-decision.md)).

**«Arkadaşlar» / davet:** İki ayrı anlam var; ikisi de **kodda uygulanmamış**:

1. **Slack «çalışma arkadaşı»** — ürün konumlandırması (`ui/src/pages/slack.astro`, charter); sosyal arkadaş listesi veya Slack workspace invite akışı **yok**.
2. **Closed Pilot davetleri (≤20)** — P1-03 **şablon hazır**, **davet gönderilmedi**; operasyonel davet listesi **başlanmadı** (`launch-readiness-gap.md` G-04). Kodda `invite`/`davet`/`send_email` akışı **bulunamadı**. Closed Pilot **entegrasyon değil**, operasyon programıdır.

---

## Entegrasyon envanteri

### APPROVED (karar onaylı)

| Alan | Durum | Kanıt |
|------|--------|-------|
| GitHub, Slack, Google Drive/Calendar/Gmail izin modeli | Charter + OD-033 | [`integrations-overview.md`](../integrations-overview.md), [`work-tools-connectors-decision.md`](../memory/work-tools-connectors-decision.md) |
| Mail (Gmail) ilke | OD-031 | [`external-integrations-permissions.md`](../memory/external-integrations-permissions.md) |
| Takvim + Kişiler | OD-032 | [`calendar-contacts-decision.md`](../memory/calendar-contacts-decision.md) |
| Linear, Notion, Asana (çalışma araçları) | OD-033 katman 3–4 | [`work-tools-connectors-decision.md`](../memory/work-tools-connectors-decision.md) |
| OpenAI (stratejik sağlayıcı) | OD-012 firm | [`computer-use-permission-gate-decision.md`](../memory/computer-use-permission-gate-decision.md) |
| Vault/credential ayrımı | OD-001 | [`vault-secret-token-decision.md`](../memory/vault-secret-token-decision.md) |

### PLANNED (onaylı, uygulama bekliyor)

| Öncelik | Entegrasyon | Not |
|---------|-------------|-----|
| Katman 1 | **GitHub connector** | İlk resmi connector adayı |
| Katman 2 | Slack, Google Drive | Katman 1 sonrası |
| Katman 3 | **Linear** | Görev motoru çakışma analizi gerekir |
| Katman 4 | **Notion**, **Asana** | Ayrı platform değerlendirmesi |
| OD-031/032 | Mail read, Calendar/Contacts | Stub/decision var, ürün yok |

### STUB / KISMİ KOD (OSS)

| Bileşen | Ne var | Ne yok |
|---------|--------|--------|
| `src/integrations/registry.py` | openai, mail, web, device provider | github/slack/google connector |
| `openai_provider` | `ModelClient` → `OPENAI_API_KEY` | Multi-vendor LLM |
| `mail_provider` | Dar v1: `connection_status`, `list_unread`, `notify_check` | send/delete/archive |
| `gmail_oauth.py` | Read-only OAuth iskelet + vault | Prod OAuth client |
| `web_search_provider` | Brave (env ile) | Google/Bing tam yol |
| `device_provider` | Gate/approval şablonu | Vendor adapter (hep `not_configured`) |
| `vault/adapter.py` | Infisical env-gated PoC | Prod tenant vault |
| `packages/kando_bridge` | LAN relay, OpenAI tool loop, mobile approval | Dış SaaS connector |

### NOT STARTED (vizyon/registry dışı veya sadece docs)

- **DeepSeek, Groq** ve diğer alternatif LLM provider registry
- **Pilot davet** e-posta/Slack otomasyonu
- **WeChat** (feasibility merge; ürün kararı bekliyor)
- **Jira, Trello, Figma** (OD-033 katman 5, `needs-review`)
- **OpenAI Agents / Realtime / Codex Plugins** (OD-034/035, `needs-review`)
- **Production OAuth** (GitHub App, Slack bot, Google consent screen)

### UI / naming registry'de olanlar (2026-06-26 öncesi)

`lumos-approved-naming-registry.md` §A.3:

- `/integrations`, `/integrations/github`, `/integrations/google`, `/slack`, `/panel`, `/connect/mac`, `/cyber`

**Registry'de yoktu, kararda vardı:** Linear, Notion, Asana, ayrı `/integrations/mail` sayfası. Bu denetim sonrası **mail** ve **linear** yaprakları eklendi; Notion/Asana yalnızca watchlist'te.

---

## «Adı geçmeyen arkadaşlar» — vizyonda var, registry/UI'da eksikti

| Aday | Nerede geçiyor | Registry/UI (önce → sonra) |
|------|----------------|----------------------------|
| Linear | OD-033 katman 3, watchlist | Yok → `/integrations/linear` (planned yaprak) |
| Notion / Asana | OD-033 katman 4 | Yok (watchlist; ayrı yaprak henüz yok) |
| Mail ayrı yaprak | Hub matrisinde Gmail satırı var | Kısmi → `/integrations/mail` (OD-031 Dar v1) |
| Calendar/Contacts | Google sayfasında örtük | Ayrı OD-032 yaprak yok |
| WeChat | Feasibility analizleri | Yok |
| Render/Vercel | UI manuel kısayol (connector değil) | Entegrasyon sayfası yok |
| DeepSeek | `kando_core` router only | Yok (bilinçli — connector değil) |

**Davet:** Gerçek pilot kuruluş adları yalnızca private sözleşme/davet listesinde tutulacak (`lumos-approved-naming-registry.md` — **OWNER_ACTION**). Public repoda `ÖrnekKuruluş-A/B/C`; **gerçek davet gönderimi yapılmamış**.

---

## Owner olmadan yapılamayanlar

- GitHub/Slack/Google **production OAuth** uygulamaları ve client secret'lar
- **OPENAI_API_KEY**, **BRAVE_SEARCH_API_KEY**, **LUMOS_VAULT_*** operatör env'leri
- Closed Pilot **davet listesi, NDA, imza** (P1-03)
- Infisical/vault PoC ve multi-tenant credential bridge
- WeChat / Çin pazarı ticari ve compliance kararları
- Ödeme/PSP (OD-011, aktif kapsam dışı)

---

## Uygulanan sonraki yapraklar (bu PR)

Mevcut pattern: statik Astro sayfa + `integrations-overview.md` + OD katman sırası. Kod değişikliği minimum, docs/UI genişlemesi:

1. **Gmail / Mail read-only yaprak (OD-031)** — `/integrations/mail`; `src/integrations/mail/` stub'ı ile hizalı; send hariç Dar v1.
2. **Linear yaprak (Katman 3, docs-first)** — `/integrations/linear`; watchlist + OD-033 onaylı; connector kodu sonra.
3. **Hub güncellemesi** — entegrasyon merkezinden mail ve linear kartları.

**Bilinçli olarak bu PR'da yok:** GitHub connector pilot kodu, OAuth, Notion/Asana ayrı yaprakları, DeepSeek adapter.

---

## `integrations-overview.md` gap kapatmaları

- **LLM:** OpenAI stratejik; DeepSeek yalnızca kando router etiketi — connector değil, engine katmanı.
- **OD-033 watchlist:** Linear, Notion, Asana — planned satırları.
- **Mail:** OSS stub (`src/integrations/mail/`) referansı güçlendirildi.
- **Closed Pilot:** entegrasyon değil; operasyon programı olarak ayrıldı.

---

## Çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`integrations-overview.md`](../integrations-overview.md) | Public entegrasyon indeksi |
| [`work-tools-connectors-decision.md`](../memory/work-tools-connectors-decision.md) | OD-033 katman sırası |
| [`mail-integration-approval-decision.md`](../memory/mail-integration-approval-decision.md) | OD-031 stub |
| [`public-repo-boundary.md`](../memory/public-repo-boundary.md) | OSS vs private sınır |
| [`lumos-approved-naming-registry.md`](./lumos-approved-naming-registry.md) | §A.3 rota kaydı |

---

*Son güncelleme: 2026-06-26 — audit fiziksel dosya + mail/linear yaprakları.*
