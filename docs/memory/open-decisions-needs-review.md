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
| OD-001 | security-architecture.md | Lumos Vault uygulaması | Secret'lar hangi vault/katman modelinde tutulacak; Lumos yüzeyinden nasıl ayrılacak? | high | needs-review | Karar taslağı: [`vault-secret-token-decision.md`](vault-secret-token-decision.md); kısmi netleşti — katman modeli; uygulama kararı bekliyor. Lumos Vault §1; product-rules UX §3 ile örtüşür |
| OD-002 | security-architecture.md | Token / vault entegrasyonu | Token ve credential yönetimi vault + bridge ile nasıl birleşecek? | high | needs-review | Karar taslağı: [`vault-secret-token-decision.md`](vault-secret-token-decision.md); kısmi netleşti — yüzeyde token yok ilkesi; entegrasyon akışı uygulama kararı bekliyor. Kimlik/token §Token; Lumos Vault §2 |
| OD-003 | data-vault-user-data.md | Vault amaç bazlı erişim | Vault Lumos'a hangi kapsamda, hangi amaç kodlarıyla erişim verecek? | high | needs-review | Karar taslağı: [`vault-secret-token-decision.md`](vault-secret-token-decision.md); kısmi netleşti — amaçlı/onaylı erişim ilkesi; API/amaç kodu uygulama kararı bekliyor. Lumos Vault §3 |
| OD-004 | data-vault-user-data.md | Risk dağılımı / segmentasyon | Ele geçirmede tüm sırlar tek yerde açığa çıkmaması için şifreleme ve segmentasyon modeli ne? | high | needs-review | Karar taslağı: [`vault-secret-token-decision.md`](vault-secret-token-decision.md); kısmi netleşti — segmentasyon hedefi; somut model uygulama kararı bekliyor. Lumos Vault §4; Risk §3 |
| OD-005 | data-vault-user-data.md | Şifreleme ve anahtar yönetimi | Vault içi şifreleme ve anahtar döngüsü nasıl tanımlanacak? | high | needs-review | Karar taslağı: [`vault-secret-token-decision.md`](vault-secret-token-decision.md); kısmi netleşti — şifreleme gerekli ilkesi; teknik spec uygulama kararı bekliyor. Migration #16; product-rules Encrypted ekseni |
| OD-006 | internal-agent-layers.md | Bando katman varlığı | Bando ayrı katman olarak kalacak mı; görev ve yetki sınırları net mi? | high | needs-review | Karar taslağı: [`internal-communication-bando-decision.md`](internal-communication-bando-decision.md); kısmi netleşti — Bando rolü (güvenlik/gözlem); dağıtım uygulama kararı bekliyor. Bando güvenlik §5; Risk §6 |
| OD-007 | internal-agent-layers.md | İç iletişim protokolü | Lumos→iç katman imzalama/şifreleme protokolü ve anahtar döngüsü ne? | high | needs-review | Karar taslağı: [`internal-communication-bando-decision.md`](internal-communication-bando-decision.md); kısmi netleşti — doğrulama ilkesi; protokol/format uygulama kararı bekliyor. İç iletişim §2; Risk §4 |
| OD-008 | project-workflow.md | Continuous progress vs tek-adım | `docs/workflow-rules.md` continuous progress ile `.cursor/rules/tek-adim-ilerleme.mdc` hangisi öncelikli? | high | decision-draft | Karar taslağı: [`workflow-decision-alignment.md`](workflow-decision-alignment.md); kısmi netleşti — tek hedef ve tur başına tek aksiyon üstün. Birincil workflow canonical ve dosya hizalaması hâlâ needs-review. |
| OD-009 | project-workflow.md | Agent-first canonical kaynak | Agent-first execution kuralı tek canonical yerde mi tutulacak? | high | decision-draft | Karar taslağı: [`workflow-decision-alignment.md`](workflow-decision-alignment.md); davranış firm — agent-first tercih edilir ama kapsam genişletmez. Tek canonical kaynak seçimi ve çift kayıt birleştirme hâlâ needs-review. |
| OD-010 | project-workflow.md | CI tamamlanma kriteri | CI yeşil olmadan tamamlandı sayma kuralı workflow belgeleriyle tam hizalı mı? | high | decision-draft | Karar taslağı: [`workflow-decision-alignment.md`](workflow-decision-alignment.md); kısmi netleşti — doğrulama, kullanıcı kabulü ve commit/push sonrası yeşil CI olmadan tamamlandı denmez. Doküman-only/analiz-only CI sınıflaması hâlâ needs-review. |
| OD-011 | commercial-domain-payments.md | Ödeme sistemi kapsamı | Şirket yapısı netleşene kadar ödeme/PSP tamamen dışarıda mı kalacak? | high | needs-review | Karar taslağı: [`payment-scope-decision.md`](payment-scope-decision.md); decision-draft eklendi — ödeme ertelenir ilkesi firm; PSP/uygulama kararı bekliyor. Ödeme sistemi ertelenmiş kapsam |
| OD-012 | external-integrations-permissions.md | Computer Use kapısı | OpenAI Computer Use onaysız dış yazma riskine karşı hangi onay katmanı uygulanacak? | high | needs-review | Karar taslağı: [`computer-use-permission-gate-decision.md`](computer-use-permission-gate-decision.md); kısmi netleşti — izin kapısı ilkeleri; teknik/UX uygulama kararı bekliyor. OpenAI ajan araçları bölümü |

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
| OD-027 | project-map-runtime-entrypoints.md | packages/kando_* geçişi | `packages/kando_*` → `src/` geçiş takvimi ve kesme kriterleri ne? | high | needs-review | Karar taslağı: [`kando-packages-transition-decision.md`](kando-packages-transition-decision.md); decision-draft eklendi — `src/` canlı; faz taslağı; hedef mimari uygulama kararı bekliyor. Manuel §4 |
| OD-028 | project-map-runtime-entrypoints.md | lumos web komutu | `lumos web` / eksik `web/app.py` restore edilecek mi kaldırılacak mı? | medium | needs-review | Karar taslağı: [`lumos-web-command-decision.md`](lumos-web-command-decision.md); decision-draft eklendi — komut kırık; restore/kaldırma uygulama kararı bekliyor. Runtime §3; Manuel §3 |
| OD-029 | tools-technology-watchlist.md | Ghidra kapsamı | Ghidra RE/firmware entegrasyonu public OSS sınırında kalacak mı? | medium | needs-review | RE/firmware araçları; public boundary |
| OD-030 | tools-technology-watchlist.md | Çin menşeli vibe coding | Çin menşeli AI prototip araçları güvenlik/veri sınırı test edildi mi? | medium | needs-review | Vibe coding kategorisi |

