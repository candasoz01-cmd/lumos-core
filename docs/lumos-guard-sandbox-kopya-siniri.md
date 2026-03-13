# Sandbox / kopya alanı sınırı — dördüncü guard paketi teşhis ve tasarım

Bu belge, Lumos’un dördüncü gerçek guard paketini (“sandbox/kopya alanı sınırı”) tanımlar. Amaç: geliştirme/deneme alanı ile dokunulmaz çekirdek alanların net ayrılması; sistem kendi üzerinde çalışırken canlı çekirdeğe doğrudan değil, tanımlı kopya/sandbox mantığına bağlı kalması.

**Referans:** `docs/lumos-karar-sozlesmesi.md` §4, `.cursor/rules/lumos-karar-ozet.mdc`, `docs/lumos-sozlesme-uygulama-plani.md`, mevcut kalıcı silme/trash, açık onay ve çekirdek overwrite guard’ları.

---

## 1. Guard gerektiren kod alanları

### 1.1 Yazma / overwrite potansiyeli olan geliştirme alanları

| Alan | Konum | Ne yazıyor | Canlı çekirdek mi |
|------|--------|------------|-------------------|
| Görev deposu | `task_engine/engine.py` — `TaskStore._save()` | `base_dir/tasks.json` | Evet (canlı state) |
| Notlar | `memory/secure_store.py` — `SecureNotesStore.save()` | `base_dir/notes.enc.json` | Evet |
| Alias | `security/aliases.py` — `save_aliases()` | `base_dir/aliases.json` | Evet |
| Presence config | `security/presence_lock.py` — `save_presence_cfg()` | `base_dir/presence.json` veya config içi | Evet |
| Kimlik | `security/identity.py` | `identity_file` (kimlik state) | Evet (güvenlik) |
| Keystore | `security/keystore.py` | `keystore_file` | Evet (güvenlik) |
| Log | `security/presence_lock.py` (logp.write_text) + main/log akışları | `logs/` altı | Evet |

Tüm bu noktalar şu an tek bir “canlı” base (`.lumos`) üzerinden yazıyor; sandbox/kopya modu yok. Sandbox açıldığında: aynı yazıcıların “hedef base”i ya canlı ya sandbox olmalı; sandbox seçiliyken bu path’lere **canlı** base üzerinden yazılmamalı.

### 1.2 Canlı çekirdek dosya / path’ler (overwrite yasağı hedefi)

`core/workspace_contract.py` içinde **CORE_STATE_PATH_NAMES** zaten tanımlı (çekirdek overwrite guard hazırlığı):

- `tasks.json`, `config`, `config.json`, `logs`, `trash`, `aliases.json`

Eksik (listeye eklenmesi önerilir, sandbox guard için):

- Not store dosya adı: `notes.enc.json`
- Güvenlik (guard kapsamında ayrı tutulabilir): keystore, identity, presence config dosyaları

Gerçek path’ler:

- `.lumos/tasks/tasks.json` (TaskStore base_dir = .lumos/tasks)
- `.lumos/aliases.json`
- `.lumos/config.json`, `.lumos/config/`, `.lumos/presence.json`
- `.lumos/logs/`
- `.lumos/trash/`
- `.lumos/notes.enc.json` (SecureNotesStore)
- Keystore/identity/presence: güvenlik modülü path’leri

### 1.3 Güvenli kopya üstünde çalışması gereken alanlar

- Deneme/geliştirme ile yapılan **görev taslakları**, **not taslakları**, **config denemeleri**: canlı `tasks.json`, notlar, config yerine **tanımlı bir kopya/sandbox dizini** (ör. `.lumos/sandbox/` veya ileride tanımlanacak) üzerinde olmalı.
- Sistem “kendi kafasına” canlı hedef seçemez: hedef ya tek canlı base ya da sözleşmeyle tanımlı tek sandbox base olmalı.

### 1.4 Doğrudan yazılması asla istenmeyen alanlar (çekirdek)

- Aynı çekirdek overwrite yasağı: canlı `tasks.json`, notlar, config, logs, trash, aliases — **sandbox/kopya yazıcısı** bu path’lere doğrudan yazmamalı.
- Güvenlik: keystore, identity, presence — sadece tanımlı güvenlik akışları yazmalı; sandbox denemesi bu dosyalara dokunmamalı.

---

## 2. Docs/rules seviyesi vs kod guard ayrımı

### 2.1 Sadece docs/rules seviyesinde kalacaklar

