# ADR-008: Agent Network Sınır Kararı (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — agent/task/executor usage map checkpoint tamamlandı; karar finalize dar import/drift incelemesi sonrası. **Ek karar (2026-07-16):** ortak koordinasyon katmanının resmi adı ve bileşen taksonomisi kabul edildi — bkz. § Lumos Board; bu, Agent Network'ün genel inşa kararını **değiştirmez**, öncelik sırası ve gating aynen geçerlidir. **Ek vizyon notu (2026-07-16, karar değil, henüz commit edilmedi):** Board = ortak durum (shared state), mesajlaşma sistemi değil; çapraz-araç (ChatGPT/Codex/Lark) ortak okuma/yazma yüzeyi ihtiyacı — bkz. § Lumos Board = Ortak Durum |
| Tarih | 2026-06-06 (güncelleme: 2026-07-16 — Lumos Board adlandırma kararı) |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, `docs/lumos-persona-layers.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010, ADR-011 |

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
- **ADR-010:** Guard/policy/trust terminolojisi; agent rol adlandırması ve onay sınırları bu ADR ile karıştırılmamalıdır.

---

## Agent Network hedef rolü

Agent Network, Lumos'ta birden fazla ajan/işleyici arasında **Lumos Orkestratör üzerinden koordineli görev paylaşımı** sağlayan katman olarak hedeflenir (ADR-001 hipotezi). Bu katmanın resmi adı **Lumos Board**'dur (bkz. § Lumos Board — resmi ad ve bileşenler); kesin API ve protokol detayları henüz kararlaştırılmamıştır (*taslak*).

Hedeflenen işlevler:

1. **Birden fazla ajan/işleyici arasında görev paylaşımı yapmak** — yalnızca kullanıcı veya Lumos Orkestratör kaynaklı yönlendirme ile alt işlere ayırma ve sonuç birleştirme; agent-to-agent komut zinciri yok.
2. **Uzun işleri alt adımlara bölmek** — plan → yürütme → doğrulama → raporlama aşamalarının sınırlı, izlenebilir parçalara ayrılması.
3. **Kod, belge, görev, kontrol, doğrulama ve raporlama rollerini ayırmak** — her rolün yetki ve yüzey sınırı açık; tek ajanın tüm yetkileri üstlenmesi hedeflenmez.
4. **AI Router, AI Firewall, Trust Engine ve Memory Graph sinyallerini kullanmak** — yönlendirme, risk, güven ve bağlam kararlarına dayalı koordinasyon (*bu katmanlar henüz birleşik değil — ADR-004, ADR-005, ADR-006, ADR-007*).
5. **Kullanıcı onayı gereken aksiyonlarda durmak** — `lumos-karar-sozlesmesi`, `profiles.py` ve `SECURITY_NEVER_AUTO` ile hizalı; onaysız dış etki veya kritik işlem yok.

Bu rol ADR-001'deki "AI Firewall → Trust → Router → Memory → Agent Network" öncelik sırasında **son katmanı** somutlaştırmayı hedefler; alt katmanlar oturmadan Agent Network'ün tek başına üretim vaadi taşımaması gerekir.

---

## OpenAI Agents SDK kullanımı — şimdilik eklenmeyecek (karar, 2026-08-08)

**Karar:** OpenAI Agents SDK bugün Lumos'a dependency olarak eklenmeyecek;
mevcut Responses API mimarisi devam edecektir. Bu karar kapsamında kod,
entegrasyon veya PR açılmaz.

**Gerekçe:** Agents SDK bugün Lumos'ta eksik olan temel bir yetenek sağlamaz.
Lumos'ta Orkestratör, Board claim/sahiplik, işlem bazlı confirmation policy,
Responses API tool-loop ve canonical kanıt/audit katmanları zaten vardır.
SDK'nin ajan döngüsü, session, handoff, approval ve tracing yüzeylerini bütün
sisteme eklemek aynı sorumluluklar için ikinci bir kontrol düzlemi ve iki ayrı
doğruluk kaynağı oluşturma riski taşır.

### Yeniden değerlendirme koşulu

Karar yalnız özel tool-loop'un ölçülebilir bakım maliyeti, tekrar eden hata veya
geliştirme darboğazı oluşturması halinde; yeni kullanıcı kararıyla yeniden
değerlendirilir. Bir örnek başlangıç projesinin veya SDK özelliğinin bulunması
tek başına entegrasyon gerekçesi değildir.

### Olası pilotun zorunlu sınırları

İleride ihtiyaç kanıtlanırsa bütün mimari taşınmaz; önce dar ve geri alınabilir
bir pilot yapılır:

1. Yalnız tek, salt-okunur uzman ajan kullanılır; gerçek dış etki oluşturamaz.
2. Ana Lumos Orkestratör yanıt ve görev sahipliğini korur. Uzman ajan araç gibi
   çağrılır (`agent.as_tool()` benzeri manager modeli); **handoff kullanılmaz**.
3. Board claim/sahiplik, confirmation policy, kimlik, memory ve canonical audit
   katmanları authoritative kalır; SDK bunları bypass edemez veya değiştiremez.
4. SDK session yalnız geçici run state olabilir; Lumos kimliği, oturumu,
   konuşma kimliği veya kalıcı memory yerine kullanılamaz.
5. SDK tracing canonical audit değildir. Veri minimizasyonu ve sır maskeleme
   doğrulanmadan varsayılan açık bırakılmaz; pilotta kapalı veya açıkça
   filtrelenmiş çalışır.
6. Pilot başarısı, mevcut güvenlik sözleşmeleri korunurken özel tool-loop bakım
   yükünün somut olarak azalmasıyla ölçülür.

**Karar anı doğrulaması:** Board claim, coordination gateway, confirmation
policy ve Responses API tool-loop kapsamındaki 93 hedefli test geçti. Bu sonuç
mevcut mimarinin test edilen davranışının karar sırasında bozulmadığını
gösterir; production/canlı Agents SDK doğrulaması değildir.

---

## Lumos Board — resmi ad ve bileşenler (karar, 2026-07-16)

Ortak koordinasyon katmanının resmi adı **Lumos Board**'dur. Bu karar kalıcıdır; alternatif adlar (`Lumos Bus`, `Lumos Blackboard`, `Command Wall`) değerlendirilmiş, **Board** tercih edilmiştir.

**Lumos Board bir ajanlar-arası mesaj veri yolu (message bus) değildir.** İsimlendirme bilinçli olarak "bus" değil "board" seçilmiştir çünkü bus terimi peer-to-peer, ajandan-ajana doğrudan mesajlaşmayı çağrıştırır — bu, § Karşılıklı denetim, sıfır kontrol ilkesindeki "yatay AI → AI komut yoktur" kuralıyla çelişir. Lumos Board, mimari olarak bir **kontrolörlü kara tahta (blackboard)** desenidir: ajanlar paylaşılan durumu okur ve kendi sonucunu yazar; görev atama, kilit ve onay kararları yalnızca Lumos Orkestratör üzerinden akar.

### Bileşen taksonomisi (hedef — henüz inşa edilmedi)

Aşağıdaki bileşenler Lumos Board'un **hedeflenen** iç mekanizmalarıdır; kullanıcı tek bir "Board" kavramıyla etkileşir, bu bileşenler geliştirici tarafında ayrışır:

| Bileşen | Rol | Mevcut repo karşılığı / ilişki |
|---------|-----|-------------------------------|
| **Event Bus** | Ajanlar arası olay yayını (görev başladı/bitti, durum değişti) — okuma amaçlı, komut değil | Yok; yeni bileşen |
| **Lock Manager** | Görev/kaynak kilit sahipliği (`TASK-145 → Owner: Cursor`), global pause/resume sinyali | ADR-011 `session_unlocked` / `keystore_ready` ile **karıştırılmamalı** — bu, task/resource-level kilit, oturum kilidi değil |
| **Task Queue** | Ajanlar arası görev durumu ve sahiplik kaydı | **Önce mevcut drift çözülmeli**: panel `.lumos/tasks.json` ile TaskEngine `.lumos/tasks/tasks.json` zaten iki ayrı, senkron olmayan depo (bkz. § Drift ve çelişki riskleri) — Task Queue üçüncü bir depo olarak eklenemez, ikisini birleştirmelidir |
| **Memory Events** | Bağlam/bellek güncellemesi bildirimleri | ADR-005 gerçek Memory Graph henüz yok — bu bileşen Memory Graph'a bağımlı |
| **Agent Status** | Hangi ajan neyle meşgul, hangi durumda | Yok; yeni bileşen |
| **Permission Channel** | Onay/izin durumu yayını | `task_engine/profiles.py`, dispatch onay kuyruğu ile hizalanmalı; ADR-007 Trust Engine'e bağımlı |
| **Notification Stream** | Kullanıcıya/diğer ajanlara bildirim akışı | Yok; yeni bileşen |

**Bu tablo bir inşa planı değildir** — bileşenler kavramsal hedef taksonomidir. ADR-001 öncelik sırası (Firewall → Trust → Router → Memory → Agent Network) ve bu ADR'nin genel gating kararı **aynen geçerlidir**: Lock Manager ADR-007 trust motorunu, Permission Channel ADR-006/007'yi, Memory Events ADR-005'i bekler. **Bu turda hiçbir bileşen için kod yazılmaz.**

### Lumos Board = Ortak Durum (Shared State), mesajlaşma sistemi değil (ileri vizyon notu — 2026-07-16, henüz karar değil, henüz commit edilmedi)

Lumos Board'un ilerideki hedefte yalnızca Lumos içi bileşenler arasında değil, **farklı dış araçlar arasında da ortak durum (shared state) yüzeyi** olması vizyonu kaydedilmiştir: ChatGPT, Codex, Cursor, Lark ve benzeri araçlar birbirine doğrudan mesaj göndermez; hepsi aynı ortak duruma yazar ve aynı ortak durumdan okur.

**Temel ayrım: Board ≠ mesajlaşma sistemi. Board = ortak durum.** Bu, § Karşılıklı denetim, sıfır kontrol ilkesindeki "yatay AI → AI komut yoktur" kuralını güçlendirir — araçlar arasında adreslenmiş mesaj veya komut yoktur; her araç bağımsız olarak paylaşılan durumu okur, kendi bulgusunu/sonucunu yazar; karar yine yalnızca Lumos Orkestratör veya kullanıcıdadır.

**Somut tetikleyici:** Bu ADR'nin güncellenmesi sırasında kullanıcı, Claude ile Codex arasında bir mesajı elle taşımak zorunda kaldı — Codex'in "buna doğrudan bir kanalım yok" demesi, Lumos Board'un çözmesi hedeflenen boşluğun canlı örneğidir.

Kullanıcının önerdiği hedef kategori seti (2026-07-16, ikinci tur netleştirme — "Tasarım Kararları" ve "Yapılacaklar" kategorileri "Olaylar" ve "Çalışma Durumu" ile netleştirilerek kaldırıldı):

| Kategori | Bileşen taksonomisiyle ilişki |
|----------|-------------------------------|
| Görevler | Task Queue |
| ADR / Kararlar | `docs/decisions/` mevcut ADR akışının Board'a yansıması |
| Bekleyen Onaylar | Permission Channel |
| Handoff Notları | Yeni kategori — ajanlar arası el değişimi notu |
| Riskler | Yeni kategori |
| Olaylar (Events) | Event Bus |
| Çalışma Durumu (Working / Idle / Blocked) | Agent Status |
| Bilgi Notları | Yeni kategori — genel amaçlı serbest not |

### Kayıt yapısı: serbest metin değil, tipli kayıt (aynı vizyon notu kapsamında, 2026-07-16)

Board'a yazılan her kayıt **serbest metin değil, tipli (typed) bir kayıt** olmalıdır. Bir aracın Board'la ilk teması metni yorumlamak değil, kaydın `TYPE` alanına bakıp kendisini ilgilendiren kayıtları filtrelemek olmalıdır; doğal dil yorumu yalnızca filtrelenmiş kayıt içinde, ikinci aşamada devreye girer.

Örnek kayıt tipleri (kullanıcı önerisi, 2026-07-16):

```text
TYPE: DECISION
Başlık: Lumos Board adı kabul edildi.
ADR: 008
Durum: Accepted
```

```text
TYPE: TASK
Başlık: Landing page mesajı yeniden yazılacak.
Öncelik: High
Sahip: Codex
Durum: Waiting
```

```text
TYPE: QUESTION
Soru: LinkedIn görselleri şimdi kullanılacak mı?
Soran: ChatGPT
Durum: Waiting Answer
```

```text
TYPE: HANDOFF
Özet:
- Push tamamlandı.
- 2 untracked dosya var.
- Commit atılmadı.
```

**Gerekçe:** Sabit alanlı (`TYPE`, `Durum`, `Sahip` vb.) kayıtlar, ajan sayısı arttıkça (ChatGPT, Codex, Lark, Slack, ...) mimariyi bozmadan ölçeklenir — her yeni araç yalnızca kendi ilgilendiği `TYPE`'ları filtreler, serbest metni baştan sona ayrıştırmaz. Format insan ve araç için ortaktır; insan da aynı yapıyla yazabilir.

**Bu da aynı vizyon notunun bir parçasıdır, karar değildir** — kayıt şeması (zorunlu/opsiyonel alanlar, `TYPE` kümesinin tam listesi) ayrı bir tasarım turunda netleşecektir. Bu turda şema kilitlenmez, kod yazılmaz.

### Kayıt yaşam döngüsü, sahiplik ve değiştirilemezlik (aynı vizyon notu kapsamında, 2026-07-16)

Tipli kayıtlarda yalnızca "ne" olduğu değil, **hangi aşamada** olduğu da sabit bir alanla görünür olmalıdır — kayıt yaşam döngüsü (`STATUS`), sahiplik (`OWNER`) ve zaman damgası da şemanın parçasıdır.

Genişletilmiş örnek alan seti (kullanıcı önerisi, 2026-07-16):

```text
TYPE: TASK
STATUS: OPEN
OWNER: Codex
PRIORITY: HIGH
CREATED_BY: ChatGPT
UPDATED_AT: 2026-07-17T...
```

Hedeflenen `STATUS` kümesi: `OPEN`, `IN_PROGRESS`, `BLOCKED`, `WAITING_APPROVAL`, `COMPLETED`, `ARCHIVED`.

**Kritik kural: Hiçbir araç başka bir aracın kaydını sessizce değiştiremez.** Bir kayıt güncellenecekse: (1) yeni bir revizyon eklenir, (2) durum açıkça değiştirilir, (3) gerekçe yazılır. Sessiz üzerine yazma yok — iz her zaman kalır. Bu, ADR'lerin kendi karar kaydı disiplinini (ekleyerek revize et, gerekçelendir, sessizce silme/değiştirme yok) Board kayıtlarına da taşır; her kayıt kendi mini "karar kaydı" izlenebilirliğine tabidir.

**Bu da aynı vizyon notunun bir parçasıdır, karar değildir** — `STATUS` kümesinin tam listesi, revizyon formatı ve "kim başkasının kaydını neden güncelleyebilir" sınırı ayrı bir tasarım turunda netleşecektir. Bu turda şema kilitlenmez, kod yazılmaz.

### Erişim modeli: görünürlük ve yetki (aynı vizyon notu kapsamında, 2026-07-16)

Her kaydın kim tarafından görülebileceği ve kimin ne yapabileceği de şemanın parçası olmalıdır.

Hedeflenen görünürlük (`VISIBILITY`) kümesi:

- `PUBLIC` — tüm araçlar okuyabilir
- `INTERNAL` — yalnızca çekirdek ajanlar
- `PRIVATE` — yalnızca sahibi ve yetkili ajanlar
- `USER_ONLY` — yalnızca kullanıcı onayıyla

Hedeflenen yetki seviyeleri: `READ`, `COMMENT`, `PROPOSE_CHANGE`, `APPLY_CHANGE`.

**Neden önemli:** `PROPOSE_CHANGE` ile `APPLY_CHANGE` ayrımı, bir aracın "bu ADR değişsin" diyebilmesini ama **tek başına değiştirememesini** şema seviyesinde somutlaştırır. Bu, ADR-008'in zaten kayıtlı olan § Karşılıklı denetim, sıfır kontrol ilkesi ve § Kayıt yaşam döngüsü "hiçbir araç başka bir aracın kaydını sessizce değiştiremez" kuralıyla birebir örtüşür — yeni bir ilke değil, mevcut ilkenin erişim modeli seviyesinde ifadesidir.

### Board bir bilgi deposu değildir — yalnızca canlı iş (aynı vizyon notu kapsamında, 2026-07-16)

Board, kalıcı bilgi deposuna (ansiklopediye) dönüşmemelidir. Kalıcı bilgi — ADR içerikleri, dokümantasyon, kod, karar gerekçeleri — her zaman kendi canonical yerinde kalır: `docs/decisions/`, Git, `docs/memory/`. Board yalnızca **canlı işin** (açık görev, bekleyen onay, güncel risk, aktif handoff) durumunu tutar ve kalıcı kayda **referans verir**, onu kopyalamaz:

```text
TYPE: DECISION
STATUS: ACCEPTED
REF: ADR-008
```

**Gerekçe:** Board kendi içinde tam metin taşımaya başlarsa zamanla okunamaz hale gelir ve canonical kaynakla çatallanma (drift) riski doğar — bu ADR'nin zaten teşhis ettiği panel `.lumos/tasks.json` ↔ TaskEngine `.lumos/tasks/tasks.json` drift'inin bir başka türü olurdu (bkz. § Drift ve çelişki riskleri). **Board = işaretçi + canlı durum; ADR/doküman/Git/Memory = gerçek içerik.**

### Denetçi (Guardian) modeli: teslim ≠ commit yetkisi (aynı vizyon notu kapsamında, 2026-07-17)

Ajanlar/araçlar kendi commit'lerini kendileri oluşturmaz. Bir araç işini bitirdiğinde Board'a bir `DELIVERY` kaydı bırakır; commit kararını ayrı bir **Denetçi (Guardian)** rolü verir.

```
Görev → Ajan(lar) → Lumos Board (TYPE: DELIVERY, STATUS: READY_FOR_REVIEW) → Denetçi → RED (geri gönder) | GREEN (commit oluştur → merge/deploy)
```

Örnek `DELIVERY` kaydı (kullanıcı önerisi):

```text
TYPE: DELIVERY
TASK_ID: T-248
OWNER: Codex
FILES:
 - packages/...
 - docs/...
