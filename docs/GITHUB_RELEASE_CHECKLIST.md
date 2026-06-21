# GitHub Release Checklist

| Alan | Değer |
|------|-------|
| **Belge ID** | RB-07 · GAP-12 |
| **Durum** | Canonical release operatör checklist (docs-only) |
| **Tarih** | 2026-06-21 |
| **Audience** | Release operatörü / merge sahibi |
| **Kapsam** | `main` dalı merge ve GitHub Actions doğrulama — **PyPI/npm otomatik publish yok** (RB-08 defer) |

Bu belge README'deki release checklist referansının hedefidir. Otomatik artifact publish workflow'u **henüz tanımlı değildir**; aşağıdaki adımlar merge-to-`main` kalite kapısı içindir.

**İlgili:** [`repo-branches.md`](repo-branches.md), [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md), [`LUMOS_V1_READINESS.md`](LUMOS_V1_READINESS.md), [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

---

## 1. Release türü seçimi

| Tür | Ne zaman | Public iddia |
|-----|----------|--------------|
| **Development merge** | Her PR → `main` | Hayır — early active development |
| **Internal Alpha milestone** | Ekip-only foundation build | Hayır — [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md) |
| **Tagged OSS snapshot** | İsteğe bağlı git tag (artifact publish yok) | «Development build» — kararlı OSS iddiası yok (RB-09) |
| **Commercial / official release** | Henüz tanımlı değil | RB-08 publish CI + banka/OD-011 kapıları gerekir |

---

## 2. Merge öncesi (PR)

### 2.1 Dal ve kapsam

- [ ] PR hedef dalı **`main`** ([`repo-branches.md`](repo-branches.md))
- [ ] Tek mantıksal değişiklik; public boundary ihlali yok ([`public-repo-boundary.md`](memory/public-repo-boundary.md))
- [ ] Secret / credential / production URL commit'te **yok**

### 2.2 Yerel kalite (pre-commit)

Pre-commit hook (`make setup-commit-guard`) veya manuel:

```bash
ruff check .
pytest -q
```

- [ ] `ruff check .` — geçti
- [ ] `pytest -q` — geçti (CI ile aynı: `KANDO_MOCK=1`, `PYTHONPATH` monorepo yolları)

UI değişikliği varsa (opsiyonel yerel):

```bash
cd ui && npm ci && npm run build && npm run e2e:smoke
```

### 2.3 PR CI (GitHub Actions)

[`ci.yml`](../.github/workflows/ci.yml) — PR'da **tümü yeşil** olmadan merge yok:

| Job | İçerik |
|-----|--------|
| `test` | ruff + pytest (Python 3.12) |
| `ui-smoke` | UI build + Playwright smoke |
| `ui-e2e` | Package-local, package-api, confirmation-panel-api, tasks-offline-online E2E |

- [ ] `test` — success
- [ ] `ui-smoke` — success
- [ ] `ui-e2e` — success

---

## 3. Merge sonrası (`main`)

### 3.1 CI doğrulama

- [ ] `main` push sonrası **en üstteki** CI run success ([`gh run list --branch main`](https://cli.github.com/manual/gh_run_list))
- [ ] Eski kırmızı run'lara bakılmaz — **son merge run** esas alınır

### 3.2 Dokümantasyon (gerektiğinde)

- [ ] Karar / defer değişikliği → [`decision-log.md`](decision-log.md) veya `docs/memory/*.md`
- [ ] ADR-012 checkpoint değişikliği → [`ADR-012-lumos-security-codex.md`](decisions/ADR-012-lumos-security-codex.md)
- [ ] Release kapsam değişikliği → [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md) (Internal Alpha)

### 3.3 Opsiyonel prod smoke

Manuel workflow (merge zorunluluğu değil; prod panel doğrulama):

```bash
gh workflow run prod-smoke.yml
```

- [ ] Prod smoke çalıştırıldı (panel deploy sonrası) — *opsiyonel*

---

## 4. Git tag (opsiyonel — publish yok)

Otomatik GitHub Release / PyPI / npm publish **yok** (RB-08). Tag yalnızca referans işaretleyicisidir:

```bash
git tag -a v0.1.0-dev -m "Development snapshot; not a stable product release"
git push origin v0.1.0-dev
```

- [ ] Tag mesajı «development / not stable» iddiasını taşır (RB-09)
- [ ] Sürüm kaynakları hizası not edildi (RB-06 — packaging tek `pip install` defer)

---

## 5. Bilinçli defer (bu checklist kapsamaz)

| RB | Konu | Not |
|----|------|-----|
| RB-06 | Python packaging tek `pip install` | CI `PYTHONPATH` zorunlu |
| RB-08 | Publish/release CI pipeline | Artifact otomasyonu yok |
| RB-01 | ADR-012 CLOSED | Internal Alpha defer — [`adr-012-internal-alpha-defer-record.md`](memory/adr-012-internal-alpha-defer-record.md) |

---

## 6. Hızlı referans — CI ortamı

CI ile yerel parity:

| Ayar | Değer |
|------|-------|
| Python | 3.12 |
| Node (UI) | 22 |
| `PYTHONPATH` | `src:packages/kando_runtime/src:packages/kando_bridge/src` |
| `KANDO_MOCK` | `1` (pytest) |

---

## 7. Revision log

| Tarih | Değişiklik |
|-------|------------|
| 2026-06-21 | İlk canonical checklist — RB-07 / GAP-12 kapanış; README referansı hedefi |

---

*Docs only — operasyonel runbook; otomatik publish taahhüdü içermez.*