| Madde | Nerede | Gerekçe |
|-------|--------|---------|
| Sandbox’un “şu an sözleşme dışı / açılınca tanımlanacak” notu | Sözleşme §4, uygulama planı | Durum tarifi; açıldığında sözleşme güncellenir. |
| “Deneme alanı aktif state kaynağı olarak kullanılmaz” | lumos-karar-ozet.mdc, sözleşme | Davranış kuralı; okuma kaynağı sadece omurga. |
| “Overwrite yasağı” metni (çekirdek state doğrudan overwrite edilmez) | Sözleşme §4, rules | İlke; kod guard ile uygulanır. |

### 2.2 Kod guard ile korunması gereken minimum kısım

| Madde | Nerede guard | Ne yapılır |
|-------|--------------|------------|
| Canlı çekirdek path’lere sandbox/kopya yazıcısıyla yazma | Yazma noktaları veya tek “hedef çözümleyici” | Sandbox modunda yazma hedefi **sadece** sandbox base; canlı base’e yazma isteği guard ile reddedilir. |
| Hedef base’in tek ve tanımlı olması | Runtime “nereye yazıyorum” kararı | Sistem keyfi “canlı” hedef seçemez; base ya `_lumos_dir()` (canlı) ya da sözleşmeyle tanımlı tek sandbox path. |
| Çekirdek state path listesi tek kaynak | `workspace_contract.py` | Mevcut `CORE_STATE_PATH_NAMES`; sandbox guard bu listeyi kullanır; notlar dosya adı eklenebilir. |

Özet: **Docs/rules** = ne yapılacağı, hangi alanın dokunulmaz olduğu. **Kod guard** = sandbox açıldığında “bu path çekirdek mi?” ve “şu an sandbox modunda canlıya yazıyorum mu?” kontrolü; canlıya yazma reddi.

---

## 3. En dar ilk sandbox guard paketi

Hedef mantık:

- **Canlı çekirdeğe doğrudan overwrite yok:** Sandbox/kopya yazıcısı canlı çekirdek path’lere yazamaz.
- **Deneme/geliştirme tanımlı kopya/sandbox alanında:** Sandbox açıldığında yazma hedefi yalnızca tanımlı sandbox base.
- **Sistem kendi kafasına canlı hedef seçemez:** Hedef base tek kaynaktan (örn. `_lumos_dir()` veya “sandbox base” sözleşme değişkeni) gelir.
- **Mevcut guard zinciriyle çelişmez:** Trash, kalıcı silme, açık onay, çekirdek inviolable sabitleri aynen kalır.

### 3.1 Paket bileşenleri (en dar)

1. **Çekirdek state path tanımı (tek kaynak)**  
   - Zaten var: `workspace_contract.CORE_STATE_PATH_NAMES`.  
   - İsteğe bağlı: notlar dosya adı `notes.enc.json` eklenir (sandbox guard’ta “bu path çekirdek” diye sayılsın).

2. **Guard yardımcı fonksiyonu (sandbox hazırlığı)**  
   - `is_core_state_path(base_dir: Path, candidate_path: Path) -> bool`: Verilen `candidate_path` (mutlak veya base’e göre), `base_dir` altındaki çekirdek state path’lerden biri mi? (Dosya adı veya base’e göre relative path, `CORE_STATE_PATH_NAMES` + “notes.enc.json” ile karşılaştırma.)  
   - Kullanım yeri: Sandbox açıldığında, “canlı base’e yazıyorum” diyen her yazma öncesi; True ise sandbox modunda yazma **yapılmaz**.

3. **Hedef base sözleşmesi (docs + opsiyonel kod)**  
   - Docs/rules: “Yazma hedefi tek: ya canlı `.lumos` (mevcut) ya da tanımlı tek sandbox base; sistem keyfi hedef seçmez.”  
   - Kod: Şu an sandbox base yok; tek base `_lumos_dir()`. Sandbox açıldığında tek bir “sandbox_base” (veya “writing_base”) kaynağı tanımlanır; yazıcılar bu base’i kullanır, guard “canlı base + çekirdek path”e yazmayı reddeder.

4. **Rules güncellemesi**  
   - `lumos-karar-ozet.mdc` veya workspace contract: “Sandbox/kopya sınırı: Deneme/geliştirme tanımlı kopya alanında yapılır; canlı çekirdek path’lere doğrudan overwrite yok; sistem canlı hedefi kendi seçemez.”  
   - Uygulama planında “Sandbox overwrite yasağı” maddesi kod guard’a bağlanır: `workspace_contract` + ileride sandbox modu.

### 3.2 Şu an yapılacak minimum (davranış değişmeden)

