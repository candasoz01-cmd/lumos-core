# Internal Alpha Release Scope (G-24 / RB-09 / GAP-01)

> **Durum:** `[decision-approved]` — ekip onaylı Internal Alpha kapsam kilidi.
>
> **Belge ID:** G-24 · RB-09 (Alpha etiketleme) · GAP-01 (canonical release kapsamı)
>
> **Audience:** Internal Alpha yalnızca ekip; müşteri / pilot dışı.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md), [`public-repo-boundary.md`](memory/public-repo-boundary.md)

**Karar:** Internal Alpha release kapsamı bu belgede tanımlanır. [`LUMOS_V1_READINESS.md`](LUMOS_V1_READINESS.md) (web panel v1 **closed** 2026-06-12) ile çelişmez: v1 = üretim panel Faz A kapısı; Internal Alpha = bir sonraki **ekip-only foundation build** aşaması.

**Repo snapshot:** `main` @ `24bdbef` (#504 queue kapanış); CI yeşil.

---

## 1. Amaç

GAP-01 («canonical release kapsamı yok») kapanışı: README «early active development» ile uyumlu, ekip imzalı tek **Internal Alpha** kapsam belgesi. Kod veya yeni özellik taahhüdü **içermez**.

---

## 2. Aşama tanımı

| Terim | Anlam |
|-------|--------|
| **Pre-Alpha (Aşama 0)** | Bugünkü açık kaynak geliştirme build'i; resmi ücretli hizmet yok |
| **Lumos v1 (closed)** | Web panel Faz A — [`LUMOS_V1_READINESS.md`](LUMOS_V1_READINESS.md) §8 sign-off; prod `welockai.com/panel` |
| **Internal Alpha (Aşama 1)** | **Bu belge** — ekip-only; çekirdek yolculuk stabilizasyonu; foundation build etiketi |

Internal Alpha **yeni bir public release iddiası değildir**; README «official/professional release not published yet» ile uyumludur.

---

## 3. Kapsam — dahil (in scope)

| # | Bileşen | Internal Alpha beklentisi |
|---|---------|---------------------------|
| I1 | **Astro panel** (`ui/` → `/panel`) | Ekip içi günlük kullanım; Sınırlı mod + yerel görevler |
| I2 | **Yerel görevler [Yerel]** | Panel `localStorage` görev ekleme/düzenleme/listeleme — v1 davranışı korunur |
| I3 | **Köprü ile sohbet (opsiyonel)** | Yapılandırılmış dev/staging ortamında chat gönder/al; prod Sınırlı mod ayrı izlenir |
| I4 | **Yerel CLI / görev motoru** | Ekip geliştirme akışı (`make test`, yerel `.lumos/` state) |
| I5 | **CI kalite kapısı** | `ruff`, `pytest`, UI smoke/E2E — merge öncesi yeşil |
| I6 | **Erken geliştirme etiketi** | README + panel «early active development» / Sınırlı mod — RB-09 karşılandı |
| I7 | **ADR-012 Alpha defer** | [`adr-012-internal-alpha-defer-record.md`](memory/adr-012-internal-alpha-defer-record.md) — CLOSED beklenmez |

---

## 4. Kapsam — hariç (out of scope)

| # | Bileşen | Neden dışarıda |
|---|---------|----------------|
| O1 | **Entegrasyonlar (mail, takvim, cihaz, ödeme)** | Public stub / private katman; Alpha vaadi yok |
| O2 | **Production vault / secret yönetimi** | Demo-safe stub; OD-001–005 implementation-pending |
| O3 | **Checkout / PSP / fatura** | OD-011 implementation-pending; tahsilatsız Alpha |
| O4 | **Packaged end-user installer** | README: yok; RB-06 defer |
| O5 | **Closed Pilot / müşteri daveti** | Alpha çıkış sonrası aşama |
| O6 | **Wave 2+ ADR-012 enforcement** | Trust Faz 4, default-on, sensitivity↔gate, Panel LockState — ayrı onay |
| O7 | **Tam modül menüsü iddiası** | ROADMAP iskelet modüller; nav «Henüz aktif değil» rozeti (#503, RB-17 kısmi) |
| O8 | **Native app / offline-first / SW** | v1 + MOBILE_PHASE_0 dışı |

---

## 5. README vs v1-readiness hizası (GAP-01)

| Kaynak | İddia | Internal Alpha ile ilişki |
|--------|-------|---------------------------|
| `README.md` | Early active development; official release not published | **Uyumlu** — Alpha ekip-only, public iddia genişletilmez |
| `LUMOS_V1_READINESS.md` | v1 web panel **closed** (Faz A) | **Uyumlu** — v1 prod kapısı korunur; Alpha v1'i geri açmaz |
| Bu belge | Internal Alpha foundation build | v1 sonrası **iç** stabilizasyon aşaması |

Kullanıcı yüzünde «v2» veya «Alpha download» **ilan edilmez**.

---

## 6. Alpha giriş kriterleri eşlemesi

| Kriter | Durum (bu belge + #500 sonrası) |
|--------|----------------------------------|
| A1 Ekip release kapsamı yazılı | **Kapandı** — bu belge |
| A2 CI yeşil | **Tamam** — `main` CI success |
| A3 P0/P1 triage listesi | **Kapandı** — [p0-p1-triage-list.md](analysis/p0-p1-triage-list.md) (G-23) |
| A4 README / panel alpha etiketi | **Tamam** — RB-09 |
| A5 ADR-012 Alpha defer | **Kapandı** — G-18 defer #500 |

**Alpha giriş:** A1 + A3 + A5 kapandı; çekirdek yolculuk tekrarı (P1-02) Alpha **çıkış** kriteri.

---

## 7. Alpha çıkış hedefleri (referans)

Çıkış doğrulaması bu belgenin kapsamı dışında operasyonel takip edilir:

- Çekirdek yolculuk ≥2 hafta ekip içi tekrarlanabilir (panel → görev; ± köprü sohbet)
- P0 = 0; P1 kapatıldı veya Pilot defer
- Release checklist mevcut — [`GITHUB_RELEASE_CHECKLIST.md`](GITHUB_RELEASE_CHECKLIST.md) (RB-07)
- ADR-012 **CLOSED şart değil** (defer kaydı yeterli)

---

## 8. Ekip onayı (sign-off)

| Rol | Onay | Tarih | Repo ref |
|-----|------|-------|----------|
| Ürün / release sahibi | Onaylandı — Internal Alpha kapsam kilidi | 2026-06-21 | `24bdbef` |
| Docs PR | Kapandı — #501 merge | 2026-06-21 | `24bdbef` |

**Sign-off koşulu:** Merge sonrası G-24 «yazılı Internal Alpha release kapsamı» **kapandı** sayılır.

---

## 9. Çapraz referanslar

| ID | Bağlantı |
|----|----------|
| G-18 | [`adr-012-internal-alpha-defer-record.md`](memory/adr-012-internal-alpha-defer-record.md) |
| G-23 | [p0-p1-triage-list.md](analysis/p0-p1-triage-list.md) |
| G-24 | Bu belge |
| RB-09 | [`release-blockers.md`](analysis/release-blockers.md#rb-09--readme-kararlı-oss-ürün-iddiası-yok) |
| v1 | [`LUMOS_V1_READINESS.md`](LUMOS_V1_READINESS.md) |

---

*Son güncelleme: 2026-06-21 — docs only.*
