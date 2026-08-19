# ADR-027 — Kontrollü çekirdek yazıcısı

> 2026-08-19 kurucu yönlendirmesi: Lumos çekirdeği «her ajan yazar» modeli
> değildir; tek-yazıcı / kontrollü-yetki modelidir. Gelişim motoru özgür
> olabilir; çekirdeğe yazma ve yetki genişletme anayasal olarak sıkıdır.
> **Bu ADR kod yazma izni değildir.** Lumos writer, değerlendirme katmanı
> veya otomasyon borusu bu belgeden uygulanmaz.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (mimari, 2026-08-19)** — hedef boru kilitli; kod sırasına girmez |
| Uygulama durumu | Uygulanmadı — kontrollü writer yok; bugün `main`'e yazma GitHub merge + geçici insan kapısı |
| Tarih | 2026-08-19 |
| Üst ilişki | [CONSTITUTION §11](../CONSTITUTION.md); [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) N8 (otorite kendine yetki üretemez); [ADR-012](ADR-012-lumos-security-codex.md) tek dış kapı; [CONTRIBUTING.md](../../CONTRIBUTING.md) § Merge gate |

## Karar

Hedef boru:

```text
Araştırmacılar / dış ajanlar
  → Lumos değerlendirme katmanı
      (politika, güvenlik, test, mimari sözleşme, yetki sınırı)
  → Lumos güvenlik / test kapıları
  → tek Lumos writer
  → main
```

Dış modeller (Claude, Cursor, Codex ve diğerleri) çekirdeği **sahiplenmez**.
Araştırır, önerir, patch/diff üretir, test eder. Onaylanan değişikliği
çekirdeğe yazan taraf Lumos'un kendi kontrollü writer'ıdır.

İnsan her typo'da merge düğmesine basan kişi **değildir**. İnsan;
anayasanın, yetki sınırlarının ve yüksek-risk istisnalarının **nihai
otoritesidir**.

«Kendi kendini geliştirir» ≠ «kendi kendine sınırsız yetki verir.»
Öğrenme adayları (yeni modeller, API'ler, açıklar, teknikler, maliyet)
dışarıdan taranır, kabiliyet envanteriyle karşılaştırılır, deney/branch'te
ölçülür; kapıları geçince çekirdeğe yükselir. Aşağıdakileri Lumos **tek
başına** yapamaz:

- kendi güvenlik politikasını gevşetmek
- kendi yazma yetkisini genişletmek
- kendi onay mekanizmasını kaldırmak

Bunlar [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) N8'in
çekirdek-yazma karşılığıdır: güven kökü kendi lehine karar veren aktöre
dönüşmez.

## Bugünkü geçici rejim (2026-08-19)

Kontrollü writer henüz yok. Bu boşlukta `main` üç kapıyla korunur
([CONTRIBUTING.md](../../CONTRIBUTING.md)):

| Hedef katman | Bugünkü vekil |
| --- | --- |
| Test kapısı | GitHub Actions `ci.yml` CheckRun'ları |
| Güvenlik kapısı | Cursor Security Reviewer CheckRun (`Cursor Security Agent: Security Reviewer`) |
| Kontrollü writer + yüksek-risk otorite | Yetkili insan maintainer; ajan/bot review sayılmaz |

«İnsan her PR'ı merge eder» kalıcı mimari değildir; writer var olana kadar
güvenli rejimdir. Onay, o anki head SHA'ya bağlıdır; head değişince sayaç
sıfırlanır.

Cursor Security Reviewer bir Git tabanlı automation'dır (Marketplace
şablonunda **PR Opened** + **PR Pushed**). `PR opened` draft açılışı
kapsamaz; draft → ready olunca ateşlenir. `PR pushed` yalnız *mevcut* PR'a
yeni commit'te ateşlenir. Draft kalıp push gelmezse CheckRun doğmayabilir
(`candasoz01-cmd/lumos-core#764` · `e73b23dc` · Checks API · 2026-08-19T18:09Z).
Bu, kapı 2'nin «yok = pending» okumasını doğrular; Cursor yavaşlığı değildir.

`layer1a.yml` ve `prod-smoke.yml` merge kapısı değildir.

## Bilinçli yapılmaz

- Lumos writer / değerlendirme motoru kodu
- Anayasa, güvenlik politikası veya onay mekanizmasını ajan eliyle gevşetmek
- Branch protection Settings (admin; beş `ci.yml` işi + Security Reviewer)
- Draft PR'ı tetik deneyi için ready yapmak (insan; SHA aynı kalır)

## İlişkili

- [AGENTS.md](../../AGENTS.md) — ajanlar önerir, merge etmez, writer sayılmaz
