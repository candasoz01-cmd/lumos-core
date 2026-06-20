# Açık kararlar ve needs-review indeksi

## Amaç

`docs/memory/` altındaki tüm canonical kayıtlardan **needs-review**, **queued** ve **incelenecek** maddelerin tek bakışta görülebilmesi için konsolide indeks. Detay, gerekçe ve bağlam **kaynak dosyalarda** kalır; bu dosya yalnızca karar kuyruğu ve öncelik haritasıdır.

---

## Kullanım kuralı

1. **Kaynak dosyalar canonical'dır.** Bu indeks özet ve yönlendirme amaçlıdır; çelişki durumunda kaynak dosya + `docs/lumos-karar-sozlesmesi.md` esas alınır.
2. **Güncelleme akışı:** Önce ilgili `docs/memory/*.md` dosyasında madde durumu güncellenir; ardından bu indeks senkronize edilir.
3. **Yeni madde:** Kaynak dosyaya eklenir → bu indekse yeni `OD-###` satırı eklenir.
4. **Kapanan madde:** Durum `superseded` veya kaynakta `migrated`/kaldırıldı olarak işaretlenir; indekste durum güncellenir (satır silinmez, arşiv notu bırakılır).
5. **Çelişki:** Kaynaklar arası çelişki bu indekste çözülmez; `Not` alanında çapraz referans ve `needs-review` işareti korunur.
6. **Gizlilik:** Secret, PII, credential veya production URL bu indekse yazılmaz.

---

