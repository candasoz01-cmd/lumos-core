# ADR-005: Memory Graph (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — memory usage map checkpoint tamamlandı; karar finalize büyük konsolidasyon planı öncesi bekletilir |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004, ADR-010, PR #84 (`492e8d1`) |

## Amaç

Lumos kod tabanında **Memory Graph** (ilişkisel bellek modeli) hedefini repo analizine dayalı olarak kayıt altına almak; mevcut parçalı bellek durumunu, hedef rolü, ilk node/ilişki türlerini ve güvenlik sınırlarını **kodsuz karar kaydı** olarak belgelemek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, graph engine, graph database veya bellek davranışı değişikliği **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). ADR-001 Memory Graph'ı **hipotez** düzeyinde listeler; ADR-003 canonical bellek katmanını (`src/memory`) kaydeder; ADR-004 usage map disiplinini router için tanımlar. Bu ADR, Memory Graph hedefini aynı disiplinle — önce analiz ve haritalama, sonra dar karar — kayıt altına alır.

---

## Mevcut durum (repo analiz bulguları, Haziran 2026)

### Gerçek graph memory yok

Repo taramasında **node/edge tabanlı bir graph bellek modeli tespit edilmemiştir**. İlişki türleri (`related_to`, `depends_on` vb.) kod veya şemada tanımlı değildir.

### Parçalı bellek katmanları

| Katman | Konum (analiz bulgusu) | Kısa rol |
|--------|------------------------|----------|
| Not belleği | `src/memory/memory.py`, `src/memory/schema.py` (`MemoryNote`) | Düz liste; `kind`, `content`, `source`, `ttl_seconds`; TTL temizliği |
| Şifreli not deposu | `src/memory/secure_store.py` (`SecureNotesStore`) | AES-GCM `notes.enc.json`; düz not serileştirme |
| Oturum belleği | `src/memory/session_memory.py` (`SessionMemory`) | `enrich()` şu an no-op — ctx'i olduğu gibi döndürür |
| Bağlam deposu | `src/core/context_store.py` | `.lumos/context.json`; repo sorgusu, panel sağlık, aktivite — graph değil |
| Runtime bağlam | `src/context/context.py` (`Context`) | Mesaj, online, confidence, `memory_note_count`; ilişki yok |
| Karar örüntüleri / bias | `src/core/memory_compressor.py`, `memory_patterns.py`, `strategy_updater.apply_memory_bias` | Loglardan istatistiksel örüntü → `.lumos/memory_patterns.json`; entity graph değil |
| Karar kayıtları | `docs/decisions/ADR-*.md` | İnsan okur Markdown; makine graph node'u değil; runtime bellekten ayrı |
| Günlük / ilerleme | `docs/journal/` | İnsan okur; runtime bellekten ayrı |
| Görev kayıtları | `task_engine`, `.lumos/tasks/` | Yapılandırılmış görev state; graph kenarı yok |
| CLI notları | `src/cli/cli_notes.py` (analiz bulgusu) | Ayrı in-memory string listesi; `MemoryNote` ile birleşik değil |

**Analiz bulgusu:** "Decision memory" (`decision_bias`: log → pattern → bias) ile "note memory" (kullanıcı/kısıt notları), `context_store` (geçici UI/oturum state) ve `docs/decisions` / `docs/journal` (insan okur kayıt) **ayrı kavramlardır**; tek graph altında birleşmemiştir.

### ADR-003 ile hizalı canonical katman

Haziran 2026 repo analizine göre **bellek için canonical kaynak `src/memory`**'dir (ADR-003). Trust/security katmanları `src/security` ve `src/policy` üzerindedir. Memory Graph tasarımı bu katmanları bypass etmemelidir.

**Analiz bulgusu:** `packages/kando_memory` aktif import taşımıyor gibi görünmekte; ayna/drift riski taşır (ADR-003). Graph kararı bu pakete dokunmaz.

### Drift riski: `memory.py` ↔ runtime `attach_store` (doğrulandı; PR #84 ile dar düzeltme)