STATUS: READY_FOR_REVIEW
```

Denetçinin kontrol listesi: aynı dosyaya birden fazla araç mı dokunmuş (çakışma), ADR'ye aykırı mı, testler geçiyor mu, kod standartlarına uyuyor mu, başkasının işini bozuyor mu, commit gerçekten tek bir konuyu mu içeriyor. Hepsi uygunsa: ilişkili `DELIVERY` kayıtlarını gruplar (gerekirse birden fazla aracın işini tek feature commit'inde birleştirir), commit mesajını üretir, onaya sunar, onay sonrası merge/deploy başlatır.

**Rol ayrımı:** İş bitince aracın görevle ilişkisi kesilir; sorumluluk Denetçiye geçer — geliştirici araçlar yeni işe geçebilir, Denetçi kalite ve entegrasyona odaklanır (kullanıcının benzetmesiyle: çalanlar ajanlar, Denetçi şef).

**Mevcut ilkelerle ilişki:** Bu model yeni bir ilke eklemez; ADR-008'in zaten var olan § Lumos AI Kurulu (bağımsız/kör inceleme) ve § Karşılıklı denetim, sıfır kontrol ilkelerinin **commit kapısı olarak somutlaşmış hâlidir**. Kurul ile Denetçi'nin aynı rol mü yoksa ayrı roller mi olduğu netleşmemiştir — ayrı bir tasarım sorusu olarak açık bırakılmıştır. Bu, [[feedback_batch_commit_inventory]] pratiğiyle de örtüşür: bu oturumda zaten "önce envanter tablosu, sonra commit onayı" şeklinde elle uygulanan disiplinin, ilerideki hedefte Board + Denetçi ile yapılandırılmış/otomatikleştirilmiş hâlidir.

**Bu turda kod veya otomasyon kurulmaz** — bu yalnızca akış tasarımı notudur. Denetçi rolünün kim/ne olacağı (insan mı, ayrı bir AI değerlendirici mi, otomatik CI gate mi) ve commit/push/merge/deploy yetkisinin devri ayrı bir karar gerektirir; mevcut "hiçbir kurul üyesi icraya karar veremez, son söz Orkestratör/kullanıcıdadır" ilkesiyle çelişmemelidir.

### Dağıtık Doğrulama (Distributed Validation): doğrulama tek nokta değil, çok katman (aynı vizyon notu kapsamında, 2026-07-17)

**Tetikleyici:** Kullanıcı, AI destekli güvenlik araştırması üzerine bir bülteni ("Harnessing Harnesses — Climbing the LLM Hills") inceledi. Bültendeki yaklaşım tek bir doğrulama aşaması tanımlıyor: `Recon → Hunt → Validate → Trace → Report` zincirinde, bir ajan açık bulduğunda **ikinci bir ajan yalnızca onu çürütmeye çalışıyor** (yanlış pozitifleri azaltmak için tek noktalı bir "validator agent").

Kullanıcının tespiti: Lumos'ta doğrulama tek bir noktada toplanmıyor; **ADR-008'de zaten kayıtlı altı ayrı doğrulama katmanına** dağılmış durumda:

| Katman | Ne sorar | ADR-008'de karşılığı |
|--------|----------|----------------------|
| **Politika doğrulaması** | İstek kurallara ve güvenlik politikasına uyuyor mu? | § Karar ilkeleri madde 3 (Firewall + Trust kontrolü); ADR-006/ADR-007 |
| **Risk doğrulaması** | Risk seviyesi nedir, onay gerekiyor mu? | § Karar ilkeleri madde 4; § Riskler; dispatch onay kuyruğu |
| **Görev doğrulaması** | Üretilen sonuç gerçekten istenen görevi karşılıyor mu? | `agent_runner` verify adımı; `task_engine` doğrulama aşaması |
| **İz/kanıt doğrulaması** | Kararın izi ve gerekçesi tutuluyor mu? | § Karar ilkeleri madde 7 (log ve açıklanabilirlik); § Kayıt yaşam döngüsü (sessiz üzerine yazma yok, her değişiklik gerekçeli) |
| **Çoklu ajan doğrulaması** | Başka bir ajan sonucu sorguluyor mu? | § Lumos AI Kurulu (kör inceleme); § Karşılıklı denetim, sıfır kontrol |
| **İnsan onayı** | Yüksek riskli işlemde son karar kullanıcıda mı? | § Karar ilkeleri madde 4 (`SECURITY_NEVER_AUTO`); § Denetçi (Guardian) modeli RED/GREEN kapısı |

**Kullanıcının çerçevelemesi:** Bu, sektördeki tekil "validator agent" desenine karşı **"dağıtık doğrulama" (distributed validation)** olarak adlandırılabilir. Avantajı: tek bir doğrulayıcının hata yapması bütün sistemi etkilemez. Dezavantajı: katmanlar arasındaki koordinasyonun iyi tasarlanmasını gerektirir — bu ADR'nin zaten § Karşılıklı denetim ve § Denetçi modelinde ele aldığı koordinasyon sorunuyla aynıdır.

**Kullanıcının teşhisi:** Lumos'un eksiği bu doğrulama katmanlarının *var olmaması* değil; mimarinin **dışarıdan bakan birinin de anlayacağı şekilde belgelenmemiş olması**. Yukarıdaki altı katman zaten ADR-008 içinde dağınık halde kayıtlıydı; bu bölüm onları tek bir isim ve tek bir tablo altında toplar — **yeni bir mekanizma eklemez, yeni bir karar değildir.**

---

**Bu bölümün tamamı (Ortak Durum ayrımı + kategori seti + tipli kayıt yapısı + yaşam döngüsü/sahiplik/değiştirilemezlik + erişim modeli + "Board ansiklopedi değildir" ilkesi + Denetçi/Guardian commit-gate modeli + Dağıtık Doğrulama çerçevesi) bir karar değildir, ileri vizyon notudur** — § Lumos Board resmi ad/bileşen kararının aksine, bu bölüm yalnızca ihtiyacı kayıt altına alır. Geçerli olan kısıtlar: (1) ADR-001 öncelik sırası ve genel gating değişmez; (2) dış araçlar arası paylaşılan yazma erişimi ayrı bir güvenlik/izin/veri sızıntısı risk değerlendirmesi gerektirir (bkz. § Riskler madde 5); (3) **bu turda kod, entegrasyon, otomasyon veya dış araç bağlantısı kurulmaz.**

**Durum notu (güncelleme: 2026-07-17):** Bu bölüm kullanıcı tarafından bilinçli olarak **commit edilmeden** tutuluyor. Kullanıcı 2026-07-16'da tanımı olgunlaşmış kabul edip bir süre dokunulmamasını istemişti; 2026-07-17'de Denetçi/Guardian modeliyle kendisi geri döndü — bu, "dışarıdan proaktif dokunma" kısıtını ihlal etmez, çünkü kısıt bana (Claude'a) yönelikti, kullanıcının kendi kararına değil. Olgunlaşma testi geçerliliğini koruyor: birkaç gün dokunulmadan hâlâ doğru duruyorsa commit için doğru zaman kabul edilecek.

### Gözlem: depo durumu, insan karar bekleme durumunu temsil etmiyor (kanıt kaydı, 2026-08-24)

**Bu bölüm karar veya vizyon notu değildir; gözlemlenmiş bir kullanım bulgusudur.** § Lumos Board gating'ini, ADR-001 öncelik sırasını ve bu ADR'nin taslak durumunu değiştirmez. İleride Agent Wall genişletmesi gündeme gelirse kanıt olarak tutulur.

**Gözlem koşulları (2026-08-24, tek geliştirme günü):** Altı eşzamanlı worktree/oturum açıktı; üçü tek satırlık bir insan onayını bekliyordu ve bekleme üç ayrı oturumdaydı. "Hangi iş nerede bekliyor?" sorusunun cevabı hiçbir yerde tutulmuyordu; durum `git worktree list` + `git status` taramalarıyla elle yeniden kuruldu.

**Bulgu — iki ayrı veri kaynağı:**

| Kaynak | Neyi bilir | Neyi bilmez |
|--------|-----------|-------------|
| Git | Dal, taban commit, değişmiş dosya | Bir işin insan kararı beklediğini |
| Agent Status | Ajanın koşup koşmadığını | Kimi, ne için beklediğini |

Panonun ucuz yarısı (hangi worktree, hangi taban, kaç dosya değişik) bugün zaten iki git komutuyla türetilebiliyor; yeni altyapı gerektirmiyor. Pahalı yarısı — "bu iş şu anda senin kararını bekliyor" — depo durumu değil oturum durumudur ve bugün hiçbir kaynakta tutulmuyor.

**Sözleşme ile tasarım niyeti arasındaki fark (doğrulandı):** `src/core/agent_status_contract.py` (KA-001, şema v1) dört durum tanımlıyor — `running`, `completed`, `failed`, `unknown`. `blocked` veya `awaiting_decision` yok. Gözlem günündeki altı oturumun altısı da bu şemaya göre `running` raporlardı; pano "6 iş çalışıyor" derdi, oysa üçü durmuş ve insanı bekliyordu. Yani mevcut haliyle Agent Status sözleşmesi, bu bölümü tetikleyen problemi çözmezdi. Buna karşılık § Kayıt yaşam döngüsü alt bölümü Board *kayıtları* için `BLOCKED` ve `WAITING_APPROVAL` durumlarını zaten tanımlıyor — fark, tasarım niyeti ile hayata geçmiş sözleşme arasındadır. `docs/contracts/task-claim-v1.md` sözleşmesinin kod karşılığı bu tarihte bulunmuyor.

**Bekleme sebebinin ayrıştırılması, olası bir genişletme yönü olarak kaydedilmiştir** (karar değildir): insan onayı, başka bir ajanın sonucu, dış olay, bağımlılık — bunlar tek bir "blocked" durumunda toplandığında hangi beklemenin insan aksiyonu gerektirdiği yine görünmez kalır.

**Kayıt gerekçesi:** ihtiyaç teoriden türetilmedi; sistem paralel çalışma sayısı arttıkça eksikliği kendisi gösterdi. Bu tarihte kod, şema değişikliği veya yeni ADR açılmamıştır.

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-008:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Tek ajan pipeline tasarım notları (demo-safe) | Gerçek agent-to-agent orchestration |
| Task/executor routing referansı (`task_dispatch`, `router` — davranışı değiştirmeden) | Cihaz kontrolü ve üretim terminal erişimi |
| Demo-safe plan yürütme pattern'i (`lumos_gate` `execute_plan` açıklaması) | Dış servis aksiyonları (prod entegrasyon) |
| `agent_runner` sınırlı hedef akışı (dokümantasyon) | Mail prod erişimi (ADR-002; public demo-safe stub only) |
| `task_engine` profil/onay matrisi referansı | Ödeme/domain/satın alma işlemleri |
| Agent/task/executor usage map (salt okuma analizi) | Production secrets ve provider key yönetimi |
| Panel görev/kayıt görünürlük (dürüst demo metinleri) | Operasyonel backend, prod multi-agent ağı |
| Karar ilkeleri ve sınır belgesi (bu ADR) | Quantum/IBM prod entegrasyonu (ADR-001) |

Public repo'da parçalı yürütme hatlarının **"tam Agent Network ürünü"** veya **otonom çok-ajan sistemi** gibi sunulması bilinçli olarak yapılmamalıdır; bu ADR yalnızca hedef, sınır ve mevcut boşluğu kaydeder.

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent, kilit ve kalıcı silme alanları **dokunulmaz**; bu ADR o sınırları gevşetmez veya genişletmez.

---

## Karar ilkeleri (taslak — 9 ilke)

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
| 8 | **Karşılıklı denetim, sıfır kontrol** | AI'lar birbirini denetleyebilir; birbirine komut, yetki, onay veya işlem başlatma hakkı veremez |
| 9 | **Bağımsız düşün, ortak değerlendir** | Lumos AI Kurulu üyeleri aynı girdiyi bağımsız inceler; sentez ve son karar Lumos Orkestratör veya kullanıcıdadır |

---

## Karşılıklı denetim, sıfır kontrol

Agent Network hedefi yatay AI kontrol zinciri değildir. İç AI'lar birbirinin çıktısını denetleyebilir; ancak birbirini yönetemez.

**İzinli:**

- Birbirinin çıktısını okumak ve incelemek.
- Hata, tutarsızlık veya risk bulmak.
- Risk raporu yazmak.
- İtiraz etmek.
- Alternatif çözüm önermek.

**Yasak:**

- Başka bir AI'a doğrudan görev vermek.
- Başka bir AI'ın yetkisini artırmak.
- Başka bir AI'ın ayarını değiştirmek.
- Başka bir AI adına onay vermek.
- Başka bir AI adına işlem başlatmak.

**Yönlendirme kuralı:** Her AI yalnızca kullanıcıdan veya Lumos Orkestratör'den görev alır. Başka bir AI'dan doğrudan görev kabul etmez. Yatay AI → AI komut oku yoktur; ihtiyaç varsa Lumos çekirdeği isteği değerlendirir ve güvenlik, yetki, trust ve onay kontrollerinden sonra yönlendirir.

```
Kullanıcı
    |
    v
