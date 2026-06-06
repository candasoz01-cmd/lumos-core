# ADR-004: AI Router / Yönlendirme Katmanı (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — usage map tamamlanmadan finalize edilmez |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-002, ADR-003 |

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

## Karar (taslak — usage map bekliyor)

1. **Mevcut gerçek:** Birleşik AI Router yok; yönlendirme `cli_router`, `bridge_intent`, `task_dispatch`, `lumos_gate`, `profiles` ve engine/model katmanlarında parçalıdır.
2. **Hedef:** Yukarıdaki dört rol ve 10 kategori taslağı; finalize için usage map zorunlu.
3. **Canonical katmanlar:** ADR-003 ile uyumlu — bellek `src/memory`, trust/security `src/policy` + `src/security`; router tasarımı bu katmanları bypass etmemelidir.
4. **Mail:** ADR-002 kapsamında kalır; bu ADR mail entegrasyonu açmaz.
5. **Quantum / Agent Network:** ADR-001 hipotez alanı; bu ADR ile birleştirilmez.
6. **Bu turda kod yok** — yalnızca karar kaydı.

Durum: **Karar usage map tamamlanana kadar bekletilir.**

---

## İlk güvenli adım: usage map / import map

Büyük refactor veya provider entegrasyonu **yapılmadan** önce mevcut yönlendirme dokunuş noktalarının haritalanması önerilir.

**Hedef çıktı (ayrı checkpoint veya bu ADR eki — henüz yazılmadı):**

| Giriş noktası | Karar türü | Tükettiği / ürettiği | Not |
|---------------|------------|----------------------|-----|
| `src/cli/cli_router.py` | Komut / live brain kapısı | `on_live_brain`, CLI handlers | Online/offline ayrımı |
| `bridge_intent` | chat \| task | Köprü POST /task | Görev motoruna gitmeden önce |
| `lumos_gate` | agent \| direct_patch \| no_op | LLM reasoning, risk reason | Ham metin executor'a gitmez |
| `task_dispatch` | task_type, risk, onay | Executor kuyrukları | `pending_approval` |
| `profiles.py` | profil × adım izni | `task_engine/engine.py` | `SECURITY_NEVER_AUTO` |
| `model_client` | model çağrısı | `OPENAI_MODEL` env | Tek model yolu |
| `online_engine` / `offline_engine` | mod kapısı | PolicyRules | Network sınırı |

**Import map kapsamı (analiz görevi):** `cli_router`, `bridge_intent`, `lumos_gate`, `task_dispatch`, `profiles`, `model_client`, `live_brain`, `kando_bridge/server.py` — kim kimi import ediyor, hangi giriş noktası hangi zinciri tetikliyor.

Usage map tamamlanmadan router birleştirme veya yeni modül kararı **verilmez**.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, usage map, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Kod yazma** (router birleştirme, yeni modül) | Usage map ve karar finalize edilmedi; kapsam şişmesi |
| **Provider entegrasyonu** | Public sınır; prod katmanı |
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

Haziran 2026 repo analizine dayanarak Lumos'ta **birleşik AI Router bulunmamaktadır**. Yönlendirme `cli_router`, `bridge_intent`, `task_dispatch`, `lumos_gate` ve `profiles` üzerinde parçalıdır; model seçimi `OPENAI_MODEL` seviyesindedir. Risk/onay sinyalleri kısmen vardır; maliyet, hız, provider/model seçimi ve production routing henüz yoktur. Mail önceliklendirme ADR-002'de taslaktır; routing/quantum notları ADR-001'de hipotez düzeyindedir.

**İlk güvenli adım:** Mevcut yönlendirme noktalarının usage map / import map olarak çıkarılması. **Bu turda kod yazılmaz.**

## Sonraki gözden geçirme

- Usage map / import map checkpoint sonuçları ile ADR revizyonu ve karar finalize
- 10 kategori için resmi router sözleşmesi taslağı (ayrı belge veya ADR eki)
- ADR-001 (ileri modüller), ADR-002 (mail), ADR-003 (canonical katmanlar) ile çakışma kontrolü
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot kategori seçimi (ör. sohbet vs görev planlama) — usage map sonrası, ayrı onay