Usage map sırasında `src/core/lumos_runtime.py` (ve `packages/kando_runtime` aynası) runtime'da şunları çağırdığı doğrulandı:

- `lumos.note_memory.attach_store(store, rk)`
- `lumos.note_memory.root_key = rk`

İlk analizde `src/memory/memory.py` içinde `attach_store`, `_load_from_store`, `_save_to_store`, `device_lock` **eksikti**; kilitsiz not persistence zinciri tutarsızdı.

**PR #84** (`492e8d1` — *fix: restore Memory attach_store persistence API*) yalnızca bu API drift'ini giderdi: `attach_store`, `_load_from_store`, `_save_to_store`, `device_lock` `src/memory/memory.py`'ye geri eklendi. Bu **büyük bellek konsolidasyonu değildir**; graph engine, graph DB veya yeni memory motoru yoktur.

Kalan drift adayları (ayrı inceleme): `packages/kando_memory` aynası, `cli/cli_notes.py` ↔ `MemoryNote`, oturum belleği stub'ı — usage map tablosunda listelenmiştir.

### Henüz olmayan alanlar

| Alan | Durum (analiz bulgusu) |
|------|------------------------|
| Graph modeli (node/edge) | Yok |
| Node türü zorlaması | `MemoryNote.kind` serbest `str`; pratikte `"constraint"` (self-test) görülür |
| İlişki türleri | Yok |
| Graph DB (Neo4j vb.) | Yok |
| Oturumlar arası ilişkisel bellek | Yok (`SessionMemory` stub) |
| ADR → makine graph eşlemesi | Yok |

### İlgili ADR durumu

- **ADR-001:** Memory Graph **hipotez**; öncelik sırasında routing/trust sonrası 3.–4. alan.
- **ADR-003:** Canonical bellek `src/memory`; büyük konsolidasyon ertelendi.
- **ADR-004:** Usage map disiplini; router ile graph aynı "önce haritala, sonra kod" ilkesini paylaşır.
- **ADR-010:** Guard/policy/trust terminolojisi; `decision_bias` ile kullanıcı belleği karıştırılmamalıdır.

---

## Mevcut memory kullanım haritası

Haziran 2026 repo taraması sonucu — **salt okuma analizi**; graph engine, graph DB veya bellek konsolidasyonu **yapılmamıştır**. PR #84 yalnızca `attach_store` persistence API drift'ini dar kapsamda giderdi (`492e8d1`).

### Özet bulgular

- **Gerçek graph memory yok.** Node/edge modeli, ilişki türleri veya graph DB tespit edilmemiştir.
- **Bellek parçalıdır:** `MemoryNote`, `context_store`, oturum belleği (`SessionMemory`), log türevli `decision_bias` (`memory_patterns` / `apply_memory_bias`), runtime `attach_store` zinciri, `docs/decisions` ve `docs/journal` ayrı katmanlardır — **tek sistem değildir**.
- **`decision_bias` kullanıcı belleği değildir.** Loglardan türetilen istatistiksel karar ağırlıklandırmasıdır (`.lumos/memory_patterns.json`); kullanıcı tercihi veya entity graph sanılmamalıdır.
- **`docs/journal` ve `docs/decisions` runtime bellekten ayrı tutulmalıdır.** İnsan okur kayıt / karar arşividir; makine graph node'u veya otomatik ingest hedefi değildir.
- **`attach_store` / persistence API drift usage map ile doğrulandı;** PR #84 `src/memory/memory.py`'de API'yi geri yükledi. Fix büyük konsolidasyon veya graph kararı değildir.
- **`packages/kando_memory` aktif değildir** (ADR-003); import taşımıyor; ayna/drift riski devam eder — graph kararı bu paketi etkinleştirmez.
- **Graph DB veya yeni memory engine kurulmaz** — bu ADR yalnızca harita ve sınır kaydıdır.

### Modül → veri türü haritası

