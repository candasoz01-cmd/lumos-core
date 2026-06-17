# OD-028 — `lumos web` / eksik `web/app.py` karar taslağı

**Durum:** `[decision-draft]` — uygulama değildir; kod değişikliği içermez.  
**Kaynak indeks:** [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) OD-028.  
**Çapraz referans:** OD-027 (`packages/kando_*` geçişi), OD-043 / OD-046 (panel/ui/frontend yüzeyleri).  
**Doğrulama tarihi:** 2026-06-17 (repo read-only tarama).

---

## 1. Amaç

Root `lumos` CLI içindeki **`web` alt komutunun** ve hedef dosya **`web/app.py`** ile repo gerçekliği arasındaki uyumsuzluğu netleştirmek; **restore** (geri yükleme) ile **kaldırma** seçeneklerini kanıta dayalı değerlendirmek.

Bu belge:

- **Uygulama belgesi değildir** — hiçbir kod, dizin oluşturma, entrypoint değişikliği veya test düzeltmesi yapmaz.
- Çekirdek sözleşme ([`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md)) üst sınır olarak geçerlidir.
- Karar seçilmeden CLI/entrypoint değişikliği yapılmaz.

---

## 2. Kapsam dışı olanlar

| Madde | Neden kapsam dışı |
|-------|-------------------|
| `panel/`, `ui/`, `frontend/` birincil yüzey seçimi | OD-043, OD-046 — ayrı karar belgeleri; `lumos web` ile karıştırılmaz |
| `packages/kando_*` → `src/` geçişi | OD-027 — [`kando-packages-transition-decision.md`](./kando-packages-transition-decision.md) |
| `backend/` Express API, `api/bridge/` Vercel proxy | Ayrı HTTP yüzeyleri; `web/app.py` minimal read-only sunucu modelinden farklı |
| `web/` dizini oluşturma veya `web/app.py` restore uygulaması | Bu oturum yalnızca karar taslağı üretir |
| Diğer `docs/memory/*.md` dosyalarının güncellenmesi | Bu oturumda yalnızca bu dosya oluşturulur |
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
| **Sınıf** | **broken / needs-review** — komut var, hedef dosya yok |

---

## 6. Restore / kaldırma seçenekleri

### 6.1 Seçenek A — Restore (geri yükleme)

| Alt seçenek | Özet | Artı | Eksi |
|-------------|------|------|------|
| **A1 — Git'ten restore** | `e607671` (veya son bilinen) `web/app.py` + gerekirse `web/` geri getirilir | Mevcut `__main__.py`, test ve dokümantasyonla hizalı; minimal read-only model zaten tanımlı | Güncel `src/` ile uyum yeniden doğrulanmalı; CI'da web testi aktifleşir |
| **A2 — Yeniden yazım (minimal)** | Aynı sözleşme: `/health`, `/status`; panel sunmaz | Sadeleştirilmiş, audit belgesine uygun yüzey | Sıfırdan/implementasyon görevi; public sınır ve demo-safe içerik gözden geçirilmeli |

**Restore ön koşulları (taslak):**

- Read-only garantisi korunur (`docs/WEB_STABILIZATION_AUDIT.md` ile uyum).
- Panel (`panel/`, `ui/`) ile karıştırılmaz — ayrı HTTP yüzeyi.
- `lumos web` çalıştırıldığında anlamlı çıktı; `test_web_health.py` skip etmez.

### 6.2 Seçenek B — Kaldırma (remove)

| Alt seçenek | Özet | Artı | Eksi |
|-------------|------|------|------|
| **B1 — Alt komutu kaldır** | `__main__.py` içinden `web` parser ve `_run_web()` silinir | Kırık komut kullanıcıya sunulmaz | `pyproject.toml` açıklaması, `ARCHITECTURE_MAP.md`, test dosyası güncellenmeli |
| **B2 — Deprecated alias** | `lumos web` → net hata mesajı + yönlendirme (ör. «kaldırıldı, CLI kullanın») | Geçiş dönemi uyarısı | Hâlâ entrypoint kodu taşır; tam kaldırma değil |
| **B3 — Dokümantasyon-only temizlik** | Kod dokunulmadan belgelerden web referansı silinir | — | **Yetersiz** — CLI kırığı devam eder; önerilmez tek başına |

**Kaldırma ön koşulları (taslak):**

- Read-only durum/health ihtiyacı başka yüzeyle karşılanıyor mu (CLI `durum`, bridge, backend) — ürün kararı.
- `packages/kando_core` içindeki aynı desen OD-027 ile birlikte ele alınır (canlı entry değil).

### 6.3 Seçenek C — Needs-review (mevcut durum)

- Ne restore ne kaldırma seçilmedi.
- `lumos web` **broken** olarak kalır; yeni CLI/entrypoint işleri bu kararı beklemez ama **web alt komutuna dokunan değişiklik** yapılmaz.

---

## 7. Karar taslağı

| Alan | Taslak ifade |
|------|----------------|
| **Mevcut gerçeklik** | Canlı CLI: `lumos_core.__main__` → `src/main.py` → `core/cli`. `lumos web` tanımlı ama `web/app.py` yok → **kırık**. |
| **Ürün tanımı çelişkisi** | `pyproject.toml` ve mimari belgeler «read-only web» öngörür; repo dosyası yok. |
| **Restore lehine sinyal** | Git geçmişinde çalışan minimal `web/app.py`; test ve audit belgeleri mevcut. |
| **Kaldırma lehine sinyal** | Panel/UI/bridge/backend ayrı HTTP yüzeyleri; web v1 kullanım sıklığı belgelenmemiş. |
| **Seçim** | **Henüz yapılmadı** — `[needs-review]` |
| **Varsayılan durum** | Kod değişikliği yok; kırık komut bilinçli olarak dokunulmadan bırakılır ta ki karar kapanana kadar. |

**Netleşen sabit kararlar (uygulama bekliyor):**

1. Bu belge **implementasyon değildir**.
2. `web/` dizini bu taslak tarafından **oluşturulmaz**.
3. OD-043 / OD-046 (birincil UI yüzeyi, build vs E2E) ile **birleştirilmez**.
4. CLI/entrypoint değişikliği, OD-028 kapanana kadar **ertelenir** (web alt komutuna özgü değişiklikler).

---

## 8. Kod değişikliği öncesi kural

[`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) §8 ve [`project-workflow.md`](./project-workflow.md) §2 ile hizalı:

1. **`lumos web` / `web/app.py` restore veya kaldırma** için kullanıcı/onaylı görev ve yazılı hedef (A/B alt seçeneği) gerekir.
2. Belirsiz «web'i düzelt» isteğiyle `__main__.py`, `pyproject.toml` veya yeni `web/` oluşturma **yapılmaz**.
3. Panel/UI/frontend build veya deploy değişikliği bu kararın **kapsamı dışındadır**.
4. Minimum diff; test + CI yeşil olmadan «tamamlandı» denmez.
5. Public repo sınırı: production API, secret veya operasyonel detay `web/app.py` restore'unda sızmamalı.

---

## 9. Riskler

| Risk | Açıklama | Azaltma (özet) |
|------|----------|----------------|
| **Kırık komut UX** | Kullanıcı `lumos web` çalıştırınca `web/app.py not found` | Karar kapatılana kadar yardım metinlerinde belirsizlik; restore veya kaldır |
| **Dokümantasyon drift** | `ARCHITECTURE_MAP.md`, `pyproject.toml` web öngörür; dosya yok | Karar sonrası tek canonical güncelleme paketi |
| **Test sahte güven** | `test_web_health.py` skip — CI yeşil ama web doğrulanmıyor | Restore sonrası skip kalkmalı; kaldırma sonrası test kaldırılmalı veya redirect testi |
| **Yüzey karışıklığı** | `lumos web` ile `panel/` / `ui/` / `backend/` aynı sanılır | Bu belge ve OD-043/046 ayrımı |
| **Çift entry (kando_core)** | Aday pakette aynı kırık desen | OD-027 ile birlikte ele alınır |
| **Erken restore** | Eski `web/app.py` güncel `src/` güvenlik sınırlarıyla uyumsuz | Restore öncesi `WEB_STABILIZATION_AUDIT` checklist |

---

## 10. Açık kararlar

| # | Soru | Durum |
|---|------|--------|
| 1 | **Restore (A)** mi **kaldırma (B)** mi? | **needs-review** |
| 2 | Restore ise: git restore (A1) mi minimal yeniden yazım (A2) mi? | **needs-review** |
| 3 | Kaldırma ise: tam silme (B1) mi deprecated mesaj (B2) mi? | **needs-review** |
| 4 | Read-only `/health` / `/status` ürün ihtiyacı devam ediyor mu? | **needs-review** |
| 5 | `pyproject.toml` açıklamasından «read-only web» ifadesi ne zaman güncellenir? | **needs-review** (karara bağlı) |
| 6 | `packages/kando_core` `web` alt komutu kök kararla birlikte mi temizlenir? | **needs-review** (OD-027 çapraz) |

---

## 11. OD eşleme tablosu

| OD | Konu | Bu belgedeki karşılık | Durum |
|----|------|------------------------|--------|
| **OD-028** | `lumos web` / eksik `web/app.py` restore veya kaldırma | Bu dosyanın tamamı | **needs-review** (decision-draft) |
| OD-027 | `packages/kando_*` → `src/` geçişi | §2 kapsam dışı; `kando_core` web kopyası notu | needs-review (çapraz) |
| OD-043 | Birincil kullanıcı yüzeyi (`panel/` / `ui/` / `frontend/`) | §2 kapsam dışı — karıştırılmaz | needs-review (çapraz) |
| OD-046 | Root `npm run build` (ui) vs panel E2E | §2 kapsam dışı — karıştırılmaz | needs-review (çapraz) |

**İndeks senkronu:** OD-028 kapanınca önce bu dosya ve [`project-map-runtime-entrypoints.md`](./project-map-runtime-entrypoints.md) §11 madde 3 güncellenir; ardından [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

---

## 12. Sonraki adım

**Tek adım:** Kullanıcı kararı — **Seçenek A (restore)** veya **Seçenek B (kaldırma)** (§6); alt seçenek (A1/A2 veya B1/B2) ile birlikte. Karar verilmeden `web/` oluşturma, `__main__.py` değişikliği veya entrypoint güncellemesi yapılmaz.

Restore seçilirse izleyen görev (ayrı oturum): git geçmişinden `web/app.py` diff incelemesi + `WEB_STABILIZATION_AUDIT.md` checklist doğrulaması + `test_web_health.py` yeşil.

Kaldırma seçilirse izleyen görev (ayrı oturum): `__main__.py` dar kaldırma + `pyproject.toml` / mimari belge senkronu + test dosyası kararı.

---

*Son güncelleme: 2026-06-17*
