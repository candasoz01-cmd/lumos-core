# Lumos Master Roadmap — tek kaynak

| Alan | Değer |
| --- | --- |
| Durum | Yürürlükte — 2026-08-12 Dosya v0.5 kabul |
| Kapsam | Core, Web, iOS, AI, Entegrasyonlar, Partner — bütün yüzeyler |
| Kural | Alt repolarda roadmap kopyası tutulmaz ([Constitution §1](CONSTITUTION.md)) |
| Güncelleme | Durum haritası haftada bir, kanıta dayanarak |

## MVP cümlesi

**Bugün yayınlasak Lumos şunu yapar:** Google ile giriş → panel → hosted chat
(OpenAI/Gemini köprüsü) + entegrasyon kataloğu + vitrin sayfaları; arka planda
yerel agent runner, evidence journal ve 1440 testlik güvence.

## Fazlar

### FAZ 1 — Ürün (aktif faz)

Hedef: "Lumos çalışıyor." diyebilmek. **Yeni özellik yok.**

Kapsam: Chat · Dosya · Görev · Kimlik · Panel · Mobil temel

### FAZ 2 — Altyapı

Yalnız eksikler: Apple Sign-In (web) · monitoring env bağlama · deploy
sertleştirme. (Google OAuth, Vercel deploy, CI 5 iş: tamam.)

### FAZ 3 — Vitrin

Site son hali · demo · README/dokümantasyon · videolar. (#620/#614 bu fazın
kararına kadar bekler.)

### FAZ 4 — Partner

PartnerU kalanları · sertifikalar · sunumlar. Ürünü bekler.

## Sürüm merdiveni

| Sürüm | Kapsam | Durum |
| --- | --- | --- |
| v0.4 | Kimlik + Chat | Fiilen bugünkü durum |
| v0.5 | Dosya + Görev sistemi | **Tamam** — Dosya kabul 2026-08-12; Görev panel canlı (önceki kanıt) |
| v0.6 | Mobil temel | **Sıradaki** — TestFlight (Apple hesap) |
| v1.0 | İlk genel sürüm (FAZ 1 tamam) | Bekliyor (v0.6 sonrası) |

### v0.5 Dosya — kabul kaydı (2026-08-12)

| Alan | Değer |
| --- | --- |
| Karar | **Accepted / completed** — yeni kod yok; canlı kanıt + envanter hizası |
| Kanıt | `prod-verify.sh` RESULT PASS (2026-07-22; yeniden 2026-08-12T06:50:09Z UTC, exit 0) |
| Uç | `GET /panel` 200 · `>Yükle<` · `fetch(UPLOAD_URL` · upload HEAD/GET/POST **401** |
| PR omurga | lumos-core #659 route · #661 panel wire · #660 UX |
| Bilinçli dışı | Sandbox redirect, trash sink derinliği, yeni upload UI — Faz 1 kapısı değil |

## Durum haritası (2026-08-12 — kanıta dayalı)

Ayrıntı ve kanıt: [`docs/MODULES.md`](MODULES.md). iOS ★: ayrı repo, sınırlı görünürlük.

```text
Lumos v1 (FAZ 1 tanımına göre)     ~%70

Core (agent/task/brain)  ████████░░  %80
Kimlik (Google OAuth)    █████████░  %90
Chat (hosted bridge)     ███████░░░  %70
Panel                    ███████░░░  %70
Görev sistemi            ██████░░░░  %60
Dosya                    ███████░░░  %70
Memory                   █████░░░░░  %50
Security                 ███████░░░  %75
iOS ★                    ███░░░░░░░ ~%35
Entegrasyonlar           █████░░░░░  %50
Board/Orchestration      ██████░░░░  %60
Deploy/Ops               ██████░░░░  %65
```

En zayıf halka (FAZ 1 ürün): **iOS / TestFlight**.

Deploy/Cloud 403 → FAZ 2 ops debt (FAZ 1 acceptance değil).

## STOP LIST

FAZ-1 bitene kadar **yeni özellik eklenmez**:

- ❌ Logo / görsel kimlik turu
- ❌ Yeni AI provider
- ❌ Quantum
- ❌ Video / Media
- ❌ Yeni entegrasyon
- ❌ Yeni sayfa
- ❌ Yeni agent / orchestration katmanı

### Dar istisna — Meta communications tamamlama dilimi

2026-08-08 kullanıcı kararıyla yalnız mevcut `communications` ailesindeki
**WhatsApp, Instagram ve Facebook** bağlantılarının tamamlanması STOP LIST'ten
dar kapsamlı olarak istisna tutulmuştur. Bu istisna yeni bir model sağlayıcısı
kararı değildir ve FAZ-1 sonrası **OpenAI → Claude pilotu → DeepSeek** sırasını
değiştirmez.

İstisna sınırları:

- mevcut provider kayıtları üzerinde OAuth, sunucu tarafı credential/vault,
  token yenileme/iptal, webhook doğrulama ve salt-okunur bağlantı/senkron;
