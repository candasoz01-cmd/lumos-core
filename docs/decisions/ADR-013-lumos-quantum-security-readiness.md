# ADR-013: Lumos Quantum Security Readiness (Taslak)

| Alan | Değer |
|------|-------|
| Durum | **Taslak** — Faz-1 docs-only; entropy sağlayıcı davranışı değiştirilmez |
| Tarih | 2026-06-21 |
| İlgili | [ADR-001](ADR-001-lumos-quantum-modules.md), `src/security/entropy/`, [readiness checklist](../analysis/lumos-quantum-readiness-checklist.md), `ROADMAP.md` |

## Amaç

Lumos'taki kuantum alanını **"kuantum bilgisayar kullanıyoruz"** veya **"kuantum-güvenli kriptografi"** iddiasından çıkarıp, **yerel, kanıta dayalı Kuantum Güvenlik Hazırlığı** (Quantum Security Readiness) olarak tanımlamak.

Bu belge **bağımsız bir hazırlık ADR'sidir**. Entropy modülü mevcut haliyle dokümante edilir; sağlayıcı seçimi veya fallback davranışı **bu ADR ile değiştirilmez**.

---

## Ürün yönü

### Problem

Bugün üç algı aynı anda var:

1. **Dürüst metinler** (landing, panel i18n, ADR-001): "Kuantum şifreleme kullanmıyoruz", "aktif üretim özelliği değil".
2. **Kod gerçeği** (`src/security/entropy/`): Qiskit Aer ve IBM Runtime sağlayıcıları mevcut; varsayılan yol `os.urandom`.
3. **Boşluk**: Kullanıcıya hazırlık durumunu gösteren kanıt tabanlı yüzey yok; panel yalnızca statik kart metinleri (`#panel-kuantum`, dört kart).

### Hedef

**Quantum Security Readiness** — Lumos'un güvenlik mimarisinde kuantum tehditlerine ve geçiş yollarına karşı **yerel, salt okunur, kanıtlı** hazırlık görünürlüğü:

- Klasik kripto bileşenlerini envanterler (AES-GCM, Scrypt vb.).
- Entropy sağlayıcı durumunu **açık etiketlerle** raporlar (aktif / kullanılamıyor / fallback).
- PQC ve harici kuantum kaynakları için checklist + açık sınır sunar.
- Panel/CLI çıktısında **mock ≠ gerçek** ayrımını şeffaf tutar.

### Ne değildir

| İddia | Durum |
|-------|-------|
| Gerçek kuantum bilgisayar üretim kullanımı | **Hayır** |
| Post-quantum / kuantum-dayanıklı kriptografi (PQC) uygulaması | **Hayır** — değerlendirme ve envanter düzeyi |
| Entropy sağlayıcı davranışını değiştirmek | **Hayır** — bu ADR mevcut `entropy()` sözleşmesine dokunmaz |
| IBM ücretli API / prod entegrasyon | **Hayır** — sınır dokümantasyonu; maliyet/onay açılmadan aktif değil |
| "Quantum powered" / "quantum secure" pazarlama dili | **Hayır** — public OSS sınırı |

### ADR-001 ile hizalama

ADR-001 kuantumu "erken hedef değil, iptal değil, araştırma/aday" konumlar. ADR-013 bunu **somutlaştırır**: üretim iddiası yerine **hazırlık raporu**. Routing, trust ve memory önceliği korunur.

---

## MVP kapsamı

### Faz-1 (bu ADR — docs-only)

1. Readiness tanımı ve sınır sözleşmesi (bu belge + checklist).
2. **Yerel envanter checklist'i** — manuel tablo; ileride script bağlanabilir:
   - Kripto algoritmaları (AES-GCM-256, Scrypt — klasik, kuantum-tehdide açık).
   - Entropy kaynağı (`LUMOS_ENTROPY_PROVIDER` env + kod varsayılanı `os`).
   - Opsiyonel sağlayıcıların kurulu/kullanılabilir olup olmadığı (import probe — Faz-2).
3. **PQC farkındalık bölümü** — "izleniyor / uygulanmıyor"; NIST PQC adayları referans notu (uygulama yok).
4. **Sessiz fallback uyarısı** — zorunlu kullanıcı-facing metin (aşağıda Riskler).
5. **Public OSS sınırı** — üretim kuantum iddiası yasağı.

### Bilinçli erteleme (MVP dışı)

| Konu | Neden |
|------|-------|
| Entropy provider kod değişikliği | Ayrı onaylı PR |
| Gerçek PQC algoritma entegrasyonu | Uzmanlık + audit gerekir |
| IBM Runtime prod bağlantısı | Maliyet, credential, public boundary |
| Qiskit Aer'i "quantum entropy" olarak pazarlamak | Simülatör ≠ donanım; kripto iddiası yok |
| Panel write aksiyonları | Readiness salt okunur olmalı |

### Başarı ölçütleri

