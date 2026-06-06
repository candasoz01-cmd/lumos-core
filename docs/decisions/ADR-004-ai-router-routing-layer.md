# ADR-004: AI Router / Yönlendirme Katmanı (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — routing usage map checkpoint tamamlandı; karar finalize import/drift incelemesi sonrası |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-002, ADR-003, ADR-006, ADR-007, ADR-010 |

## Amaç

Lumos kod tabanında **birleşik AI Router** olup olmadığını repo analizine dayalı olarak netleştirmek; hedef router rolünü, ilk routing kategorilerini ve public/private sınırını **kodsuz karar kaydı** olarak belgelemek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, router davranışı değişikliği veya provider entegrasyonu **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). ADR-001 AI Router'ı **hipotez** düzeyinde listeler; ADR-002 mail önceliklendirme taslağını taşır; ADR-003 canonical bellek ve trust/security katmanlarını kaydeder. Bu ADR, **yönlendirme kararının** nerede parçalandığını ve birleşik router hedefinin ne olması gerektiğini analiz bulgusuna dayanarak kayıt altına alır.

---

## Mevcut durum (repo analiz bulguları, Haziran 2026)

### Birleşik AI Router yok

Repo taramasında **tek, merkezi “AI Router” modülü tespit edilmemiştir**. Kullanıcı isteği farklı giriş noktalarında, farklı kurallarla yönlendirilmektedir.

### Parçalı yönlendirme katmanları

| Katman | Konum (analiz bulgusu) | Kısa rol |
|--------|------------------------|----------|
| CLI giriş yönlendirme | `src/cli/cli_router.py` | Bilinen komut → handler; `unknown` + online → live brain; offline → fallback |
| Köprü chat / görev ayrımı | `packages/kando_runtime/src/kando_runtime/bridge_intent.py` | `task` \| `chat` sınıflandırması |
| Görev türü → executor | `packages/kando_runtime/src/kando_runtime/router.py`, `task_dispatch.py` | `video/image/audio/file/shell/generic`; risk ve onay |
| LLM reasoning öncesi gate | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | `agent` \| `direct_patch` \| `no_op`; risk ipuçları |
| Yetki / onay matrisi | `src/task_engine/profiles.py` | Profil × adım türü; `SECURITY_NEVER_AUTO` |
| Online / offline engine | `src/engine/online_engine.py`, `src/policy/offline_engine.py` | Moda göre engine seçimi |
| Model çağrısı | `src/engine/model_client.py` | Tek OpenAI yolu |

Ek not (analiz bulgusu): `src/core/user_intent_classifier.py` ve `src/core/live_brain.py` CLI live brain hattında niyet yönlendirmesi yapar; `packages/kando_bridge/src/kando_bridge/server.py` köprü girişinde `bridge_intent`, `lumos_gate`, `task_dispatch` zincirini çağırır. `src/kando/kando_core.py` içinde ayrı bir `ToolRouter` (dev/demo araç yönlendirme) bulunur — ana çekirdek router ile birleşik değildir.

### Tek model ayarı

Model seçimi pratikte **ortam değişkeni seviyesindedir**: `OPENAI_MODEL` (varsayılan örnek: `gpt-4.1-mini`). `ModelClient` token kullanımını loglar; **maliyet, hız veya doğruluk sinyaline göre model tier seçimi yoktur** (analiz bulgusu).

### Risk / onay sinyalleri — kısmen var

Dağıtık guard'lar mevcuttur; merkezi router kararı değildir:

- `profiles.py`: profil × adım türü matrisi, `may_execute_step_at_runtime`
- `lumos_gate`: risk düzeyi reason alanı, `no_op` / onay öncesi durdurma
- `task_dispatch`: `pending_approval`, risk seviyesine göre `execution_permitted`
- CLI: `genel_onay_ac` / `genel_onay_kapat` bayrağı

**Analiz bulgusu:** Risk sinyalleri katmanlar arasında tutarlı bir skor modeli olarak birleşmemiştir; bazı yollar (ör. `infer_risk`) zayıf veya sabit `low` dönebilir.

