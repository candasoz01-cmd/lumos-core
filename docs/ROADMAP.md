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

Yeni provider ancak ayrı karar, güvenlik ve veri sınırı, maliyet, test ve geçiş
kanıtıyla etkinleştirilir.

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