- Hiçbir kullanıcı metninde "kuantum bilgisayar kullanıyoruz" veya "kuantum-güvenli şifreleme" **yok**.
- Readiness çıktısı **kanıt türü** ile etiketli (`env_ok`, `simulasyon`, `kullanılamıyor`, `fallback_aktif`, `docs_only`).
- Entropy modülü **davranış değişmeden** dokümante edilmiş.
- ADR-001 ve public-github-boundary ile çelişki yok.

---

## Panel alanları (spesifikasyon — uygulama Faz-2)

Mevcut panel kuantum sekmesi (`ui/src/pages/panel.astro`, `#panel-kuantum`) dört statik kart taşır. Faz-2'de altına **readiness paneli** eklenir; Faz-1'de yalnızca bu alan listesi geçerlidir.

### Sekme banner (öneri)

Üst banner: *"Araştırma / hazırlık — üretim kuantum özelliği değildir"*

Mevcut dört kart (Kuantum Güvenlik Araştırması, Çoklu İhtimal, Belirsizlik Dengesi, Karar Sınırı) korunabilir.

### Readiness alanları

| Alan | Tür | Etiket (mock/gerçek) | Açıklama |
|------|-----|----------------------|----------|
| **Genel durum** | Salt okunur badge | `hazırlık_raporu` | `tamamlandi` / `kısmi` / `doğrulanamadi` |
| **Kripto envanteri** | Salt okunur liste | `gerçek` (koddan) | AES-GCM, Scrypt; "klasik — PQC değil" |
| **Aktif entropy sağlayıcı** | Salt okunur | `gerçek` (env+probe) | `os` / `qiskit_aer` / `ibm_runtime` / `bilinmiyor` |
| **Sağlayıcı kullanılabilirlik** | Salt okunur | `gerçek` (probe) | import OK / eksik paket / credential yok |
| **Fallback durumu** | Salt okunur uyarı | `gerçek` | `sessiz_fallback_riski` — env ≠ efektif kaynak ise vurgulu |
| **Qiskit Aer sınırı** | Salt okunur info | `simulasyon` | "Yerel simülatör; kuantum donanımı değil" |
| **IBM Runtime sınırı** | Salt okunur info | `demo_kapalı` | "Credential/onay yok; public OSS'te prod yok" |
| **PQC durumu** | Salt okunur | `izleme` | "Değerlendirme aşamasında; uygulanmıyor" |
| **Son kontrol zamanı** | Salt okunur | `gerçek` | ISO timestamp (Faz-2) |
| **Kanıt kaynağı** | Salt okunur | `gerçek` | `local_probe` / `docs_only` (Faz-1) |

### Faz-1 mock kuralı

Backend probe bağlı değilken:

- Sabit banner: **`DEMO / DOKÜMANTASYON — CANLI PROBE YOK`**
- Statik örnek değerler mock olarak işaretlenir; gerçek başarı gibi gösterilmez.

### MVP'de olmayan aksiyonlar

| Aksiyon | MVP | Gerekçe |
|---------|-----|---------|
| Entropy sağlayıcı değiştir | Hayır | Env değişikliği = güvenlik etkisi; ayrı onay |
| IBM bağlantı testi (canlı job) | Hayır | Maliyet + external; onay kapılı |
| PQC anahtar üretimi | Hayır | Uygulama yok |

---

## Entropy Lab sınırları

Entropy modülü: `src/security/entropy/` — tek giriş `entropy(n, provider)` / `get_random_bytes(n)`.

```
get_random_bytes(n)
    └── entropy(n, provider=LUMOS_ENTROPY_PROVIDER veya "os")
            └── get_provider(name)
                    ├── os          → OSUrandomProvider (os.urandom)  [VARSAYILAN]
                    ├── qiskit_aer  → QiskitAerProvider (simülatör)   [OPSİYONEL]
                    └── ibm_runtime → IBMRuntimeProvider (harici)     [OPSİYONEL]
```

**Pratik üretim yolu:** `crypto.py`, `keystore.py`, `request_signer.py` → `get_random_bytes` → env set edilmediğinde **os.urandom**. `pyproject.toml` yalnızca `cryptography>=42`; qiskit paketleri core bağımlılık değildir.

### `os` (OSUrandomProvider)

- Standart CSPRNG yolu; varsayılan ve üretime uygun referans.
- Readiness raporunda **efektif kaynak** olarak kabul edilir.

### Qiskit Aer (QiskitAerProvider)

| Konu | Sınır |
|------|-------|
| Doğası | **Klasik CPU simülasyonu** (`AerSimulator`) — kuantum donanımı değil |
| Entropy iddiası | Kriptografik QRNG **değil**; ölçüm çıktısı simüle |
| Bağımlılık | `qiskit`, `qiskit-aer` — opsiyonel pip; core deps'te yok |
| Public OSS | "Kuantum entropy kullanıyoruz" **yasak**; "simülatör probe (deneysel)" ifadesi |
| Fallback | Import/init hatası → `os` — **sessiz** (`get_provider`) |