## Kritik açık kararlar

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-001 | security-architecture.md | Lumos Vault uygulaması | Secret'lar hangi vault/katman modelinde tutulacak; Lumos yüzeyinden nasıl ayrılacak? | high | decision-approved / implementation-pending | Karar: [`vault-secret-token-decision.md`](vault-secret-token-decision.md) — Lumos secret taşımaz; vault/kasa ayrı güvenli katman; Lumos yetkili geçit/orkestratör. **Bekleyen:** somut vault ürünü/teknolojisi, depolama ve dağıtım modeli. |
| OD-002 | security-architecture.md | Token / vault entegrasyonu | Token ve credential yönetimi vault + bridge ile nasıl birleşecek? | high | decision-approved / implementation-pending | Karar: [`vault-secret-token-decision.md`](vault-secret-token-decision.md) — token/credential Lumos yüzeyinde açık tutulmaz; bridge kontrollü geçit. **Bekleyen:** token formatı, credential şeması, bridge + kimlik katmanı entegrasyon akışı. |
| OD-003 | data-vault-user-data.md | Vault amaç bazlı erişim | Vault Lumos'a hangi kapsamda, hangi amaç kodlarıyla erişim verecek? | high | decision-approved / implementation-pending | Karar: [`vault-secret-token-decision.md`](vault-secret-token-decision.md) — erişim sınırlı, amaçlı, onaylı ve görünür. **Bekleyen:** amaç kodu listesi, vault-Lumos API sözleşmesi, izin profili eşlemesi. |
| OD-004 | data-vault-user-data.md | Risk dağılımı / segmentasyon | Ele geçirmede tüm sırlar tek yerde açığa çıkmaması için şifreleme ve segmentasyon modeli ne? | high | decision-approved / implementation-pending | Karar: [`vault-secret-token-decision.md`](vault-secret-token-decision.md) — tek bileşen ele geçirildiğinde tüm sırlar açığa çıkmamalı. **Bekleyen:** somut segmentasyon modeli, connector izolasyonu, vault içi şifreleme yapısı. |
| OD-005 | data-vault-user-data.md | Şifreleme ve anahtar yönetimi | Vault içi şifreleme ve anahtar döngüsü nasıl tanımlanacak? | high | decision-approved / implementation-pending | Karar: [`vault-secret-token-decision.md`](vault-secret-token-decision.md) — şifreleme ve anahtar yönetimi gerekli; anahtar Lumos yüzeyinde açık tutulmaz. **Bekleyen:** algoritma, KDF, döngü politikası, HSM/secure enclave yolu. |
| OD-006 | internal-agent-layers.md | Bando katman varlığı | Bando ayrı katman olarak kalacak mı; görev ve yetki sınırları net mi? | high | decision-approved / implementation-pending | Karar: [`internal-communication-bando-decision.md`](internal-communication-bando-decision.md) — Bando yalnızca güvenlik/gözlem/anomali için ayrı katman; sıradan görev ajanı değil; yürütme yok; kullanıcıya görünmez; dış kaynaktan doğrudan komut/veri/dosya kabul etmez. **Bekleyen:** dağıtım modeli, edge-case senaryoları. |
| OD-007 | internal-agent-layers.md | İç iletişim protokolü | Lumos→iç katman imzalama/şifreleme protokolü ve anahtar döngüsü ne? | high | decision-approved / implementation-pending | Karar: [`internal-communication-bando-decision.md`](internal-communication-bando-decision.md) — Lumos→iç katman iletişimi doğrulanmalı; imzalama ve/veya şifreleme tercih edilir. **Bekleyen:** protokol, mesaj formatı, anahtar döngüsü, vault entegrasyonu — public repoda tanımlanmaz; private/gizli uygulama paketini bekler. |
| OD-008 | project-workflow.md | Continuous progress vs tek-adım | `docs/workflow-rules.md` continuous progress ile `.cursor/rules/tek-adim-ilerleme.mdc` hangisi öncelikli? | high | decision-approved | Karar: [`workflow-decision-alignment.md`](workflow-decision-alignment.md); tek hedef / tek adım continuous progress'ten önceliklidir. Birincil workflow canonical: `docs/memory/project-workflow.md`. |
| OD-009 | project-workflow.md | Agent-first canonical kaynak | Agent-first execution kuralı tek canonical yerde mi tutulacak? | high | decision-approved | Karar: [`workflow-decision-alignment.md`](workflow-decision-alignment.md); agent-first tercih edilen yürütme yöntemidir ama kapsam genişletmez. Canonical kaynak: `docs/memory/project-workflow.md`; `.cursor/rules/**` operasyonel katmandır. |
| OD-010 | project-workflow.md | CI tamamlanma kriteri | CI yeşil olmadan tamamlandı sayma kuralı workflow belgeleriyle tam hizalı mı? | high | decision-approved / implementation-pending | Karar: [`workflow-decision-alignment.md`](workflow-decision-alignment.md); commit/push/merge senaryosunda CI yeşil olmadan tamamlandı denmez. Doküman-only/analiz-only CI sınıflaması uygulama detayı olarak beklemede. |
| OD-011 | commercial-domain-payments.md | Ödeme sistemi kapsamı | Ödeme modeli/PSP/hukuk-mali akış uygulama paketi gelene kadar ödeme/PSP aktif kapsam dışı mı kalacak? | high | decision-approved / implementation-pending | Karar: [`payment-scope-decision.md`](payment-scope-decision.md) — şirket/vergi kaydı mevcut; erteleme nedeni şirket yokluğu değil. Ödeme ürün modeli + PSP/hukuk-mali ödeme akışı uygulama paketi hazır olana kadar ödeme sistemi, PSP, banka, merchant, checkout, webhook, settlement ve gerçek ödeme entegrasyonu aktif geliştirme kapsamı dışı; Lumos onaysız ödeme, satın alma, abonelik, domain satın alma/yenileme veya ödeme linki oluşturma başlatmaz; QR/tek link yalnızca gelecek ürün notu (uygulama yok); credential, banka/merchant detayı ve production endpoint public repoda ve Lumos yüzeyinde tutulmaz. **Bekleyen:** PSP seçimi, ödeme sağlayıcı entegrasyonu, vergi/fatura akışı, abonelik modeli, maliyet paylaşımı modeli, ödeme verisi vault entegrasyonu; OD-040/041 detayları. |
| OD-012 | external-integrations-permissions.md | Computer Use kapısı | OpenAI Computer Use onaysız dış yazma riskine karşı hangi onay katmanı uygulanacak? | high | decision-approved / implementation-pending | Karar: [`computer-use-permission-gate-decision.md`](computer-use-permission-gate-decision.md) — Computer Use serbest yetkilendirilmiş katman değildir; Lumos geçidi, görev kapsamı, mod ayrımı ve dış etkili aksiyonlarda açık kullanıcı onayı zorunlu; geri dönüşsüz/kritik aksiyonlar otomatik yapılmaz; gerçek kanıt sunulur (mock ≠ gerçek); public repoda secret/protokol yasağı geçerlidir. OpenAI çekirdek stratejik AI sağlayıcısıdır (sağlayıcı kararı kapalı). **Bekleyen:** Computer Use teknik entegrasyonu, sandbox modeli, onay UX'i, log/kanıt politikası, credential entegrasyonu. |