- **Kod:** Sadece guard hazırlığı:  
  - `is_core_state_path(base_dir, candidate_path)` (ve gerekirse notlar dosya adını içeren genişletilmiş çekirdek listesi) `workspace_contract` içinde.  
  - Mevcut yazma noktalarına **çağrı eklenmez**; sandbox modu olmadığı için davranış değişmez.  
- **Test:** `is_core_state_path` için unit test: bilinen çekirdek path’ler True, diğerleri False.  
- **Docs:** Bu belge + rules’ta sandbox sınırı cümlesi.

---

## 4. Bilerek dokunulmayacak alanlar

- **Workspace omurgası:** `.lumos/`, `tasks/`, `logs/`, `trash/`, `config/`; `lumos-workspace-contract.mdc` ve ilgili kurallar. Yeni omurga dizini eklenmaz; sandbox açılsa bile omurga sabit kalır.
- **Kalıcı silme guard’ı:** `may_perform_permanent_delete`, `TaskStore.delete(user_initiated=...)`, `is_allowed_trash_path`, `trash_path`, `LUMOS_TRASH_DIRNAME`. Trash tek path; davranış değiştirilmez.
- **Açık onay guard’ı:** `is_allowed_for_profile(..., general_approval)`, `TaskEngine.run_task` kullanımı; genel onay kapalıyken write_local yürütülmez.
- **Çekirdek overwrite / inviolable guard’ı:** `profiles.PROFILE_*`, `STEP_TYPE_*`, `SECURITY_NEVER_AUTO`, `inviolable.verify_core_constants()`, `LUMOS_TRASH_DIRNAME` sabiti. Sabitler gevşetilmez.
- **Büyük mimari taşıma:** Tüm yazıcıların refactor’u, yeni katmanlar, UI açılması bu paket kapsamı dışında.

---

## 5. Önerilen uygulama sırası

1. **Teşhis doğrulama**  
   - Bu belgedeki “guard gerektiren kod alanları” ve “canlı çekirdek path’ler” listesini kodla karşılaştır; eksik path varsa (örn. `notes.enc.json`) not et.

2. **Çekirdek path listesi**  
   - `CORE_STATE_PATH_NAMES`’e ihtiyaç halinde `notes.enc.json` ekle (veya ayrı tuple `CORE_STATE_FILE_NAMES`).  
   - Tek kaynak kalsın; sandbox guard bu listeyi kullanacak.

3. **Guard yardımcı fonksiyonu**  
   - `workspace_contract.is_core_state_path(base_dir, candidate_path)` ekle; mevcut yazma noktalarına **henüz bağlama** (sandbox modu yok).

4. **Test**  
   - `test_workspace_contract.py`: `is_core_state_path` için testler (çekirdek path’ler True, sandbox/other False).

5. **Rules / docs**  
   - Sandbox/kopya sınırı cümlesi (rules); bu belgeyi referans ver.

6. **Sandbox açıldığında (sonraki adım)**  
   - “Yazma hedefi” = sandbox base veya canlı base tek kaynaktan.  
   - Her çekirdek state yazma noktasında (veya merkezi “writer” katmanında): “şu an sandbox modunda mıyım?” evet ise “hedef canlı çekirdek path mi?” kontrolü; evet ise yazma yapma.  
   - `is_core_state_path` bu kontrolde kullanılır.

---

## Özet tablolar

| Çıktı | İçerik |
|-------|--------|
| **Guard gerektiren kod alanları** | TaskStore._save, SecureNotesStore.save, save_aliases, save_presence_cfg, identity/keystore write, log write; hedef path’ler çekirdek state. |
| **Aktif risk noktaları** | Sandbox açılmadan önce: keyfi “alternatif base” ile yazma yok (tek base). Sandbox açıldığında: sandbox modunda canlı path’e yazma riski → guard ile kapatılır. |
| **En dar ilk sandbox guard paketi** | CORE_STATE_PATH_NAMES (+ notes?), `is_core_state_path()` hazırlığı, rules cümlesi, test; mevcut davranış değişmez. |
| **Bilerek dokunulmayacaklar** | Omurga, kalıcı silme, açık onay, çekirdek inviolable guard’ları; büyük mimari/UI. |
| **Uygulama sırası** | Teşhis → path listesi → guard helper + test → rules/docs → (sandbox açıldığında) yazma noktalarına guard bağlama. |

---

*Referans: docs/lumos-karar-sozlesmesi.md §4, docs/lumos-sozlesme-uygulama-plani.md, docs/lumos-guard-cekirdek-overwrite-cikti.md, .cursor/rules/lumos-karar-ozet.mdc, .cursor/rules/lumos-workspace-contract.mdc.*
