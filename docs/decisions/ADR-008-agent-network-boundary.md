# ADR-008: Agent Network Sınır Kararı (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — agent/task/executor usage map tamamlanmadan finalize edilmez |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007 |

## Amaç

Lumos kod tabanında **birleşik Agent Network** olup olmadığını repo analizine dayalı olarak netleştirmek; hedef ajan koordinasyon rolünü, public/private sınırını, karar ilkelerini ve güvenli ilerleme adımını **kodsuz karar kaydı** olarak belgelemek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, agent davranışı değişikliği, orchestration framework veya production ajan ağı **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). ADR-001 Agent Network'ü **hipotez** düzeyinde listeler — "koordineli ajanlar arası görev paylaşımı". ADR-003 canonical bellek ve trust/security katmanlarını kaydeder. ADR-004 birleşik AI Router'ın olmadığını; ADR-006 birleşik AI Firewall'ın olmadığını; ADR-007 birleşik Trust Engine'in olmadığını; ADR-005 gerçek Memory Graph'ın olmadığını kaydeder. Bu ADR, Agent Network hedefini aynı disiplinle — önce analiz ve haritalama, sonra dar karar — kayıt altına alır.

**Öncelik sırası (ADR-001, ADR-004, ADR-005, ADR-006, ADR-007 ile hizalı):** AI Firewall → Trust → Router → Memory → **Agent Network**. Agent Network, bu omurga netleşmeden açılmamalıdır.

---

## Mevcut durum (repo analiz bulguları, Haziran 2026)

### Birleşik Agent Network yok

Repo taramasında **tek, merkezi "Agent Network" veya çok-ajan koordinasyon katmanı tespit edilmemiştir**. Mevcut yapı **tek-ajan ve parçalı yürütme hatları** şeklindedir; birleşik orchestration/coordination katmanı yoktur.

### Parçalı tek-ajan / yürütme hatları

| Katman | Konum (analiz bulgusu) | Kısa rol |
|--------|------------------------|----------|
| Tek tuş agent akışı | `src/kando/agent_runner.py` | Repo tarama → hedef seçimi → executor → verify → commit/push → rapor; `src/core/` altı sınırlı hedef |
| LLM plan yürütme | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | `execute_plan`, `_execute_plan_steps`; çok adımlı agent modu; gate reasoning |
| Görev türü → executor | `packages/kando_runtime/src/kando_runtime/task_dispatch.py`, `router.py` | `video/image/audio/file/shell/generic`; risk ve onay kuyrukları |
| Cursor köprü / patch | `src/kando/cursor_bridge.py` | Execution/result paketleri, onay kuyruğu, patch uygulama; `may_execute_step_at_runtime` |
| Köprü giriş zinciri | `packages/kando_bridge/src/kando_bridge/server.py` | `bridge_intent`, `lumos_gate`, `task_dispatch`; `agent_runner` import |
| Görev motoru | `src/task_engine/*` | Planlama, kuyruk, executor'lar, doğrulama, profil matrisi |
| Runtime executor'lar | `packages/kando_runtime/src/kando_runtime/executors/*` | file, shell, video, image, read vb. — dispatch üzerinden |
| Panel görev/kayıt | `panel/js/app.js` (analiz bulgusu) | Görevler/Kayıtlar görünürlüğü; demo/köprü durumuna bağlı |

**Analiz bulgusu:** Bu hatlar **birbirine bağlı ancak birleşik değildir** — örneğin `agent_runner` tek dosya hedefli patch akışı çalıştırır; `lumos_gate` çok adımlı plan üretir; `task_dispatch` executor yönlendirmesi yapar; `cursor_bridge` ayrı onay/patch sözleşmesi taşır; `task_engine` görev state ve profil sınırlarını uygular. Aralarında tutarlı bir **ajan kimliği, rol sözleşmesi veya koordinasyon protokolü** yoktur.

### Birleşik koordinasyon katmanı yok

| Alan | Durum (analiz bulgusu) |
|------|------------------------|
| Agent-to-agent mesajlaşma / delegasyon | Yok |
| Rol tabanlı ajan registry | Yok |
| Merkezi orchestrator / coordinator | Yok |
| Çok-ajan görev paylaşım sözleşmesi | Yok |
| Agent Network durum modeli | Yok — ADR-001 hipotez |
| Production multi-agent orchestration | Public sınır dışı |

### İlgili ADR durumu