---

## Ürün/UX açık kararları

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-013 | ui-chat-experience.md | Görsel üretim kapsamı | Chat içinde image generation ürün kapsamına girecek mi? | medium | needs-review | Görsel destek beklentisi §1 |
| OD-014 | ui-chat-experience.md | Chat görsel destek UX | Görsel destek kart/mesaj modeliyle nasıl hizalanacak? | medium | needs-review | Görsel destek beklentisi §2 |
| OD-015 | voice-media-experience.md | Görsel üretim (ses dok.) | Ses/medya dokümanındaki görsel üretim beklentisi UI kararıyla tek mi? | medium | needs-review | ui-chat-experience.md OD-013/014 ile çapraz; çelişki çözülmedi |
| OD-016 | voice-media-experience.md | Kamera erişimi | Kamera/foto kalitesi iyileştirme hangi izin ve onay akışıyla sunulacak? | medium | needs-review | Kamera ve fotoğraf fikri |
| OD-017 | voice-media-experience.md | Foto / arka plan düzenleme | Foto ve arka plan düzenleme akışları ürün kapsamına alınacak mı? | medium | needs-review | Ürün kapsamı netleşene kadar bekliyor |
| OD-018 | ui-chat-experience.md | Yeni sohbet menüsü | Yeni sohbet menüsü UX ve davranışı nasıl tanımlanacak? | medium | queued | Özellik izleniyor; tam spesifikasyon yok |
| OD-019 | ui-chat-experience.md | Sohbetten dal oluşturma | Mevcut sohbetten branch-from-current akışı nasıl çalışacak? | medium | queued | Kart aksiyonu «çatalla» ile ilişki netleşmeli |
| OD-020 | repair-assistant-requirements.md | Tamir asistanı yüzeyi | Tamir asistanı Lumos'un hangi yüzeyinde ve hangi yetki profiliyle çalışır? | medium | needs-review | Needs-review özeti §1 |
| OD-021 | repair-assistant-requirements.md | Ses katmanı istisnası | Genel üründe ses varken tamir alanı metin-only — çakışma nasıl yönetilir? | medium | needs-review | voice-media-experience.md ile çapraz |
| OD-022 | repair-assistant-requirements.md | Kart fotoğrafı hattı | PCB fotoğrafı nerede işlenir, saklanır, kim görür? | medium | needs-review | Girdi türleri §1 |
| OD-023 | product-rules.md | Vault UX detayı | «Gizli anahtarlar Lumos yüzeyinde tutulmaz» ilkesi UX'te nasıl anlatılacak? | medium | needs-review | UX kuralları §3; security-architecture ile örtüşür |

---

## Güvenlik/mimari açık kararları

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-024 | product-rules.md | Şifreleme detayı (ürün) | Veri sahipliği Encrypted ekseninde şifreleme politikası hangi belgede genişletilecek? | high | needs-review | Veri sahipliği ekseni; data-vault OD-005 ile örtüşür |
| OD-025 | security-architecture.md | Vault migration maddeleri | ChatGPT kaynaklı vault/token maddeleri uygulama tanımına taşındı mı? | high | needs-review | Migration: Lumos vault + token detayı |
| OD-026 | internal-agent-layers.md | Doğrulanmamış iç mesaj | Reddedilen iç mesaj için operasyonel olay kaydı prosedürü ne? | medium | needs-review | İç iletişim §3 — operasyonel detay |
| OD-027 | project-map-runtime-entrypoints.md | packages/kando_* geçişi | `packages/kando_*` → `src/` geçiş takvimi ve kesme kriterleri ne? | high | decision-approved / implementation-pending | Karar: [`kando-packages-transition-decision.md`](kando-packages-transition-decision.md) — **Seçenek C (Hibrit)** onaylandı: `src/` canonical; `kando_bridge` + `kando_runtime` **keep**; `kando_core`/`memory`/`policy`/`context` **archive candidate**. Faz 1 envanter: [`kando-packages-faz1-inventory.md`](kando-packages-faz1-inventory.md). **Bekleyen:** ayna paket arşivi, `lumos_runtime` ölü ayna temizliği, `kando_core.__main__` web kalıntısı, §8 kesme checklist ile cutover. |
| OD-028 | project-map-runtime-entrypoints.md | lumos web komutu | `lumos web` / eksik `web/app.py` — B1: alt komutu kaldır (restore değil) | medium | closed | Karar: [`lumos-web-command-decision.md`](lumos-web-command-decision.md) — **B1** uygulandı: `__main__.py` web dalı kaldırıldı, `test_web_health.py` silindi, mimari belge senkronu. `packages/kando_core` web kalıntısı OD-027'de. |
| OD-029 | tools-technology-watchlist.md | Ghidra kapsamı | Ghidra RE/firmware entegrasyonu public OSS sınırında kalacak mı? | medium | needs-review | RE/firmware araçları; public boundary |
| OD-030 | tools-technology-watchlist.md | Çin menşeli vibe coding | Çin menşeli AI prototip araçları güvenlik/veri sınırı test edildi mi? | medium | needs-review | Vibe coding kategorisi |

