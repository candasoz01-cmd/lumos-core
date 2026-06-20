# Platform connector'ları / çalışma araçları — onaylı karar (OD-033)

> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md), [`calendar-contacts-decision.md`](./calendar-contacts-decision.md), [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md), [`computer-use-permission-gate-decision.md`](./computer-use-permission-gate-decision.md), [`vault-secret-token-decision.md`](./vault-secret-token-decision.md), [`tools-technology-watchlist.md`](./tools-technology-watchlist.md), [`product-rules.md`](./product-rules.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

**Kaynak OD:** OD-033 (`external-integrations-permissions.md` — Platform connector'ları / çalışma araçları)

---

## Kapsam sınırı (firm)

| Dahil (OD-033) | Hariç — ayrı karar |
|----------------|---------------------|
| **GitHub** — repo, issue, PR, yorum bağlamı | **Takvim + Kişiler** → [`calendar-contacts-decision.md`](./calendar-contacts-decision.md) (OD-032) |
| **Slack** — kanal, mesaj, bildirim bağlamı | **İletişim kanalları** (mail, Telegram, WhatsApp, SMS, sosyal DM) → [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) (OD-031) |
| **Google Drive** — dosya okuma, referans, paylaşım sınırları | **Ticari domain / ödeme** → OD-039–OD-042, [`commercial-domain-payments.md`](./commercial-domain-payments.md) |
| **Linear** — issue, proje, durum senkronu | **OpenAI Agents / Realtime / Codex Plugins** → OD-034, OD-035 (ayrı değerlendirme) |
| **Notion** — sayfa, veritabanı, görev referansı | Takvim, kişi, mail veya ticari işlem bu belgede **birleştirilmez** |
| **Asana** — görev, proje, atama bağlamı | |
| **Benzeri çalışma/ürün verimliliği araçları** — aynı ilke omurgası; listeye ekleme **ayrı OD kararı** | |

**Firm:** Çalışma araçları **değerlendirme listesi modeli** ile yönetilir; connector **otomatik eklenmez**. Her platform **ihtiyaç + etki analizi** sonrası tek tek değerlendirilir. OD-032 (takvim/kişi) ve OD-031 (iletişim kanalları) ile **tek karar dosyasında birleştirilmez**.

---

## Amaç

OD-033 kapsamında **platform connector / çalışma araçları** entegrasyonunun ürün davranış ilkesini, değerlendirme listesini, granüler izin paketlerini ve onay omurgasını netleştirmek.

Bu belge:

- GitHub, Slack, Google Drive, Linear, Notion, Asana ve benzeri araçları **aynı izin/onay omurgası** altında tanımlar.
- OD-031 (iletişim kanalları), OD-032 (takvim/kişiler), OD-041 (hibrit onay), OD-012 (Computer Use) ve `product-rules.md` ile **aynı çatıyı** paylaşır.
- **Değerlendirme listesi modelini** onaylar — watchlist ≠ entegrasyon; toplu/rastgele connector ekleme yasak.
- Entegrasyon **yöntemine kilitlenmez** — resmi API tercih edilir; yöntem ikincildir.
- Vault/credential (OD-001/002) ve public repo sınırı ile hizalanır.

**Uygulama notu:** İlke kararları onaylandı; kod, test, connector, OAuth scope seçimi, webhook/poll modeli veya onay UX **henüz başlamadı**.

---

## Onaylanan ilke vs bekleyen uygulama

| Katman | Durum | Kapsam |
|--------|--------|--------|
| **İlke kararları** | `decision-approved` | WT1–WT11; değerlendirme listesi modeli (otomatik connector yok); granüler izin omurgası (`{platform}_*`); katman 1–5 öncelik özeti; OD-031/032/039–042 kapsam ayrımı; OD-041/OD-012 hibrit onay; vault ilkesi (OD-001/002); resmi API tercih; UI kısayolu ≠ connector. |
| **Uygulama / teknik detay** | `implementation-pending` | İlk connector pilotu (öneri GitHub); OAuth scope/API versiyonu; webhook vs poll; onay UX; vault credential şeması; görev motoru çakışma algoritması; bridge/connector kodu; katman 2–4 tek tek değerlendirme. Hiçbiri uygulanmadı; bu belge uygulama izni vermez. |
| **Needs-review (açık alt detay)** | `needs-review` | GitHub App vs OAuth user token; Slack bot vs user token; Drive shared drive; Notion admin API sınırları; çoklu org/workspace UX. Katman 5 yeni araçlar listeye ayrı karar ile eklenir. |

---

## Çekirdek çerçeve

**Lumos, kullanıcının kontrollü dijital uzantısıdır.** Çalışma araçları alanında kullanıcı adına hareket edebilir; ancak yalnızca:

1. **Kullanıcının açık isteği veya tanımlı kuralı**
2. **Verilmiş izin paketi** (platform + kapsam + granüler seviye; geri alınabilir)
3. **Çekirdek güvenlik ve ürün kuralları** ([`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`product-rules.md`](./product-rules.md), OD-012, OD-041)

Lumos **kendi kendine tam platform yetkisi üstlenmez**; izin paketi ve kurallar olmadan okuma, yazma, bildirim veya dış etki yapmaz.

**Entegrasyon yöntemi ikincildir:** Bkz. [`external-integrations-permissions.md`](./external-integrations-permissions.md) §Entegrasyon felsefesi — **resmi API** (OAuth, REST, platform SDK) mümkün olduğunda tercih edilir; Computer Use, yerel bağlayıcı veya gelecekteki izinli yollar **aynı granüler izin tablosu** altında değerlendirilir.

**UI kısayolu ≠ connector:** Render / Vercel / GitHub **manuel kısayolları** ([`ui-chat-experience.md`](./ui-chat-experience.md)) yalnızca kullanıcı yönlendirmesidir; otomatik veri akışı, credential veya connector **değildir**.

---

## Firm ilkeler

| # | İlke | Durum |
|---|------|--------|
| WT1 | **Varsayılan pasif:** İzin olmadan platform okuma, yazma veya dış etki yok. | `decision-approved` |
| WT2 | **Değerlendirme listesi modeli:** Connector otomatik eklenmez; ihtiyaç + etki analizi + tek platform değerlendirmesi zorunlu. | `decision-approved` |
| WT3 | **Granüler izin paketi:** Platform ve kapsam bazlı; geri alınabilir; üst seviye alt seviyeyi otomatik kapsamaz. | `decision-approved` |
| WT4 | **Dış etkili aksiyon** (oluştur, güncelle, sil, paylaş, gönder) oturum izninden **türemez** — kural-kapsamlı grant veya işlem bazlı onay. | `decision-approved` |
| WT5 | **Kalıcı silme asla otomatik değil** — issue/PR/dosya/görev kalıcı silme kullanıcı açık komutu + tek satır uyarı. | `decision-approved` |
| WT6 | **Credential Lumos yüzeyinde değil** — vault/kasa (OD-001/002). | `decision-approved` |
| WT7 | **İçerik public repo, gereksiz log ve kalıcı bellekte değil** — minimum tutma, provenance. | `decision-approved` |
| WT8 | **Sessiz onay yok;** varsayılan-onay yok; carry-forward yok — OD-041 CA4. | `decision-approved` |
| WT9 | **Panel/görev akışı çakışma kontrolü** — Lumos iç görev motoru ile dış platform senkronu çakışmada güvenli davranış. | `decision-approved` |
| WT10 | **Kalıcı import onaysız yok** — toplu dosya/issue/görev içe aktarma açık onay gerektirir. | `decision-approved` |
| WT11 | **Takvim/kişi/mail/ticari domain bu belgede değil** — OD-032, OD-031, OD-039–042 ayrı. | `decision-approved` |

---

## Genel izin seviyeleri (platform-agnostik)

Tüm çalışma araçları connector'ları aşağıdaki **ortak omurgayı** paylaşır; platform önekleri (ör. `gh_`, `slack_`) uygulama aşamasında tanımlanır.

| Seviye | Kod (şablon) | Etki | Varsayılan | Onay modeli |
|--------|--------------|------|------------|-------------|
| **Okuma** | `{platform}_read` | Liste, arama, bağlam okuma | Kapalı | Oturum + platform/kapsam (OD-041 CA1) |
| **Bildirim** | `{platform}_notify` | Değişiklik, mention, atama bildirimi | Kapalı | Oturum + kapsam |
| **Oluşturma** | `{platform}_create` | Issue, görev, sayfa, dosya, yorum oluşturma | Kapalı | **İşlem bazlı veya kural-kapsamlı açık izin** |
| **Güncelleme** | `{platform}_update` | Durum, atama, metadata, içerik güncelleme | Kapalı | İşlem veya kural-kapsamlı izin |
| **Yorum / tepki** | `{platform}_comment` | Yorum, reaction, thread yanıtı | Kapalı | İşlem veya kural-kapsamlı izin |
| **Paylaşım** | `{platform}_share` | Dosya/link paylaşımı, erişim verme | Kapalı | **İşlem bazlı açık onay** (yüksek etki) |
| **Silme** | `{platform}_delete` | Issue/PR/dosya/görev silme (geri alınabilir katman) | Kapalı | **Yüksek risk — açık onay zorunlu** |
| **Kalıcı silme** | — | Geri dönüşsüz silme | **Asla otomatik** | Kullanıcı açık komutu + tek satır uyarı; `SECURITY_NEVER_AUTO` |

**Firm kurallar:**

1. `{platform}_read` oturumu `{platform}_create` / `{platform}_delete` **kapsamaz** — OD-041 CA6.
2. Kural-kapsamlı otomasyon yalnızca **açık opt-in kural + ilgili write grant** ile; OD-031 çakışma ilkesi (güvenli kazanır) geçerlidir.
3. Çoklu kaynak / workspace / org seçimi kullanıcıya **görünür scope** olarak sunulur.

---

## Platform notları (yüksek seviye — uygulama değil)

### GitHub

| Boyut | İzin sınırı (taslak) | Not |
|-------|----------------------|-----|
| Repo okuma | `gh_read` — belirli org/repo listesi | Public/private repo scope ayrı grant |
| Issue / PR okuma | `gh_read` alt kapsam | Provenance: repo, issue #, zaman |
| Issue / PR oluşturma | `gh_create` | Dış etki; işlem veya kural-kapsamlı onay |
| Yorum / review | `gh_comment` | PR merge **ayrı yüksek risk grant** değerlendirmesi |
| Push / branch yazma | `gh_write` | **Yüksek risk** — varsayılan kapalı; işlem onayı |
| Repo silme / force push | `gh_delete` / kritik | **Asla otomatik**; işlem bazlı açık onay |

**Mevcut repo:** UI'da GitHub **manuel kısayolu** var; otomatik connector yok. `kando_core` INTEGRATION görev tipinde `github` anahtar kelimesi tanımlı — connector değil, niyet sınıflandırması.

### Slack

| Boyut | İzin sınırı (taslak) | Not |
|-------|----------------------|-----|
| Kanal / DM okuma | `slack_read` | Workspace + kanal listesi scope |
| Bildirim / özet | `slack_notify` | OD-031 bildirim modeli ile hizalı; **Slack mesajlaşma OD-031 değil** — çalışma bağlamı bildirimi |
| Mesaj gönderme | `slack_post` | Dış etki; işlem veya kural-kapsamlı onay |
| Reaction / thread | `slack_comment` | Düşük-orta risk; grant ayrı |
| Kanal yönetimi / invite | `slack_admin` | **Yüksek risk** — varsayılan kapalı |

**Sınır:** Slack **iş yeri bildirim/özet** bağlamı OD-033; kişisel mesajlaşma kanalı otomasyonu OD-031 ile çakışırsa **daha dar kapsam + güvenli davranış** tercih edilir.

### Google Drive

| Boyut | İzin sınırı (taslak) | Not |
|-------|----------------------|-----|
| Dosya listeleme / okuma | `drive_read` | Klasör scope zorunlu |
| Referans / link | `drive_read` | Lumos özetinde provenance |
| Dosya oluşturma / yükleme | `drive_create` | Dış etki; onay |
| Güncelleme / taşıma | `drive_update` | İşlem veya kural-kapsamlı |
| Paylaşım / ACL | `drive_share` | **Yüksek risk** — işlem onayı |
| Kalıcı silme | `drive_delete` | Açık onay; asla otomatik kalıcı |

**WT10:** Toplu dosya **kalıcı import** onaysız yapılmaz.

### Linear

| Boyut | İzin sınırı (taslak) | Not |
|-------|----------------------|-----|
| Issue / proje okuma | `linear_read` | Team/project scope |
| Issue oluşturma | `linear_create` | Lumos görev akışı ile **çakışma kontrolü** (WT9) |
| Durum / atama güncelleme | `linear_update` | İşlem veya kural-kapsamlı |
| Yorum | `linear_comment` | Grant ayrı |
| Silme | `linear_delete` | Yüksek risk |

### Notion

| Boyut | İzin sınırı (taslak) | Not |
|-------|----------------------|-----|
| Sayfa / DB okuma | `notion_read` | Workspace + sayfa scope |
| Sayfa / satır oluşturma | `notion_create` | Dış etki |
| İçerik güncelleme | `notion_update` | İşlem veya kural-kapsamlı |
| Paylaşım | `notion_share` | Yüksek risk |
| Silme / arşiv | `notion_delete` | Açık onay |

### Asana

| Boyut | İzin sınırı (taslak) | Not |
|-------|----------------------|-----|
| Görev / proje okuma | `asana_read` | Workspace/project scope |
| Görev oluşturma | `asana_create` | Panel görev motoru çakışması — WT9 |
| Atama / durum | `asana_update` | İşlem veya kural-kapsamlı |
| Yorum | `asana_comment` | Grant ayrı |
| Silme | `asana_delete` | Yüksek risk |

---

## Değerlendirme listesi ve öncelik katmanları

**Model (firm):** Watchlist → somut ihtiyaç → tek platform değerlendirmesi → dar pilot → entegrasyon. [`tools-technology-watchlist.md`](./tools-technology-watchlist.md) ve [`docs/tool-watchlist.md`](../tool-watchlist.md) TW-D03 ile hizalı.

| Katman | Platformlar | Gerekçe (özet) | Connector durumu |
|--------|-------------|----------------|------------------|
| **Katman 1** | **GitHub** | Repo bağlamı doğal; UI manuel kısayol mevcut; geliştirme akışı hizası | `implementation-pending` — **ilk connector adayı** (sıra onayı uygulama paketinde) |
| **Katman 2** | **Slack**, **Google Drive** | Bildirim/özet ve dosya referansı — yüksek kullanım potansiyeli | `implementation-pending` — katman 1 sonrası tek tek |
| **Katman 3** | **Linear** | Görev/issue senkronu — Lumos görev motoru çakışma analizi gerekir | `implementation-pending` |
| **Katman 4** | **Notion**, **Asana** | Sayfa/görev araçları — benzer ihtiyaç; ayrı platform değerlendirmesi | `implementation-pending` |
| **Katman 5** | Diğer benzer araçlar (Jira, Trello, Figma, …) | Listeye ekleme **yeni OD veya indeks güncellemesi** ile | `needs-review` — otomatik listeye alınmaz |

**Firm:** Katman sırası **ilk uygulama önerisidir**; her platform yine de **tek tek** değerlendirme kriterlerini ([`tools-technology-watchlist.md`](./tools-technology-watchlist.md) §Kabul kriterleri) geçmeden implemente edilmez.

---

## Hibrit onay modeli (OD-041 / OD-012)

```
[ Oturum / görev kapsamı + platform scope ]
        →  düşük risk: {platform}_read · {platform}_notify · bağlam okuma

[ Kural-kapsamlı açık izin ]
        →  kullanıcı tanımlı kural ile sınırlı: create · update · comment
           (yalnızca kural eşleşmesinde; revoke = anında dur)

[ İşlem bazlı açık onay ]
        →  kural dışı veya yüksek risk: share · delete · admin · merge/push
           ne / nerede / hangi kaynak / etki görünür
```

| OD-041 ilkesi | Çalışma araçları karşılığı |
|---------------|----------------------------|
| CA1 — düşük riskli okuma oturum bazlı | `{platform}_read`, `{platform}_notify` |
| CA2 — dış etkili aksiyon işlem bazlı | create/update/share/delete kural dışında |
| CA4 — sessiz / carry-forward onay yok | Platform grant ve kurallar açık opt-in |
| CA6 — oturum izni ≠ dış etki | Oturum okuma ≠ issue/PR/dosya oluşturma |
| CA7 — ne/nerede/etki | Write öncesi kaynak, hedef, etki özeti zorunlu |

**OD-012:** Computer Use ile tarayıcı tabanlı GitHub/Notion vb. erişimi **aynı granüler izin tablosu** ile sınırlanır; ayrı gevşek model yok.

---

## Kural modeli — OD-031 çapraz referans

Çalışma araçları otomasyon kuralları, OD-031 **kural boyutlarını** paylaşır (kanal yerine platform/kaynak):

| Boyut | Örnek |
|-------|--------|
| **Platform / kaynak** | "Yalnızca `org/repo` GitHub issue'ları" |
| **Kişi / atama** | "Bana atanan Linear issue" |
| **Konu / etiket** | PR label `urgent`, Notion tag |
| **İçerik / bağlam** | Başlık anahtar kelimesi |
| **Görev / proje** | Lumos görev X ile ilişkili GitHub issue |
| **Önem** | Kullanıcı tanımlı öncelik |

**Çakışma:** Otomatik oluşturma vs "taslak + onay" → **taslak + onay kazanır** (OD-031 CC7).

---

## Vault / credential (OD-001 / OD-002)

| Konu | Karar | Durum |
|------|--------|--------|
| Platform OAuth token / API key | Vault/kasa katmanında; Lumos yüzeyinde **açık tutulmaz** | decision-approved (ilke) |
| Connector erişimi | Bridge üzerinden amaç bazlı, kapsam sınırlı | decision-approved (ilke); API `implementation-pending` |
| Log / chat / panel | Credential, token, ham dosya/issue gövdesi **gereksiz yazılmaz** | decision-approved |
| Scope | Hangi org, repo, workspace, kanal — kullanıcıya görünür | decision-approved (ilke); UX `implementation-pending` |

---

## Gizlilik ve public repo sınırı

| Gereksinim | Kural |
|------------|--------|
| **Public repo** | Issue/PR/dosya içeriği, credential, token, production endpoint **yazılmaz** |
| **Log** | PII ve platform içeriği operasyonel loga yazılmaz |
| **Kalıcı bellek** | Gereksiz tam issue/dosya dump'ı kalıcı state'e yazılmaz; özet/provenance minimum |
| **Provenance** | Öneri/aksiyon hangi platform, kaynak, zaman — kullanıcıya görünür |
| **Demo-safe** | Public repoda yalnızca ilke, onay modeli, placeholder |

---

## Repo gerçekliği (read-only — uygulama yok)

| Konu | Mevcut durum |
|------|--------------|
| **GitHub / Slack / Drive / Linear / Notion / Asana connector** | Yok — otomatik entegrasyon kodu yok |
| **`controlled_bridge.py`** | `mail`/`calendar` yüzeyleri bilinçli reddedilir; çalışma araçları **özel blok listesinde değil** — `STEP_TYPE_EXTERNAL` profil katmanında zaten kapalı |
| **`task_engine/profiles.py`** | `STEP_TYPE_EXTERNAL` — dış servis adımları yetki profiline göre **bloklu** |
| **UI** | GitHub (Render/Vercel ile) **manuel kısayol** — [`ui-chat-experience.md`](./ui-chat-experience.md) |
| **Watchlist** | GitHub, Slack, Drive, Linear — `takip maddesi`; TW-D03 rollout sırası OD-033 |
| **`kando_core`** | INTEGRATION görev tipinde `github`, `slack`, `notion` anahtar kelimeleri — niyet sınıflandırması, connector değil |

Bu bölüm **durum tespiti**dir; OD-033 ilke onayı otomatik implementasyon **başlatmaz**.

---

## Implementation-pending

| Konu | Durum | Not |
|------|--------|-----|
| **İlk connector seçimi** (öneri: GitHub Katman 1) | **implementation-pending** | Dar pilot + etki analizi paketi |
| OAuth scope / API versiyonu (platform başına) | **implementation-pending** | Resmi API tercih |
| Webhook vs poll vs hibrit sync | **implementation-pending** | Platform ve risk profiline göre |
| Onay UX, kural editörü (platform tetikleyicileri) | **implementation-pending** | OD-031 UX ile hizalanır |
| Vault API ve platform credential şeması | **implementation-pending** | OD-001/002 ile birlikte |
| Lumos görev motoru ↔ Linear/Asana çakışma algoritması | **implementation-pending** | WT9 |
| Bridge entegrasyonu, connector kodu | **implementation-pending** | Public repoda demo-safe |
| Katman 2–4 platformları tek tek değerlendirme | **implementation-pending** | Sıra: katman modeli öneri, her biri ayrı paket |

**Needs-review (açık alt detay):**

- GitHub App vs OAuth user token modeli
- Slack bot vs user token kapsam ayrımı
- Drive shared drive / link-only erişim
- Notion workspace admin API sınırları
- Çoklu org/workspace hesap birleştirme UX'i

---

## GitHub pilot scope (Katman 1 — public stub)

**Durum:** `decision-approved` (pilot kapsam ilkesi) / `implementation-pending` (kod).  
**Referans:** OD-033 [`work-tools-connectors-decision.md`](./work-tools-connectors-decision.md) katman 1.

| # | Pilot sınırı | Onay |
|---|--------------|------|
| G1 | **Read-only ilk adım:** `{github}_read`, `{github}_notify` | Oturum + scope grant |
| G2 | Issue/PR **oluşturma** | Kural-kapsamlı veya işlem onayı — OD-041 |
| G3 | **Delete / admin / merge** | Her zaman işlem bazlı onay |
| G4 | OAuth scope minimum prensibi | Resmi GitHub API |
| G5 | Repo/org allowlist kullanıcı tanımlı | WT granüler izin |
| G6 | Credential vault (OD-001/002) | Lumos yüzeyinde token yok |
| G7 | Public repoda issue gövdesi / token **yok** | Demo-safe stub only |

**Sıra:** Vault stub → OD-041 onay UX → G1 read pilot → G2+ (onaylı impl paketi).

---

## Bağımlılıklar

| OD / belge | İlişki | Durum |
|------------|--------|--------|
| **OD-031** | Kural modeli, granüler izin, çakışma ilkesi | decision-approved / implementation-pending |
| **OD-032** | Takvim/kişi — **kapsam dışı** | decision-approved / implementation-pending |
| **OD-041** | Hibrit onay — oturum vs işlem vs kural-kapsamlı | decision-approved / implementation-pending |
| **OD-012** | Computer Use / dış etki kapısı | decision-approved / implementation-pending |
| **OD-001 / OD-002** | Vault, token, credential bridge | decision-approved / implementation-pending |
| **OD-039–042** | Ticari domain — **kapsam dışı** | ayrı kararlar |
| **OD-034 / OD-035** | OpenAI Agents / Codex — **kapsam dışı** | needs-review |
| **OD-036** | Vault import connector sırası — çalışma araçları ile **ilişkili ama ayrı** | needs-review |
| **tools-technology-watchlist** | Değerlendirme kriterleri, watchlist | canonical |
| **product-rules** | Lumos geçidi, ne/nerede/etki | canonical |

**Sıra önerisi (firm, uygulama paketi için):** Vault (OD-001/002) → granüler izin/onay UX (OD-041) → **tek platform** değerlendirmesi (öneri GitHub) → connector pilot → sonraki katman.

---

## Yasak (onaysız veya otomatik)

| # | Aksiyon | Gerekçe |
|---|---------|---------|
| Y1 | Onaysız platform okuma, oluşturma, güncelleme, silme, paylaşım | WT1; external-integrations-permissions |
| Y2 | Oturum izni ile otomatik issue/PR/dosya/görev oluşturma (kural olmadan) | WT4; OD-041 CA6 |
| Y3 | Otomatik kalıcı silme (issue, dosya, görev) | WT5; lumos-karar-sozlesmesi |
| Y4 | Credential'ın Lumos yüzeyinde veya logda açığa çıkması | WT6; OD-001/002 |
| Y5 | Platform içeriğinin public repo veya gereksiz kalıcı belleğe yazılması | WT7 |
| Y6 | Sessiz kural, varsayılan-onaylı otomasyon, carry-forward izin | WT8; OD-041 CA4 |
| Y7 | Toplu/rastgele connector ekleme; watchlist'ten otomatik entegrasyon | WT2 |
| Y8 | Onaysız kalıcı import (dosya, issue, görev toplu aktarım) | WT10 |
| Y9 | Takvim/kişi/mail/ticari işlemi OD-033 altında birleştirme | WT11 |
| Y10 | Platform bypass, scraping, unofficial API | OD-031 CC11 ile aynı omurga |

---

## OD eşleme

| OD | Kaynak | Konu | Bu belgedeki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-033** | external-integrations-permissions.md | Platform connector'ları / çalışma araçları | Bu belgenin tamamı | **decision-approved / implementation-pending** |
| OD-031 | mail-integration-approval-decision.md | İletişim kanalları — **hariç** | §Kapsam sınırı; kural çapraz ref | decision-approved / implementation-pending |
| OD-032 | calendar-contacts-decision.md | Takvim + Kişiler — **hariç** | §Kapsam sınırı | decision-approved / implementation-pending |
| OD-041 | commercial-approval-model-decision.md | Hibrit onay | §Hibrit onay modeli | decision-approved / implementation-pending |
| OD-012 | computer-use-permission-gate-decision.md | Dış etki kapısı | §OD-012 | decision-approved / implementation-pending |
| OD-001/002 | vault-secret-token-decision.md | Vault / credential | §Vault | decision-approved / implementation-pending |

**İndeks notu:** `open-decisions-needs-review.md` OD-033 satırı bu belgeyle senkron tutulur.

---

## Sonraki adım

1. **Onay (tamamlandı — ilke):** WT1–WT11, değerlendirme listesi modeli ve granüler izin omurgası `decision-approved`.
2. **Implementation-pending:** GitHub dar pilot (Katman 1) — OAuth scope, webhook/poll, onay UX — ayrı uygulama paketi.
3. Vault (OD-001/002) netleşmeden platform credential **Lumos yüzeyine taşınmaz**.
4. Katman 2+ platformlar **sırayla tek tek** değerlendirilir; toplu rollout yok.
5. Kural editöründe OD-031 modeli **genişletilir**, yeniden icat edilmez.

**Yasak (bu aşamada):** kod, test, connector, credential, production endpoint, platform içeriğinin repoya yazılması.

---

Son güncelleme: 2026-06-20 (GitHub pilot scope — envanter ab791c14 §12 #6)