Lumos Orkestratör
    |-- Chat AI
    |-- Cyber AI
    |-- Mail AI
    |-- Lab AI
    `-- ...
```

Bu modelde yatay bağlantılar yalnızca denetim, rapor, itiraz ve kanıt referansı üretebilir; kontrol, görev atama veya yetki aktarımı yapamaz.

---

## Lumos AI Kurulu

Lumos AI Kurulu, Agent Network içinde icra makamı değil, **bağımsız denetim ve risk değerlendirme modeli** olarak ele alınır. Kurul üyeleri aynı dosya, karar, risk veya çıktıyı farklı bakış açılarıyla inceler; birbirinin raporunu yazmaz ve birbirine talimat vermez.

Denetim bağımsız olmalıdır. Bir AI, değerlendirmesini başka bir AI'ın sonucuna göre değil, kendi gözlem ve kanıtına göre oluşturur. Başka bir AI'ın "risk var" demesi tek başına kanıt sayılmaz; ancak ortak değerlendirme aşamasında karşılaştırma girdisi olabilir.

Varsayılan kurul akışı **kör inceleme (blind review)** modelidir:

1. Aynı kanıt paketi ilgili AI'lara gönderilir.
2. Her AI diğer AI sonuçlarını görmeden bağımsız rapor üretir.
3. Raporlar kilitlenir; sonradan başka bir AI'ın görüşüne göre sessizce değiştirilmez.
4. Kilitli raporlar ortak değerlendirme aşamasında karşılaştırılır.
5. Lumos Orkestratör veya kullanıcı nihai kararı verir.

