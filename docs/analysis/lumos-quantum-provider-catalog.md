# Lumos Quantum Layer — Sağlayıcı Kataloğu

| Alan | Değer |
|------|-------|
| Durum | **Adapter hazır** — salt okunur keşif; canlı hesap bağlantısı credential bekliyor |
| Tarih | 2026-07-17 |
| Mimari | [`lumos-quantum-layer-architecture.md`](./lumos-quantum-layer-architecture.md) |
| Kod stub | `src/integrations/quantum_registry.py` |

**Onay katmanları (özet):**

| Katman | Anlam | Örnek |
|--------|-------|-------|
| **auto-doc** | Yerel dokümantasyon / katalog; dış etki yok | `list_catalog`, araştırma linkleri |
| **needs-owner** | Kimlik bilgisi, ücret veya dış hesaplama potansiyeli | `connect`, `discover` (harici), credential vault |
| **blocked** | Otonom veya onaysız yasak | Otonom job submit, sessiz token yazma |

**Durum değerleri:** `planned` · `stub` · `none`

**Bağlantı önceliği (`connect_priority`):** `1` = ilk yol arkadaşı (pilot connect spike) · `2` = Aer kanıtlandıktan sonra · boş = sonraki dal / planlı. Öncelik **otomatik bağlantı anlamına gelmez** — tüm `connect` yolları onay kapısından geçer.

| Öncelik | Sağlayıcı | Rol |
|---------|-----------|-----|
| **1** | Qiskit, Qiskit Aer | İlk yol arkadaşı — yerel framework + sim spike |
| **2** | IBM Quantum (cloud) | İlk bulut dalı — yerel Aer kanıtlandıktan sonra |
| — | Azure, Braket, diğerleri | Sonraki dallar |

Hikâye: [`lumos-quantum-first-companion.md`](./lumos-quantum-first-companion.md).

---

## Bulut sağlayıcılar (cloud)

| Sağlayıcı | Tür | `connect_priority` | Auth modeli | Maliyet riski | Veri egress riski | Onay katmanı | Durum | Demo-safe vs production |
|-----------|-----|-------------------|-------------|---------------|-------------------|--------------|-------|-------------------------|
| **IBM Quantum** | cloud | **2** | IBM Cloud API key / `QiskitRuntimeService` token | **Yüksek** — QPU/saas dakika ücreti | Orta — devre ve sonuçlar IBM bulutunda | needs-owner | stub | Salt okunur backend keşfi hazır; `IBM_QUANTUM_API_KEY` gerekli; job göndermez |
| **Azure Quantum** | cloud | — | Azure AD + workspace resource | **Yüksek** — reserved / pay-per-shot | Orta — Azure tenant sınırı | needs-owner | stub | Salt okunur target keşfi hazır; `AZURE_QUANTUM_RESOURCE_ID` ve Azure kimliği gerekli; job göndermez |
| **Amazon Braket** | cloud | — | AWS IAM + Braket rolü | **Yüksek** — device/time billing | Orta — sonuçlar S3 / AWS | needs-owner | stub | Salt okunur device keşfi hazır; AWS credential chain ve region gerekli; job göndermez |
| **Google Quantum AI** | cloud | — | Google Cloud IAM + Quantum Engine API | **Yüksek** — processor zamanı | Orta — GCP projesi | needs-owner | stub | Salt okunur processor keşfi hazır; erişim Google tarafından kısıtlıdır; job göndermez |

---

## Çerçeveler (framework)