- her dış etkili adımda mevcut onay ve politika kapılarının korunması;
- ilk dilimde mesaj gönderme, yorum, paylaşım veya yayınlama **yok**;
- secret, access token ve kişisel içerik client'a veya public repo'ya yazılmaz;
- Meta kimliği, izin/App Review veya canlı credential yoksa durum
  `awaiting_credentials` / `external_approval_required` kalır; **canlı** denmez;
- her uygulama dilimi ayrı küçük PR, test, CI ve merge-sonrası `main`
  doğrulamasıyla kapanır.

Normatif karar ve kabul kapıları: [ADR-020](decisions/ADR-020-meta-communications-exception.md).

### Dar istisna — Robotik egemenlik standardı ve çevrimdışı simülatör

2026-08-08 kullanıcı kararıyla **Lumos Robotics Sovereignty Layer v0.1** için
yalnız normatif teknik şartname ve gerçek robot/üretici SDK'sı kullanmayan
çevrimdışı güvenlik simülatörü STOP LIST'ten dar kapsamlı olarak istisna
tutulmuştur. Bu kayıt yeni bir son kullanıcı ürünü veya canlı robot bağlantısı
yetkisi vermez.

İstisna sınırları:

- üreticiden bağımsız tehdit modeli, uyumluluk sözleşmesi ve test profili;
- saf yazılım simülasyonunda varsayılan-red yetki, ağ/veri çıkışı kapısı,
  yerel imzalı güncelleme kararı, audit zinciri ve güvenli duruş;
- gerçek robot, üretici firmware'i/SDK'sı, bulut hesabı, yeni UI veya uzaktan
  komut kanalı **yok**;
- fiziksel acil durdurma yalnız normatif gereksinim ve simüle olaydır; donanım
  doğrulaması yapılmadan **uyumlu**, **canlı** veya **doğrulandı** denmez;
- sonraki donanım pilotu ayrı kullanıcı kararı, Board claim'i, risk analizi ve
  fiziksel test planı gerektirir.

Normatif karar ve kabul kapıları: [ADR-021](decisions/ADR-021-robotics-sovereignty-layer-v0-1.md).

### Dar istisna — Account Activity Correlation (güvenlik kanıtı)

2026-09-04 kullanıcı kararıyla **Account Activity Correlation / Security
Evidence Correlation** için yalnız yerel, gizliliği koruyan çekirdek STOP
LIST'ten dar kapsamlı olarak istisna tutulmuştur. Bu kayıt activity
tracking, yeni sayfa, mail ürünü veya otomatik hesap eylemi yetkisi vermez.

İstisna sınırları:

- üçüncü taraf güvenlik uyarısını kayıtlı cihaz/oturum kanıtıyla eşleştirme;
- minimal metadata (servis, zaman, cihaz kimliği, oturum türü, ağ sınıfı);
- raw browser history, parola, içerik ve düz metin IP **yok**;
- cihaz etiketi kimlik değildir; kayıt `device_id` + anahtar parmak izine bağlıdır;
- kesin hüküm yok (`owner_match` / `likely_owner` / `unknown` / `suspicious`);
- mail uyarısı şifre değiştirme veya oturum kapatmaya **çevrilmez**;
- yeni sayfa, yeni entegrasyon, tarayıcı sniffing veya çoklu cihaz senkronu **yok**.

Normatif karar ve kabul kapıları: [ADR-032](decisions/ADR-032-account-activity-correlation.md).

## FAZ-1 sonrası provider stratejisi

Bu kayıt yalnız FAZ-1 tamamlandıktan sonra değerlendirilecek yönü tanımlar;
bugün yeni provider geliştirme veya entegrasyon yetkisi vermez.

- **OpenAI:** Ana karar ve genel orkestratör.
- **Claude:** İlk kontrollü pilot; sınırlı kapsam, ölçüm ve geri alma planıyla
  FAZ-1 sonrasında denenir.
- **DeepSeek:** Claude pilotunun kalite, maliyet, gecikme ve bakım sonuçları
  ölçüldükten sonra değerlendirilecek aday.
- **Ürün yüzü:** Kullanıcı yalnız **Lumos** görür. Provider adları ürün kimliği
  olarak sunulmaz; teknik şeffaflık gerektiğinde doğru biçimde açıklanır.
  Kullanıcıya model/sağlayıcı seçtiren bir arayüz **yapılmaz** — 2026-08-08
  kararı, [ADR-019](decisions/ADR-019-product-surface-separation-modelregistry.md)
  ve [`product-rules.md`](product-rules.md) PR-005.

Yeni provider ancak ayrı karar, güvenlik ve veri sınırı, maliyet, test ve geçiş
kanıtıyla etkinleştirilir.

### Provider evaluation backlog (FAZ-1 sonrası)

