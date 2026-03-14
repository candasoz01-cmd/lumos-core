# Lumos Panel v1 — İskelet

Kullanıcı panelinin ilk bilgi mimarisi ve ekran iskeleti. Ana backend/sink/guard hattına dokunmaz; ayrı çalışma alanı.

## Çalıştırma

- **Tarayıcıda:** `panel/index.html` dosyasını doğrudan açın (file:// veya yerel bir HTTP sunucusu ile).
- Örnek (Python 3): `python -m http.server 8080` ile repo kökünden `http://localhost:8080/panel/` açılabilir.
- Gerçek API entegrasyonu yok; tüm veri mock.

## Ekran haritası (Panel v1)

| Ekran            | Hash        | Açıklama (placeholder)        |
|------------------|------------|-------------------------------|
| Dashboard        | `#dashboard` | Özet: mod, kilit, görev sayısı, sandbox |
| Görevler         | `#tasks`      | Görev listesi                 |
| Sandbox durumu   | `#sandbox`   | Sandbox açık/kapalı, yazım hedefi |
| Identity/Keystore| `#identity`  | Kimlik ve keystore durumu     |
| Config           | `#config`    | Ayarlar                       |
| Trash/Silinenler | `#trash`     | .lumos/trash özeti            |
| Logs/Activity    | `#logs`      | Son aktivite / log            |

## Yapı

- **Sol menü:** `#nav-menu` — tüm ekranlara hash linkleri.
- **Üst bar:** `#topbar-status` — mock durum metni (mod, kilit, sandbox).
- **Ana içerik:** `#main-content` — hash’e göre tek ekran placeholder’ı.

## Bileşen haritası

- `index.html`: Layout kabuğu (topbar, sidebar, main).
- `css/app.css`: Grid layout, menü ve placeholder stilleri.
- `js/app.js`: SCREENS haritası, mockState, hash routing, her ekran için render* placeholder fonksiyonları (Dashboard, Tasks, Sandbox, Identity, Config, Trash, Logs).

## Dokunulmayan alanlar

- `src/`, `web/app.py`, `tests/`, guard/sink/runtime/security akışları — panel bunlara bağlı değil.
