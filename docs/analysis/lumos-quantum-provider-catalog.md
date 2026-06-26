# Lumos Quantum Layer — Sağlayıcı Kataloğu

| Alan | Değer |
|------|-------|
| Durum | **Planlı** — salt okunur katalog; canlı API yok |
| Tarih | 2026-06-26 |
| Mimari | [`lumos-quantum-layer-architecture.md`](./lumos-quantum-layer-architecture.md) |
| Kod stub | `src/integrations/quantum_registry.py` |

**Onay katmanları (özet):**

| Katman | Anlam | Örnek |
|--------|-------|-------|
| **auto-doc** | Yerel dokümantasyon / katalog; dış etki yok | `list_catalog`, araştırma linkleri |
| **needs-owner** | Kimlik bilgisi, ücret veya dış hesaplama potansiyeli | `connect`, `discover` (harici), credential vault |
| **blocked** | Otonom veya onaysız yasak | Otonom job submit, sessiz token yazma |

**Durum değerleri:** `planned` · `stub` · `none`

---

## Bulut sağlayıcılar (cloud)

| Sağlayıcı | Tür | Auth modeli | Maliyet riski | Veri egress riski | Onay katmanı | Durum | Demo-safe vs production |
|-----------|-----|-------------|---------------|-------------------|--------------|-------|-------------------------|
| **IBM Quantum** | cloud | IBM Cloud API key / `QiskitRuntimeService` token | **Yüksek** — QPU/saas dakika ücreti | Orta — devre ve sonuçlar IBM bulutunda | needs-owner | stub | OSS: metadata only; Entropy Lab'de opsiyonel runtime probe (deneysel, üretim değil). Prod: IAM + billing guard gerekir |
| **Azure Quantum** | cloud | Azure AD + workspace resource | **Yüksek** — reserved / pay-per-shot | Orta — Azure tenant sınırı | needs-owner | planned | OSS: yok. Prod: enterprise policy + maliyet kotası |
| **Amazon Braket** | cloud | AWS IAM + Braket rolü | **Yüksek** — device/time billing | Orta — sonuçlar S3 / AWS | needs-owner | planned | OSS: yok. Prod: AWS Organizations guardrails |
| **Google Quantum AI** | cloud | Google Cloud IAM + Quantum Engine API | **Yüksek** — processor zamanı | Orta — GCP projesi | needs-owner | planned | OSS: yok. Prod: quota + VPC-SC değerlendirmesi |

---

## Çerçeveler (framework)

| Sağlayıcı | Tür | Auth modeli | Maliyet riski | Veri egress riski | Onay katmanı | Durum | Demo-safe vs production |
|-----------|-----|-------------|---------------|-------------------|--------------|-------|-------------------------|
| **Qiskit** | framework | Yerel pip; bulut için IBM token (ayrı) | Düşük (yerel) / Yüksek (Runtime backend) | Düşük (yerel) / Orta (bulut backend) | auto-doc (yerel) · needs-owner (Runtime) | stub | OSS: `qiskit`/`qiskit-aer` opsiyonel import; readiness/entropy envanterinde. Prod: backend seçimi onaylı |
| **Cirq** | framework | Yerel pip; Google Quantum için GCP auth | Düşük (yerel) / Yüksek (Google cloud) | Düşük / Orta | auto-doc · needs-owner (cloud) | planned | OSS: katalog only. Prod: private adapter |
| **PennyLane** | framework | Yerel pip; plugin başına bulut auth | Düşük–Orta (plugin'e bağlı) | Plugin'e bağlı | auto-doc · needs-owner | planned | OSS: katalog only. Prod: plugin allowlist |

---

## Simülatörler (simulator)

| Sağlayıcı | Tür | Auth modeli | Maliyet riski | Veri egress riski | Onay katmanı | Durum | Demo-safe vs production |
|-----------|-----|-------------|---------------|-------------------|--------------|-------|-------------------------|
| **Qiskit Aer** | simulator | Yok (yerel CPU/GPU) | **Düşük** | **Düşük** (yerel) | auto-doc | stub | OSS: Entropy Lab deneysel; simülatör ≠ QPU. Prod: kaynak limiti politikası |
| **Yerel CPU/GPU simülatörleri** | simulator | Yok | Düşük | Düşük | auto-doc | planned | OSS: genel not. Prod: sandbox CPU/RAM kotası |
| **Bulut yönetilen simülatörler** | simulator | Bulut sağlayıcı auth (IBM/Azure/AWS/GCP) | Orta–Yüksek | Orta | needs-owner | planned | OSS: yok. Prod: sim ≠ QPU etiketi zorunlu |

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
| `stub` durumunda | 5 |
| `planned` durumunda | 7 |
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