### Henüz olmayan alanlar

| Alan | Durum (analiz bulgusu) |
|------|------------------------|
| Maliyet bazlı yönlendirme | Yok |
| Hız bazlı model seçimi | Yok (timeout/kırpma dışında) |
| Provider / model seçimi | Tek provider + env model |
| Production routing | Yok |
| Mail önceliklendirme | Yalnız ADR-002 taslağı; kod yok |
| Quantum / IBM routing | ADR-001 hipotez; uygulama yok |

### İlgili ADR durumu

- **ADR-001:** AI Router ve güvenli yönlendirme **hipotez**; quantum erken hedef değil.
- **ADR-002:** Mail önceliklendirme kategorileri **taslak**; OAuth/IMAP/kod yok.
- **ADR-003:** Canonical bellek (`src/memory`) ve trust/security (`src/security`, `src/policy`) kayıtlı; router bu katmanlara bağlanmalı, ancak bu ADR canonical kararı değiştirmez.
- **ADR-006 / ADR-007 / ADR-010:** Guard, trust ve terminoloji sınırları router ile **kavramsal olarak yakın** noktalarda örtüşür; bu ADR router usage map'i kaydeder, firewall/trust kararlarını router'a taşımaz.

---

## Mevcut routing kullanım haritası

Haziran 2026 repo taraması sonucu — **salt okuma analizi**; kod veya davranış değişikliği yoktur.

### Özet bulgular

- **Birleşik AI Router yok.** `ai_router`, `routing_engine` veya tek merkezi yönlendirme modülü tespit edilmemiştir.
- **Yönlendirme parçalıdır:** `cli_router`, `bridge_intent`, `lumos_gate`, `task_dispatch`, `profiles` ve engine/model katmanları ayrı karar verir.
- **Model seçimi yalnızca `OPENAI_MODEL` ortam değişkeni seviyesindedir** (`model_client`, `lumos_gate`, `text_executor`, köprü `server.py`). Provider, tier, maliyet veya hız sinyaline göre routing **yoktur**.
- **Router / Firewall / Trust sınırları** bazı noktalarda örtüşür (risk, onay, `no_op`, profil deny). Ayrım için ADR-006 (guard), ADR-007 (trust) ve ADR-010 (terminoloji) **birlikte** okunmalıdır; bu ADR firewall veya trust kararlarını router'a **taşımaz**.
- **Kod veya büyük refactor için erken.** Usage map kilitlendikten sonra dar **import/drift karşılaştırması** yapılabilir; router motoru veya provider entegrasyonu bu aşamada **yapılmaz**.

### Giriş noktası → zincir haritası

| Giriş noktası | Karar türü | Sonraki adım / tüketici | Not |
|---------------|------------|-------------------------|-----|
| `src/main.py` → `src/core/lumos_runtime.py` | CLI bootstrap | `cli_router.run_cli_loop` | Router yalnızca CLI dağıtımı |
| `src/cli/cli_router.py` | Komut eşleme; `unknown` + online | `on_live_brain` → `live_brain.handle_live_brain` | Offline: `get_fallback_message` |
| `src/core/live_brain.py` | Serbest metin / pending intent | `online_engine.OnlineEngineV1.process` → `model_client` | `user_intent_classifier` (deterministik intent) |
| `packages/kando_bridge/.../server.py` POST `/task` | Köprü girişi | `bridge_intent` → `lumos_gate` → `task_dispatch` → executor | Panel/chat hattı ayrı |
| `bridge_intent.classify_bridge_message_intent` | `task` \| `chat` | `task`: gate+dispatch; `chat`: LLM cevap (gate bypass) | `lumos_gate` regex yardımcılarına import bağımlılığı |
| `lumos_gate.run_lumos_gate` | `agent` \| `direct_patch` \| `no_op` | `lumos_gate_execute`, pending approval | LLM reasoning; ham metin doğrudan executor'a gitmez |
| `task_dispatch` + `kando_runtime/router.py` | `task_type`, risk, onay | `ROUTES` → `text`/`video`/`agent` executor | Gate risk öncelikli; yoksa `infer_risk` |
| `src/task_engine/profiles.py` | Profil × adım türü | `task_engine/engine.py`, `may_execute_step_at_runtime` | `SECURITY_NEVER_AUTO`; köprü hattında doğrudan değil |
| `src/engine/model_client.py` | Tek OpenAI çağrısı | `OnlineEngineV1`, gate içi LLM | `OPENAI_MODEL` env; token log |
| `src/policy/offline_engine.py` | Offline mod | CLI fallback, policy kuralları | Network kapısı |
| `src/kando/kando_core.py` `ToolRouter` | Demo araç yönlendirme | Claude/Cursor/Codex seçimi | Ana CLI/köprü zinciriyle **birleşik değil** |

