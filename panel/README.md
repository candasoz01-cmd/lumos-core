# Lumos Panel v1

**Kapsam:** Mock tabanlı operatör paneli. Backend veya canlı API yok; tüm veri `js/app.js` içindeki `mockState` ile beslenir. Hash routing ile tek sayfada ekranlar arası geçiş yapılır.

## Çalıştırma

- **Doğrudan:** `panel/index.html` açın (`file://`).
- **HTTP ile:** Repo kökünden `python3 -m http.server 8080` → `http://localhost:8080/panel/`
- **Yönlendirme:** `#dashboard`, `#tasks`, `#sandbox`, `#config`, `#identity`, `#keystore`, `#trash`, `#logs`, `#system`

## Hazır ekranlar

| Ekran           | Hash         |
|-----------------|--------------|
| Gösterge Paneli | `#dashboard` |
| Görevler        | `#tasks`     |
| Korumalı Alan   | `#sandbox`   |
| Yapılandırma    | `#config`    |
| Kimlik          | `#identity`  |
| Anahtar Kasası  | `#keystore`  |
| Silinenler      | `#trash`     |
| Kayıtlar        | `#logs`      |
| Sistem Durumu   | `#system`    |

Ortak bileşenler: Sidebar, Topbar, StatusBadge, MetricCard, SectionCard, EmptyState, EventList, DetailPanel, ViewHeader. Detay ve mock state yapısı için `js/app.js` ve `css/app.css` kaynak dosyalarına bakın.
