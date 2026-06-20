# OD-013/014/015 — Görsel üretim ve chat görsel destek kararı (taslak)

**Durum:** **`decision-approved`** (kapsam ilkesi) / **`implementation-pending`** (UX ve teknik pilot).  
**Kaynak OD:** OD-013 (`ui-chat-experience.md`), OD-014 (chat görsel UX), OD-015 (`voice-media-experience.md` — UI ile birleşik).  
**Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md); public GitHub boundary.

---

## 1. Birleşik kapsam kararı

| Soru | Onaylı cevap |
|------|----------------|
| Chat içinde image generation ürün kapsamına girer mi? | **Evet — sınırlı kapsamda** (OD-013). Kullanıcı onaylı, görev kapsamlı görsel üretim **desteklenen** ürün yönüdür; varsayılan kapalı değil, **opt-in + onay kapısı** ile açılır. |
| Görsel destek UX modeli | **Kart/mesaj hizası** (OD-014): metin sohbet akışı içinde görsel kart; mock ≠ gerçek kanıt kuralı geçerli. |
| Ses dokümanı görsel beklentisi | **OD-015 → OD-013/014'e merge** — tek canonical karar kaynağı bu belgedir; `voice-media-experience.md` çapraz referans verir, ayrı çelişkili karar tutmaz. |

**Kapsam dışı (public repo):** API key, provider credential, production görsel pipeline, NSFW/policy bypass.

---

## 2. Onaylı ilkeler

| # | İlke |
|---|------|
| VG1 | Görsel üretim **Lumos geçidi** arkasında; dış provider doğrudan kullanıcıya açılmaz. |
| VG2 | **Kullanıcı onayı + görev kapsamı** zorunlu; sessiz arka plan üretimi yok. |
| VG3 | Üretilen görseller **gerçek kanıt** ile raporlanır; mock ekran gerçek çıktı gibi sunulmaz. |
| VG4 | Kamera/foto düzenleme (OD-016/017) **ayrı karar** — bu belge yalnızca **chat içi üretim** kapsamındadır. |
| VG5 | Public repoda provider detayı, prompt şablonu secret veya PII taşımaz. |

---

## 3. Implementation-pending

| Konu | Durum |
|------|--------|
| Provider seçimi (OpenAI Images vb.) | implementation-pending |
| Kart/mesaj UX wireframe | implementation-pending |
| Onay kapısı + yetki profili eşlemesi | implementation-pending — OD-012/041 hizası |
| Ses modunda görsel istek yönlendirmesi | implementation-pending — `voice-media-experience.md` sync |

---

## 4. OD eşleme

| OD | Durum | Not |
|----|--------|-----|
| **OD-013** | decision-approved / implementation-pending | Bu belge §1 |
| **OD-014** | decision-approved / implementation-pending | §1 kart/mesaj |
| **OD-015** | **closed (merge)** | OD-013/014 altında birleşik |

---

## 5. Sonraki adım

1. UX spesifikasyonu (kart modeli) — ayrı docs/ürün paketi.
2. Public-safe pilot yalnızca onaylı impl paketinde; **bu belge kod izni vermez**.

---

Son güncelleme: 2026-06-20 (envanter ab791c14 §10/§12 — Phase 2)
