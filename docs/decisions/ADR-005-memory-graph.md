# ADR-005: Memory Graph (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — usage map tamamlanmadan finalize edilmez |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004 |

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
| Karar kayıtları | `docs/decisions/ADR-*.md` | İnsan okur Markdown; makine graph node'u değil |
| Görev kayıtları | `task_engine`, `.lumos/tasks/` | Yapılandırılmış görev state; graph kenarı yok |
| CLI notları | `src/cli/cli_notes.py` (analiz bulgusu) | Ayrı in-memory string listesi; `MemoryNote` ile birleşik değil |

**Analiz bulgusu:** "Decision memory" (log → pattern → bias) ile "note memory" (kullanıcı/kısıt notları) ve `context_store` (geçici UI/oturum state) **ayrı kavramlardır**; tek graph altında birleşmemiştir.

### ADR-003 ile hizalı canonical katman

Haziran 2026 repo analizine göre **bellek için canonical kaynak `src/memory`**'dir (ADR-003). Trust/security katmanları `src/security` ve `src/policy` üzerindedir. Memory Graph tasarımı bu katmanları bypass etmemelidir.

**Analiz bulgusu:** `packages/kando_memory` aktif import taşımıyor gibi görünmekte; ayna/drift riski taşır (ADR-003). Graph kararı bu pakete dokunmaz.

### Drift riski: `memory.py` ↔ runtime `attach_store`

`src/core/lumos_runtime.py` (ve `packages/kando_runtime` aynası) runtime'da şunları çağırır:

- `lumos.note_memory.attach_store(store, rk)`
- `lumos.note_memory.root_key = rk`

Güncel `src/memory/memory.py` içinde `attach_store`, `_load_from_store`, `_save_to_store`, `device_lock` metodları **bulunmamaktadır** (analiz bulgusu). Kilitsiz not persistence zinciri tutarsız görünmektedir.

**Bu ADR kapsamında çözülmez** — ayrı, dar kapsamlı inceleme gerektirir; usage map çıktısının parçası olarak ele alınmalıdır.

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

## Karar (taslak — usage map bekliyor)

1. **Mevcut gerçek:** Graph memory yok; bellek `MemoryNote`, `context_store`, decision bias (`memory_patterns` / `apply_memory_bias`) ve `docs/decisions` üzerinden parçalıdır.
2. **Canonical katman:** ADR-003 ile uyumlu — bellek `src/memory`; graph bu katmanı bypass etmemelidir.
3. **Hedef:** Yukarıdaki dört rol, 10 node türü ve 10 ilişki türü taslağı; finalize için usage map zorunlu.
4. **Büyük refactor veya graph database şimdi kurulmaz** — Neo4j, toplu schema değişikliği veya yeni memory engine bu ADR kapsamında yoktur.
5. **Drift incelemesi:** `memory.py` ↔ runtime `attach_store` ayrı dar inceleme; usage map parçası.
6. **ADR-001 / ADR-004 ile hizalı:** Memory Graph hipotez alanı; router usage map disiplimi ile aynı sıra — önce haritalama, sonra kod.
7. **Bu turda kod yok** — yalnızca karar kaydı.

Durum: **Karar usage map tamamlanana kadar bekletilir.**

---

## İlk güvenli adım: usage map ve ilişkisel harita

Büyük refactor, graph database veya memory engine değişikliği **yapılmadan** önce mevcut bellek dokunuş noktalarının haritalanması önerilir (ADR-004 usage map disiplini ile paralel).

**Hedef çıktı (ayrı checkpoint veya bu ADR eki — henüz yazılmadı):**