| Modül / konum | Veri türü | Tüketiciler / üretenler | Graph / drift notu |
|---------------|-----------|-------------------------|-------------------|
| `src/memory/memory.py` | `MemoryNote` listesi; `SecureNotesStore` persistence | `lumos.py` (`note_memory.enrich`), `lumos_runtime` (`attach_store`) | Düz liste; graph yok. PR #84: `attach_store` API geri yüklendi |
| `src/memory/secure_store.py` | AES-GCM `notes.enc.json` | `lumos_runtime` unlock hattı | Şifreli düz not; entity ilişkisi yok |
| `src/memory/session_memory.py` | Oturum (stub) | `lumos.py` runtime zinciri | `enrich()` no-op; oturumlar arası bellek yok |
| `src/core/context_store.py` | `.lumos/context.json` | `llm.py`, `panel_runtime`, `product_features` | UI/repo geçici state; graph değil |
| `src/context/context.py` | Runtime `Context` (mesaj, online, `memory_note_count`) | Engine, enrich zinciri | İlişki modeli yok |
| `memory_compressor` → `memory_patterns.json` | Log türevli karar örüntüleri | `strategy_updater.apply_memory_bias`, `decision_ranker` | **decision_bias** — kullanıcı hafızası değil |
| `docs/decisions/ADR-*.md` | İnsan okur karar kayıtları | Geliştirici / dokümantasyon | Runtime bellekten **ayrı**; otomatik graph ingest yok |
| `docs/journal/` | İlerleme / günlük notları | İnsan okur | Runtime bellekten **ayrı** |
| `task_engine` / `.lumos/tasks/` | Görev state | CLI, panel | Yapılandırılmış görev; graph kenarı yok |
| `src/cli/cli_notes.py` | In-memory string listesi | CLI | `MemoryNote` ile birleşik değil — drift adayı |
| `packages/kando_memory` | Ayna kopya (`memory.py`, `schema.py`) | Aktif import **yok** | ADR-003 drift riski; etkinleştirilmez |

### Runtime persistence zinciri (checkpoint)

```
lumos_runtime unlock → SecureNotesStore → note_memory.attach_store(store, rk)
  → _load_from_store / add → _save_to_store
lumos.py.enrich_context → note_memory.enrich → session_memory.enrich (no-op)
context_store ← llm / panel (ayrı dosya: .lumos/context.json)
memory_compressor → .lumos/memory_patterns.json → apply_memory_bias (strateji ağırlığı)
```

**Analiz bulgusu:** Not persistence (`MemoryNote` + `attach_store`) ile bağlam deposu (`context_store`) ve karar bias'ı (`memory_patterns`) **farklı dosyalar, farklı sözleşmeler**; tek graph altında birleşmemiştir.

### Drift ve çelişki riskleri (teşhis listesi)

Usage map sonrası **özellikle** ayrı tutulması veya dar inceleme gereken noktalar (analiz bulgusu):

| Risk | Açıklama | Etkilenen modüller |
|------|----------|-------------------|
| **Runtime vs doküman karışımı** | ADR/journal kayıtları runtime bellek sanılabilir | `docs/decisions`, `docs/journal`, `MemoryNote` |
| **decision_bias vs kullanıcı tercihi** | Log örüntüleri profil/tercih graph'ına karışabilir | `memory_patterns.json`, `apply_memory_bias` |
| **CLI notları ↔ MemoryNote** | İki ayrı not deposu; senkron yok | `cli_notes.py`, `memory.py` |
| **`SessionMemory` stub** | Oturum belleği hedef rolü ile kod uyumsuz | `session_memory.py`, `lumos.py` |
| **`src/` ↔ `packages/kando_memory`** | Ayna drift; aktif import yok | ADR-003 |
| **`context_store` vs `MemoryNote`** | Geçici UI state ile kalıcı not karışımı | `context_store.py`, `memory.py` |
| **attach_store (dar fix sonrası)** | PR #84 API'yi geri yükledi; mirror/CLI drift devam | `memory.py`, `lumos_runtime`, `kando_memory` |

