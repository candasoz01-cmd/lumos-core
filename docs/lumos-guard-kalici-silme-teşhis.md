# Kalıcı silme yasağı ve trash hedefi — guard teşhis ve en dar paket

Bu belge, karar sözleşmesindeki kalıcı silme/trash kurallarının kod guard’ı için yapılan teşhis ve en dar ilk paketin sınırlarını tanımlar.

## 1. Guard gerektiren kod alanları

| Alan | Konum | Mevcut durum | Guard ihtiyacı |
|------|--------|--------------|----------------|
| **Kalıcı silme tetikleyicisi** | `src/main.py` route `gorev_sil` | `task_store.delete(tid)` doğrudan çağrılıyor; tek çağrı noktası bu. | Silme yalnızca “açık kullanıcı komutu” ile yapılmalı; başka yerden `delete()` çağrılırsa işlem yapılmamalı. |
| **Kalıcı silme uygulaması** | `src/task_engine/engine.py` `TaskStore.delete()` | Parametre yok; çağıran herkes silebilir. | Çağrı “kullanıcı kaynaklı” olmadan silme yapılmamalı (kod guard). |
| **Trash hedefi** | `src/main.py` | `trash_dir = base / "trash"` iki yerde (self_check, omurga oluşturma); sabit string dağınık. | Tek tanım; sistem başka trash dizini (trash2, deleted vb.) üretememeli. |
| **Arşiv → kalıcı silme** | `TaskStore.archive()` + `delete()` | Arşiv ayrı; silme sadece `gorev_sil` ile. Arşivlenen görev de `delete` ile silinebiliyor (testte kullanılıyor). | Arşivden kalıcı silmeye geçiş yine yalnızca kullanıcı komutu (gorev_sil) ile; mevcut tek giriş noktası aynı guard ile korunmalı. |
| **Geri döndürülemez işlem** | `profiles.py` `SECURITY_NEVER_AUTO` | Engine adım türünde `critical`/`external` reddediliyor; `delete()` engine adımından çağrılmıyor. | Engine tarafında ek guard gerekmez; silme sadece CLI’dan. Yine de `delete()` parametre guard’ı gelecekteki başka çağrı yollarını kapatır. |

## 2. Aktif risk noktaları

- **R1** — **Doğrudan delete çağrısı:** Yeni bir route veya otomatik job ileride `task_store.delete(id)` çağırırsa, kullanıcı onayı olmadan kalıcı silme yapılır. Risk: yüksek (tek satır ekleme).
- **R2** — **Trash path dağınıklığı:** Trash yolu sadece `base / "trash"` olarak main’de; başka modül “çöp” için farklı path (örn. `base / "deleted"`) kullanırsa sözleşme ihlali. Risk: orta (henüz başka kullanım yok).
- **R3** — **Silinen öğe trash’e gitmiyor:** Sözleşme “silinen/taşınan öğeler için yalnızca .lumos/trash/” diyor; mevcut kod silince doğrudan JSON’dan siliyor, trash’e yazmıyor. Bu turda “taşıma” veya purge eklenmeyecek; sadece guard (silme izni + tek trash tanımı) konacak.

## 3. Docs/rules vs kod guard ayrımı

| Kural | Şu an sadece docs/rules | Kod guard ile korunacak |
|-------|--------------------------|--------------------------|
| Doğrudan kalıcı silme yok | ✓ Karar + workspace sözleşmesi | ✓ `delete(..., user_initiated=True)` olmadan silme yapılmaz |
| Sadece sabit trash hedefi | ✓ Workspace sözleşmesi | ✓ Tek `trash_path(base)`; başka path üretilmez |
| Sistem yeni trash üretemez | ✓ Sözleşme metni | ✓ Trash yolu tek modülden; yeni dizin adı sabit constant |
| Kalıcı temizleme kullanıcı kararı | ✓ Sözleşme | ✓ Kalıcı silme = delete; delete yalnızca user_initiated ile |

## 4. En dar ilk guard paketi

1. **Sabit trash tanımı**  
   - `src/core/workspace_contract.py`: `LUMOS_TRASH_DIRNAME = "trash"`, `trash_path(base_dir) -> Path`.  
   - Tüm trash path ihtiyacı buradan; main’deki `base / "trash"` bu fonksiyonla değiştirilir.

2. **Kalıcı silme guard’ı**  
   - `TaskStore.delete(task_id, *, user_initiated: bool = False)`.  
   - `user_initiated is False` ise hiçbir değişiklik yapmadan `False` döner.  
   - Sadece `gorev_sil` path’inde `user_initiated=True` ile çağrılır.

3. **Test**  
   - `delete(..., user_initiated=False)` çağrısında silme yapılmadığı test edilir.  
   - Mevcut delete testleri `user_initiated=True` ile güncellenir.

## 5. Bilerek dokunulmayacak alanlar

- **Görev motoru (TaskEngine):** Adım yürütümü, `run_task`, `_execute_step` — değiştirilmez; silme zaten engine üzerinden yapılmıyor.
- **profiles.py / SECURITY_NEVER_AUTO:** Mevcut tanım ve testler korunur; ek guard burada değil, `TaskStore.delete` ve tek giriş noktasında.
- **Workspace omurgası:** tasks/, logs/, config/ dizin oluşturma mantığı aynı kalır; sadece trash path’i tek fonksiyondan alınır.
- **Purge / “çöpü kalıcı boşalt”:** Bu turda yok; kullanıcı kararı ile kalıcı temizleme ileride ayrı özellik.
- **Silinen görevi trash’e taşıma:** Bu turda yapılmaz; guard sadece “kim silebilir” ve “trash neresi” ile sınırlı.
- **UI / ek onay penceresi:** Kapsam dışı.

## 6. Önerilen uygulama sırası

1. `src/core/workspace_contract.py` ekle: `LUMOS_TRASH_DIRNAME`, `trash_path()`.
2. `src/main.py`: `trash_dir = base / "trash"` → `trash_path(base)`; `task_store.delete(tid)` → `task_store.delete(tid, user_initiated=True)`.
3. `src/task_engine/engine.py`: `TaskStore.delete(self, task_id, *, user_initiated: bool = False)`; False ise return False.
4. `tests/test_task_engine.py`: delete çağrılarına `user_initiated=True` ekle; yeni test: `user_initiated=False` ile silme yapılmaz.
5. Mevcut testleri çalıştır; CI yeşil.