| Dokunuş noktası | Veri türü | Tüketiciler / üretenler | Not |
|-----------------|-----------|-------------------------|-----|
| `src/memory/memory.py` | `MemoryNote` listesi | `src/core/lumos.py` (`note_memory.enrich`) | Düz liste; graph yok |
| `src/memory/secure_store.py` | Şifreli notlar | `lumos_runtime` unlock hattı | `attach_store` drift riski |
| `src/memory/session_memory.py` | Oturum (stub) | Runtime zinciri | No-op enrich |
| `src/core/context_store.py` | `.lumos/context.json` | `llm.py`, `panel_runtime`, `product_features` | UI/repo state |
| `memory_compressor` → `memory_patterns.json` | Karar örüntüleri | `strategy_updater`, `decision_ranker` | Bias; entity graph değil |
| `docs/decisions/` | ADR Markdown | İnsan okur | Makine node yok |
| `task_engine` / `.lumos/tasks/` | Görev state | CLI, panel | Graph kenarı yok |
| `cli/cli_notes.py` | In-memory notlar | CLI | `MemoryNote` ile ayrı |

**İlişkisel harita kapsamı (analiz görevi):** Yukarıdaki kaynaklar arasında veri akışı, olası node eşlemesi (taslak), çift kayıt ve drift noktaları — özellikle `memory.py` ↔ `lumos_runtime.attach_store`.

Usage map tamamlanmadan graph şema implementasyonu, graph DB veya memory engine refactor kararı **verilmez**.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, usage map, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Kod yazma** (graph engine, schema implementasyonu) | Usage map ve karar finalize edilmedi |
| **Graph database ekleme** (Neo4j vb.) | Omurga oturmadan operasyonel karmaşıklık; erken hedef değil |
| **Memory engine refactor** | ADR-003 büyük konsolidasyon ertelendi; drift önce netleşmeli |
| **Kullanıcı verisi taşıma** | Onay ve gizlilik sınırı; public repo riski |
| **Mail/OAuth entegrasyonu** | ADR-002 — izin akışı ve kod kapsam dışı |
| **Agent Network kurma** | ADR-001 taslak; graph öncesi değil |
| **Quantum/IBM tarafına geçme** | ADR-001 — erken hedef değil |

Ek olarak: abartılı ürün vaadi, otomatik graph doldurma (onaysız ingest) ve public sınırı aşan PII graph içeriği **yapılmaz**.

---

## Riskler (analiz bulgusu)

| Risk | Not |
|------|-----|
| `memory.py` ↔ runtime drift | `attach_store` API uyumsuzluğu; persistence zinciri belirsiz |
| Çoklu bellek kaynağı | Notlar, context, tasks, logs, panel — tek graph yok |
| Graph şişmesi | İlişkisiz node birikimi; TTL/compressor graph'a uyarlanmalı |
| Gizlilik sızıntısı | Kişi/konuşma node'ları public demo'ya karışabilir |
| Bias vs graph karışımı | Decision pattern'ler kullanıcı tercihi sanılabilir |
| Mirror paket drift | `kando_memory` (ADR-003) |
| Erken graph DB | CI/regresyon; onay modeli karmaşıklaşması |
| Onaysız yazım | Auto-ingest karar sözleşmesini ihlal eder |

---

## Sonuç (geçici)

Haziran 2026 repo analizine dayanarak Lumos'ta **gerçek graph memory bulunmamaktadır**. Bellek `MemoryNote`, `context_store`, decision bias (`memory_patterns` / `apply_memory_bias`) ve `docs/decisions` kayıtları üzerinden **parçalıdır**. ADR-003'e göre canonical bellek katmanı **`src/memory`**'dir. Memory Graph hedef rolü, 10 node türü ve 10 ilişki türü **taslak sözleşme** olarak kaydedilmiştir; büyük refactor veya graph database **hemen kurulmayacaktır**.

**İlk güvenli adım:** Mevcut bellek dokunuş noktalarının usage map ve ilişkisel haritası; `memory.py` ↔ runtime `attach_store` drift'inin ayrı incelemesi. **Bu turda kod yazılmaz.**

## Sonraki gözden geçirme

- Usage map / ilişkisel harita checkpoint sonuçları ile ADR revizyonu ve karar finalize
- `memory.py` ↔ `attach_store` drift incelemesi bulguları (ayrı dar kapsam)
- ADR-001 (ileri modüller), ADR-003 (canonical katmanlar), ADR-004 (router usage map) ile çakışma kontrolü
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot node/ilişki seçimi — usage map sonrası, ayrı onay