Bu tablo **teşhis listesidir**; PR #84 yalnızca `attach_store` satırındaki API eksikliğini giderdi. Büyük bellek refactor veya graph implementasyonu **bu ADR kapsamında yapılmaz**.

### PR #84 notu (dar düzeltme — konsolidasyon değil)

| Alan | Değer |
|------|-------|
| PR | #84 — *fix: restore Memory attach_store persistence API* |
| Merge commit | `492e8d1` |
| Dosya | `src/memory/memory.py` (+47 satır) |
| Kapsam | `attach_store`, `_load_from_store`, `_save_to_store`, `device_lock` geri yükleme |
| **Değil** | Graph DB, memory engine, `kando_memory` etkinleştirme, kullanıcı verisi taşıma, büyük konsolidasyon |

---

## Memory Graph hedef rolü

Memory Graph, Lumos'ta hafızanın düz not listesi olmaktan çıkıp **ilişki kurabilen ve bağlamı takip edebilen** bir katman olmasını hedefler. Kesin API, modül adı veya depolama biçimi henüz kararlaştırılmamıştır (*taslak*).

Hedeflenen işlevler:

1. **Kullanıcı tercihlerini takip etmek** — tekrarlayan tercihlerin bağlama bağlanması; profil/onay sınırları içinde.
2. **Proje kararlarını bağlama bağlamak** — ADR ve karar kayıtlarının proje, görev ve ilgili varlıklara ilişkilendirilmesi.
3. **Görevler, kararlar, kişiler, dosyalar, konuşmalar ve riskler arasında ilişki kurmak** — çoklu varlık graph'ı; dağınık sinyallerin tek sözleşme altında toplanması (*hedef*; mevcut değil).
4. **Geçmiş bağlamı korurken gereksiz hafıza şişmesini engellemek** — TTL, sıkıştırma, özet ve scope sınırları ile; "her şeyi sakla" modeli hedeflenmez.

Bu rol ADR-001'deki "oturumlar ve görevler arası ilişkisel bellek modeli" hipotezini somutlaştırmayı hedefler; firewall, trust ve router oturmadan tek başına üretim vaadi taşımamalıdır.

---

## İlk memory node türleri (taslak — 10 tür)

Aşağıdaki türler **ürün/hedef sözleşmesidir**; repo'da tanımlı veya zorlanmış değildir.

| # | Node türü | Kısa tanım | Mevcut repo karşılığı (analiz bulgusu) |
|---|-----------|------------|----------------------------------------|
| 1 | **kullanıcı tercihi** | Tekrarlayan kullanıcı seçimi veya tercih ifadesi | Graph yok; panel/LLM bağlamı düz metin |
| 2 | **proje kararı** | Proje kapsamında alınmış karar | `docs/decisions/ADR-*.md` (insan okur) |
| 3 | **ürün kuralı** | Ürün/çekirdek politika veya kural | `.cursor/rules/`, `docs/lumos-karar-sozlesmesi.md` |
| 4 | **görev** | Yapılacak veya devam eden iş birimi | `task_engine`, `.lumos/tasks/` |
| 5 | **açık soru** | Cevaplanmamış veya takip gerektiren soru | Kod karşılığı yok |
| 6 | **risk / uyarı** | Risk, uyarı veya dikkat gerektiren durum | `lumos_gate`, `change_sensitivity`, profiller — dağınık |
| 7 | **kaynak / doküman** | Referans dosya, ADR, not veya kaynak | `SecureNotesStore`, ADR/docs |
| 8 | **kişi / kurum** | İletişim veya kurumsal varlık | `device/contacts.py` (graph entegrasyonu yok) |
| 9 | **sistem durumu** | Runtime veya panel durum snapshot'ı | `context_store`, panel state |
| 10 | **ertelenmiş fikir** | Bilinçli ertelenmiş veya sonra ele alınacak fikir | ADR-001 "bilinçli ertelenen" tablosu; dokümantasyon düzeyi |

Node ataması **öneri** niteliğindedir; kullanıcı override, profil sınırları ve onay kuralları her zaman üstünde kalır.

---

## İlk ilişki türleri (taslak — 10 tür)