- **ADR-001:** Agent Network **hipotez**; öncelik sırasında Firewall → Trust → Router → Memory **sonrasında** konumlanmalıdır. Quantum erken hedef değil.
- **ADR-003:** Canonical bellek `src/memory`; trust/security `src/security` ve `src/policy`. Agent Network tasarımı bu katmanları ve `profiles.py` yetki sınırlarını bypass etmemelidir.
- **ADR-004:** Birleşik AI Router **yok**; router Trust/Firewall kararlarından **sonra** yönlendirme yapmalı. Agent Network router sinyallerini **kullanmalı**; router'ın yerine geçmemelidir.
- **ADR-005:** Gerçek Memory Graph **yok**; bellek parçalı. Agent Network bağlam paylaşımı Memory Graph oturmadan tek başına üretim vaadi taşımamalıdır.
- **ADR-006:** Birleşik AI Firewall **yok**; guard parçalı. Her dış aksiyon ve hassas adım firewall + trust kontrolünden geçmelidir (*hedef ilke*).
- **ADR-007:** Birleşik Trust Engine **yok**; trust parçalı. Agent yetkileri trust durumu ve profil matrisi ile sınırlı olmalıdır (*hedef ilke*).

---

## Agent Network hedef rolü

Agent Network, Lumos'ta birden fazla ajan/işleyici arasında **koordineli görev paylaşımı** sağlayan katman olarak hedeflenir (ADR-001 hipotezi). Kesin API, protokol veya modül adı henüz kararlaştırılmamıştır (*taslak*).

Hedeflenen işlevler:

1. **Birden fazla ajan/işleyici arasında görev paylaşımı yapmak** — delegasyon, alt görev atama ve sonuç birleştirme; tek monolitik agent yerine rol ayrımı.
2. **Uzun işleri alt adımlara bölmek** — plan → yürütme → doğrulama → raporlama aşamalarının sınırlı, izlenebilir parçalara ayrılması.
3. **Kod, belge, görev, kontrol, doğrulama ve raporlama rollerini ayırmak** — her rolün yetki ve yüzey sınırı açık; tek ajanın tüm yetkileri üstlenmesi hedeflenmez.
4. **AI Router, AI Firewall, Trust Engine ve Memory Graph sinyallerini kullanmak** — yönlendirme, risk, güven ve bağlam kararlarına dayalı koordinasyon (*bu katmanlar henüz birleşik değil — ADR-004, ADR-005, ADR-006, ADR-007*).
5. **Kullanıcı onayı gereken aksiyonlarda durmak** — `lumos-karar-sozlesmesi`, `profiles.py` ve `SECURITY_NEVER_AUTO` ile hizalı; onaysız dış etki veya kritik işlem yok.

Bu rol ADR-001'deki "AI Firewall → Trust → Router → Memory → Agent Network" öncelik sırasında **son katmanı** somutlaştırmayı hedefler; alt katmanlar oturmadan Agent Network'ün tek başına üretim vaadi taşımaması gerekir.

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-008:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Tek ajan pipeline tasarım notları (demo-safe) | Gerçek agent-to-agent orchestration |
| Task/executor routing referansı (`task_dispatch`, `router` — davranışı değiştirmeden) | Cihaz kontrolü ve üretim terminal erişimi |
| Demo-safe plan yürütme pattern'i (`lumos_gate` `execute_plan` açıklaması) | Dış servis aksiyonları (prod entegrasyon) |
| `agent_runner` sınırlı hedef akışı (dokümantasyon) | Mail/Gmail/IMAP/OAuth erişimi (ADR-002) |
| `task_engine` profil/onay matrisi referansı | Ödeme/domain/satın alma işlemleri |
| Agent/task/executor usage map (salt okuma analizi) | Production secrets ve provider key yönetimi |
| Panel görev/kayıt görünürlük (dürüst demo metinleri) | Operasyonel backend, prod multi-agent ağı |
| Karar ilkeleri ve sınır belgesi (bu ADR) | Quantum/IBM prod entegrasyonu (ADR-001) |

Public repo'da parçalı yürütme hatlarının **"tam Agent Network ürünü"** veya **otonom çok-ajan sistemi** gibi sunulması bilinçli olarak yapılmamalıdır; bu ADR yalnızca hedef, sınır ve mevcut boşluğu kaydeder.

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent, kilit ve kalıcı silme alanları **dokunulmaz**; bu ADR o sınırları gevşetmez veya genişletmez.

---