### Model / provider dokunuş noktaları

| Konum | Seçim mekanizması | Drift notu |
|-------|-------------------|------------|
| `model_client._generate_openai` | `OPENAI_MODEL` → varsayılan `gpt-4.1-mini` | Canonical engine yolu |
| `lumos_gate` (iç LLM) | Aynı env, yerel okuma | `model_client` ile paylaşımlı env; ayrı kod yolu |
| `text_executor` | Aynı env | Executor içinde tekrar |
| `kando_bridge/server.py` | `os.environ.get("OPENAI_MODEL", ...)` | Panel/chat için üçüncü kopya |

**Analiz bulgusu:** Model adı **davranış routing'i değildir**; yalnızca sabit env. Maliyet, hız, doğruluk veya çoklu provider seçimi **yoktur**.

### Drift ve çelişki riskleri (teşhis listesi)

Usage map ve sonraki import karşılaştırmasında **özellikle** kontrol edilmesi gereken noktalar (analiz bulgusu):

| Risk | Açıklama | Etkilenen modüller |
|------|----------|-------------------|
| **Çift niyet sınıflandırıcı** | `bridge_intent` (task\|chat) ile `user_intent_classifier` (deterministik intent) farklı kurallar | Köprü vs CLI live brain |
| **Gate ↔ dispatch risk** | Gate `risk_reason` ile `infer_risk` farklı kaynak; dispatch gate öncelikli ama fallback zayıf olabilir | `lumos_gate`, `task_dispatch` |
| **Gate allow + profil deny** | Köprü hattı `profiles` ile doğrudan hizalı değil; task engine ayrı yol | ADR-006/010 ile ortak risk |
| **`bridge_intent` → `lumos_gate` import** | Niyet katmanı gate regex'ine bağımlı; router sınırı bulanık | `bridge_intent`, `lumos_gate` |
| **`src/` vs `packages/kando_*`** | Runtime köprüde; task engine `src/` altında | ADR-003 ayna drift |
| **`ToolRouter` izolasyonu** | Demo brain hattı; CLI/köprü zincirine bağlı değil | `kando_core` |
| **`OPENAI_MODEL` tekrarı** | Aynı env birden fazla dosyada okunur; tier routing yok | `model_client`, gate, executor, server |
| **Firewall/router örtüşmesi** | `no_op`, risk, onay kararları guard ve router adayı alanlarında karışabilir | ADR-006, ADR-007, ADR-010 |

Bu tablo **teşhis listesidir**; bu ADR drift'i **düzeltmez**, yalnızca haritalar.

### Import map özeti (checkpoint — tam değil)

Dar import karşılaştırması için öncelikli kenarlar (analiz bulgusu):

```
main → lumos_runtime → cli_router → live_brain → online_engine → model_client
kando_bridge/server → bridge_intent → lumos_gate → task_dispatch → router.ROUTES → executors
task_engine/engine → profiles.may_execute_step_at_runtime
lumos_gate → (iç) OPENAI_MODEL; bridge_intent ← lumos_gate yardımcıları
```

Tam import diff ve çift kayıt analizi **ayrı dar checkpoint** olarak planlanır; bu bölüm usage map'i **kilitler**, import map'i tamamlamaz.

---

## AI Router hedef rolü

AI Router, Lumos'ta **tek sorumluluklu yönlendirme karar katmanı** olarak hedeflenir. Kesin API veya modül adı henüz kararlaştırılmamıştır (*taslak*).

