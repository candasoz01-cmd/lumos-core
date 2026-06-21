# Lumos Quantum Security Readiness — Envanter Checklist

| Alan | Değer |
|------|-------|
| Durum | **Faz-1 referans** — manuel / docs-only |
| Tarih | 2026-06-21 |
| İlgili | [ADR-013](../decisions/ADR-013-lumos-quantum-security-readiness.md) |

Bu tablo Faz-1'de **salt okunur envanter şablonu**dur. Faz-2 probe bağlandığında `durum` ve `kanıt` sütunları otomatik doldurulabilir.

## Kripto envanteri

| Bileşen | Konum | Algoritma | Kuantum-tehdit notu | PQC durumu | Durum (Faz-1) | Kanıt |
|---------|-------|-----------|---------------------|------------|---------------|-------|
| Şifreleme | `src/security/crypto.py` | AES-GCM-256 | Klasik simetrik | Uygulanmıyor | Biliniyor | Kod |
| Anahtar türetme | `src/security/crypto.py` | Scrypt | Klasik KDF | Uygulanmıyor | Biliniyor | Kod |
| Keystore root | `src/security/keystore.py` | 256-bit random | Entropy kaynağına bağlı | Uygulanmıyor | Biliniyor | Kod |
| İstek imzası | `src/security/request_signer.py` | nonce/seed | Entropy kaynağına bağlı | Uygulanmıyor | Biliniyor | Kod |

## Entropy sağlayıcı envanteri

| Sağlayıcı | Env değeri | Konum | Donanım / simülasyon | Core dep | Fallback | Durum (Faz-1) | Kanıt |
|-----------|------------|-------|----------------------|----------|----------|---------------|-------|
| OS CSPRNG | `os` (varsayılan) | `providers/os_urandom.py` | OS kernel | Evet (`cryptography` yolu) | Yok (referans) | Aktif (varsayılan) | Kod |
| Qiskit Aer | `qiskit_aer` | `providers/qiskit_aer.py` | **Simülatör** | Hayır | Sessiz → `os` | Opsiyonel / çoğu kurulumda kapalı | Kod |
| IBM Runtime | `ibm_runtime` | `providers/ibm_runtime.py` | Harici backend (onaysız) | Hayır | Sessiz → `os.urandom` | Kapalı (credential yok) | Kod |

## Ortam ve operasyon

| Kontrol | Beklenen (Faz-1) | Not |
|---------|------------------|-----|
| `LUMOS_ENTROPY_PROVIDER` | Set değil veya `os` | Farklı değer → sessiz fallback riski |
| qiskit / qiskit-aer kurulu | Hayır (typical) | Import fail → OS |
| IBM token / `QiskitRuntimeService` | Yok | Public OSS |
| Panel readiness endpoint | Yok | Faz-2 |
| Entropy birim testi | Yok | Faz-2 |

## PQC izleme (uygulama yok)

| Konu | Durum | Not |
|------|-------|-----|
| NIST PQC standardizasyonu | İzleniyor | Kod entegrasyonu yok |
| Panel "kuantum dayanıklı" metni | Gelecek tense | İddia değil — ADR-001/013 hizalı |
| Hybrid / migration planı | Tanımsız | Ayrı ADR/onay gerekir |

## Readiness rapor alanları (panel Faz-2)

| Alan | Faz-1 kaynak | Faz-2 kaynak |
|------|--------------|--------------|
| Genel durum | `docs_only` | `local_probe` |
| Kripto envanteri | Bu tablo | Kod taraması |
| Aktif entropy | Env + kod varsayılanı | Probe |
| Fallback uyarısı | Zorunlu statik metin | Env ≠ efektif kaynak |
| PQC durumu | `izleme` | `izleme` |

---

**Kullanım:** Faz-1 PR sonrası manuel gözden geçirme; Faz-2'de probe çıktısı ile satır güncelleme. Entropy **davranışı** değiştirilmez.