Bu akışta kanıt kişiden veya modelden üstündür; güven, tek bir modele değil yönetişim ilkesine dayanır.

Örnek rol dağılımı:

| Üye / perspektif | Rol | Sınır |
|------------------|-----|-------|
| Diamond | İnceler, risk ve açık adaylarını bulur | Uygulama emri vermez |
| ChatGPT | Riski bağımsız değerlendirir, gerekçe ve karşı kanıt arar | Başka AI adına onay vermez |
| Claude | Mantık, mimari tutarlılık ve edge case sorgular | Yetki veya ayar değiştirmez |
| Diğer ajanlar | Tanımlı uzmanlık alanında görüş üretir | Orkestratör dışı görev başlatmaz |

Kurul üyeleri yalnızca şu tip ifadeler üretebilir:

- "Ben burada şu riski görüyorum."
- "Katılmıyorum, gerekçem şu."
- "Bu açık tekrar incelensin."
- "Bu risk yanlış sınıflandırılmış olabilir."
- "Alternatif çözüm şu olabilir."

Kurul üyeleri şu tip ifadelerle birbirini yönetemez:

- "Şunu düzelt."
- "Bunu kabul et."
- "Benim dediğimi uygula."
- "Bu işlemi benim adıma başlat."

Son söz Lumos Orkestratör'de veya nihayetinde kullanıcıdadır. Orkestratör, kurul çıktılarının sentezini yapar; güvenlik, yetki, trust ve onay kontrolleri geçmeden hiçbir kurul görüşü icraya dönüşmez.