Router'ın hedeflediği işlevler:

1. **Kullanıcı isteğini sınıflandırma** — niyet, görev türü, hassasiyet ve bağlam sinyallerine göre kategori atama.
2. **Karar sinyallerini değerlendirme** — risk, gizlilik, maliyet, hız, doğruluk, dış kaynak ihtiyacı, offline uygunluk, görev uzunluğu/karmaşıklığı (*hedef sinyal seti; birleşik skor modeli henüz yok*).
3. **Uygun model / katman / çalışma moduna yönlendirme** — örn. offline engine, gate + executor, live brain, salt analiz profili, onay bekleyen kuyruk.
4. **Gerektiğinde kullanıcı onayı isteme** — `lumos-karar-sozlesmesi` ve `profiles.py` ile hizalı; onaysız dış etki veya kritik işlem yok.

Bu rol, ADR-001'deki "AI Firewall → Trust → Router → Memory → Agent Network" öncelik sırasında **router katmanını** somutlaştırmayı hedefler; firewall ve trust tam oturmadan router'ın tek başına üretim vaadi taşımaması gerekir (*ADR-001 ile hizalı*).

---

## İlk routing kategorileri (taslak — 10 kategori)

Aşağıdaki kategoriler **ürün yönlendirme hedefidir**; repo'da birleşik karşılıkları henüz tanımlı değildir. Mevcut parçalı eşleşmeler analiz bulgusudur, finalize edilmiş mapping değildir.

| # | Kategori | Hedef | Mevcut repo karşılığı (analiz bulgusu) | Boşluk |
|---|----------|-------|----------------------------------------|--------|
| 1 | **Düşük riskli sohbet / açıklama** | Hafif model veya yerel cevap; düşük maliyet | `bridge_intent` → `chat`; CLI `unknown` + online → `live_brain` → `OnlineEngineV1` | Birleşik kategori yok; maliyet kontrolü yok |
| 2 | **Kod analizi** | Analiz profili; yürütme ayrı | `kando_core.ToolRouter` (ayrı demo hattı); Brain `analyze` adımı | Ana CLI/köprü hattında otomatik kod-analiz router yok |
| 3 | **Doküman okuma / özetleme** | Read + özet; gate veya read executor | `lumos_gate` dosya okuma; `read_executor` | Ayrı "doküman kategorisi" sözleşmesi yok |
| 4 | **Mail önceliklendirme** | ADR-002 kategorilerine göre sınıflandırma | **Kod yok** — yalnız ADR-002 | Tam boşluk |
| 5 | **Görev planlama** | Plan üret; uygulama onaylı | `task_engine/planner.py`, `lumos_gate` `mode=agent` | "Planlama kategorisi" router sözleşmesi yok |
| 6 | **Güvenlik / hassas işlem** | `no_op` veya açık onay; profil kısıtı | `profiles.py` `STEP_TYPE_CRITICAL/EXTERNAL`, `SECURITY_NEVER_AUTO`; gate risk | Birleşik hassas kategori router yok |
| 7 | **Dış servis aksiyonu** | External step blok veya onaylı köprü | Profilde `external` asla; video → Replicate yolu | Merkezi dış-aksiyon router yok |
| 8 | **Cihaz / yerel işlem** | Offline veya safe_local profili | `OfflineEngineV1`, `controlled_bridge` sınırları | Cihaz aksiyonları demo/sınırlı |
| 9 | **Uzun analiz** | Yüksek doğruluk / çok adımlı agent yolu | `lumos_gate` çok adımlı → `agent`; `decision_pipeline` (kando_core) | Maliyet/süre sinyali ile tier seçimi yok |
| 10 | **Offline / yerel cevap** | Network yok; policy offline engine | `LUMOS_MODE`, `PolicyRules`, CLI offline fallback | Keyword tabanlı sınırlı intent seti |

Kategori ataması **öneri** niteliğindedir; kullanıcı override ve profil sınırları her zaman üstünde kalır (`lumos-karar-sozlesmesi`).