Repoda **hiçbir ilişki türü** kod veya şemada tanımlı değildir. Aşağıdaki liste hedef sözleşmedir.

| # | İlişki türü | Taslak anlam |
|---|-------------|--------------|
| 1 | **related_to** | Genel ilişki; zayıf veya çok amaçlı bağ |
| 2 | **depends_on** | Hedef node, kaynak node'a bağımlı |
| 3 | **blocks** | Kaynak, hedefin ilerlemesini engeller |
| 4 | **decided_by** | Karar veya sonuç, belirtilen kaynak tarafından alındı |
| 5 | **supersedes** | Yeni kayıt eski kaydı geçersiz kılar |
| 6 | **conflicts_with** | İki node çelişkili veya uyumsuz |
| 7 | **belongs_to_project** | Node belirli proje kapsamına aittir |
| 8 | **needs_review** | İnsan incelemesi veya onay bekler |
| 9 | **source_of** | Bilgi, özet veya kararın kaynağı |
| 10 | **reminder_for_later** | Ertelenmiş hatırlatma veya takip bağı |

İlişki yönü ve cardinality (1:1, 1:N) henüz tanımlanmamıştır; usage map ve şema taslağı sonrası netleştirilir.

---

## Güvenlik ve gizlilik sınırları

Memory Graph tasarımı `lumos-karar-sozlesmesi` ve ADR-003 trust/security katmanlarını **gevşetmemelidir**.

| Kural | Graph için anlam |
|-------|------------------|
| **Kullanıcı onayı olmadan hassas veri kalıcı hafızaya alınmaz** | Graph node/edge yazımı onay ve profil kurallarına tabidir; otomatik ingest yok |
| **Gereksiz kişisel ayrıntılar saklanmaz** | Minimum gerekli alan; PII birikimi hedeflenmez |
| **Proje kararları ile kullanıcı özel hayatı ayrılır** | Scope ve erişim ayrımı; kişisel node'lar proje graph'ına karışmaz |
| **Silinen/geri alınan kararlar aktif karar gibi davranmaz** | `supersedes` / trash prensibi; çekirdek kalıcı silme kuralı geçerli |
| **Memory Graph kullanıcıyı manipüle etmek için kullanılmaz** | Graph bağlamı cevap disiplini ve dürüstlük modeli ile sınırlı; kanıtsız iddia kaynağı olmaz |

Ek ilkeler (ADR-003 / çekirdek hizası):

- Graph yazımı kilit/keystore açıkken; hassas içerik `SecureNotesStore` deseni ile uyumlu olmalıdır.
- `SECURITY_NEVER_AUTO` kapsamındaki işlemler otomatik graph'a yansımaz.
- Offline modda dış/network graph senkronu yok.
- Sandbox: yazım `workspace_contract` sink'leri ve `is_sandbox_mode` ile sınırlı; canlı çekirdek overwrite yok.

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-005:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Basit memory schema taslağı (node/edge **tipleri**, demo-safe sözleşme) | Kişisel uzun vadeli kullanıcı hafızası |
| Proje karar graph **fikri** ve ADR kayıtları | Gerçek kullanıcı profili ve PII içeren graph |
| `SecureNotesStore` desen açıklaması (şifreli yerel store) | Production keystore, cihaz kimliği, operasyonel backend |
| Sentetik/demo graph fixture tanımı | Cross-service memory senkronu |
| Usage map / bellek dokunuş noktası analizi (salt okuma) | Mail/IMAP/OAuth graph içeriği (ADR-002) |
| | Agent Network graph genişlemesi (ADR-001 hipotez) |
| | Quantum / IBM prod entegrasyonu (ADR-001) |

Public repo'da Memory Graph'ın **"tam ürün bellek motoru"** gibi sunulması bilinçli olarak yapılmamalıdır; bu ADR yalnızca hedef, mevcut boşluk ve sınırları kaydeder.

---

## Karar (taslak — büyük konsolidasyon planı bekliyor)