---

## Entegrasyon/veri açık kararları

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-031 | external-integrations-permissions.md | İletişim kanalları otomasyon modeli (mail ilk kanal) | Kullanıcı tanımlı iletişim kanalları takip/otomasyon modelinin kapsam, izin paketi ve onay seviyeleri ne? | medium | decision-approved / implementation-pending | Karar: [`mail-integration-approval-decision.md`](mail-integration-approval-decision.md) — Lumos = kullanıcının kontrollü dijital uzantısı; yalnızca açık istek/kural + izin paketi + çekirdek kurallar içinde hareket; **özetleme/pasif okuma sınırı yok** — izin paketi sınırları içinde tam otomasyon mümkün; varsayılan pasif (izinsiz okuma yok); granüler izin: read, notify, draft_prep, send_reply, archive, label, delete; kural: kanal/kişi/kaynak/içerik/görev; örnekler: Angel→bildir, Leyla→otomatik yanıt+bildirim kapalı, Hasan→her zaman bildir, Müşteri X→taslak+onay, grup→takip+yalnızca önemli bildir; kalıcı silme asla otomatik; credential vault (OD-001/002); içerik public repo/log/kalıcı belleğe yazılmaz; OD-041 oturum=read/notify, send/delete=işlem veya kural-kapsamlı; OD-012 + product-rules hizası; kapalı platformlar (Telegram/WhatsApp/Messenger) resmi API ayrı değerlendirme — bypass/scraping yok. **Mail = ilk kanal;** Telegram/WhatsApp/Messenger/SMS/sosyal DM genişleme adayı. **Bekleyen:** mail provider, diğer kanal API'leri, vault API, kural UX, sync, çakışma algoritması. |
| OD-032 | external-integrations-permissions.md | Takvim + Kişiler | Takvim (okuma, oluştur, taşı, iptal, RSVP, planlama) ve kişiler (bul, ilişkilendir, geçmiş bağla, kişi kuralları) için izin/onay modeli ne? | medium | decision-approved / implementation-pending | Karar: [`calendar-contacts-decision.md`](calendar-contacts-decision.md) — **yalnızca Takvim + Kişiler**; granüler izin (`cal_*`, `contact_*`); OD-031 kişi kuralları, OD-041/OD-012 hibrit onay, vault OD-001/002; varsayılan pasif; entegrasyon yöntemi ikincil. **Çalışma araçları bu OD'de değil** → OD-033. **Bekleyen:** provider (Google Calendar, iCal, CalDAV, kişi kaynağı), connector, onay UX, sync. |
| OD-033 | external-integrations-permissions.md | Platform connector'ları / çalışma araçları | GitHub/Slack/Drive/Linear/Notion/Asana vb. connector'ları hangi ilke, izin paketi ve değerlendirme sırasıyla yönetilecek? | medium | decision-approved / implementation-pending | Karar: [`work-tools-connectors-decision.md`](work-tools-connectors-decision.md) — **yalnızca çalışma araçları**; granüler izin (`{platform}_read` … `_delete`); değerlendirme listesi (otomatik ekleme yok); katman 1–5 (GitHub → Slack/Drive → Linear → Notion/Asana); OD-031/032/039–042 **hariç**; OD-041/OD-012 hibrit onay; vault OD-001/002; resmi API tercih. **Bekleyen:** ilk connector (öneri GitHub), OAuth scope, webhook vs poll, onay UX, görev motoru çakışması. |
| OD-034 | external-integrations-permissions.md | OpenAI Agents / Realtime | Agents SDK ve Realtime ses entegrasyonu hangi onay kapısından geçer? | medium | needs-review | Tek tek evaluate |
| OD-035 | external-integrations-permissions.md | Codex Plugins | Codex Plugins public repo + onay modeliyle uyumlu mu? | medium | needs-review | Watchlist ile çapraz |
| OD-036 | data-vault-user-data.md | Dış platform connector'ları | Belirli dış platform import connector'ları hangi sırayla planlanacak? | medium | needs-review | Migration #15 |
| OD-037 | repair-assistant-requirements.md | Dış arama / online politika | Şema/saha taraması hangi entegrasyonlarla; offline'da ne olur? | medium | needs-review | Analiz §3; Kaynak tarama §5 |
| OD-038 | repair-assistant-requirements.md | Public demo sınırı | Hangi tamir akışları demo-safe, hangileri private katmanda kalır? | medium | needs-review | Needs-review özeti §4 |
| OD-039 | commercial-domain-payments.md | Domain varyasyon redirect | Edinilen varyasyon domain'ler `welockai.com`'a nasıl yönlendirilecek? | medium | decision-approved / implementation-pending | Karar: [`domain-redirect-model-decision.md`](domain-redirect-model-decision.md) — tüm edinilen varyasyonlar `welockai.com`'a yönlendirilir; varyasyonda ayrı içerik yok; satın alma onayı ≠ DNS/redirect onayı (OD-041 CA3 — ayrı işlem onayı); ne/nerede/etki/maliyet öncesi zorunlu; sessiz/varsayılan/carry-forward redirect yok; yalnızca onaylı edinim sonrası (OD-042 adım 5); ödeme kapsamı dışı (OD-011); varsayılan **301 Permanent Redirect**; kabul edilen yollar: **registrar forwarding** veya **Cloudflare tabanlı redirect**; davranış sabiti: kullanıcı her zaman birincil domain'de sonlanır. **Bekleyen:** somut registrar/Cloudflare kurulumu, SSL, apex/www, rollback, redirect onay UX. |
| OD-040 | commercial-domain-payments.md | Maliyet paylaşımı QR/link | QR veya tek ödeme linki ile maliyet paylaşımı ürün/hukuk/PSP modeli ne? | low | needs-review | Ödeme ertelenmiş kapsam |
| OD-041 | commercial-domain-payments.md | Ticari onay modeli | Domain/ödeme onayı tek seferlik mi oturum bazlı mı? | medium | decision-approved / implementation-pending | Karar: [`commercial-approval-model-decision.md`](commercial-approval-model-decision.md) — hibrit model: düşük riskli okuma/izleme/araştırma/durum kontrolü oturum bazlı; dış etkili ticari aksiyonlar (ödeme, satın alma, abonelik, yenileme, para transferi, domain satın alma/transfer, DNS değişikliği) her işlem için ayrı açık onay; sessiz/varsayılan/carry-forward onay yok; oturum izni asla ödeme veya ticari işlem yetkisi değil; OD-012 işlem bazlı onay ile hizalı; işlem öncesi ne/nerede/etki/yaklaşık maliyet zorunlu. **Bekleyen:** onay UX akışı, işlem onay ekranı, `kisitli_otonom` genel onay UI ayrımı. |
| OD-042 | commercial-domain-payments.md | Domain izleme tasarımı | Marka koruma izleme/raporlama UX ve veri kaynağı nasıl? | medium | decision-approved / implementation-pending | Karar: [`domain-monitoring-design-decision.md`](domain-monitoring-design-decision.md) — `welockai.com` birincil; marka varyasyonları + kullanıcı watchlist; kaynak/müsaitlik/fiyat sinyali/risk şeffaf sunum; pasif rapor varsayılan, alarm bilgi-only (otomatik satın alma yok); akış: izle → risk göster → kullanıcı karar → satın alma (OD-041 işlem onayı) → redirect (OD-039); izleme oturum izni, satın alma ayrı; ödeme kapsamı dışı (OD-011). **Bekleyen:** veri kaynağı nihai seçimi (WHOIS/registrar / marka koruma / hibrit — değerlendirme adayı), kontrol sıklığı, risk skor detayı, rapor vs dashboard UX, alarm eşikleri/kanalları.