Yukarıdaki sıra (**OpenAI → Claude pilotu → DeepSeek**) **değişmez**. Aşağıdakiler
bu sıraya girmeyi bekleyen adaylardır; bugün entegrasyon yetkisi **yoktur**.

| Aday | Durum | Not |
|------|-------|-----|
| Kimi / Moonshot | **Backlog — değerlendirilmedi** | 2026-08-08'de kayda alındı; entegrasyon yapılmadı |
| Gemini | Backlog | Ayrı karar bekler |

Değerlendirme tek başına "şu modeli ekle" biçiminde yapılmaz. Adaylar ortak
ölçütlerle karşılaştırılıp Router'a hangilerinin alınacağına karar verilir:
**kalite, maliyet, gecikme, tool-use, coding, context penceresi, güvenilirlik.**
Alınanlar kullanıcı yüzeyine değil, Router'ın altındaki `ModelRegistry`
katmanına bağlanır (ADR-004 § Router altında ModelRegistry sınırı).

## Lumos Agent Wall — iç operatör yüzeyi

Lumos Agent Wall (eski ad: Command Wall — 2026-08-08 kurucu ad kararı), **internal operator/admin surface**'tir; piyasaya çıkacak bir son
kullanıcı ürünü **değildir**. Lumos ile aynı motoru (AI Runtime / Router)
kullanır, ayrı bir motor kurmaz.

- **Karar durumu:** sınır tanımı kabul edildi (2026-08-08, ADR-019).
- **Uygulama durumu:** yeni operatör arayüzü veya orchestration kodu
  **yazılmadı**. Bugünkü kapsam `src/lumos_board/` CLI ile sınırlıdır.
- **Decision Queue / Human Action Queue (2026-08-24):** mevcut Agent Wall
  başlığının alt kavramı — paralel ajan işlerinde insan onayı bekleyen
  karar noktalarını görünür kılmak. Ayrı ROADMAP maddesi veya
  `Lumos Workboard` ürünü **değil**. OD-063 / ADR-019.
- **Güncelleme (2026-08-25):** OD-063 için minimal human-on-exception dilimi
  yetkilendirildi — agent-status şema v2 (`blocked` / `awaiting_decision` +
  `wait_reason`) ve salt-okunur Decision Queue görünümü; güvenilir-yazıcı
  sınırı ayrı onay. Kapsam `src/lumos_board/` dilimlerinin genişletmesidir;
  yeni ürün / yeni Agent Network / ajanlar arası doğrudan komut /
  auto-merge / auto-deploy / dış gönderim yok.
- STOP LIST'teki "yeni agent / orchestration katmanı" yasağı **sürer**; bu tanım
  onu delmez, yalnız gelecekteki işin adını ve sınırını sabitler.

Kullanıcı yüzüne sağlayıcı/model adı, `session_id`, `instance_id`, worktree,
heartbeat, PR/merge kapısı ve iç ajan koordinasyonu **sızmaz**.

## Panel kendini yönetme yüzeyi (FAZ-1 sonrası yön)

2026-08-27 kullanıcı kararı: panel **dönüşebilir**; üç ayrı ürün veya üç
yeni sayfa **açılmaz**. Aynı `/panel` üç mercek gösterir:

1. **Kontrol merkezi** — ne çalışıyor, ne harcıyor, hangi işlem.
2. **Denetim merkezi** — doğru muydu, yetkili miydi, kayıt var mı.
3. **Güven kurulu** — kritik adım için insan / onay / kural.

Cümle: **Lumos sadece sistemi çalıştırmaz; sistemin kendini nasıl
yönettiğini de gösterir.**

Bu kayıt FAZ-1 uygulama izni değildir. STOP LIST (`yeni sayfa`, `yeni
özellik`) sürer. Panel bağlama FAZ-1 kapanış onayından sonra.
Sağlayıcı/model adı kullanıcı merceğine sızmaz (ADR-019); o ayrıntı
Agent Wall’dadır. Normatif taslak:
[`docs/analysis/lumos-self-governance-surface.md`](analysis/lumos-self-governance-surface.md).

## v2 rafı (şimdi konuşulmaz)

- **Media** (video üretimi, render, ses, kolaj)
- **Quantum** (ADR-001/013 doküman olarak durur)
- **Mail** (kullanıcı bugün Mail değil Lumos istiyor; #616 kapatıldı, iş
  ADR/dokümanlarda kayıtlı)
- Multi-device sync (zaten bilinçli v1 dışı)

## Bağlı kayıtlar

- Çalışma kuralları: [`docs/CONSTITUTION.md`](CONSTITUTION.md)
- Modül envanteri: [`docs/MODULES.md`](MODULES.md)
- Teknik borç: [`docs/TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md)
- Kanıt merdiveni: [`docs/analysis/scope-accounting.md`](analysis/scope-accounting.md)
- Kendini yönetme yüzeyi: [`docs/analysis/lumos-self-governance-surface.md`](analysis/lumos-self-governance-surface.md)
