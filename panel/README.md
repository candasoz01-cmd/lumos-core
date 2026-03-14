# Lumos Panel v1 — Operatör Paneli İskeleti

**Amaç:** Teknik omurgayı (sink, guard, sandbox, trash, config, identity, keystore, TaskStore) yansıtan, Türkçe öncelikli, mock state ile çalışan operatör paneli. Backend’e bağlı nihai ürün değildir; **canlı veri entegrasyonu bu aşamada açık değildir.**

## Çalıştırma

- **Tarayıcıda doğrudan:** `panel/index.html` dosyasını açın (`file://`).
- **HTTP sunucusu ile:** Repo kökünden veya `panel/` içinden basit bir sunucu çalıştırın:
  - `python3 -m http.server 8080` → `http://localhost:8080/panel/`
- **Yönlendirme:** Hash routing kullanılır (`#dashboard`, `#tasks`, `#sandbox`, …). Sayfa yenilenmeden ekranlar arası geçiş yapılır.

## Ekranlar

| Ekran            | Hash        | Açıklama |
|------------------|------------|----------|
| Gösterge Paneli  | `#dashboard` | Korumalı alan durumu, yazım hedefi, koruma, son aktivite; son olaylar, uyarılar, hızlı geçişler |
| Görevler         | `#tasks`   | Görev listesi, detay paneli, çalıştırma notu, filtre |
| Korumalı Alan    | `#sandbox` | Kaynak (CLI/ENV/varsayılan), Sandbox Base, Writing Direction, Contract Status, çözümleme mantığı, guard kuralı, canlı/sandbox farkı |
| Yapılandırma     | `#config`  | Config özeti, yazım durumu, son aktivite |
| Kimlik           | `#identity`| Identity ready, son yazım, kapsam, guard sonucu |
| Anahtar Kasası   | `#keystore`| Hazır mı, şifreli durum, son güncelleme, yazım kapsamı |
| Silinenler       | `#trash`   | Trash Location, Last Move, Item Count, Scope; liste (Name, Original Path, Trash Path, Moved At, Scope) ve seçilen öğe detayı |
| Kayıtlar         | `#logs`    | Sekmeli filtre (Tümü, Görevler, Korumalı Alan, Yapılandırma, Silinenler, Kimlik, Anahtar Kasası, Koruma); kayıt listesi filtreye göre değişir |
| Sistem Durumu    | `#system`  | Workspace contract, task engine, sandbox, trash, config/identity/keystore sink, genel sağlık |

## Ortak bileşen mantığı

Ortak bileşen mantığı kuruldu; kopyala-yapıştır bloklar kaldırıldı. Tüm ekranlar aynı kart ve bölüm dilini kullanır. Tekrar kullanılabilir parçalar (`js/app.js` içinde factory fonksiyonları):

- **Sidebar** — Sol menü; `renderSidebar()` ile doldurulur.
- **Topbar** — Üst bar (sayfa başlığı, arama mock, temel path, rozetler); `renderTopbar()` ile doldurulur.
- **StatusBadge** — Durum rozeti (CANLI, KORUMALI ALAN, KORUMA AKTİF, vb.).
- **MetricCard** — Başlık + değer (+ isteğe bağlı teknik not).
- **SectionCard** — Bölüm başlığı + gövde HTML.
- **EmptyState** — Henüz veri yok / açıklama metni.
- **EventList** — Zamanlı olay listesi.
- **DetailPanel** — Başlık + detay gövdesi (ör. seçilen görev/silinen öğe).
- **ViewHeader** — Sayfa başlığı + alt başlık.

Dashboard, Korumalı Alan, Silinenler ve Kayıtlar ekranları ortak bileşenler ve helper’lar (renderMetricCards, renderSection, renderEmptyState) ile toparlandı; aynı kart/bölüm diline oturtuldu. Bu turda özellikle **Gösterge Paneli** ve **Korumalı Alan** ekranları güçlendirildi: Dashboard üst kartları (Korumalı Alan Durumu, Yazım Hedefi, Koruma Durumu, Son Aktivite) anlamlı alt açıklama ve mock değerlerle operasyon odaklı hale getirildi; Korumalı Alan ekranında Kaynak, Sandbox Base, Yazım Yönü ve Sözleşme Durumu üst kartlarda net gösteriliyor, Çözümleme Mantığı / Guard Kuralı / canlı–sandbox farkı bölümleri tek bakışta "nereye yazılıyor" sorusuna cevap verecek şekilde sıkılaştırıldı. Bu turda **Yapılandırma**, **Kimlik** ve **Anahtar Kasası** ekranları da aynı kalite seviyesine taşındı: üst kartlarda (Config özeti, yazım durumu, son aktivite; Identity ready, son yazım, hedef kapsam, guard sonucu; Keystore hazır mı, şifreli durum, son güncelleme, yazım kapsamı) ve alt bölümlerde sink/guard hattı veya görünürlük ilkesi net anlatılıyor; mock state (configSnapshot, identityState, keystore alanları) buna göre zenginleştirildi.

## Mock state yapısı

Mock state merkezileştirildi; tek kaynaktan (`mockState`) erişilir. Helper’lar: formatTime, getBadgeVariant, renderMetricCards, renderSection, renderEmptyState. Gerçek API yok.

- **appMode** — Bağlantı (online / offline).
- **sandboxMode**, **sandboxSource**, **writingBaseDir** — Korumalı alan ve yazım hedefi.
- **workspaceName**, **branchName**, **basePath** — Çalışma alanı bilgisi.
- **guardStatus** — Koruma durumu.
- **recentEvents** — Son olaylar (Dashboard).
- **warnings** — Uyarı / not listesi.
- **trashItems** — Silinenler listesi (name, originalPath, trashPath, movedAt, scope).
- **trashLocation**, **trashLastMove** — Trash konumu ve son taşıma.
- **logItems** — Kayıt satırları (id, kind, text, ts); sekme filtresine göre filtrelenir.
- **configSnapshot** — Config özeti (profil, workspace_root, writeStatus, lastActivity, lastActivityText).
- **identityState**, **identityLastWrite**, **identityTargetScope**, **identityGuardResult** — Kimlik durumu ve kapsam.
- **keystoreState**, **keystoreReady**, **keystoreLastUpdate**, **keystoreWriteScope** — Anahtar kasası durumu (anahtar ifşası yok).
- **systemHealth** — Çekirdek bileşen sağlık durumları.
- **taskList**, **selectedTaskId**, **selectedTrashId**, **logFilter** — Görev/silinen seçimi ve log filtresi (etkileşim).

## Yapı

- **index.html** — Üst bar, sol menü, alt bölüm (çalışma alanı, dal, mod), ana içerik alanı.
- **css/app.css** — Koyu tema, tutarlı spacing, kart/section/badge, split view, sekmeler, listeler.
- **js/app.js** — Merkezi mock state, ortak bileşenler, Sidebar/Topbar render, hash routing, ekran renderları, tıklama delegasyonu (görev/silinen seçimi, log sekmesi).

## Bilerek dokunulmayan alanlar

- `panel/` dışındaki tüm dosyalar.
- Backend, sink, guard, runtime, security hatları.
- Gerçek API, WebSocket, kimlik doğrulama, panelden kalıcı veri yazımı veya guard kuralı değiştirme.

## Teknik not

Panel yalnızca mock state ile beslenir. Canlı entegrasyon sonraki aşamada açılacaktır.
