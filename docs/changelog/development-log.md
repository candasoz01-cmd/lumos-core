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