---

## Entegrasyon/veri açık kararları

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-031 | external-integrations-permissions.md | Mail entegrasyonu | İzinli mail okuma/özet gelecek özelliğinin kapsam ve onay modeli ne? | medium | needs-review | Bölüm durumu needs-review |
| OD-032 | external-integrations-permissions.md | Takvim / kişiler / çalışma araçları | Takvim, kişiler ve Notion/Asana benzeri araçlar için izin modeli tanımlanacak mı? | low | needs-review | Placeholder bölüm |
| OD-033 | external-integrations-permissions.md | Platform connector'ları | GitHub/Slack/Drive/Linear connector'ları tek tek ne zaman değerlendirilecek? | medium | needs-review | Değerlendirme listesi; otomatik ekleme yok |
| OD-034 | external-integrations-permissions.md | OpenAI Agents / Realtime | Agents SDK ve Realtime ses entegrasyonu hangi onay kapısından geçer? | medium | needs-review | Tek tek evaluate |
| OD-035 | external-integrations-permissions.md | Codex Plugins | Codex Plugins public repo + onay modeliyle uyumlu mu? | medium | needs-review | Watchlist ile çapraz |
| OD-036 | data-vault-user-data.md | Dış platform connector'ları | Belirli dış platform import connector'ları hangi sırayla planlanacak? | medium | needs-review | Migration #15 |
| OD-037 | repair-assistant-requirements.md | Dış arama / online politika | Şema/saha taraması hangi entegrasyonlarla; offline'da ne olur? | medium | needs-review | Analiz §3; Kaynak tarama §5 |
| OD-038 | repair-assistant-requirements.md | Public demo sınırı | Hangi tamir akışları demo-safe, hangileri private katmanda kalır? | medium | needs-review | Needs-review özeti §4 |
| OD-039 | commercial-domain-payments.md | Domain varyasyon redirect | Edinilen varyasyon domain'ler `welockai.com`'a nasıl yönlendirilecek? | medium | needs-review | Edinim onaylı; teknik detay sonra |
| OD-040 | commercial-domain-payments.md | Maliyet paylaşımı QR/link | QR veya tek ödeme linki ile maliyet paylaşımı ürün/hukuk/PSP modeli ne? | low | needs-review | Ödeme ertelenmiş kapsam |
| OD-041 | commercial-domain-payments.md | Ticari onay modeli | Domain/ödeme onayı tek seferlik mi oturum bazlı mı? | medium | needs-review | Kullanıcı onayı §3; çekirdek sözleşme esas |
| OD-042 | commercial-domain-payments.md | Domain izleme tasarımı | Marka koruma izleme/raporlama UX ve veri kaynağı nasıl? | medium | needs-review | Bölüm durumu needs-review |

