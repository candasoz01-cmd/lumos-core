# UI paneli — Görevler sekmesi ve `POST /task`

## Aktif köprü kaynağı (tek doğru uygulama)

- **Modül:** `packages/kando_bridge/src/kando_bridge/server.py` (`kando_bridge.server`); testler buradan import eder.
- **Çalıştırma:** `python -m kando_bridge` (paket kurulu venv) veya repoda `python3 scripts/kando_bridge_server.py` — script yalnızca `sys.path` ekleyip aynı `main()` çağrısını yapar; kopya sunucu kodu yok.

## Önceki davranış (yalnız yerel)

- Görevler listesi `localStorage` (`lumos_panel_gorevler_list_v1`) ve bellekteki `panelGorevlerTasks` ile tutulur.
- Ekleme: başlık doğrulama → `push` → `persistPanelGorevlerTasks()` → `render()`.
- Köprüye istek yoktu; görev yalnızca tarayıcıda kalırdı.

## Güncel davranış (yerel önce, köprü sonra)

- Yerel akış **aynı**: görev önce listeye yazılır, kalıcı yerel kayıt ve UI güncellenir.
- Liste satırında `bridgeLast.lastBridgeAt` varsa **“Son köprü:”** satırı (tarih + kısaltılmış route) gösterilir; detay panelinde route, source, accepted, result_file, execution_file ve son işlem zamanı yer alır; eski kayıtlarda bu alanlar **—** olur.
- Ardından tarayıcı `POST {BRIDGE_BASE_URL}/task` çağırır (upload ile aynı köprü tabanı: `PUBLIC_LUMOS_PANEL_UPLOAD_URL` üzerinden `BRIDGE_BASE_URL`).
- JSON gövde: `goal` (görev metni), `source: "panel_gorevler"`, `priority`, `status` (panel meta; köprü yürütmesi için zorunlu değil).
- `X-Kando-Token`: sohbet ve dosya yükleme ile aynı başlık; `KANDO_BRIDGE_SECRET` açıksa köprü bunu doğrular.
- Ağ hatası, HTTP hata kodu veya `accepted: false` yanıtında kullanıcıya kısa uyarı gösterilir; **yerel liste geri alınmaz** (görev zaten kaydedilmiş kabul edilir).

## Köprü tarafı (`_resolve_task_routing`)

- JSON için gövde metni `task` veya `goal` alanından okunur (`goal` panel ile uyumludur).
- Normalde `file` yoksa metinden ilk `path.ext` benzeri parça **dosya yolu sanılarak** `direct_patch` moduna düşülebilirdi.
- `source === "panel_gorevler"` iken bu çıkarım **yapılmaz**; böylece panel başlığındaki dosya adı geçen ifadeler yanlışlıkla hedef dosya patch’i olarak yorumlanmaz ve görev **agent** metnine gider.

## Manuel test

1. `python3 scripts/kando_bridge_server.py` veya `python -m kando_bridge` (aynı sunucu).
2. `npm --prefix ui run dev` → panelde Görevler’den görev ekle.
3. `.lumos/outbox` altında `last_result.json` / `last_execution.json` veya ilgili çıktıların güncellenmesini kontrol et (ortam ve gate’e bağlı).
