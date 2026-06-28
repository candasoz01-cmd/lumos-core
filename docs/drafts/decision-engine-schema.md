# WeLockAI · Lumos — Decision Engine (taslak şema)

> Kod ve model değişir; karar ağacı kalır.

## Amaç

Backlog listesinden karar sistemine: izlenebilir, ilişkili, katmanlı karar hafızası. Yeni ajan sadece son kararı değil; neden, bağlam, iptal zincirini okur.

## Karar kaydı — hedef alanlar

| Alan | Açıklama |
|------|----------|
| **ID** | LUMOS-NNNN — sabit; güncellemede aynı ID |
| **Katman** | L0–L4 (aşağı) |
| **Tarih** | İlk kayıt |
| **Son güncelleme** | Son revizyon |
| **Durum** | 🟢 AKTİF · 🟡 TEST · 🔴 İPTAL · 🔒 DONDURULDU · 🚀 YAYINLANDI |
| **Karar** | Ne kararlaştırıldı |
| **Gerekçe** | Neden |
| **source** | Kim: insan, Cursor, Lumos… |
| **basis** | Toplantı, test, geri bildirim… |
| **Etkilenen dosyalar / sürümler** | Path veya tag |
| **supersedes** | Hangi ID geçersiz kılındı |
| **reversible** | evet / hayır |
| **confidence** | Deneysel · Onaylı · Çekirdek |
| **approved_by** | Onaylayan |
| **effective_from** | Geçerlilik başlangıcı (sürüm veya tag) |
| **retired_in** | Emekliye ayrılma (sürüm veya tag) |
| **relations** | spawned · cancelled · updated_by — ID listesi |

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