Kısa ilke: **Bağımsız düşün, ortak değerlendir.**

---

## Karar (taslak — import/drift incelemesi bekliyor)

0. **Resmi ad (kalıcı karar, 2026-07-16):** Ortak koordinasyon katmanının adı **Lumos Board**'dur; bileşen taksonomisi (Event Bus, Lock Manager, Task Queue, Memory Events, Agent Status, Permission Channel, Notification Stream) § Lumos Board bölümünde kayıtlıdır. Bu, aşağıdaki gating kararlarını **değiştirmez** — inşa sırası madde 3'e tabidir.
1. **Mevcut gerçek:** Birleşik Agent Network yok; yürütme `agent_runner`, `lumos_gate`, `task_dispatch`, `cursor_bridge`/köprü ve `task_engine` üzerinde **parçalı tek-ajan hatları** şeklindedir; birleşik koordinasyon katmanı yoktur.
2. **Hedef:** Yukarıdaki beş rol, dokuz karar ilkesi ve public/private sınır; usage map checkpoint tamamlandı — finalize için dar import/drift incelemesi beklenir.
3. **Öncelik sırası (ADR-001):** Firewall → Trust → Router → Memory → **Agent Network**; alt katmanlar oturmadan Agent Network açılmaz.
4. **Alt katman ilişkisi:** ADR-004 (router sinyalleri), ADR-005 (bağlam/bellek), ADR-006 (firewall/guard), ADR-007 (trust) ile uyumlu ilerlenmeli; Agent Network bu katmanları bypass etmemelidir.
5. **Canonical katmanlar (ADR-003):** Bellek `src/memory`; trust/security `src/security` + `src/policy`; yetki `task_engine/profiles.py`.
6. **Bu turda kod yok** — yalnızca karar kaydı.

