# Temizlenmesi gerekenler — liste

*Oluşturulma: 2025-03-19. ADIM 2 öncesi referans.*

---

## 1. Kesin temizlik (hiçbir kod bunlara referans vermiyor)

### 1.1 `src/` altındaki `.bak` / `.bak_*` dosyaları

| Dosya | Not |
|-------|-----|
| `src/context/context.py.bak` | Yedek |
| `src/context/context.py.bak_gate` | Yedek |
| `src/context/context.py.bak_unlock` | Yedek |
| `src/core/lumos.py.bak_unlock` | Yedek |
| `src/engine/model_client.py.bak_full` | Yedek |
| `src/memory/memory.py.bak` | Yedek |
| `src/memory/memory.py.bak2` | Yedek |
| `src/memory/schema.py.bak` | Yedek |
| `src/memory/secure_store.py.bak2` | Yedek |
| `src/policy/offline_engine.py.bak` | Yedek |
| `src/policy/offline_engine.py.bak_fallback_cli` | Yedek |
| `src/policy/offline_engine.py.bak_lock_cli` | Yedek |
| `src/policy/offline_engine.py.bak_unlock` | Yedek |
| `src/policy/rules.py.bak` | Yedek |
| `src/policy/rules.py.bak_gate` | Yedek |
| `src/security/keystore.py.bak2` | Yedek |
| `src/scripts/init_keystore.py.bak_fix` | Yedek |

**Toplam:** 17 dosya. Hiçbiri `import` edilmiyor; güvenle silinebilir veya önce `archive/` altına taşınıp sonra silinebilir.

---

### 1.2 `src/security.bak_lock/` klasörü (tamamı)

| Öğe | Açıklama |
|-----|----------|
| `src/security.bak_lock/crypto.py` | Eski yedek |
| `src/security.bak_lock/identity.py` | Eski yedek |
| `src/security.bak_lock/keystore.py` | Eski yedek |
| `src/security.bak_lock/keystore.py.bak2` | Yedek içinde yedek |
| `src/security.bak_lock/permissions.py` | Eski yedek |

Docs’ta “legacy/backup, production’da kullanılmaz” diye geçiyor; kodda referans yok. **Klasörün tamamı** silinebilir veya `archive/backups_pre_stabilization/src/security.bak_lock/` gibi bir yere taşınıp sonra `src/` altından kaldırılabilir.

---

### 1.3 Diğer tek dosyalar

| Öğe | Açıklama |
|-----|----------|
| **lumos-quantum/** | Boş/placeholder; kuantum modülü için rezerve alan (iptal değil — bkz. ADR-001). Temizlikte silinmemeli; durum ADR-001 ile takip edilir. |
| **YARIN_DEVAM.txt** | Geçici not. Commit’e girmemeli; silinebilir veya içerik başka yere taşınır. |
| **PROJE_DOSYA_LISTESI.txt** | Eski liste (.lumos, __pycache__ karışık). `docs/PROJE_HARITA_ADIM1.md` ile ikame edildi; kaldırılabilir. |
| **package-lock.json** (repo kökü) | Backend kendi `backend/package-lock.json` kullanıyor. Root’taki untracked; gereksizse silinir veya `.gitignore`’a eklenir. |

---

## 2. Arşiv (silme zorunlu değil)

| Öğe | Açıklama |
|-----|----------|
| **archive/refactor_history/** | 12 adet eski `main.py` yedeği. Bilinçli arşiv; istenirse olduğu gibi bırakılır veya sıkıştırılıp tek arşiv dosyası yapılır. |

---

## 3. Commit / repo disiplini (temizlik değil, hatırlatma)

- **backend/.env** — Zaten commit’e girmemeli; `.gitignore`’da olmalı (kontrol et).
- **logs/** — `.gitignore`’da; commit’e girmez.
- **.lumos/** — `.gitignore`’da; canlı state, commit’e girmez.

---

## 4. Özet sayılar

| Kategori | Adet / kapsam |
|----------|----------------|
| `src/` içi .bak dosyaları | 17 dosya |
| `src/security.bak_lock/` | 1 klasör, 5 dosya |
| lumos-quantum | 1 klasör |
| YARIN_DEVAM.txt | 1 dosya |
| PROJE_DOSYA_LISTESI.txt | 1 dosya |
| Root package-lock.json | 1 dosya (opsiyonel) |
| archive/refactor_history | İsteğe bağlı; silinmeyebilir |

---

## 5. Önerilen sıra (ADIM 2 uygulama)

1. **Önce yedek al (isteğe bağlı):** Tüm .bak ve security.bak_lock’u `archive/backups_pre_stabilization/` altında path’leri koruyarak kopyala; sonra asıllarını sil.
2. **src/ içi .bak’ları sil** (veya 1’deki arşive taşıyıp sil).
3. **src/security.bak_lock/** klasörünü kaldır (veya arşive taşıyıp kaldır).
4. **lumos-quantum/** — Silme; placeholder olarak bırak (durum: ADR-001 Güncel durum).
5. **YARIN_DEVAM.txt** — İçerik gerekliyse başka yere taşı; değilse sil.
6. **PROJE_DOSYA_LISTESI.txt** — Sil (yerine PROJE_HARITA_ADIM1.md var).
7. **Root package-lock.json** — Kullanılmıyorsa sil veya `.gitignore`’a ekle.
8. **archive/refactor_history** — Dokunma veya tek .zip/.tar ile sıkıştır; silme zorunlu değil.

Bu liste, ADIM 2 temizlik işlerinde tek referans olarak kullanılabilir.
