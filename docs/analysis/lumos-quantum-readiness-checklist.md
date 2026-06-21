# Lumos Quantum Readiness — Envanter ve Rapor Checklist

> **Lumos Quantum Readiness yerel, salt-okunur, kanıtlı kuantum sonrası güvenlik hazırlık tarayıcısıdır.**

| Alan | Değer |
|------|-------|
| Durum | **Faz-2 kısmi (docs-kapalı)** — yerel tarayıcı, CLI, panel GET + live fields + migration tables (#468–#482); `hazırlık_raporu` badge opsiyonel/ertelendi |
| Tarih | 2026-06-21 |
| İlgili | [ADR-013](../decisions/ADR-013-lumos-quantum-security-readiness.md) |

Bu belge Faz-1'de **salt okunur envanter ve rapor şablonu** olarak başladı. Faz-2 yerel tarayıcı (`scan_quantum_readiness`), `lumos quantum-readiness` CLI (#479), panel `GET /quantum-readiness` ve kuantum sekmesi live UI (#480, #482) aynı şemayı döner; tablo satırları tarayıcı çıktısı ile güncellenebilir.

**Sınır:** Kuantum bilgisayar, kuantum-güvenli veya "quantum secure" iddiası yok. Entropy Lab ayrı deneysel bölümdür.

---

## 1. Şifreleme / imza / anahtar türleri (`crypto_inventory`)

| Bileşen | Konum | Tür | Algoritma / mekanizma | Kuantum sonrası not | PQC durumu | Durum (Faz-1) | Kanıt |
|---------|-------|-----|----------------------|---------------------|------------|---------------|-------|
| Şifreleme (simetrik) | `src/security/crypto.py` | encryption | AES-GCM-256 | Klasik simetrik — HNDL riski orta | Uygulanmıyor | Biliniyor | Kod |
| Anahtar türetme | `src/security/crypto.py` | key_derivation | Scrypt | Klasik KDF | Uygulanmıyor | Biliniyor | Kod |
| Keystore root | `src/security/keystore.py` | key_storage | 256-bit random | Entropy kaynağına bağlı | Uygulanmıyor | Biliniyor | Kod |
| İstek imzası | `src/security/request_signer.py` | nonce/integrity | nonce + seed | Entropy kaynağına bağlı; ayrı imza algoritması yok | Uygulanmıyor | Biliniyor | Kod |

---

## 2. Uzun ömürlü veri (`long_lived_data`)

| Veri sınıfı | Konum / store | Saklama | Crypto at rest | HNDL riski | Durum (Faz-1) | Kanıt |
|-------------|---------------|---------|----------------|------------|---------------|-------|
| Keystore | `src/security/keystore.py` | Indefinite (kullanıcı silene kadar) | AES-GCM (via crypto modülü) | Orta — uzun ömürlü anahtar | Biliniyor | Kod |
| Workspace config | `.lumos/config/` | Indefinite | (şifreleme yok — düz metin varsayım) | Düşük (gizli anahtar içermemeli) | Kısmi | Sözleşme |
| Görev / log state | `.lumos/tasks/`, `.lumos/logs/` | Operasyonel | Düz metin JSON/JSONL | Düşük (içerik bağlı) | Biliniyor | Sözleşme |

---

## 3. Değiştirilmesi zor algoritma bağımlılıkları (`hard_to_change_deps`)

| Bileşen | Algoritma | Değiştirme maliyeti | Neden zor | Durum (Faz-1) | Kanıt |
|---------|-----------|---------------------|-----------|---------------|-------|
| `crypto.py` encrypt/decrypt | AES-GCM-256 | Yüksek | API yüzeyi + mevcut şifreli blob formatı | Biliniyor | Kod |
| `crypto.py` KDF | Scrypt | Yüksek | Mevcut passphrase türetilmiş anahtarlar | Biliniyor | Kod |
| Keystore format | 256-bit + AES wrapper | Yüksek | Dağıtılmış keystore dosyaları | Biliniyor | Kod |
| Entropy varsayılan | os.urandom | Düşük | Env ile değiştirilebilir; efektif kaynak probe gerekir | Biliniyor | Kod |

---

## 4. Kripto çeviklik düzeyi (`crypto_agility_level`)

| Kriter | Değerlendirme (Faz-1) | Not |
|--------|----------------------|-----|
| Algoritma soyutlama katmanı | Kısmi | Modül sınırları var; tek algoritma sabit |
| Konfig ile algoritma seçimi | Yok | Hard-coded AES-GCM / Scrypt |
| Versiyonlama / migration hook | Yok | PQC geçiş hook tanımsız |
| **Genel skala** | **Orta** | ADR-013 § crypto_agility_level |

---

## 5. Kuantum sonrası geçiş hazırlığı (`post_quantum_transition_readiness`)

| Konu | Durum (Faz-1) | Not |
|------|---------------|-----|
| `pqc_status` | `uygulanmiyor` | Kod entegrasyonu yok |
| NIST PQC farkındalığı | Evet | ADR/checklist referans |
| Hibrit (klasik+PQC) hazırlık | Hayır | Migration hook yok |
| Panel "kuantum dayanıklı" metni | Gelecek tense | İddia değil — ADR-001/013 hizalı |
| Geçiş engelleri | Format sabitliği, keystore migrasyonu, audit eksikliği | Checklist §7 |

---

## 6. Kanıtlı dosya / konfig bulguları (`evidenced_findings`)

| ID | Önem | Kategori | Özet | Dosya | Kanıt türü | Doğrulandı (Faz-1) |
|----|------|----------|------|-------|------------|-------------------|
| CR-001 | Orta | crypto | AES-GCM-256 klasik simetrik; PQC değil | `src/security/crypto.py` | code | Manuel |
| CR-002 | Orta | crypto | Scrypt KDF — kuantum sonrası değiştirme planı yok | `src/security/crypto.py` | code | Manuel |
| EN-001 | Yüksek | entropy | Sessiz fallback: qiskit_aer/ibm_runtime → os | `src/security/entropy/` | code | Manuel |
| EN-002 | Orta | entropy | Qiskit Aer simülatör — donanım değil | `src/security/entropy/providers/qiskit_aer.py` | code | Manuel |
| CF-001 | Düşük | config | `LUMOS_ENTROPY_PROVIDER` unset → os varsayılan | env / docs | config | Manuel |
| DOC-001 | Düşük | docs | PQC izleme; uygulama yok | ADR-013, bu checklist | docs | Manuel |

Faz-2: yerel tarama satır/snapshot ile `verified: true` işaretler.

---

## 7. Önceliklendirilmiş geçiş planı (`prioritized_migration_plan`)

| Öncelik | Adım | Hedef | Bağımlılık | Efor | Durum |
|---------|------|-------|------------|------|-------|
| P0 | Sessiz entropy fallback uyarısını readiness raporunda zorunlu göster | Entropy Lab bölümü | Faz-2 probe | S | `oneri` |
| P1 | Kripto envanter yerel tarama (panel GET / standalone script / CLI) | Tüm `crypto_inventory` | Faz-2 kısmi (#468, #469, #479) | M | `kismi` |
| P1 | Lumos CLI alt komutu (`quantum-readiness`) | CLI JSON çıktı | Faz-2 tamamlama | M | **uygulandı** (#479 — `lumos quantum-readiness`) |
| P1 | Panel kuantum sekmesi — live fields + migration tables | `generated_at`, `evidenced_findings`, `entropy_lab`, migration tabloları | Faz-2 panel UI | M | **uygulandı** (#480, #482) |
| P1 | Keystore / encrypted blob format versiyonlama taslağı | `hard_to_change_deps` | Ayrı ADR | L | `ertelendi` |
| P2 | NIST PQC aday izleme notu güncelleme | `post_quantum_transition_readiness` | — | S | `oneri` |
| P3 | Hibrit PQC POC (private/onaylı) | PQC uygulama | P1 + audit | L | `ertelendi` |

**Not:** Plan salt okunur öneridir; otomatik migrasyon veya kod değişikliği bu ADR kapsamında yok.

---

## Entropy Lab envanteri (deneysel — ayrı bölüm)

| Sağlayıcı | Env değeri | Konum | Donanım / simülasyon | Core dep | Fallback | Durum (Faz-1) | Kanıt |
|-----------|------------|-------|----------------------|----------|----------|---------------|-------|
| OS CSPRNG | `os` (varsayılan) | `providers/os_urandom.py` | OS kernel | Evet | Yok (referans) | Aktif (varsayılan) | Kod |
| Qiskit Aer | `qiskit_aer` | `providers/qiskit_aer.py` | **Simülatör — deneysel** | Hayır | Sessiz → `os` | Opsiyonel / çoğu kurulumda kapalı | Kod |
| IBM Runtime | `ibm_runtime` | `providers/ibm_runtime.py` | Harici backend (onaysız) | Hayır | Sessiz → `os.urandom` | Kapalı (credential yok) | Kod |

---

## Ortam ve operasyon

| Kontrol | Beklenen (Faz-1) | Not |
|---------|------------------|-----|
| `LUMOS_ENTROPY_PROVIDER` | Set değil veya `os` | Farklı değer → sessiz fallback riski |
| qiskit / qiskit-aer kurulu | Hayır (typical) | Import fail → OS |
| IBM token / `QiskitRuntimeService` | Yok | Public OSS |
| Readiness yerel tarama | Panel `GET /quantum-readiness` + `scripts/quantum_readiness_scan.py` + `lumos quantum-readiness` | **Uygulandı** (#468–#469, #479); panel live fields (#480, #482) |
| `hazırlık_raporu` genel durum badge | Opsiyonel — `tamamlandi` / `kısmi` / `doğrulanamadi` | **Ertelendi** — local_scan/docs rozetleri (#469, #475) yeterli; ayrı UI PR bekleniyor |
| Entropy birim testi | Yok | Faz-2+ |

---

## Rapor meta (Faz-1 şablon / Faz-2 tarayıcı)

| Alan | Faz-1 (manuel) | Faz-2 tarayıcı (`scan_quantum_readiness`) |
|------|----------------|-------------------------------------------|
| `report_type` | `quantum_readiness` | `quantum_readiness` |
| `scan_mode` | `docs_only` (manuel referans) | `local` |
| `read_only` | `true` | `true` |
| `evidence_basis` | `docs_only` | `local_scan` |
| `generated_at` | — | ISO-8601 (tarayıcı) |
| `crypto_agility_level` | `orta` | tarayıcı değerlendirmesi |
| `pqc_status` | `uygulanmiyor` | `uygulanmiyor` |
| `disclaimer` | Hazırlık raporu — kuantum güvenli veya kuantum bilgisayar iddiası taşımaz | aynı |

---

## Readiness rapor alanları özeti (panel Faz-2)

| Alan | Faz-1 kaynak | Faz-2 kaynak |
|------|--------------|--------------|
| Şifreleme / imza / anahtar türleri | §1 tablo | Yerel kod taraması |
| Uzun ömürlü veri | §2 tablo | Store path + metadata taraması |
| Zor değişen bağımlılıklar | §3 tablo | Kod + format analizi |
| Kripto çeviklik | §4 skala | Otomatik kriter puanı |
| PQC geçiş hazırlığı | §5 tablo | `izleme` + blocker listesi |
| Kanıtlı bulgular | §6 tablo | `evidenced_findings` JSON |
| Geçiş planı | §7 tablo | Salt okunur öneri (güncellenebilir) |
| Entropy Lab | Entropy envanteri | Probe + fallback uyarısı |
| Genel durum | `docs_only` | `local_scan` (panel GET, CLI veya script başarılı) |
| Panel live fields | Statik § tablolar | `generated_at`, `evidenced_findings`, `entropy_lab` (#480) |
| Migration tabloları | §2–§3, §7 statik | `long_lived_data`, `hard_to_change_deps`, `prioritized_migration_plan` (#482) |
| `hazırlık_raporu` badge | — | **Ertelendi (opsiyonel)** — ADR-013 § Panel alanları |

---

**Kullanım:** `lumos quantum-readiness`, `python -m scripts.quantum_readiness_scan` veya panel kuantum sekmesi (`GET /quantum-readiness` live fetch). **`hazırlık_raporu` genel durum badge'i opsiyonel/ertelendi** — ayrı UI PR bekleniyor. Entropy **davranışı** değiştirilmez; Entropy Lab readiness raporunda **deneysel** etiketli kalır.