Durum: **Usage map checkpoint tamamlandı; karar dar import/drift incelemesi sonrası finalize edilir.**

---

## Mevcut agent/task/executor kullanım haritası

Haziran 2026 repo taraması sonucu — **salt okuma analizi**; kod, import, test, executor davranışı veya orchestration değişikliği **yoktur**.

### Özet bulgular

- **Birleşik Agent Network yok.** `agent_network`, `agent_coordinator` veya merkezi çok-ajan orchestration modülü tespit edilmemiştir.
- **Yürütme parçalıdır:** `agent_runner`, `lumos_gate`, `task_dispatch`, `cursor_bridge`, köprü (`kando_bridge/server.py`), `task_engine` ve panel görev hattı **ayrı tek-ajan / yürütme hatları** olarak çalışır; aralarında rol sözleşmesi veya koordinasyon protokolü yoktur.
- **`bridge_intent`, `task_engine` ve panel görev akışları ayrı boru hatlarıdır** — birbirini otomatik tüketmez; ortak state modeli yoktur.
- **Kritik drift:** Panel görev deposu `.lumos/tasks.json` (`panel_tasks_server.py`); TaskEngine görev deposu `.lumos/tasks/tasks.json` (`TaskStore` base_dir = `.lumos/tasks`). Farklı path, farklı JSON şeması ve farklı yazıcı; tek kaynak yoktur.
- **`POST /task` ≠ `POST /tasks`:** Köprü yürütme girişi `POST /task` (tekil; `kando_bridge/server.py`); panel görev CRUD'u `POST /tasks` (çoğul; `panel_tasks_server.py` → `.lumos/tasks.json`). İsim benzerliği yanlış birleştirme riski taşır.
- **`_resolve_task_routing` ↔ `task_dispatch` sınırı:** `_resolve_task_routing` köprü HTTP gövdesinden `direct_patch` \| `agent` modu ve payload üretir (gate öncesi); `task_dispatch` gate kararı sonrası `task_type` → executor yönlendirmesi, risk ve onay kuyruğu yapar. İkisi farklı katmandır; birleşik agent routing değildir.
- **Kod veya büyük refactor için erken.** Usage map kilitlendikten sonra dar **import/drift karşılaştırması** yapılabilir; Agent Network motoru veya executor birleştirmesi bu aşamada **yapılmaz**.

### Parçalı yürütme modülleri

