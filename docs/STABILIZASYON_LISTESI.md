# Stabilizasyon listesi

*Kör test bırakıp sabit kontrol noktalarına geçiş. Referans: 2025-03-19.*

---

## 1. API sağlık kontrolü (sabit)

Backend’in **temel ayakta** sayılması için aşağıdaki endpoint’ler **kontrol noktası** kabul edilir. Hepsi 200 dönüyorsa backend temel olarak ayaktadır.

| Endpoint | Açıklama |
|----------|----------|
| **GET /posts/feed** | Feed skoru ile sıralı liste (limit destekli). |
| **GET /posts/rated-high** | Yüksek ortalama puanlı postlar (minVotes, limit). |
| **GET /posts/rated-low** | Düşük puan (1–2★) yoğunluğu yüksek postlar (minVotes≥2, limit). |

- **GET /health** — Sunucu ayaktaysa 200 + `{ ok: true, checkpoints: ["/posts/feed", "/posts/rated-high", "/posts/rated-low"] }`. Tam sağlık doğrulaması için bu üç checkpoint’e ayrıca GET atılır.
- Mevcut test: `test_api.sh` (feed, rated-high, rated-low kullanıyor).

---

## 2. Temizlik — silinecekler ayrımı

Ayrıntılı liste: **`docs/TEMIZLENMESI_GEREKENLER_LISTESI.md`**.

### Kontrol noktası adayları (özet)

| Kategori | İçerik |
|----------|--------|
| **.bak / _bak_*** | `src/` altındaki `.bak`, `.bak_gate`, `.bak_unlock`, `.bak_full`, `.bak_fix`, `.bak2` vb. — toplam 17 dosya (liste dokümanda). |
| **security.bak_lock** | `src/security.bak_lock/` klasörü (crypto, identity, keystore, permissions + keystore.py.bak2). Production’da kullanılmaz; referans yok. |
| **Eski / belirsiz** | `lumos-quantum/` (boş/placeholder — repo kökünde fiziksel dizin yok; bkz. [^lumos-quantum-drift]), `YARIN_DEVAM.txt`, `PROJE_DOSYA_LISTESI.txt`, repo kökündeki `package-lock.json` (opsiyonel). |
| **Arşiv (silme zorunlu değil)** | `archive/refactor_history/` — isteğe bağlı. |

Uygulama sırası ve “önce arşive taşı” seçeneği `TEMIZLENMESI_GEREKENLER_LISTESI.md` §5’te yazılı.

---

## 3. Frontend / panel girişi

| Öğe | Değer |
|-----|--------|
| **Giriş dosyası** | **`panel/index.html`** |
| **Açılış** | Tarayıcıda `panel/index.html` dosyasını açmak veya bir HTTP sunucusu ile `panel/` kökünü servis etmek. |
| **Backend** | `cd backend && npm start` — varsayılan `http://127.0.0.1:3000`. Panel, `LUMOS_POSTS_API_BASE` veya `localStorage.lumos_posts_api_base` ile base URL alır; yoksa `http://127.0.0.1:3000` kullanılır. |
| **Yüklenen script sırası** | `js/contracts.js` → `js/feed-api.js` → `js/fixtures.js` → `js/state_inject.js` → `js/backend-bridge.js` → `js/app.js`. |
| **Akış ekranı** | `#feed` — doğrudan **GET /posts/feed** çağrısı (mock yok). Hash routing ile ekranlar arası geçiş. |

Detay: `panel/README.md`.

[^lumos-quantum-drift]: 2026-06-21 — `lumos-quantum/` bu listede tarihsel placeholder; repo kökünde fiziksel dizin yok (ADR-001, ADR-013).
