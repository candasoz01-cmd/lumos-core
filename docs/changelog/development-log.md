# Development Log — Panel (kronolojik)

Kısa kronolojik kayıt. Detaylı günlük: `docs/journal/`.

---

## 2026-06-05

Panel sohbet akışı ve Görevler/Kayıtlar görünürlüğü üzerinde ardışık iyileştirmeler (PR #60–#66 merge).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | #60 | Chat cevap kartı + hızlı işlem çubuğu |
| 2 | #61 | Quick-action audit düzeltmeleri |
| 3 | #62 | Chat input + dosya/medya menüsü |
| 4 | #63 | Kullanıcı mesajı aksiyonları |
| 5 | #64 | Chat aksiyon feedback standardı |
| 6 | #65 | Chat ekranı boş / bekleme / hata durum standardı |
| 7 | #66 | Görevler/Kayıtlar görünürlüğü — merge edildi |

**Not:** Jilee ürüne aktarılmadı. AI Gateway analizi beklemede.

---

## 2026-06-05 / 2026-06-06

Panel quality tour — ana sol menü ekranları görünürlüğü ve audit polish (PR #69–#73 merge; base `main` @ f5fc985).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | #69 | Sistem Durumu / Koruma görünürlüğü — topbar rozetleri, demo seçiciler, `#system` genel bakış |
| 2 | #70 | Korunalı Alan / Anahtar Kasası görünürlüğü — `#sandbox`, `#keystore` genel bakış ve durum rozetleri |
| 3 | #71 | Yapılandırma / Kimlik görünürlüğü — `#config`, `#identity` genel bakış; pasif `yakında` aksiyonlar |
| 4 | #72 | Akış / Gösterge Paneli görünürlüğü — `#feed`, `#dashboard` genel bakış, boş durumlar, köprü-aware metin |
| 5 | #73 | Panel audit polish — chat offline bilgi mesajı, dashboard metni, 320px overflow, trash `console.log` kaldırma |

**Durum:** Ana sol menü ekranları büyük ölçüde toparlandı.

**Kalan:** Mobil/dar ekran polish (`#system` 320px audit notu); gerçek backend entegrasyonları (ileride).

**Not:** Mail/Inbox Intelligence gelecek fikir düzeyinde — uygulanmadı. Jilee ürüne aktarılmadı. AI Gateway analizi beklemede.

---

## 2026-06-06

ADR-008 agent/task/executor usage map revizyonu tamamlandı (PR #87 merge; docs-only; `main` @ `7e7dd8b`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#87](https://github.com/candasoz01-cmd/lumos-core/pull/87) | ADR-008 usage map — agent/task/executor kullanım haritası eklendi |

**Kapsam:** Yalnızca `docs/decisions/ADR-008-agent-network-boundary.md`; kod değişikliği yok.

---

## 2026-06-06

CI pytest kapısı gerçek kırmızı/yeşil sinyale alındı (PR #89 merge; `main` @ `60cf4fd`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#89](https://github.com/candasoz01-cmd/lumos-core/pull/89) | CI pytest `continue-on-error` kaldırıldı; `video_executor` testleri için `requests` bağımlılığı düzeltildi |

**Kapsam:** CI workflow + test bağımlılığı; CI artık gerçek red/green sinyali veriyor.

---

## 2026-06-06

`requirements.txt` dependency tekrarı temizlendi (PR #91 merge; `main` @ `0083d17`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#91](https://github.com/candasoz01-cmd/lumos-core/pull/91) | Gereksiz `requests` satırı `requirements.txt`'ten kaldırıldı; CI inline kurulum düzeni korundu |

**Kapsam:** Yalnızca `requirements.txt`; `requests` zaten `kando_runtime` transitif bağımlılığı ve CI workflow inline kurulumunda mevcut — drift riski azaltıldı.

---

## 2026-06-06

CI dependency kurulumu tek manifest kaynağına alındı (PR #93 merge; `main` @ `f7de2f7`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#93](https://github.com/candasoz01-cmd/lumos-core/pull/93) | Inline `pip install pytest cryptography openai requests` kaldırıldı; CI artık `pip install -r requirements.txt` kullanıyor |

**Kapsam:** Yalnızca `.github/workflows/ci.yml`; PYTHONPATH ve test adımları aynı — dependency drift riski azaltıldı.

---

## 2026-06-07

Makefile test/check CI pytest env ile hizalandı (PR #95 merge; `main` @ `aca679b`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#95](https://github.com/candasoz01-cmd/lumos-core/pull/95) | `make test` ve `make check` artık `TEST_PYTHONPATH` (src + kando_runtime + kando_bridge) ve `KANDO_MOCK=1` kullanıyor |

**Kapsam:** Yalnızca `Makefile`; yerelde 565 passed, 2 skipped.

---

## 2026-06-07

Cando `branch-cleanup-review` read-only dry-run recipe MVP (PR #97 merge; `main` @ `b6235a0`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#97](https://github.com/candasoz01-cmd/lumos-core/pull/97) | `branch-cleanup-review` read-only dry-run recipe MVP — dal temizliği önizlemesi; silme yapmaz |

**Komut:** `python scripts/cando_local.py recipe branch-cleanup-review --dry-run`

**Kapsam:** Read-only; dal silmez. Yerelde 568 passed, 2 skipped.

**Sonraki adım (henüz yok):** continuity / registry / run-history ileride değerlendirilebilir — bu PR'da uygulanmadı.

---

## 2026-06-11

PR #145 merge, prod deploy ve smoke sign-off (`welockai.com`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | #145 | Merge edildi |

**Deploy:** Prod deploy `welockai.com` üzerinde tamamlandı.

**Smoke:** Desktop/prod PASS; mobil viewport PASS. iPhone 13 viewport ile mobil Kuantum/roadmap/harita ve kısayol kontrolü geçti.

**Sonuç:** Ek düzeltme gerekmiyor.

---

## 2026-06-11

V1 readiness §6 zorunlu maddeler PASS (PR #142 merge; docs-only; `main` @ `791d9f1`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#142](https://github.com/candasoz01-cmd/lumos-core/pull/142) | V1 readiness §6 — zorunlu maddeler 7/7 PASS olarak main'e girdi |

**Kapsam:** Yalnızca `docs/LUMOS_V1_READINESS.md`; ürün kodu değişmedi.

**Not:** Opsiyonel tam-mod operatör maddeleri açık kaldı; public v1 için blokaj yok.

---

## 2026-06-11

Quantum docs status netliği (PR #144 merge; docs-only; `main` @ `541819b2`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#144](https://github.com/candasoz01-cmd/lumos-core/pull/144) | PR #144 merge edildi — Quantum docs main'e girdi |

**Kapsam:** README, ROADMAP ve `docs/*` güncellendi; ürün kodu değişmedi.

**Durum:** Açık PR kalmadı.

---

## 2026-06-12

Main hash hizalama / readiness sync (PR #149 merge; `main` @ `f5d99b5`).

| Sıra | PR | Özet |
|------|-----|------|
| 1 | [#149](https://github.com/candasoz01-cmd/lumos-core/pull/149) | §6 smoke hash (`9c4d025`) traceability hizası — merge edildi |

**Kapsam:** Yalnızca docs hash hizalama; PR #149 ≠ §8 kapanış sign-off.

**Repo:** `main` `origin/main` ile hizalı.

**Durum:** Açık PR kalmadı.