## Karar ilkeleri (taslak — 7 ilke)

Agent Network tasarımı ve ilerideki dar uygulama adımları aşağıdaki ilkelere uymalıdır:

| # | İlke | Kısa açıklama |
|---|------|---------------|
| 1 | **Her agent rolü açık tanımlanmalı** | Kod, belge, görev, kontrol, doğrulama, raporlama vb. roller sözleşme ile; belirsiz "genel ajan" yok |
| 2 | **Her agent yetkisi sınırlı olmalı** | `profiles.py`, trust durumu ve yüzey blokları ile; en az yetki prensibi |
| 3 | **Her dış aksiyon önce Firewall + Trust kontrolünden geçmeli** | ADR-006 ve ADR-007 ile hizalı; parçalı guard'lar birleşmeden bile bu hedef korunur |
| 4 | **Kritik işlemler kullanıcı onayı olmadan yapılmamalı** | `SECURITY_NEVER_AUTO`, genel onay, açık komut; otonom dış etki yok |
| 5 | **Public repo yalnızca demo-safe orchestration göstermeli** | Gerçek multi-agent prod davranışı public'e taşınmaz |
| 6 | **Gerçek production ajan ağı ayrı private layer'da ele alınmalı** | Cihaz, secret, mail, ödeme ve operasyonel orchestration private katman |
| 7 | **Log ve açıklanabilirlik zorunlu olmalı** | Hangi ajan, hangi adım, hangi onay — izlenebilir kayıt; kör otonomi hedeflenmez |

---

## Karar (taslak — usage map bekliyor)

1. **Mevcut gerçek:** Birleşik Agent Network yok; yürütme `agent_runner`, `lumos_gate`, `task_dispatch`, `cursor_bridge`/köprü ve `task_engine` üzerinde **parçalı tek-ajan hatları** şeklindedir; birleşik koordinasyon katmanı yoktur.
2. **Hedef:** Yukarıdaki beş rol, yedi karar ilkesi ve public/private sınır; finalize için agent/task/executor usage map zorunlu.
3. **Öncelik sırası (ADR-001):** Firewall → Trust → Router → Memory → **Agent Network**; alt katmanlar oturmadan Agent Network açılmaz.
4. **Alt katman ilişkisi:** ADR-004 (router sinyalleri), ADR-005 (bağlam/bellek), ADR-006 (firewall/guard), ADR-007 (trust) ile uyumlu ilerlenmeli; Agent Network bu katmanları bypass etmemelidir.
5. **Canonical katmanlar (ADR-003):** Bellek `src/memory`; trust/security `src/security` + `src/policy`; yetki `task_engine/profiles.py`.
6. **Bu turda kod yok** — yalnızca karar kaydı.

Durum: **Karar agent/task/executor usage map tamamlanana kadar bekletilir.**

---

## İlk güvenli adım: agent/task/executor usage map

Büyük agent framework refactor veya production orchestration **yapılmadan** önce mevcut ajan/yürütme dokunuş noktalarının haritalanması önerilir.

**Hedef çıktı (ayrı checkpoint veya bu ADR eki — henüz yazılmadı):**

| Giriş noktası | Akış türü | Tükettiği / ürettiği | Not |
|---------------|-----------|----------------------|-----|
| `agent_runner.py` | Tek tuş agent | Hedef seçimi → executor → verify | `src/core/` sınırlı; köprü/server import |
| `lumos_gate.execute_plan` | Çok adımlı plan | LLM plan, substep yürütme | Gate reasoning; ham metin executor'a gitmez |
| `task_dispatch.py` | task_type → executor | Risk, onay kuyrukları, dispatch plan | `pending_approval`, `execution_permitted` |
| `cursor_bridge.py` | Patch/onay köprüsü | Execution/result paketleri | `may_execute_step_at_runtime`; onay dosyası |
| `kando_bridge/server.py` | Köprü POST | `bridge_intent` → gate → dispatch | Panel/chat girişi |
| `task_engine/engine.py` | Görev motoru | Plan, kuyruk, profil, doğrulama | `.lumos/tasks/` state |
| `task_engine/executors/*` | Adım yürütme | read, analyze, patch, safe_local vb. | Profil × adım matrisi |
| `kando_runtime/executors/*` | Runtime executor | file, shell, video, image vb. | Dispatch üzerinden |
| Panel görev/kayıt | UX görünürlük | Demo/köprü durumu | Orchestration değil |

