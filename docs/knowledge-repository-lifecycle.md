# Knowledge Repository Lifecycle

> **Sürüm:** v1.0 — kapsam donduruldu. Yeni fikirler bu dosyaya eklenmez; ayrı kayıtlarda yaşar.

## 1. Amaç

Lumos Knowledge Repository; kodu, kararları, araştırmaları ve ürün vizyonunu tek bir hafızada tutar.

Amacı bilgi biriktirmek değil; alınan kararların gerekçesini, kanıtını ve yaşam döngüsünü izlenebilir kılmaktır.

---

## 2. Temel İlkeler

- Kod kadar karar da versiyonlanır.
- Her önemli kararın gerekçesi kayıt altına alınır.
- Hiçbir kayıt "unutulmak" için oluşturulmaz.
- Hiçbir karar değiştirilemez kabul edilmez.
- Her karar gerektiğinde yeniden değerlendirilebilir.
- Bilgi uygulanmadan önce doğrulanır.
- Mimari, uygulamadan önce netleşir.

Boş alan olabilir; yanlış alan olmaz. Sahip, kanıt veya onay yoksa uydurulmaz — kayıt açık belirsizlikle bırakılır (LUMOS-0003 ruhu).

---

## 3. Repository Katmanları

| Katman | İçerik |
|--------|--------|
| **Technical Memory** | Kod, test, CI, güvenlik, release |
| **Product Memory** | Backlog, ADR, ürün kararları, mimari |
| **Research Memory** | Benchmark, PoC, deneyler, araştırmalar |
| **Vision Memory** | Uzun vadeli fikirler ve ürün aileleri |

Bir kayıt birden fazla katmana dokunabilir; ana katman tek seçilir, ilişkiler `Related ADR` / `Related Epic` ile bağlanır.

**İlgili kaynaklar:** [Karar Duvarı](docs/drafts/BACKLOG.md) · [Vizyon çekmecesi](docs/drafts/lumos-2040-vision-draft.md)

---

## 4. Status

```
Idea → Validated → Recorded → Needs Decision → Planned → In Progress → Implemented → Archived
```

| Status | Anlam |
|--------|-------|
| Idea | Fikir oluştu; henüz araştırma veya karar yok |
| Validated | Araştırıldı, doğrulandı veya ilk kanıt toplandı |
| Recorded | Hafızaya yazıldı; uygulama taahhüdü olmayabilir |
| Needs Decision | Owner, güvenlik veya ürün kararı bekliyor |
| Planned | Kapsam, owner ve kapanış koşulu net |
| In Progress | Aktif geliştirme veya doğrulama sürüyor |
| Implemented | Kod, test ve gerekiyorsa doküman tamam |
| Archived | Bilinçli kaldırıldı, ertelendi veya superseded |

Status yalnızca sürecin mevcut durumunu gösterir.

---

## 5. Maturity

| Seviye | Anlam |
|--------|-------|
| M0 | Concept |
| M1 | Research |
| M2 | Decision Candidate / Karar Adayı |
| M3 | Architecture Ready |
| M4 | Prototype / First Implementation |
| M5 | Production |

Maturity ürünün ne kadar olgun olduğunu gösterir. Status ile aynı şey değildir: bir kayıt `In Progress` olabilir ama henüz M4 olmayabilir; bir vizyon kaydı yıllarca `Recorded` kalıp M1'de durabilir.

---

## 6. Zorunlu Alanlar

| Alan | Açıklama |
|------|----------|
| Status | Lifecycle aşaması |
| Maturity | M0–M5 olgunluk seviyesi |
| Owner | Karar sahibi; bilinmiyorsa `Pending` |
| Reason | Kayıt neden var |
| Evidence | PR, test, doküman, log veya analiz linki |
| Related ADR | İlgili karar kaydı |
| Related Epic | Büyük iş paketi veya backlog başlığı |
| Review Date | Tekrar bakılacak tarih veya release kapısı |
| Supersedes | Geçersiz kıldığı önceki kayıt |

Alanlar başlangıçta boş olabilir; yanlış bilgi yasaktır. `Pending` veya boş alan, uydurma onaydan doğrudur.

---

## 7. Karar İlkesi

Repository'de olmak ≠ uygulanacak / öncelikli / değişmez.

Kayıt gerçek durumu yansıtır; gelecek planını garanti etmez. Bir kaydın varlığı uygulama taahhüdü değildir; `Implemented` olması da değişmezlik anlamına gelmez.

---

## 8. Gözden Geçirme

Bilgi unutulmaz. Kararlar kutsallaştırılmaz.

Gerekçe, kanıt ve yeni bilgilerle her kayıt yeniden değerlendirilebilir. `Needs Decision` ve `Planned` kayıtlar `Review Date` ile periyodik olarak gözden geçirilir; güvenlik ve trust konularında owner onayı olmadan `Planned`'a geçilmez.

---

## 9. Son İlke

Lumos yalnızca kodun değil; bilginin, kararların ve vizyonun da hafızasını oluşturur.

> **«Repository'nin amacı geçmişi korumak değil, gelecekte doğru karar almayı kolaylaştırmaktır.»**

---

## 10. Örnekler

| Konu | Katman | Status | Maturity | Not |
|------|--------|--------|----------|-----|
| NA-01 | Technical Memory | Needs Decision | M2 | Core güvenlik; koddan önce karar gerekir |
| AnchorUSB | Research Memory | Recorded veya Needs Decision | M2–M3 | Secure Device Framework altında |
| Trust Phase 4 | Technical Memory | Needs Decision | M2–M3 | Çatı başlık; alt maddeler `Planned` olabilir |
| Lumos Mobility | Vision Memory | Recorded | M1 | Uzun vadeli vizyon; uygulama taahhüdü değil |
| Product Families | Vision Memory | Recorded | M1 | Ürün aileleri için yön kaydı |

**Çapraz bağlantılar:** [Karar Duvarı](docs/drafts/BACKLOG.md) · [Vizyon çekmecesi](docs/drafts/lumos-2040-vision-draft.md)