| Modül | Konum (analiz bulgusu) | Kısa rol | Agent Network ile ilişki |
|-------|------------------------|----------|--------------------------|
| Tek tuş agent | `src/kando/agent_runner.py` | Hedef seçimi → executor → verify → commit/push | Tek ajan; `src/core/` sınırlı hedef |
| LLM plan yürütme | `packages/kando_runtime/.../lumos_gate.py` | `execute_plan`, gate reasoning, `agent` \| `direct_patch` \| `no_op` | Çok adımlı plan; koordinasyon değil |
| Görev türü dispatch | `packages/kando_runtime/.../task_dispatch.py`, `router.py` | `task_type` → executor; risk, onay kuyrukları | Gate sonrası yürütme yönlendirmesi |
| Cursor köprü | `src/kando/cursor_bridge.py` | Patch/onay paketleri; subprocess yürütme | Ayrı onay sözleşmesi |
| Köprü sunucu | `packages/kando_bridge/.../server.py` | `POST /task`, `POST /chat`; `_resolve_task_routing` | Panel/chat giriş orkestrasyonu |
| Köprü niyet | `packages/kando_runtime/.../bridge_intent.py` | `task` \| `chat` sınıflandırması | Gate/dispatch öncesi ayrım (ADR-004 ile örtüşür) |
| Görev motoru | `src/task_engine/engine.py`, `executors/*` | Plan, kuyruk, profil, doğrulama | CLI/main hattı; köprüden bağımsız |
| Runtime executor | `packages/kando_runtime/executors/*` | file, shell, video, image, read vb. | Dispatch üzerinden |
| Panel görev sunucu | `panel/scripts/panel_tasks_server.py` | `GET/POST /tasks` → `.lumos/tasks.json` | UX görev listesi; TaskEngine değil |
| Panel read-only | `panel/js/app.js`, `read_backend_state.py` | Görev/kayıt görünürlük; demo/fixture | Orchestration değil |

### Giriş noktası → zincir haritası

| Giriş noktası | Akış türü | Sonraki adım / tüketici | Not |
|---------------|-----------|-------------------------|-----|
| `kando_bridge/server.py` POST `/task` | Köprü yürütme | `_resolve_task_routing` → `direct_patch` \| `agent` → gate/dispatch veya `agent_runner` | Panel Görevler `source: panel_gorevler` ile buraya gelir |
| `_resolve_task_routing` | HTTP gövde ayrıştırma | `direct_patch`: TARGET talimatı; `agent`: serbest goal metni | Gate **öncesi**; `task_dispatch` **değil** |
| `bridge_intent.classify_bridge_message_intent` | `task` \| `chat` | `task`: gate+dispatch; `chat`: LLM (gate bypass) | `/chat` ve bazı `/task` yollarında |
| `lumos_gate.run_lumos_gate` | Gate kararı | `execute_plan`, pending approval, risk | Ham metin doğrudan executor'a gitmez |
| `task_dispatch.dispatch_*` | `task_type`, risk, onay | `ROUTES` → runtime executor | Gate kararı **sonrası** yürütme |
| `agent_runner` (köprüden) | Agent job | Hedef seç → executor → verify → git | Tek dosya/hedef odaklı |
| `cursor_bridge` (subprocess) | Patch uygulama | `.lumos/cursor_bridge` paketleri | `may_execute_step_at_runtime` |
| `src/main.py` → `TaskEngine` | CLI görev motoru | `planner` → kuyruk → `task_engine/executors/*` | `.lumos/tasks/tasks.json` |
| `panel_tasks_server.py` POST `/tasks` | Panel CRUD | `.lumos/tasks.json` yaz/oku | Köprü `/task` ile **bağlı değil** |
| Panel read-only script | Salt okuma | `read_backend_state.py` → panel adapter | `.lumos/tasks.json` okur; TaskEngine path drift riski |

### POST `/task` vs POST `/tasks` (ayrım)

| Özellik | `POST /task` | `POST /tasks` |
|---------|--------------|---------------|
| Sunucu | `kando_bridge/server.py` | `panel/scripts/panel_tasks_server.py` |
| Amaç | Yürütme / köprü orkestrasyonu | Panel görev listesi CRUD |
| State | `.lumos/outbox`, cursor_bridge, dispatch onay dosyaları | `.lumos/tasks.json` |
| TaskEngine | Doğrudan kullanmaz (ayrı hat) | Kullanmaz |
| Tipik gövde | `goal`, `file+task`, `text`; `source: panel_gorevler` | Görev satırı ekleme/tamamlama/silme |
| Agent Network adayı | Evet (yürütme girişi) | Hayır (UX depo) |

**Analiz bulgusu:** İki endpoint **birleştirilmemelidir**; isim benzerliği migration veya orchestration kararında bilinçli ayrım gerektirir.

### `_resolve_task_routing` vs `task_dispatch` sınırı

| Katman | Fonksiyon / modül | Ne zaman | Çıktı |
|--------|-------------------|----------|-------|
| Köprü routing | `_resolve_task_routing` (`server.py`) | HTTP gövdesi parse edildiğinde | `mode`: `direct_patch` \| `agent`; payload; UI mesajı |
| Gate karar | `lumos_gate` | Agent/direct_patch yolunda | `agent` \| `direct_patch` \| `no_op`; risk; plan |
| Yürütme dispatch | `task_dispatch` | Gate sonrası | `task_type`, `execution_permitted`, executor kuyruğu |

**Analiz bulgusu:** `_resolve_task_routing` panel başlığındaki dosya adını yanlış patch hedefi sanmaması için `source === "panel_gorevler"` istisnası taşır (`docs/ui_panel_gorevler_bridge.md`). Bu, köprü routing ile dispatch arasında **üçüncü özel kural** katmanıdır — birleşik agent sözleşmesi değildir.

### Ayrı boru hatları (pipeline)

| Boru hattı | Giriş | State / çıktı | TaskEngine ile |
|------------|-------|---------------|----------------|
| Köprü yürütme | `POST /task`, `/chat` | outbox, dispatch onay, cursor_bridge | Bağımsız |
| TaskEngine | CLI, `main.py` | `.lumos/tasks/tasks.json` | Canonical motor |
| Panel görev CRUD | `POST /tasks` (panel sunucu) | `.lumos/tasks.json` | **Farklı dosya** |
| Panel read-only | `read_backend_state.py` | UI adapter | TaskEngine path ile drift |
| Tek tuş agent | Köprü agent modu | git commit/push raporu | Bağımsız |

### Drift ve çelişki riskleri (teşhis listesi)

Usage map ve sonraki import karşılaştırmasında **özellikle** kontrol edilmesi gereken noktalar (analiz bulgusu):