---

## Proje/repo açık kararları

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-043 | project-map-runtime-entrypoints.md | Birincil kullanıcı yüzeyi | Birincil üretim/dış kullanıcı yüzeyi hangisi? | high | decision-approved | Karar: [`primary-user-surface-decision.md`](primary-user-surface-decision.md); birincil üretim/dış kullanıcı yüzeyi `ui/` Astro olarak onaylandı. `panel/` legacy/statik E2E kalite kapısıdır; `frontend/` birincil/canlı yüzey değildir. OD-046 Option A uygulamasıyla E2E hizası ayrıca tamamlanacak. |
| OD-044 | project-map-runtime-entrypoints.md | frontend/ rolü | `frontend/` dizininin panel/ui ile ilişkisi ve yaşam döngüsü ne? | medium | decision-approved | Karar: [`frontend-role-decision.md`](frontend-role-decision.md); Seçenek B onaylandı — izole köprü E2E + prototip referans; üretim/deploy/root build/root E2E yüzeyi değil; kod/taşıma/arşiv/silme yok. Seçenekler A/C/D seçilmedi. Çapraz: OD-043 birincil `ui/`; OD-046 E2E hizası ayrı uygulama. |
| OD-045 | project-map-runtime-entrypoints.md | lumos-demo konumu | `lumos-demo` nerede; lumos-core ile ilişkisi ne? | low | superseded / not-found | Kapandı (2026-06-17): `work_2026` altında bulunamadı; aktif lumos-core parçası değil (giriş noktası, build hedefi, app bağımlılığı yok). Sonradan bulunursa ayrı repo/yan klasör olarak yeniden değerlendirilir — otomatik lumos-core parçası sayılmaz. |
| OD-046 | project-map-runtime-entrypoints.md | Root build vs panel E2E | `npm run build` (ui) ile panel E2E hangi yüzeyi hedefler? | medium | decision-approved / **implementation-partial** (plan approved) | Karar: [`build-e2e-surface-alignment-decision.md`](build-e2e-surface-alignment-decision.md); Seçenek A. **v1–v2:** smoke+CI (#294–296). **Migrasyon planı:** [`od-046-e2e-migration-plan.md`](od-046-e2e-migration-plan.md) — Faz 0 kayıtlı; ürün blocker kapandı (E2E tamamla = UI/API, chat `görev tamamla` kapsam dışı). Faz 1–4 kod PR bekliyor. |
| OD-047 | repair-assistant-requirements.md | Ürün vizyonu hizası | Teknik servis asistanı genel Lumos vizyonuna nasıl bağlanır? | medium | needs-review | Kapsam §4 migration notu |
| OD-058 | evidence-continuity-v1-decision.md | Evidence Continuity v1 | Panel + engine sunucu mutasyonları için append-only journal (Karar A) uygulandı mı? | medium | closed | Karar: [`evidence-continuity-v1-decision.md`](evidence-continuity-v1-decision.md) — **Karar A** uygulandı ve doğrulandı (PR #248, `main`); H0/H1/H2 hook'ları canlı. **v2 backlog:** [`evidence-continuity-v2-backlog.md`](evidence-continuity-v2-backlog.md) — 14/14 `implementation-complete` (PR #255–#291). |
| OD-059 | audit-hook-term-decision.md | Audit hook terminolojisi | Informal «audit hook» takip maddesi ayrı git hook gerektiriyor mu? | low | closed | Karar: [`audit-hook-term-decision.md`](audit-hook-term-decision.md) — **Hayır**; git hook reddi. Üç katman: commit guard (dev), EC runtime (v1), EC v2 #4/#14. Informal takip maddesi docs seviyesinde **CLOSED**. Opsiyonel CI ruff parity (Paket B) ayrı PR — `implementation-pending`. |

---

## Marka/dış vitrin açık kararları

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-048 | public-identity-branding.md | Landing page kopyası | Landing tonu, iddia seviyesi ve hedef kitle nasıl tanımlanacak? | medium | needs-review | Dış vitrin fazı §5 |
| OD-049 | public-identity-branding.md | Landing tonu (migration) | Kanal bazlı landing taslağı ne zaman hazırlanacak? | medium | needs-review | Migration #6 |
| OD-050 | public-identity-branding.md | LUMOS AI skull logo | Skull logo gelecek görsel kimlikte kullanılacak mı; nerede? | low | needs-review | Görsel commit yok; kullanıcı tercihi notu |
| OD-051 | public-identity-branding.md | Logo kullanım kuralları | Logo boyut, arka plan ve birlikte metin kuralları ne? | low | needs-review | Migration #7 |
| OD-052 | public-identity-branding.md | Landing görsel tonu | Landing görsel tonu metin tonuyla nasıl hizalanacak? | low | needs-review | Marka §4 |
| OD-053 | public-identity-branding.md | LinkedIn profil güncellemesi | Dış vitrin fazında LinkedIn metni ne zaman yayınlanacak? | low | queued | Dış vitrin §1 |
| OD-054 | public-identity-branding.md | Profil fotoğrafı | Vitrin fotoğrafı görsel kimlikle nasıl seçilecek? | low | queued | Dış vitrin §2 |
| OD-055 | public-identity-branding.md | Kısa tanıtım metni | Kişisel/proje intro metni taslağı ne? | low | queued | Dış vitrin §3 |
| OD-056 | public-identity-branding.md | GitHub README metni | Public README vitrin metni ne zaman güncellenecek? | low | queued | Dış vitrin §4 |
| OD-057 | public-identity-branding.md | Renk / tipografi | Marka renk, tipografi ve ikon seti kararı var mı? | low | queued | Marka §3 — henüz canonical karar yok |

---

## Migration tablosu (indeks bakımı)

Kaynak dosyalardaki migration tablolarından **needs-review / queued** özetleri; tam liste kaynak dosyada.

| Kaynak dosya | needs-review (yaklaşık) | queued (yaklaşık) | İndeks OD aralığı |
|--------------|-------------------------|-------------------|-------------------|
| product-rules.md | 4 | 0 (+5 boş manuel incelenecek) | OD-023, OD-024 |
| security-architecture.md | 4 | 0 | OD-001, OD-002, OD-025 |
| project-workflow.md | 3 | 5 (boş manuel) | OD-008, OD-009, OD-010 |
| ui-chat-experience.md | 3 | 2 (+5 boş manuel) | OD-013, OD-014, OD-018, OD-019 |
| voice-media-experience.md | 3 | 5 (boş manuel) | OD-015, OD-016, OD-017 |
| data-vault-user-data.md | 5 | 5 (boş manuel) | OD-003, OD-004, OD-005, OD-036 |
| external-integrations-permissions.md | 5 | 5 (boş manuel) | OD-031 – OD-035, OD-012 |
| commercial-domain-payments.md | 5 | 5 (boş manuel) | OD-039 – OD-042, OD-011 |
| repair-assistant-requirements.md | 5 | 5 (boş manuel) | OD-020 – OD-022, OD-037, OD-038, OD-047 |
| tools-technology-watchlist.md | 3 | 3 (boş manuel) | OD-029, OD-030 |
| internal-agent-layers.md | 4 | 5 (boş manuel) | OD-006, OD-007, OD-026 |
| public-identity-branding.md | 5 | 9 (+5 boş manuel) | OD-048 – OD-057 |
| project-map-runtime-entrypoints.md | 3 | 1 | OD-027, OD-028 (closed), OD-043/044 (approved), OD-046 (approved/pending) |
| evidence-continuity-v1-decision.md | 0 | 0 | OD-058 (closed / v2 backlog: evidence-continuity-v2-backlog.md) |
| audit-hook-term-decision.md | 0 | 0 | OD-059 (closed / terminoloji) |
| chatgpt-saved-memories-migration.md | 0 | 5 (boş manuel) | — (süreç rehberi; madde yok) |

**İndeks senkron kontrolü:** Kaynak dosyada `needs-review` / `queued` / `incelenecek` sayısı değişince bu tablo ve ilgili OD satırları güncellenir.

---

## Manuel eklenecek maddeler

Kaynak dosyalardaki boş manuel şablonlar burada tekrarlanmaz. Yeni açık karar için aşağıya satır ekleyin; ardından hedef canonical dosyaya da işleyin.

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-060 | *(manuel)* | | | | queued | |

---

Son güncelleme: 2026-06-20 (OD-046 Faz 0 migrasyon planı; görev tamamla blocker kapalı; implementation-partial)
