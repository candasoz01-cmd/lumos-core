# WeLockAI · Lumos — Decision Engine (taslak şema)

> Kod ve model değişir; karar ağacı kalır.

## Amaç

Backlog listesinden karar sistemine: izlenebilir, ilişkili, katmanlı karar hafızası. Yeni ajan sadece son kararı değil; neden, bağlam, iptal zincirini okur.

## Çekirdek bütünlük kuralı

> **Boş alan olabilir, yanlış alan olmamalı.**

- Gün birinde çoğu alan boş kalabilir; eksik bilgi boş bırakılır.
- Alan yalnızca doğrulanabilir kaynak varsa doldurulur (toplantı notu, PR, onay kaydı, gerçek kişi/kurul).
- İleride 30–40 anlamlı alan kabul edilir; her alanın tanımı ve kaynağı net olmalıdır.

## Onay bütünlüğü (approval integrity)

**Yasak:** Uydurma onaylayıcı veya kurul adı — örn. `Approved by: OpenAI`, `WeLockAI Board` — gerçek onay kaydı yoksa yazılmaz.

**İzinli değerler (örnek):**

| Değer | Ne zaman |
|-------|----------|
| **Pending** | Onay bekleniyor; henüz kimse onaylamadı |
| **Project Owner** | Proje sahibi gerçekten onayladıysa |
| **Core Team** | Çekirdek ekip gerçekten onayladıysa |
| *(boş)* | Onay süreci başlamadı veya bilinmiyor |

**Review alanları** (Technical, Security, Accessibility, Privacy): aynı kural — `Pending`, gerçek onaylayıcı adı, veya boş. «Reviewed» yazıp kişi uydurma.

Kayıt: [LUMOS-0003](./BACKLOG.md) (BACKLOG).

## Karar kaydı — alan kataloğu

### Kimlik ve durum

| Alan | Açıklama |
|------|----------|
| **ID** | LUMOS-NNNN — sabit; güncellemede aynı ID |
| **Decision level** | L0–L4 (katman; aşağı) |
| **Status** | 🟢 AKTİF · 🟡 TEST · 🔴 İPTAL · 🔒 DONDURULDU · 🚀 YAYINLANDI |
| **Tarih** | İlk kayıt |
| **Son güncelleme** | Son revizyon |
| **Last reviewed** | Son gözden geçirme tarihi |
| **Review due** | Sonraki gözden geçirme hedefi |

### İçerik

| Alan | Açıklama |
|------|----------|
| **Karar** | Ne kararlaştırıldı |
| **Gerekçe** | Neden |
| **Evidence** | Kanıt: link, PR, test, toplantı notu |
| **source** | Kaynak türü: insan, Cursor, Lumos… |
| **basis** | Dayanak: toplantı, test, geri bildirim… |
| **Etkilenen dosyalar / sürümler** | Path veya tag |

### Onay ve inceleme

| Alan | Açıklama |
|------|----------|
| **Proposed by** | Öneren (kişi veya rol — gerçekse) |
| **Reviewed by** | İnceleyen (gerçekse; yoksa boş veya Pending) |
| **Technical review** | Teknik inceleme durumu / onaylayan |
| **Security review** | Güvenlik inceleme durumu / onaylayan |
| **Accessibility review** | Erişilebilirlik inceleme durumu / onaylayan |
| **Privacy review** | Gizlilik inceleme durumu / onaylayan |
| **approved_by** | Nihai onaylayan (bkz. onay bütünlüğü) |

### Risk ve güven

| Alan | Açıklama |
|------|----------|
| **Risk level** | Düşük · Orta · Yüksek · Kritik (tanımlı ölçek) |
| **Confidence** | Deneysel · Onaylı · Çekirdek |
| **reversible** | evet / hayır |

### İlişki ve yaşam döngüsü

| Alan | Açıklama |
|------|----------|
| **Related decisions** | İlgili karar ID'leri |
| **supersedes** | Bu kaydın geçersiz kıldığı ID |
| **superseded_by** | Bu kaydı geçersiz kılan ID |
| **effective_from** | Geçerlilik başlangıcı (sürüm, tag veya tarih) |
| **retired_in** | Emekliye ayrılma (sürüm, tag veya tarih) |
| **relations** | spawned · cancelled · updated_by — ID listesi |

**Not:** Pilot aşamada BACKLOG yalnızca temel alanları taşır; katalog hedef şemadır. Boş alan normaldir.

## Katmanlar (L0 → L4)

| Katman | Ad | Değişmezlik | Örnek |
|--------|-----|-------------|-------|
| **L0** | Kurucu ilkeler | Çok zor | İnsan odaklı; güvenlikten taviz yok; belirsizse eminim demez; erişilebilirlik temel değer |
| **L1** | Ürün kararları | Zor | Lansman; premium; ücretsiz özellikler |
| **L2** | Mimari kararları | Orta | Decision Engine; router; hafıza yapısı |
| **L3** | Uygulama kararları | Normal | Dosya, API, klasör |
| **L4** | Geçici deneyler | Kolay | A/B; pilot; deneme |

**Kural:** L3 değişebilir; L0'a dokunulmaz (onay + ADR zorunlu).

## İlişki modeli

```
Karar A
  ├── spawned    → B, E        (A'dan türeyen yeni kararlar)
  ├── cancelled  → C            (A ile iptal edilen kararlar)
  └── updated_by → D            (A'yı revize eden karar)
```

- **spawned:** A kararı yeni bir karar doğurdu.
- **cancelled:** A, listedeki başka bir kararı geçersiz kıldı.
- **updated_by:** A'nın içeriği D tarafından güncellendi; A aynı ID ile kalır veya supersedes zinciri kurulur.

## Pilot (bugün)

| Kaynak | Örnek | Katman |
|--------|-------|--------|
| [`BACKLOG.md`](./BACKLOG.md) | LUMOS-0001 — lansman erişilebilirliği | L1 |
| [`BACKLOG.md`](./BACKLOG.md) | LUMOS-0002 — yerelleştirme omurgası | L1 |
| [`BACKLOG.md`](./BACKLOG.md) | LUMOS-0003 — onay bütünlüğü / alan kataloğu | L2 |
| lumos-book-v0.1 (`0799c34`) | 🔒 dondurulmuş omurga | — |
| [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) | L0 referans adayı (çekirdek sözleşme — ayrı katman) | L0 |

## Uygulama fazları

1. **Şimdi:** BACKLOG + ID pilot (LUMOS-NNNN, temel alanlar)
2. **Sonra:** tam alan seti; supersedes / relations; confidence ve katman etiketi
3. **İleride:** Lumos / ajan okuma yüzeyi (ürün — public boundary dikkat)

## Sınırlar

- Bu belge **vizyon ve hedef şema**dır; ürün kodu değildir.
- **Status:** taslak — motor yok, otomasyon yok.
- Public repo sınırı: karar hafızası demo-safe kalır; özel orchestration / operasyonel backend bu şemaya taşınmaz.