**Import map kapsamı (analiz görevi):** `agent_runner` → `cursor_bridge` / executor → `lumos_gate` → `task_dispatch` → `profiles` / `may_execute_step_at_runtime` → `task_engine` → runtime executor'lar → köprü (`kando_bridge/server.py`) — kim kimi import ediyor, hangi giriş noktası hangi yürütme zincirini tetikliyor, hangi onay/trust/firewall sinyali tüketiliyor.

Usage map tamamlanmadan Agent Network birleştirme, yeni orchestration modülü veya agent framework kararı **verilmez**.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, usage map, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Kod yazma** (orchestration, yeni agent modülü) | Usage map ve karar finalize edilmedi; kapsam şişmesi |
| **Gerçek Agent Network kurma** | ADR-001 taslak; Firewall → Trust → Router → Memory öncesi değil |
| **Büyük agent framework / refactor** | Regresyon riski; parçalı hatlar önce haritalanmalı |
| **Cihaz / terminal kontrolü ekleme** | Public sınır; private/professional katman |
| **Mail / OAuth / Gmail entegrasyonu** | ADR-002 — izin akışı ve kod kapsam dışı |
| **Ödeme / domain işlem entegrasyonu** | Public sınır; prod katmanı |
| **Production secrets / provider key kullanımı** | Gizli anahtar public repo'da olmamalı |
| **Quantum / IBM tarafına geçme** | ADR-001 — erken hedef değil |
| **Public repo'da otonom dış aksiyon** | Onaysız dış etki yasağı; demo-safe sınır ihlali |

Ek olarak: abartılı "otonom ajan ordusu" vaadi, production orchestration'un public'e taşınması ve alt katmanları bypass eden koordinasyon **yapılmaz**.

---

## Riskler (analiz bulgusu)

| # | Risk | Not |
|---|------|-----|
| 1 | **Ajanların yetki sınırını aşması** | Parçalı profil/gate; tek ajan tüm executor yüzeyine erişebilir |
| 2 | **Kullanıcı onayı olmadan dış aksiyon** | Dispatch onay kuyruğu kısmen var; tüm hatlarda tutarlı değil |
| 3 | **Task loop / sonsuz worker** | Kuyruk watcher ve çok adımlı plan — üst sınır/abort sözleşmesi birleşik değil |
| 4 | **Yanlış ajana yanlış görev** | Rol registry yok; `task_type` heuristic ve dispatch karışıklığı |
| 5 | **Private veri sızıntısı** | Agent bağlam paylaşımı; Memory Graph oturmadan cross-agent context riski |
| 6 | **Public repo'ya production orchestration sızması** | Multi-agent prod mantığı public foundation'a karışabilir |
| 7 | **Kontrolsüz cihaz / terminal erişimi** | `shell_executor`, `device_tasks` — demo sınırlı; prod cihaz kontrolü public dışı |
| 8 | **Kullanıcıyı yanıltan "otonom" vaat** | Parçalı hatlar birleşik Agent Network gibi sunulabilir |

---

## Sonuç (geçici)

Haziran 2026 repo analizine dayanarak Lumos'ta **birleşik Agent Network bulunmamaktadır**. Yürütme `agent_runner`, `lumos_gate`, `task_dispatch`, `cursor_bridge`/köprü ve `task_engine` üzerinde **parçalı tek-ajan hatları** şeklindedir; birleşik koordinasyon/orchestration katmanı yoktur. ADR-001 sırasına göre Agent Network, Firewall → Trust → Router → Memory omurgası netleşmeden açılmamalıdır. ADR-004, ADR-005, ADR-006 ve ADR-007 ile uyumlu ilerlenmelidir.

**İlk güvenli adım:** Mevcut agent/task/executor dokunuş noktalarının usage map / import map olarak çıkarılması. **Bu turda kod yazılmaz; büyük agent framework refactor yapılmaz; production orchestration kurulmaz.**

## Sonraki gözden geçirme

- Agent/task/executor usage map checkpoint sonuçları ile ADR revizyonu ve karar finalize
- Rol sözleşmesi taslağı (kod, belge, görev, kontrol, doğrulama, raporlama) — usage map sonrası
- ADR-001 (ileri modüller), ADR-003 (canonical katmanlar), ADR-004 (router), ADR-005 (memory graph), ADR-006 (firewall), ADR-007 (trust) ile çakışma kontrolü
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot tek-rol delegasyon seçimi — usage map sonrası, ayrı onay