1. **Mevcut gerçek:** Graph memory yok; bellek `MemoryNote`, `context_store`, oturum belleği, `decision_bias` (`memory_patterns` / `apply_memory_bias`), runtime `attach_store` ve `docs/decisions` / `docs/journal` üzerinden **parçalıdır** (usage map: yukarıdaki bölüm).
2. **Usage map checkpoint:** Bellek modülleri, persistence zinciri ve drift riskleri bu ADR'de **kilitlendi**; graph engine veya büyük refactor yapılmadı.
3. **PR #84 (dar fix):** `memory.py` ↔ runtime `attach_store` API drift'i giderildi (`492e8d1`); bu bellek konsolidasyonu veya graph kararı **değildir**.
4. **Canonical katman:** ADR-003 ile uyumlu — bellek `src/memory`; graph bu katmanı bypass etmemelidir.
5. **Sınır:** `decision_bias` kullanıcı belleği değildir; `docs/journal` ve `docs/decisions` runtime bellekten ayrı kalır.
6. **Hedef:** Yukarıdaki dört rol, 10 node türü ve 10 ilişki türü taslağı; finalize için terminoloji sözleşmesi ve (gerekirse) ayrı konsolidasyon planı gerekir.
7. **Graph database, yeni memory engine ve `kando_memory` etkinleştirme şimdi yapılmaz.**
8. **ADR-001 / ADR-004 / ADR-010 ile hizalı:** Memory Graph hipotez alanı; router usage map disiplini ile aynı sıra — önce haritalama, sonra dar kod.
9. **Bu turda kod yok** — yalnızca karar kaydı (PR #84 önceden merge edilmiş dar fix dışında).

Durum: **Karar bellek terimleri / persistence sınırları netleştirildikten ve büyük konsolidasyon için ayrı plan onaylanmadan finalize edilmez.**

---

## İlk güvenli adım: usage map kilitlendi → terimler ve sınırlar

**Tamamlanan (bu ADR):** Mevcut memory kullanım haritası — bkz. [Mevcut memory kullanım haritası](#mevcut-memory-kullanım-haritası). Graph engine, graph DB veya büyük refactor **yapılmadı**. PR #84 yalnızca `attach_store` API drift'ini dar kapsamda giderdi.

**Sonraki güvenli adımlar (henüz yapılmadı):**

| Adım | Amaç | Not |
|------|------|-----|
| Bellek terimleri sözleşmesi | `MemoryNote`, `context_store`, `decision_bias`, ADR/journal ayrımını tek tabloda kilitle | Memory Graph öncesi zorunlu |
| Persistence sınırları | Hangi veri nereye yazılır; runtime vs doküman | Onaysız ingest yok |
| Dar drift incelemesi (opsiyonel) | `cli_notes` ↔ `MemoryNote`, `kando_memory` aynası | PR #84 kapsamı dışı |
| Büyük konsolidasyon planı | Çoklu kaynak birleştirme | **Ayrı ADR / onay** — bu ADR'de yapılmaz |

**Yapılmaması gereken (ilk adımda):**

- Runtime bellek ile `docs/decisions` / `docs/journal` kayıtlarını tek sistem gibi sunmak veya otomatik eşlemek.
- PR #84 fix'ini "bellek birleştirildi" veya "graph hazır" diye yorumlamak.
- Usage map tamamlanmadan graph şema, graph DB veya memory engine kararı vermek *(usage map tamamlandı; graph kararı hâlâ verilmez)*.

Büyük bellek konsolidasyonu **ayrı plan ve kullanıcı onayı** olmadan başlatılmamalıdır.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, konsolidasyon planı, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Graph database ekleme** (Neo4j vb.) | Omurga oturmadan operasyonel karmaşıklık; erken hedef değil |
| **Büyük memory refactor / konsolidasyon** | Usage map kilitlendi; terimler ve persistence sınırları önce; ADR-003 büyük birleştirme ertelendi |
| **Kullanıcı verisi taşıma** | Onay ve gizlilik sınırı; public repo riski |
| **`kando_memory` etkinleştirme** | Aktif import yok; ayna drift; graph kararı paketi açmaz |
| **Runtime bellek ↔ docs kararlarını tek sistem sunma** | `docs/decisions` ve `docs/journal` runtime ingest hedefi değil |
| **`decision_bias`'ı kullanıcı hafızası gibi kullanma** | Log türevli ağırlık; entity/tercih graph'ı değil |
| **Kod yazma** (graph engine, schema implementasyonu) | Terim sözleşmesi ve karar finalize edilmedi |
| **Mail/OAuth entegrasyonu** | ADR-002 — izin akışı ve kod kapsam dışı |
| **Agent Network kurma** | ADR-001 taslak; graph öncesi değil |
| **Quantum/IBM tarafına geçme** | ADR-001 — erken hedef değil |

Ek olarak: abartılı ürün vaadi, otomatik graph doldurma (onaysız ingest), PR #84 fix'ini konsolidasyon sanma ve public sınırı aşan PII graph içeriği **yapılmaz**.

---

## Riskler (analiz bulgusu)

| Risk | Not |
|------|-----|
| `memory.py` ↔ runtime drift | PR #84 `attach_store` API'yi geri yükledi; CLI/`kando_memory` drift devam edebilir |
| Runtime vs docs karışımı | ADR/journal otomatik graph veya runtime bellek sanılabilir |
| Çoklu bellek kaynağı | Notlar, context, tasks, logs, panel — tek graph yok |
| Graph şişmesi | İlişkisiz node birikimi; TTL/compressor graph'a uyarlanmalı |
| Gizlilik sızıntısı | Kişi/konuşma node'ları public demo'ya karışabilir |
| Bias vs graph karışımı | `decision_bias` kullanıcı tercihi sanılabilir (ADR-010) |
| Mirror paket drift | `kando_memory` aktif değil (ADR-003) |
| Erken graph DB | CI/regresyon; onay modeli karmaşıklaşması |
| Onaysız yazım | Auto-ingest karar sözleşmesini ihlal eder |
| PR #84 yanlış yorum | Dar API fix'i büyük konsolidasyon sanılması |

---

## Sonuç (geçici)

Haziran 2026 repo analizine dayanarak Lumos'ta **gerçek graph memory bulunmamaktadır**. Bellek `MemoryNote`, `context_store`, oturum belleği, `decision_bias` (`memory_patterns` / `apply_memory_bias`), runtime `attach_store` ve `docs/decisions` / `docs/journal` kayıtları üzerinden **parçalıdır** — tek birleşik bellek sistemi yoktur. ADR-003'e göre canonical bellek katmanı **`src/memory`**'dir. Memory Graph hedef rolü, 10 node türü ve 10 ilişki türü **taslak sözleşme** olarak kaydedilmiştir.

**Usage map checkpoint tamamlandı** — modül haritası, persistence zinciri ve drift teşhis listesi bu ADR'de kilitlendi. **PR #84** (`492e8d1`) yalnızca `attach_store` persistence API drift'ini dar kapsamda giderdi; graph DB, memory engine veya büyük konsolidasyon **yapılmadı**. **`kando_memory` etkinleştirilmedi.**

**Sonraki güvenli adım:** Bellek terimleri ve persistence sınırlarını dokümante etmek; runtime bellek ile docs/journal/decisions kayıtlarını karıştırmamak; büyük konsolidasyon için ayrı plan. **Bu turda graph implementasyonu veya büyük refactor yapılmaz.**

## Sonraki gözden geçirme

- Bellek terimleri / persistence sınırları sözleşmesi (Memory Graph öncesi)
- Büyük konsolidasyon planı — ayrı ADR veya onaylı checkpoint
- `cli_notes` ↔ `MemoryNote` ve `kando_memory` ayna drift incelemesi (dar kapsam)
- ADR-001 (ileri modüller), ADR-003 (canonical katmanlar), ADR-004 (router usage map), ADR-010 (terminoloji) ile çakışma kontrolü
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot node/ilişki seçimi — terim sözleşmesi sonrası, ayrı onay