---

## Karar sinyalleri (hedef set — birleşik değil)

Router hedefinde değerlendirilecek sinyaller (*henüz merkezi skor modeli yok*):

| Sinyal | Repo durumu (analiz bulgusu) |
|--------|------------------------------|
| Risk | Kısmen — gate, dispatch, profiles |
| Gizlilik | Kısmen — keystore, imzalı istek, bridge sınırları |
| Maliyet | Yok (routing); token log var |
| Hız | Minimal — timeout/kırpma |
| Doğruluk ihtiyacı | Yok — tek model |
| Dış kaynak ihtiyacı | Kısmen — online/offline kapı, external step blok |
| Kullanıcı onayı | Evet (dağınık) |
| Offline çalışabilirlik | Evet |
| Görev uzunluğu / karmaşıklık | Kısmen — video vague kontrolü vb. |

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-004:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Basit **task route haritası** (dokümantasyon, demo-safe sözleşme) | Provider API key yönetimi ve gerçek key'ler |
| Intent sınıflandırma iskeleti (`bridge_intent`, classifier tasarım notları) | Ücretli model seçimi ve prod tier politikası |
| Profil / onay matrisi referansı (`profiles.py` davranışını değiştirmeden) | Production routing ve operasyonel model yönlendirme |
| Gate pattern açıklaması (`lumos_gate` — kontrollü reasoning) | Kişisel veri (PII) işleyen routing kuralları |
| Offline stub davranış tanımı | Cihaz aksiyonları ve prod orchestration |
| Usage map / import map (salt okuma analizi) | Mail/IMAP/OAuth entegrasyonu (ADR-002) |
| | Quantum / IBM prod entegrasyonu (ADR-001) |

Public repo'da parçalı router'ların **"tam AI Router ürünü"** gibi sunulması bilinçli olarak yapılmamalıdır; bu ADR yalnızca hedef ve mevcut boşluğu kaydeder.

---

## Karar (taslak — import/drift incelemesi bekliyor)

1. **Mevcut gerçek:** Birleşik AI Router yok; yönlendirme `cli_router`, `bridge_intent`, `task_dispatch`, `lumos_gate`, `profiles` ve engine/model katmanlarında parçalıdır (usage map: yukarıdaki bölüm).
2. **Usage map checkpoint:** Routing giriş noktaları, zincirler ve drift riskleri bu ADR'de **kilitlendi**; kod veya refactor yapılmadı.
3. **Hedef:** Yukarıdaki dört rol ve 10 kategori taslağı; karar finalize için dar import/drift karşılaştırması gerekir.
4. **Canonical katmanlar:** ADR-003 ile uyumlu — bellek `src/memory`, trust/security `src/policy` + `src/security`; router tasarımı bu katmanları bypass etmemelidir.
5. **Guard/trust sınırı:** ADR-006/007/010 ile hizalı — firewall ve trust kararları router'a **taşınmaz**; router guard/trust sinyallerini **tüketir** (hedef).
6. **Mail:** ADR-002 kapsamında kalır; bu ADR mail entegrasyonu açmaz.
7. **Quantum / Agent Network:** ADR-001 hipotez alanı; bu ADR ile birleştirilmez.
8. **Bu turda kod yok** — yalnızca karar kaydı.

Durum: **Karar dar import/drift incelemesi ve ADR-006/007 usage map hizası sonrası finalize edilir.**

---

## İlk güvenli adım: usage map kilitlendi → import/drift