### IBM Runtime (IBMRuntimeProvider)

| Konu | Sınır |
|------|-------|
| Credential | `QiskitRuntimeService()` — token/account public repoda yok |
| Maliyet | ADR-001: maliyet açılmadı; aktif entegrasyon yok |
| Backend | Gerçek IBM queue/backend — **onaysız MVP dışı** |
| Public boundary | Production API, operasyonel backend detayı public repoya girmez |
| Fallback | Her failure → `os.urandom` — **sessiz, log yok** |
| Network | Offline mod ile çelişebilir — harici çağrı onay kapılı |

### Standart kullanıcı uyarısı (readiness metni)

> *"`LUMOS_ENTROPY_PROVIDER` qiskit_aer veya ibm_runtime olsa bile, sağlayıcı kullanılamazsa sistem uyarı vermeden os.urandom kullanabilir. Bu, kuantum entropy kullanımı anlamına gelmez."*

---

## Riskler

### Sessiz fallback (birincil risk)

Fallback **üç katmanda**, çoğunlukla log/audit olmadan:

| Katman | Davranış | Risk |
|--------|----------|------|
| `get_provider("qiskit_aer")` | Import/init hatası → `_OS` | Kullanıcı "qiskit_aer seçtim" sanır; OS kullanılır |
| `entropy()` | `get_entropy` exception → `_OS` | Aynı |
| `IBMRuntimeProvider` | Her hata → `os.urandom` | "IBM quantum entropy" algısı; gerçekte OS |

**Operasyonel sonuç:** Env farklı sağlayıcı gösterse bile efektif kaynak OS olabilir — readiness panelinde **zorunlu uyarı alanı** olmalıdır.

> **Bu ADR kapsamı dışı:** Fallback davranışını değiştirmek, log eklemek veya provider seçimini sıkılaştırmak — ayrı onaylı PR gerektirir.

### Diğer riskler

| Risk | Önem | Azaltma (Faz-2+) |
|------|------|------------------|
| Panel mock'un gerçek sanılması | Yüksek | Faz-1 banner + `simulasyon` / `docs_only` etiketi |
| "Quantum Security" pazarlama kayması | Yüksek | Public README/landing review checklist |
| Qiskit bağımlılık ekleme baskısı | Orta | Faz-2 optional extra; core deps'e ekleme |
| `lumos-quantum/` doküman drift | Orta | ADR-001 notu — placeholder dizin repo kökünde yok (2026-06-21) |
| Entropy modülü test boşluğu | Orta | Faz-2 probe testleri |

### Kriptografik dürüstlük tablosu

| İddia | Gerçek |
|-------|--------|
| "Kuantum-güvenli" | **Hayır** — AES-GCM + Scrypt klasik |
| "Post-quantum" | **Hayır** — yalnızca hazırlık/izleme |
| "Kuantum bilgisayar" | **Hayır** — Aer simülatör; IBM opsiyonel ve kapalı |

---

## Faz-1 / Faz-2 yol haritası

| Faz | Kapsam | Çıktı |
|-----|--------|-------|
| **Faz-1** | Docs-only: ADR-013, checklist, panel alan spesifikasyonu | Bu PR; entropy kodu değişmez |
| **Faz-2** | Salt okunur readiness probe (CLI veya panel GET) | Env + import probe; fallback uyarısı zorunlu; **kullanıcı onayı gerekir** |
| **Faz-3** (onaylı, private olabilir) | IBM Runtime POC, maliyet/onay kapısı | Credential vault; public repoda yalnızca sınır metni |

### Faz-2 aday dosyalar (onay sonrası — bu PR'da yok)

- `src/security/entropy/readiness.py` — probe; `get_entropy` çağırmadan env/import kontrolü
- CLI alt komut veya panel `GET` endpoint — salt okunur JSON
- `tests/test_entropy_readiness.py`
- Panel kuantum sekmesi — bu ADR'deki alanlar; mock banner kaldırma

---

## Bilinen boşluklar (2026-06-21)

1. **`lumos-quantum/`** — Belgelerde placeholder; repo kökünde fiziksel dizin yok.
2. **Entropy testleri** — Yok.
3. **Readiness API/CLI** — Yok.
4. **PQC** — Panel i18n'de gelecek tense ifade; kod yok.
5. **IBM / Qiskit** — Kod var; bağımlılık ve operasyon yok; çoğu kurulumda pratikte yalnızca `os.urandom`.

---

## Sonuç

Kuantum alanı Lumos'ta **hazırlık ve şeffaflık** servisi olarak konumlanır; üretim kuantum iddiası taşımaz. Faz-1 bu sözleşmeyi kilitleyerek kod değişikliği olmadan panel ve probe tasarımına zemin hazırlar.
