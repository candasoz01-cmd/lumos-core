# Lumos Panel v1 — Operatör Paneli İskeleti

**Amaç:** Teknik omurgayı (sink, guard, sandbox, trash, config, identity, keystore, TaskStore) yansıtan, Türkçe öncelikli, mock state ile çalışan operatör paneli. Backend’e bağlı nihai ürün değildir; canlı veri entegrasyonu bu aşamada açık değildir.

## Çalıştırma

- **Tarayıcıda doğrudan:** `panel/index.html` dosyasını açın (`file://`).
- **HTTP sunucusu ile:** Repo kökünden veya `panel/` içinden basit bir sunucu çalıştırın; örneğin:
  - `python3 -m http.server 8080` → `http://localhost:8080/panel/`
- **Yönlendirme:** Hash routing kullanılır (`#dashboard`, `#tasks`, vb.). Sayfa yenilenmeden ekranlar arası geçiş yapılır.

## Ekranlar

| Ekran            | Hash        | Açıklama |
|------------------|------------|----------|
| Gösterge Paneli  | `#dashboard` | Özet kartlar, son olaylar, uyarılar, hızlı geçişler |
| Görevler         | `#tasks`   | Görev listesi, detay paneli, çalıştırma notu, filtre |
| Korumalı Alan    | `#sandbox` | Kaynak, sandbox base, yazım yönü, sözleşme, guard kuralı |
| Yapılandırma     | `#config`  | Config özeti, yazım durumu, son aktivite |
| Kimlik           | `#identity`| Identity ready, son yazım, kapsam, guard sonucu |
| Anahtar Kasası   | `#keystore`| Hazır mı, şifreli durum, son güncelleme, yazım kapsamı |
| Silinenler       | `#trash`   | Trash konumu, son taşıma, öğe sayısı, liste ve detay |
| Kayıtlar         | `#logs`    | Sekmeli filtre (Tümü, Görevler, Sandbox, …), kayıt listesi |
| Sistem Durumu    | `#system`  | Workspace contract, task engine, sandbox, trash, config/identity/keystore sink, genel sağlık |

## Yapı

- **index.html:** Üst bar (sayfa başlığı, arama mock, temel path, rozetler, hızlı aksiyon), sol menü, alt bölüm (çalışma alanı, dal, mod), ana içerik alanı.
- **css/app.css:** Koyu tema, kart/section/badge stilleri, split view, sekmeler, listeler.
- **js/app.js:** Merkezi mock state, hash routing, ortak bileşenler (ViewHeader, EmptyState, StatusBadge, MetricCard, SectionCard, EventList, DetailPanel), ekran renderları, basit etkileşimler (görev seçimi, silinen seçimi, log filtresi).

## Bilerek dokunulmayan alanlar

- `panel/` dışındaki tüm dosyalar.
- Backend, sink, guard, runtime, security hatları.
- Gerçek API, WebSocket, kimlik doğrulama, panelden kalıcı veri yazımı veya guard kuralı değiştirme.

## Teknik not

Panel yalnızca mock state ile beslenir. Canlı entegrasyon sonraki aşamada açılacaktır.