| Risk | Açıklama | Etkilenen modüller |
|------|----------|-------------------|
| **Çift görev deposu** | Panel `.lumos/tasks.json` vs TaskEngine `.lumos/tasks/tasks.json` — farklı path, şema, yazıcı | `panel_tasks_server.py`, `task_engine/engine.py`, `read_backend_state.py` |
| **`POST /task` ↔ `POST /tasks` karışıklığı** | İsim benzerliği; farklı sunucu, farklı sözleşme | `kando_bridge/server.py`, `panel_tasks_server.py` |
| **Köprü routing ↔ dispatch örtüşmesi** | `_resolve_task_routing` mod kararı ile `task_dispatch` task_type kararı farklı katman | `server.py`, `task_dispatch.py` |
| **Panel görev → köprü → yerel liste** | Yerel liste önce yazılır; köprü hatası geri alınmaz | Panel UI, `POST /task` |
| **Gate + profil hizasızlığı** | Köprü hattı `profiles.py` ile doğrudan hizalı değil; task engine ayrı yol | ADR-006/007/010 ile ortak risk |
| **`bridge_intent` ↔ task engine** | Köprü niyeti task engine planlayıcısını çağırmaz | `bridge_intent`, `task_engine/planner.py` |
| **`src/` vs `packages/kando_*`** | Runtime köprüde; task engine `src/` altında | ADR-003 ayna drift |
| **`agent_runner` ↔ `cursor_bridge`** | Subprocess ve outbox kopyası; tek agent kimliği yok | `agent_runner`, `cursor_bridge`, köprü |
| **Read-only panel boş görev** | `read_backend_state.py` `.lumos/tasks.json` okur; görevler `.lumos/tasks/` altındaysa panel boş görünür | `PANEL_READONLY_AUDIT`, `WORKSPACE_CONTRACT_STABILITY_AUDIT` |

Bu tablo **teşhis listesidir**; bu ADR drift'i **düzeltmez**, yalnızca haritalar.

### Import map özeti (checkpoint — tam değil)

Dar import karşılaştırması için öncelikli kenarlar (analiz bulgusu):

```
kando_bridge/server → _resolve_task_routing → lumos_gate → task_dispatch → router.ROUTES → executors
kando_bridge/server → bridge_intent; agent_runner; cursor_bridge (subprocess)
agent_runner → executor / git / verify → cursor_bridge outbox
main → TaskEngine → task_engine/executors → profiles.may_execute_step_at_runtime
panel_tasks_server → .lumos/tasks.json (TaskEngine'den bağımsız)
read_backend_state → .lumos/tasks.json (TaskEngine path drift adayı)
```

Tam import diff ve çift kayıt analizi **ayrı dar checkpoint** olarak planlanır; bu bölüm usage map'i **kilitler**, import map'i tamamlamaz.

### İlk güvenli sonraki adım

1. **Usage map kilitle** — bu bölüm checkpoint olarak kabul edilir; Agent Network birleştirme kararı verilmez.
2. **Dar import/drift karşılaştırması** — yukarıdaki drift tablosu maddeleri için salt okuma diff; özellikle görev path (`tasks.json` vs `tasks/tasks.json`) ve köprü routing sınırı.
3. **Kod, migration veya executor birleştirmesi yapılmaz** — ADR-004/005 disiplini ile hizalı.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, usage map, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Agent Network kurma / birleştirme** | ADR-001 taslak; Firewall → Trust → Router → Memory öncesi değil; birleşik katman yok |
| **Executor davranışı değiştirme** | Usage map kilitlendi; dar drift incelemesi önce; regresyon riski |
| **Görev path/model migration** | `.lumos/tasks.json` ↔ `.lumos/tasks/tasks.json` drift bilinçli ayrım; otomatik birleştirme yok |
| **Panel görev deposunu runtime TaskEngine ile hemen birleştirme** | Farklı boru hatları; migration ayrı onay ve ADR gerektirir |
| **Kod yazma** (orchestration, yeni agent modülü) | Karar finalize edilmedi; kapsam şişmesi |
| **Büyük agent framework / refactor** | Regresyon riski; parçalı hatlar önce haritalandı — import diff sonrası dar adım |
| **Cihaz / terminal kontrolü ekleme** | Public sınır; private/professional katman |
| **Mail prod entegrasyonu** | ADR-002 — demo-safe stub public; prod connector private |
| **Ödeme / domain işlem entegrasyonu** | Public sınır; prod katmanı |
| **Production secrets / provider key kullanımı** | Gizli anahtar public repo'da olmamalı |
| **Quantum / IBM tarafına geçme** | ADR-001 — erken hedef değil |
| **Public repo'da otonom dış aksiyon** | Onaysız dış etki yasağı; demo-safe sınır ihlali |

Ek olarak: abartılı "otonom ajan ordusu" vaadi, production orchestration'un public'e taşınması, `POST /task` ile `POST /tasks` endpoint birleştirmesi ve alt katmanları bypass eden koordinasyon **yapılmaz**.

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

Haziran 2026 repo analizine dayanarak Lumos'ta **birleşik Agent Network bulunmamaktadır**. Yürütme `agent_runner`, `lumos_gate`, `task_dispatch`, `cursor_bridge`/köprü, `task_engine` ve panel görev hattı üzerinde **parçalı tek-ajan hatları** şeklindedir; birleşik koordinasyon/orchestration katmanı yoktur. **Usage map checkpoint tamamlandı** — kritik drift: panel `.lumos/tasks.json` ile TaskEngine `.lumos/tasks/tasks.json` ayrımı; `POST /task` (köprü yürütme) ile `POST /tasks` (panel CRUD) ayrımı kayıt altındadır.

ADR-001 sırasına göre Agent Network, Firewall → Trust → Router → Memory omurgası netleşmeden açılmamalıdır. ADR-004, ADR-005, ADR-006, ADR-007 ve ADR-010 ile uyumlu ilerlenmelidir.

**Sonraki güvenli adım:** Dar import/drift karşılaştırması (görev path, köprü routing sınırı). **Bu turda kod yazılmaz; Agent Network kurulmaz; görev path migration yapılmaz.**

## Sonraki gözden geçirme

- Dar import/drift checkpoint sonuçları ile ADR revizyonu ve karar finalize
- Rol sözleşmesi taslağı (kod, belge, görev, kontrol, doğrulama, raporlama) — drift incelemesi sonrası
- ADR-001 (ileri modüller), ADR-003 (canonical katmanlar), ADR-004 (router), ADR-005 (memory graph), ADR-006 (firewall), ADR-007 (trust), ADR-010 (terminoloji), ADR-011 (lock semantiği) ile çakışma kontrolü
- Panel `.lumos/tasks.json` ↔ TaskEngine `.lumos/tasks/tasks.json` drift — salt okuma audit; migration kararı ayrı onay (Lumos Board Task Queue bileşeni bu birleşmeyi bekler)
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot tek-rol delegasyon seçimi — karar finalize sonrası, ayrı onay
- Lumos Board bileşen teknik tasarımı (Event Bus, Lock Manager, Task Queue, Memory Events, Agent Status, Permission Channel, Notification Stream) — import/drift checkpoint ve alt katman (ADR-005/006/007) unifikasyonu sonrası ayrı ADR/tasarım turu
- Lumos Board = Ortak Durum vizyon notu — henüz commit edilmedi; tanım netleşince tek commit, ardından karara dönüştürülmeden önce ayrı güvenlik/izin/veri sızıntısı risk değerlendirmesi ve dış araç entegrasyon onayı gerekir
