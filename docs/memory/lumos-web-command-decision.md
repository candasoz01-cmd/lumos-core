# OD-028 — `lumos web` / eksik `web/app.py` karar belgesi

**Durum:** `[implemented]` — **B1 (alt komutu kaldır)** uygulandı (2026-06-17). `web/app.py` restore edilmedi.  
**Kaynak indeks:** [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) OD-028.  
**Çapraz referans:** OD-027 (`packages/kando_*` geçişi), OD-043 / OD-046 (panel/ui/frontend yüzeyleri).  
**Doğrulama tarihi:** 2026-06-17 (repo read-only tarama).  
**Karar tarihi:** 2026-06-17 — B1 onaylandı.

---

## 1. Amaç

Root `lumos` CLI içindeki **`web` alt komutunun** ve hedef dosya **`web/app.py`** ile repo gerçekliği arasındaki uyumsuzluğu netleştirmek; **restore** (geri yükleme) ile **kaldırma** seçeneklerini kanıta dayalı değerlendirmek.

**Seçilen yön (2026-06-17):** **B1 — alt komutu kaldır.** `web/app.py` restore edilmeyecek.

Bu belge:

- **Karar belgesidir** — seçim kayıtlıdır; **uygulama ayrı görevdir** (§12.2).
- **B1 uygulandı** — `lumos web` alt komutu `__main__.py`'den kaldırıldı.
- Çekirdek sözleşme ([`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md)) üst sınır olarak geçerlidir.

---

## 2. Kapsam dışı olanlar

| Madde | Neden kapsam dışı |
|-------|-------------------|
| `panel/`, `ui/`, `frontend/` birincil yüzey seçimi | OD-043, OD-046 — ayrı karar belgeleri; `lumos web` ile karıştırılmaz |
| `packages/kando_*` → `src/` geçişi | OD-027 — [`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md) |
| `backend/` Express API, `api/bridge/` Vercel proxy | Ayrı HTTP yüzeyleri; `web/app.py` minimal read-only sunucu modelinden farklı |
| `web/` dizini oluşturma veya `web/app.py` restore uygulaması | **B1 seçildi** — restore yok; uygulama §12.2'de |
| Diğer `docs/memory/*.md` dosyalarının güncellenmesi | Uygulama paketi (§12.2) — indeks senkronu uygulama sonrası |
| `packages/kando_core` içindeki benzer `web` alt komutu | Aday paket; kök `lumos` canlı entry değil |

---

## 3. Mevcut CLI gerçekliği

### 3.1 Kök entry point (`pyproject.toml`)

```toml
[project.scripts]
lumos = "lumos_core.__main__:main"

[tool.setuptools]
package-dir = { "" = "src" }
```

- Proje açıklaması: `"Lumos core CLI and read-only web"` — web yüzeyi hâlâ ürün tanımında anılıyor.
- Eski/hatalı not: `lumos_core.main:main` — **geçersiz**; `src/lumos_core/main.py` yok.

### 3.2 Canlı CLI zinciri (repo-verified)

```
lumos  (veya python -m lumos_core)
  → src/lumos_core/__main__.py : main()
    → varsayılan veya "cli" alt komutu
      → _run_cli()
        → src/main.py : main()
          → core.lumos_runtime.create_runtime()
          → cli.cli_router.run_cli_loop(router_ctx)
```

**Özet:** Aktif ana giriş `src/` tarafındadır. `src/main.py` etkileşimli CLI döngüsünü başlatır.

### 3.3 Tüm `lumos` alt komutları (`__main__.py`)

| Alt komut | Hedef | Repo durumu |
|-----------|--------|-------------|
| `cli` (varsayılan) | `src/main.py` → CLI döngüsü | **Canlı** |
| `web` | `web/app.py` (`_run_web()`) | **`web/` ve `web/app.py` yok** — kırık |
| `decision` | `core.decision_pipeline` / `core.decision_runner` | `src/` içi — canlı |

---

## 4. `lumos web` alt komutu

### 4.1 Kod davranışı

`src/lumos_core/__main__.py` içinde:

- `sub.add_parser("web", help="run Web v1 server")` — alt komut **tanımlı**.
- `args.cmd == "web"` → `_run_web()` çağrılır.
- `_run_web()` repo kökünü `Path(__file__).resolve().parent.parent.parent` ile bulur; `web/app.py` yüklemeye çalışır.
- Dosya yoksa: `sys.exit("web/app.py not found")` — **sessiz başarı yok**.

### 4.2 Beklenen hedef (dokümantasyon)

| Kaynak | İfade |
|--------|--------|
| `docs/ARCHITECTURE_MAP.md` | `lumos web` → `web/app.py`; GET `/health`, GET `/status` (read-only) |
| `docs/WEB_STABILIZATION_AUDIT.md` | `web/app.py` minimal HTTP sunucu; `/health` ve `/status` |
| `tests/test_web_health.py` | `web/app.py` subprocess; `/health` → 200, `ok: true` |

### 4.3 Aday paket kopyası (canlı değil)

`packages/kando_core/src/kando_core/__main__.py` aynı `_run_web()` ve `web` alt komut desenini taşır. Kök `lumos` komutu bunu **çağırmaz**; OD-027 kapsamında aday alan.

---

## 5. Eksik `web/app.py` durumu

### 5.1 Repo doğrulaması (2026-06-17)

| Kontrol | Sonuç |
|---------|--------|
| `web/` dizini (repo kökü) | **Yok** |
| `web/app.py` | **Yok** |
| `archive/` içinde `web/app.py` | **Bulunamadı** |

**Kural:** `web/` eksikliği repo doğrulaması olarak belgelenir; bu karar taslağı **`web/` oluşturmaz**.

### 5.2 Git geçmişi (restore ipucu)

- `git log -- web/app.py` → commit `e607671` (*Release v0.1.0: core + CLI + web v1 + smoke + packaging*).
- O commit'te `web/app.py` mevcut: minimal read-only HTTP sunucu (`GET /health`, `GET /status`); `lumos_core.version` ve isteğe bağlı `security.presence_lock` okuması.
- Mevcut working tree'de dosya yok; **kaldırılmış veya dal dışı** olabilir — kesin silme commit'i bu taramada ayrıca doğrulanmadı.

### 5.3 Test durumu

`tests/test_web_health.py`:

- `web/app.py` yoksa `pytest.skip("web/app.py not found")` — test **atlanır**, CI kırmızıya düşürmez.
- Alt komut kırığı ile test atlama **farklı semptomlar**: CLI hata verir, test sessizce skip eder.

### 4.4 Sonuç sınıflandırması

| Durum | Değerlendirme |
|-------|----------------|
| `lumos web` alt komutu tanımlı | Evet |
| `web/app.py` mevcut | Hayır |
| **Sınıf** | **broken** — komut var, hedef dosya yok; **B1 seçildi**, uygulama bekliyor (§12.2) |

---

## 6. Restore / kaldırma seçenekleri

> **Not:** Aşağıdaki seçenekler karar öncesi değerlendirme kaydıdır. **Seçilen yön B1** (§7, §12.1). Restore (A) ve B2/B3 **seçilmedi** — yalnızca tarihsel referans.

### 6.1 Seçenek A — Restore (geri yükleme) *(seçilmedi — tarihsel referans)*

| Alt seçenek | Özet | Artı | Eksi |
|-------------|------|------|------|
| **A1 — Git'ten restore** | `e607671` (veya son bilinen) `web/app.py` + gerekirse `web/` geri getirilir | Mevcut `__main__.py`, test ve dokümantasyonla hizalı; minimal read-only model zaten tanımlı | Güncel `src/` ile uyum yeniden doğrulanmalı; CI'da web testi aktifleşir |
| **A2 — Yeniden yazım (minimal)** | Aynı sözleşme: `/health`, `/status`; panel sunmaz | Sadeleştirilmiş, audit belgesine uygun yüzey | Sıfırdan/implementasyon görevi; public sınır ve demo-safe içerik gözden geçirilmeli |

**Restore ön koşulları (taslak):**

- Read-only garantisi korunur (`docs/WEB_STABILIZATION_AUDIT.md` ile uyum).
- Panel (`panel/`, `ui/`) ile karıştırılmaz — ayrı HTTP yüzeyi.
- `lumos web` çalıştırıldığında anlamlı çıktı; `test_web_health.py` skip etmez.

### 6.2 Seçenek B — Kaldırma (remove) *(B1 seçildi)*

| Alt seçenek | Özet | Artı | Eksi |
|-------------|------|------|------|
| **B1 — Alt komutu kaldır** | `__main__.py` içinden `web` parser ve `_run_web()` silinir | Kırık komut kullanıcıya sunulmaz | `pyproject.toml` açıklaması, `ARCHITECTURE_MAP.md`, test dosyası güncellenmeli |
| **B2 — Deprecated alias** | `lumos web` → net hata mesajı + yönlendirme (ör. «kaldırıldı, CLI kullanın») | Geçiş dönemi uyarısı | Hâlâ entrypoint kodu taşır; tam kaldırma değil |
| **B3 — Dokümantasyon-only temizlik** | Kod dokunulmadan belgelerden web referansı silinir | — | **Yetersiz** — CLI kırığı devam eder; önerilmez tek başına |

**Kaldırma ön koşulları (taslak):**

- Read-only durum/health ihtiyacı başka yüzeyle karşılanıyor mu (CLI `durum`, bridge, backend) — ürün kararı.
- `packages/kando_core` içindeki aynı desen OD-027 ile birlikte ele alınır (canlı entry değil).

### 6.3 Seçenek C — Needs-review (mevcut durum) *(seçilmedi — superseded)*

- Karar öncesi «henüz seçim yok» durumuydu.
- **B1 onaylandı** — bu seçenek geçersiz; uygulama §12.2'de.

---

## 7. Karar özeti

| Alan | İfade |
|------|--------|
| **Mevcut gerçeklik** | Canlı CLI: `lumos_core.__main__` → `src/main.py` → `core/cli`. `lumos web` tanımlı ama `web/app.py` yok → **kırık**. |
| **Ürün tanımı çelişkisi** | `pyproject.toml` ve mimari belgeler «read-only web» öngörür; repo dosyası yok. |
| **Restore lehine sinyal** | Git geçmişinde çalışan minimal `web/app.py`; test ve audit belgeleri mevcut. |
| **Kaldırma lehine sinyal** | Panel/UI/bridge/backend ayrı HTTP yüzeyleri; web v1 kullanım sıklığı belgelenmemiş. |
| **Seçim** | **B1 — alt komutu kaldır** (`[decision-approved]`) |
| **Restore** | **Seçilmedi** — `web/app.py` geri getirilmeyecek. |
| **Uygulama durumu** | **Bekliyor** — kod henüz değişmedi. |

**Netleşen sabit kararlar:**

1. **Restore değil, kaldırma yönü seçildi** — alt seçenek **B1**.
2. `web/` dizini **oluşturulmayacak**; `web/app.py` restore edilmeyecek.
3. OD-043 / OD-046 (birincil UI yüzeyi, build vs E2E) ile **birleştirilmez**.
4. Uygulama paketi (§12.2) tamamlanana kadar OD-028 **closed** sayılmaz; indeks senkronu uygulama sonrası yapılır.

---

## 8. Kod değişikliği öncesi kural

[`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) §8 ve [`project-workflow.md`](./project-workflow.md) §2 ile hizalı:

1. **B1 seçildi** — restore yapılmaz; kaldırma uygulaması §12.2 paketinde, onaylı görev olarak yürütülür.
2. Belirsiz «web'i düzelt» veya restore isteğiyle `__main__.py`, `pyproject.toml` veya yeni `web/` oluşturma **yapılmaz**.
3. Panel/UI/frontend build veya deploy değişikliği bu kararın **kapsamı dışındadır**.
4. Minimum diff; test + CI yeşil olmadan «tamamlandı» denmez.
5. Public repo sınırı: production API, secret veya operasyonel detay kod değişikliklerinde sızmamalı.

---

## 9. Riskler

| Risk | Açıklama | Azaltma (özet) |
|------|----------|----------------|
| **Kırık komut UX** | Kullanıcı `lumos web` çalıştırınca `web/app.py not found` | B1 uygulanana kadar bilinçli; §12.2 ile kaldırılır |
| **Dokümantasyon drift** | `ARCHITECTURE_MAP.md`, `pyproject.toml` web öngörür; dosya yok | §12.2 uygulama paketi (madde 3, 5) |
| **Test sahte güven** | `test_web_health.py` skip — CI yeşil ama web doğrulanmıyor | §12.2 madde 4 — test kaldır veya güncelle |
| **Yüzey karışıklığı** | `lumos web` ile `panel/` / `ui/` / `backend/` aynı sanılır | Bu belge ve OD-043/046 ayrımı |
| **Çift entry (kando_core)** | Aday pakette aynı kırık desen | OD-027 ile birlikte ele alınır |
| **Erken restore** | Eski `web/app.py` güncel `src/` güvenlik sınırlarıyla uyumsuz | Restore öncesi `WEB_STABILIZATION_AUDIT` checklist |

---

## 10. Açık kararlar

| # | Soru | Durum |
|---|------|--------|
| 1 | **Restore (A)** mi **kaldırma (B)** mi? | **Kapandı** — **B (kaldırma)** |
| 2 | Restore ise: git restore (A1) mi minimal yeniden yazım (A2) mi? | **Geçersiz** — restore seçilmedi |
| 3 | Kaldırma ise: tam silme (B1) mi deprecated mesaj (B2) mi? | **Kapandı** — **B1** |
| 4 | Read-only `/health` / `/status` ürün ihtiyacı devam ediyor mu? | **OD-028 dışı** — B1 ile web v1 sunulmayacak; ihtiyaç CLI/bridge/backend ürün kararı (bu belgenin uygulama paketi değil) |
| 5 | `pyproject.toml` açıklamasından «read-only web» ifadesi ne zaman güncellenir? | **§12.2 madde 3** — uygulama paketi |
| 6 | `packages/kando_core` `web` alt komutu kök kararla birlikte mi temizlenir? | **§12.2 madde 6** — uygulama paketi (OD-027 çapraz temizlik) |

---

## 11. OD eşleme tablosu

| OD | Konu | Bu belgedeki karşılık | Durum |
|----|------|------------------------|--------|
| **OD-028** | `lumos web` / eksik `web/app.py` restore veya kaldırma | **B1 seçildi** — restore değil; uygulama bekliyor | **decision-approved** (uygulama pending) |
| OD-027 | `packages/kando_*` → `src/` geçişi | §2 kapsam dışı; `kando_core` web kopyası notu | needs-review (çapraz) |
| OD-043 | Birincil kullanıcı yüzeyi (`panel/` / `ui/` / `frontend/`) | §2 kapsam dışı — karıştırılmaz | needs-review (çapraz) |
| OD-046 | Root `npm run build` (ui) vs panel E2E | §2 kapsam dışı — karıştırılmaz | needs-review (çapraz) |

**İndeks senkronu:** OD-028 kapanınca önce bu dosya ve [`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) §11 madde 3 güncellenir; ardından [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

---

## 12. Sonraki adım

### 12.1 Karar (tamamlandı)

**B1 — Alt komutu kaldır** seçildi. **Restore (A) seçilmedi.**

### 12.2 Uygulama paketi (tamamlandı — 2026-06-17)

Aşağıdaki işler **ayrı uygulama görevidir**; bu belge kod değiştirmez:

| # | Hedef | Not |
|---|--------|-----|
| 1 | `src/lumos_core/__main__.py` — `web` alt komutunu kaldır | `sub.add_parser("web", …)` ve `args.cmd == "web"` dalı |
| 2 | `src/lumos_core/__main__.py` — `_run_web()` fonksiyonunu kaldır | İlgili importlar temizlenir |
| 3 | `pyproject.toml` — açıklamadaki «read-only web» ifadesini gözden geçir | Örn. yalnızca CLI odaklı açıklama |
| 4 | `tests/test_web_health.py` — kaldır veya güncelle | `web/app.py` artık hedef değil |
| 5 | `docs/ARCHITECTURE_MAP.md` ve ilgili dokümanlar — senkronize et | `lumos web` referanslarını kaldır veya arşiv notu |
| 6 | `packages/kando_core` içindeki benzer `web` kalıntısı | OD-027 çapraz temizlik; canlı entry değil ama B1 ile hizalı kaldırma |

**Kabul:** İlgili testler + CI yeşil; `lumos web` artık tanımlı değil veya bilinçli deprecated mesaj (B1 = tam kaldırma).

**İndeks senkronu (uygulama sonrası):** [`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) §11 madde 3 → [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) OD-028 satırı → `docs/project-map.md` / `docs/decision-log.md`.

### 12.3 Seçilmeyen yol (kayıt)

| Seçenek | Durum |
|---------|--------|
| A — Restore (`web/app.py` geri getirme) | **Reddedildi** |
| B2 — Deprecated alias | **Reddedildi** — B1 tercih edildi |
| B3 — Yalnızca dokümantasyon temizliği | **Reddedildi** |

---

*Son güncelleme: 2026-06-17 (B1 kararı işlendi)*