| Sağlayıcı | Tür | `connect_priority` | Auth modeli | Maliyet riski | Veri egress riski | Onay katmanı | Durum | Demo-safe vs production |
|-----------|-----|-------------------|-------------|---------------|-------------------|--------------|-------|-------------------------|
| **Qiskit** | framework | **1** · *ilk yol arkadaşı* | Yerel pip; bulut için IBM token (ayrı) | Düşük (yerel) / Yüksek (Runtime backend) | Düşük (yerel) / Orta (bulut backend) | auto-doc (katalog) · needs-owner (`connect`) | stub | OSS: `qiskit`/`qiskit-aer` opsiyonel import; readiness/entropy envanterinde. **İlk connect spike** framework kökü. Prod: backend seçimi onaylı |
| **Cirq** | framework | — | Yerel pip; Google Quantum için GCP auth | Düşük (yerel) / Yüksek (Google cloud) | Düşük / Orta | auto-doc · needs-owner (cloud) | planned | OSS: katalog only. Prod: private adapter |
| **PennyLane** | framework | — | Yerel pip; plugin başına bulut auth | Düşük–Orta (plugin'e bağlı) | Plugin'e bağlı | auto-doc · needs-owner | planned | OSS: katalog only. Prod: plugin allowlist |

---

## Simülatörler (simulator)

| Sağlayıcı | Tür | `connect_priority` | Auth modeli | Maliyet riski | Veri egress riski | Onay katmanı | Durum | Demo-safe vs production |
|-----------|-----|-------------------|-------------|---------------|-------------------|--------------|-------|-------------------------|
| **Qiskit Aer** | simulator | **1** · *ilk yol arkadaşı* | Yok (yerel CPU/GPU) | **Düşük** | **Düşük** (yerel) | needs-owner (`connect`) · auto-doc (katalog) | stub | OSS: onaylı `connect` spike (`qiskit_aer` / `qiskit_aer_sim`); opsiyonel `pip install 'lumos-core[quantum]'` veya `requirements-quantum.txt`. Entropy Lab deneysel; simülatör ≠ QPU. **İlk sim connect spike** — API anahtarı yok, otomatik bağlantı yine yok. Prod: kaynak limiti politikası |
| **Yerel CPU/GPU simülatörleri** | simulator | — | Yok | Düşük | Düşük | auto-doc | planned | OSS: genel not. Prod: sandbox CPU/RAM kotası |
| **Bulut yönetilen simülatörler** | simulator | — | Bulut sağlayıcı auth (IBM/Azure/AWS/GCP) | Orta–Yüksek | Orta | needs-owner | planned | OSS: yok. Prod: sim ≠ QPU etiketi zorunlu |

---

## Araştırma / salt okunur katalog (research)

| Sağlayıcı | Tür | Auth modeli | Maliyet riski | Veri egress riski | Onay katmanı | Durum | Demo-safe vs production |
|-----------|-----|-------------|---------------|-------------------|--------------|-------|-------------------------|
| **NIST PQC / standart izleme** | research | Yok (public doküman) | Yok | Yok | auto-doc | stub | OSS: ADR-013 readiness raporunda «izleniyor / uygulanmıyor». Prod: aynı — uygulama ayrı karar |
| **Kuantum benchmark / makale indeksi** | research | Yok (curated link list) | Yok | Düşük (kullanıcı tıklar) | auto-doc | planned | OSS: statik referans listesi hedefi. Prod: tenant curated feed |
| **Quantum Readiness envanteri** | research | Yerel dosya taraması | Yok | Yok (yerel) | auto-doc | stub | OSS: `scan_quantum_readiness` — **bağlantı değil**, PQC hazırlık |

---

## Özet sayılar

| Metrik | Değer |
|--------|-------|
| **Toplam katalog satırı** | **13** |
| Cloud | 4 |
| Framework | 3 |
| Simulator | 3 |
| Research | 3 |
| `stub` durumunda | 8 |
| `planned` durumunda | 4 |
| `none` (aktif prod bağlantı) | 0 |

### Onay katmanı dağılımı

| Katman | Satır sayısı (birincil) |
|--------|-------------------------|
| auto-doc | 6 |
| needs-owner | 10 |
| blocked (politika — tüm `connect`/`discover` harici) | Tüm harici hesaplama yolları |

> Bir satır hem `auto-doc` (yerel) hem `needs-owner` (bulut backend) taşıyabilir; tabloda birincil OSS davranışı esas alınmıştır.

---

## Entropy Lab ayrımı (tekrar)

| Kayıt | Quantum Layer kataloğunda | Entropy Lab |
|-------|---------------------------|-------------|
| Qiskit Aer | simulator / stub | Aktif deneysel sağlayıcı |
| IBM Runtime | cloud / stub | Aktif deneysel sağlayıcı (token varsa) |

Entropy sağlayıcı seçimi veya fallback **bu katalog üzerinden otomatik bağlanmaz**; ADR-013 sınırı geçerlidir.

---

*Canlı fiyat, kota veya cihaz listesi bu dosyada tutulmaz; değişiklikler mimari belge ve private ops vault ile senkronize edilir.*