**Tamamlanan (bu ADR):** Mevcut routing kullanım haritası — bkz. [Mevcut routing kullanım haritası](#mevcut-routing-kullanım-haritası). Kod veya refactor **yapılmadı**.

**Sonraki dar checkpoint (henüz yapılmadı):** Küçük import/drift karşılaştırması — öncelikli kenarlar:

| Modül çifti / kenar | Kontrol sorusu |
|---------------------|----------------|
| `bridge_intent` ↔ `lumos_gate` | Regex/import bağımlılığı router sınırını bulanıklaştırıyor mu? |
| `bridge_intent` ↔ `user_intent_classifier` | task\|chat vs deterministik intent çelişkisi var mı? |
| `lumos_gate` risk ↔ `task_dispatch.infer_risk` | Aynı görev için farklı risk sonucu mümkün mü? |
| `profiles` ↔ köprü hattı | Task engine profil deny, köprü yürütmesine yansıyor mu? |
| `OPENAI_MODEL` okuma noktaları | Env tekrarı; tier routing ihtiyacı dokümante mi? |
| `src/` ↔ `packages/kando_runtime` | Ayna drift; canonical yol hangisi? |

Import map tamamlanmadan router birleştirme, yeni modül veya provider entegrasyonu kararı **verilmez**.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, import/drift incelemesi, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Router motoru / birleşik engine** | Usage map kilitlendi; import map ve karar finalize edilmedi |
| **Kod yazma** (router birleştirme, yeni modül) | Erken; ADR-006/007 guard/trust hizası önce |
| **Provider entegrasyonu** | Public sınır; prod katmanı; usage map sonrası bile ayrı ADR |
| **Model seçim davranışı değiştirme** | `OPENAI_MODEL` tek env; tier/maliyet routing kararı yok |
| **Firewall kararlarını Router'a taşıma** | ADR-006 guard öncelikli; router guard'ın yerine geçmez |
| **Trust kararlarını Router'a taşıma** | ADR-007 trust öncelikli; lock/consent router'da birleştirilmez |
| **API key ekleme / yönetimi** | Gizli anahtar public repo'da olmamalı |
| **Agent Network kurma** | ADR-001 taslak; router öncesi değil |
| **Quantum / IBM'e geçme** | ADR-001 — erken hedef değil |
| **Mail entegrasyonu kurma** | ADR-002 — izin akışı ve kod kapsam dışı |
| Büyük refactor (tek PR'da birleştirme) | Regresyon riski; ADR-003 ile uyumsuz erken konsolidasyon |
| Abartılı ürün vaadi | Bu belge taslak; teslim veya prod routing taahhüdü yok |

---

## Riskler (analiz bulgusu)

| Risk | Not |
|------|-----|
| Parçalı router çelişkisi | Farklı katmanlar chat/task veya risk için farklı karar verebilir |
| Maliyet kontrolsüzlük | Online `unknown` girdiler LLM'e gidebilir |
| Public sınır sızıntısı | Prod orchestration veya PII routing public'e taşınabilir |
| `src/` vs `packages/kando_*` drift | ADR-003 ile uyumlu; iki ağaç senkron riski |
| Erken birleştirme | CI/regresyon; onay modeli karmaşıklaşması |

---

## Sonuç (geçici)

Haziran 2026 repo analizine dayanarak Lumos'ta **birleşik AI Router bulunmamaktadır**. Yönlendirme `cli_router`, `bridge_intent`, `task_dispatch`, `lumos_gate` ve `profiles` üzerinde parçalıdır; model seçimi yalnızca `OPENAI_MODEL` ortam değişkeni seviyesindedir. Provider, maliyet, hız ve tier routing **yoktur**. Router/firewall/trust sınırları bazı noktalarda örtüşür; ayrım ADR-006, ADR-007 ve ADR-010 ile birlikte okunmalıdır.

**Usage map checkpoint tamamlandı** — giriş zincirleri ve drift riskleri bu ADR'de kilitlendi. **Sonraki güvenli adım:** dar import/drift karşılaştırması. **Bu turda kod yazılmaz; router motoru kurulmaz.**

## Sonraki gözden geçirme

- Import/drift checkpoint sonuçları ile ADR revizyonu ve karar finalize
- ADR-006 (guard), ADR-007 (trust), ADR-010 (terminoloji) usage map hizası — router sınırı çakışma kontrolü
- 10 kategori için resmi router sözleşmesi taslağı (ayrı belge veya ADR eki)
- ADR-001 (ileri modüller), ADR-002 (mail), ADR-003 (canonical katmanlar) ile çakışma kontrolü
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot kategori seçimi (ör. sohbet vs görev planlama) — import map sonrası, ayrı onay