---

## Proje/repo açık kararları

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-043 | project-map-runtime-entrypoints.md | Birincil kullanıcı yüzeyi | Birincil yüzey `panel/`, `ui/` veya `frontend/` mi? | high | needs-review | Karar taslağı: [`primary-user-surface-decision.md`](primary-user-surface-decision.md); kısmi netleşti — üretim taslağı `ui/`; kesin karar uygulama kararı bekliyor (OD-046 önkoşul). Üç dizin mevcut; build/e2e farklı hedefler |
| OD-044 | project-map-runtime-entrypoints.md | frontend/ rolü | `frontend/` dizininin panel/ui ile ilişkisi ve yaşam döngüsü ne? | medium | needs-review | Canlı/aday ayrımı tablosu |
| OD-045 | project-map-runtime-entrypoints.md | lumos-demo konumu | `lumos-demo` nerede; lumos-core ile ilişkisi ne? | low | needs-review | `work_2026` altında bulunamadı |
| OD-046 | project-map-runtime-entrypoints.md | Root build vs panel | `npm run build` (ui) ile panel E2E hangi yüzeyi «canlı» sayar? | medium | needs-review | Karar taslağı: [`build-e2e-surface-alignment-decision.md`](build-e2e-surface-alignment-decision.md); kısmi netleşti — üretim `ui/`, E2E `panel/`; hizalama seçeneği uygulama kararı bekliyor. Migration: birincil yüzey needs-review |
| OD-047 | repair-assistant-requirements.md | Ürün vizyonu hizası | Teknik servis asistanı genel Lumos vizyonuna nasıl bağlanır? | medium | needs-review | Kapsam §4 migration notu |

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
| project-map-runtime-entrypoints.md | 6 | 1 | OD-027, OD-028, OD-043 – OD-046 |
| chatgpt-saved-memories-migration.md | 0 | 5 (boş manuel) | — (süreç rehberi; madde yok) |

**İndeks senkron kontrolü:** Kaynak dosyada `needs-review` / `queued` / `incelenecek` sayısı değişince bu tablo ve ilgili OD satırları güncellenir.

---

## Manuel eklenecek maddeler

Kaynak dosyalardaki boş manuel şablonlar burada tekrarlanmaz. Yeni açık karar için aşağıya satır ekleyin; ardından hedef canonical dosyaya da işleyin.

| ID | Kaynak dosya | Konu | Kısa karar sorusu | Öncelik | Durum | Not |
|----|--------------|------|-------------------|---------|--------|-----|
| OD-058 | *(manuel)* | | | | queued | |
| OD-059 | *(manuel)* | | | | queued | |
| OD-060 | *(manuel)* | | | | queued | |

---

Son güncelleme: 2026-06-17
