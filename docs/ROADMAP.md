# Lumos Master Roadmap — tek kaynak

| Alan | Değer |
| --- | --- |
| Durum | Yürürlükte — 2026-07-20 kullanıcı kararı |
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
| v0.5 | Dosya + Görev sistemi | Sıradaki hedef |
| v0.6 | Mobil temel | Bekliyor |
| v1.0 | İlk genel sürüm (FAZ 1 tamam) | Bekliyor |

## Durum haritası (2026-07-20 — kanıta dayalı değerlendirme)

Ayrıntı ve kanıt: [`docs/MODULES.md`](MODULES.md). iOS ★: ayrı repo, sınırlı görünürlük.

```text
Lumos v1 (FAZ 1 tanımına göre)     ~%60

Core (agent/task/brain)  ████████░░  %80
Kimlik (Google OAuth)    █████████░  %90
Chat (hosted bridge)     ███████░░░  %70
Panel                    ███████░░░  %70
Görev sistemi            ██████░░░░  %60
Dosya                    ███░░░░░░░  %30
Memory                   █████░░░░░  %50
Security                 ███████░░░  %75
iOS ★                    ███░░░░░░░ ~%35
Entegrasyonlar           █████░░░░░  %50
Board/Orchestration      ██████░░░░  %60
Deploy/Ops               ██████░░░░  %65
```

En zayıf iki halka: **Dosya** ve **iOS**.

## STOP LIST

FAZ-1 bitene kadar **yeni özellik eklenmez**:

- ❌ Logo / görsel kimlik turu
- ❌ Yeni AI provider
- ❌ Quantum
- ❌ Video / Media
- ❌ Yeni entegrasyon
- ❌ Yeni sayfa
- ❌ Yeni agent / orchestration katmanı

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

## Command Wall — iç operatör yüzeyi

Command Wall, **internal operator/admin surface**'tir; piyasaya çıkacak bir son
kullanıcı ürünü **değildir**. Lumos ile aynı motoru (AI Runtime / Router)
kullanır, ayrı bir motor kurmaz.

- **Karar durumu:** sınır tanımı kabul edildi (2026-08-08, ADR-019).
- **Uygulama durumu:** yeni operatör arayüzü veya orchestration kodu
  **yazılmadı**. Bugünkü kapsam `src/lumos_board/` CLI ile sınırlıdır.
- STOP LIST'teki "yeni agent / orchestration katmanı" yasağı **sürer**; bu tanım
  onu delmez, yalnız gelecekteki işin adını ve sınırını sabitler.

Kullanıcı yüzüne sağlayıcı/model adı, `session_id`, `instance_id`, worktree,
heartbeat, PR/merge kapısı ve iç ajan koordinasyonu **sızmaz**.

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
