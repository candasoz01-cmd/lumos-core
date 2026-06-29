# WeLockAI · Lumos — karar günlüğü (taslak)

> **Çatı:** WeLockAI yayıncı ve kurumsal çatı; Lumos ürün ve referans içeriği bu çatı altında. Bu dosya proje tarihçesidir — sohbet değil, tarihli karar kaydı (bkz. `docs/lumos-book-outline.md` Belge §10).

## Sıralama kuralı

- Ters kronoloji: en yeni üstte
- Aynı gün: Lansman → Ürün → Mimari → Politika
- DONDURULDU / tag blokları günlük kararların üstünde ayrı tutulur

## Durum etiketleri

| Etiket | Anlam |
|--------|-------|
| 🟢 AKTİF | Geçerli, uygulanıyor |
| 🟡 TEST | Pilot / deneme |
| 🔴 İPTAL | Vazgeçildi |
| 🔒 DONDURULDU | Beklemede / değişmez çapa |
| 🚀 YAYINLANDI | Metne veya ürüne geçti |

## 🔒 DONDURULDU

**lumos-book-v0.1** (`0799c34`): `docs/lumos-book-outline.md` bu sürüme yeni fikir eklenmez. Yeni bölüm / vizyon / manifesto fikirleri yalnızca backlog'a veya yeni taslak dosyasına gider.

## Merged taslaklar

| Durum | Bölüm | Dosya | Not |
|-------|--------|-------|-----|
| Merged | §14 – Lumos Academy (Uzun Vadeli Vizyon) | [`section-14-lumos-academy-vision.md`](./section-14-lumos-academy-vision.md) (arşiv) | `lumos-book-outline.md` §14 — V1 dışı · taslak arşivde |

## İleride — karar kimliği (ADR-lite)

Karar sayısı arttıkça arama ve izlenebilirlik için kısa kimlik şeması (ADR-lite) pilot edilir.

**Önerilen alanlar:** ID (LUMOS-NNNN), Tarih, Durum, Karar, Gerekçe, Etkilenen dosyalar, Son güncelleme.

- Aynı karar evrildiğinde **aynı ID** korunur; geçmiş git diff'te kalır.
- Yalnızca **gerçekten yeni** kararlar yeni ID alır.

**Durum:** değerlendirme — pilot başladı, tam şema ileride.

Tam şema taslağı: [decision-engine-schema.md](./decision-engine-schema.md)

## Aktif kararlar

```
ID: LUMOS-0005
[2026-06-28] 🟢 AKTİF
Karar: Belirsizlik hata değildir; gizlenen belirsizlik hatadır. Hakem rolü susmak veya kesin konuşmak değil; ikilemi açık tutmaktır. Karar net değilse ikilem gizlenmez: seçenek A/B (artıları ve riskleri), Lumos değerlendirmesi, güven düzeyi (confidence) ve belirsizlik açıkça sunulur; nihai karar kullanıcıya aittir.
Gerekçe: Sahte kesinlik veya sessizlik güveni zedeler; dürüst karar hafızası belirsizliği görünür kılar, boş veya yanlış alan üretmez (bkz. LUMOS-0003).
Uygulama: Decision Engine ve hakem modeli — belirsiz kararlarda A/B şablonu; confidence ve uncertainty alanları doldurulur veya bilinçli boş bırakılır; son söz kullanıcıda.
İlişkili kararlar: LUMOS-0003
Decision level: L2 (hakem modeli, Decision Engine davranışı)
Etkilenen dosyalar: docs/drafts/decision-engine-schema.md, docs/drafts/BACKLOG.md
Son güncelleme: 2026-06-28
```

```
ID: LUMOS-0003
[2026-06-28] 🟢 AKTİF
Karar: Karar kayıtları zengin alan seti taşıyabilir (Proposed by, Reviewed by, Technical/Security/Accessibility/Privacy review, Risk level, Confidence, Evidence, Related decisions, Supersedes, Superseded by, Effective from, Last reviewed, Review due, Status, Decision level L0–L4); gün birinde çoğu alan boş kalabilir. Onay bütünlüğü: uydurma onaylayıcı yasak — «Approved by: OpenAI» veya «WeLockAI Board» gibi gerçek olmayan değerler yazılmaz. İzinli örnekler: Pending, Project Owner, Core Team (yalnızca gerçekten onaylandıysa). Çekirdek kural: **Boş alan olabilir, yanlış alan olmamalı.** İleride 30–40 anlamlı ve doğrulanabilir kaynaklı alan kabul edilir.
Gerekçe: Karar hafızası güvenilir olmalı; eksik bilgi boş bırakılır, sahte onay veya kurul adı üretilmez.
Uygulama: `docs/drafts/decision-engine-schema.md` alan kataloğu ve onay bütünlüğü bölümü; yeni kayıtlarda alanlar yalnızca kanıtlandığında doldurulur.
Etkilenen dosyalar: docs/drafts/decision-engine-schema.md, docs/drafts/BACKLOG.md
Son güncelleme: 2026-06-28
```

```
ID: LUMOS-0001
[2026-06-28] 🟢 AKTİF
Karar: Engelli modu lansmanda görünür; temel erişilebilirlik özellikleri ücretsiz açık belirtilir; küçük ve hedef odaklı değişiklik politikası korunur.
Gerekçe: Kullanıcının ilk gördüğü anda Lumos'un sosyal faydası anlaşılmalı.
Uygulama: Belge §12 lansman metinleri — v0.1 outline'a doğrudan ekleme yok; v0.2 veya ayrı commit.
Etkilenen dosyalar: docs/lumos-book-outline.md Belge §12 (v0.2+)
Son güncelleme: 2026-06-28
```

```
ID: LUMOS-0002
[2026-06-28] 🟢 AKTİF
Karar: Yerelleştirme (TR arayüz) erişilebilirlik omurgasının parçasıdır; sonradan eklenen süs değil. Panel / arayüz çok dilli sunum Belge §12 🌍 Dil engeli ile hizalı.
Gerekçe: Kullanıcı kendi dilinde rahat hissetmeli; anlaşılır ve erişilebilir olmak özellik kadar önemli.
Uygulama: Belge §12 dil engeli tablosu; lansman metinlerinde dil/erişilebilirlik birlikte düşünülür — v0.1 outline'a doğrudan ekleme yok.
Not: Kurucu kişisel tercih — «TR arayüz gelmeden aktif kullanmama» — ürün hedefi ile uyumlu; teknik zorunluluk değil.
Etkilenen dosyalar: docs/lumos-book-outline.md Belge §12 (v0.2+)
Son güncelleme: 2026-06-28
```

**Kural:** Backlog maddeleri web/lansman/yayımlandı indeksine Belge §11 onayı olmadan taşınmaz; v0.1 dondurulmuşken yeni fikirler outline'a yazılmaz.
