# ADR-006: AI Firewall / Guard Katmanı (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — guard/policy usage map tamamlanmadan finalize edilmez |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004 |

## Amaç

Lumos kod tabanında **birleşik AI Firewall** olup olmadığını repo analizine dayalı olarak netleştirmek; hedef firewall rolünü, ilk risk kategorilerini, firewall karar tiplerini ve public/private sınırını **kodsuz karar kaydı** olarak belgelemek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, guard davranışı değişikliği veya yeni güvenlik motoru **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). ADR-001 AI Firewall'ı **hipotez** düzeyinde listeler ve öncelik sırasında **Router'dan önce** konumlandırır. ADR-003 canonical trust/security katmanlarını (`src/security`, `src/policy`) kaydeder. ADR-004 birleşik AI Router'ın olmadığını ve router'ın firewall sinyallerini kullanması gerektiğini kaydeder — firewall router'ın yerine geçmez. Bu ADR, guard/firewall hedefini aynı disiplinle — önce analiz ve haritalama, sonra dar karar — kayıt altına alır.

---

## Mevcut durum (repo analiz bulguları, Haziran 2026)

### Birleşik AI Firewall yok

Repo taramasında **tek, merkezi "AI Firewall" modülü tespit edilmemiştir**. Güvenlik ve guard davranışı farklı giriş noktalarında, farklı kurallarla uygulanmaktadır.

### Parçalı guard / politika katmanları

| Katman | Konum (analiz bulgusu) | Kısa rol |
|--------|------------------------|----------|
| LLM reasoning öncesi gate | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | `agent` \| `direct_patch` \| `no_op`; `classify_risk`; risk ipuçları |
| Yetki / onay matrisi | `src/task_engine/profiles.py` | Profil × adım türü; `SECURITY_NEVER_AUTO`; `may_execute_step_at_runtime` |
| Minimal aksiyon politikası | `src/policy/action_policy.py` | Offline mutasyon red; koruma aktifken delete red; identity/keystore consent |
| Offline engine | `src/policy/offline_engine.py` | Network gerektiren intent red; SMS kapalı; taslak-only |
| Path hassasiyeti | `src/core/change_sensitivity.py` | CRITICAL / HIGH / NORMAL / LOW; `write_interceptor` kullanır |
| Güvenlik çekirdeği | `src/security/*` | identity, keystore, lock, crypto, presence (demo) |
| Kontrollü köprü | `packages/kando_runtime/src/kando_runtime/controlled_bridge.py` | workspace sandbox; silme/mail/shell blok |
| Görev dispatch | `packages/kando_runtime/src/kando_runtime/task_dispatch.py` | task_type → executor; risk → onay kuyruğu |

**Analiz bulgusu:** Bu katmanlar **kısmen örtüşür** — örneğin dosya düzenleme hem `lumos_gate` (`classify_risk`, `direct_patch`) hem `change_sensitivity` hem `write_interceptor` hem `profiles` üzerinden değerlendirilir; ancak aralarında tutarlı bir risk skoru veya tek karar sözleşmesi yoktur. `lumos_gate` ile `change_sensitivity` **doğrudan bağlı değildir** (analiz bulgusu).

### İlgili ADR durumu

- **ADR-001:** AI Firewall **hipotez**; öncelik sırasında güvenli yönlendirme (routing) ve politika sınırlarından **önce** temel güvenlik katmanı olarak konumlanmalıdır. Quantum erken hedef değil.
- **ADR-003:** Canonical trust/security kaynakları **`src/security`** ve **`src/policy`**; yetki profilleri `task_engine/profiles.py` ile hizalı. Firewall tasarımı bu katmanları bypass etmemelidir.
- **ADR-004:** Birleşik AI Router **yok**; router firewall sinyallerini **kullanmalı**; firewall router'ın yerine **geçmemelidir**. Firewall ve trust tam oturmadan router'ın tek başına üretim vaadi taşımaması gerekir.

### Henüz olmayan alanlar

| Alan | Durum (analiz bulgusu) |
|------|------------------------|
| Birleşik risk sınıflandırma (11 kategori) | Yok — dağınık keyword/heuristic |
| Birleşik firewall karar sözlüğü (7 tip) | Yok — `lumos_gate` alt kümesi |
| Trust Engine / birleşik güven skoru | Yok — ADR-001 hipotez |
| Tüm entrypoint'lerde aynı guard zinciri | Yok — CLI, köprü, task engine, demo hattı ayrı |
| PII tespiti / filtreleme | Yok |
| Production auth / ödeme / mail aksiyonu | Public sınır dışı |

---

## AI Firewall hedef rolü

AI Firewall, Lumos'ta model ve araç çağrıları için **politika, filtre ve sınır katmanı** olarak hedeflenir (ADR-001 hipotezi). Kesin API veya modül adı henüz kararlaştırılmamıştır (*taslak*).

Hedeflenen işlevler:

1. **Kullanıcı isteğini risk açısından kontrol etmek** — niyet, metin, hedef path ve adım türü sinyallerini birleştirmek.
2. **Hassas veri, dış servis, dosya sistemi, cihaz işlemleri ve geri dönüşsüz aksiyonları sınıflandırmak** — 11 risk kategorisine (aşağıda) map etmek.
3. **Gerektiğinde kullanıcı onayı istemek** — `lumos-karar-sozlesmesi` ile uyumlu; genel onay, açık komut veya yüksek risk kartı.
4. **Güvenli olmayan veya kapsam dışı işlemleri durdurmak** — `no_op`, `deny`, `SECURITY_NEVER_AUTO`, köprü yüzey blokları.
5. **AI Router ve Trust Layer ile birlikte çalışmak** — firewall karar verir; router yönlendirir; trust skoru/kaynak güveni besler (*Trust Engine henüz birleşik değil — ADR-001 hipotez*).

Bu rol ADR-001'deki "AI Firewall → Trust → Router → Memory → Agent Network" öncelik sırasında **firewall katmanını** somutlaştırmayı hedefler; router oturmadan firewall'ın tek başına üretim vaadi taşımaması gerekir (*ADR-004 ile hizalı: firewall router'ın yerine geçmez*).

---

## İlk risk kategorileri (taslak — 11 kategori)

Aşağıdaki kategoriler **ürün/guard hedef sözleşmesidir**; repo'da birleşik karşılıkları henüz tanımlı değildir. Mevcut parçalı eşleşmeler analiz bulgusudur, finalize edilmiş mapping değildir.

| # | Kategori | Hedef firewall davranışı | Mevcut repo karşılığı (analiz bulgusu) | Boşluk |
|---|----------|--------------------------|----------------------------------------|--------|
| 1 | **Düşük riskli bilgi/sohbet** | `allow` / `log_only` | `bridge_intent` → chat; `OfflineEngineV1` keyword cevapları; CLI `unknown` + online → live brain | Birleşik kategori yok; maliyet/risk skoru yok |
| 2 | **Proje içi okuma/özetleme** | `allow` (read profili) | `profiles.py` `STEP_TYPE_READ/ANALYZE`; `lumos_gate` özet modu; `controlled_bridge` read | Okuma ile özetleme firewall sözleşmesi ayrılmamış |
| 3 | **Dosya düzenleme** | `allow` / `ask_confirmation` / `sandbox_only` | `lumos_gate` `direct_patch`; `classify_risk` keyword; `task_dispatch` risk→onay; `write_interceptor` + `change_sensitivity` | Gate ile `change_sensitivity` **bağlı değil** |
| 4 | **Dış servis yazma** | `deny` / `defer_to_private_layer` | `profiles.py` `STEP_TYPE_EXTERNAL` → hiçbir profilde izinli değil | Merkezi "external write" sınıflandırıcı yok |
| 5 | **Mail gönderme/silme/arşivleme** | `deny` / `defer_to_private_layer` | `controlled_bridge` mail/takvim regex blok; `offline_engine` SMS kapalı | ADR-002 taslak; demo-safe stub; prod aksiyon yok |
| 6 | **Ödeme/domain/satın alma** | `deny` / `defer_to_private_layer` | `kando_core._infer_risk` "payment" keyword → high (demo hattı) | Üretim entegrasyonu yok; public sınır dışı |
| 7 | **Cihaz/yerel işlem** | `sandbox_only` / `ask_confirmation` | `OfflineEngineV1` + `PermissionManager` lease stub; `controlled_bridge` workspace sandbox | Gerçek cihaz kontrolü yok (public sınır) |
| 8 | **Kalıcı silme** | `deny` (otomatik) / `ask_confirmation` (açık komut) | `SECURITY_NEVER_AUTO` `permanent_delete`; `may_perform_permanent_delete`; gate `HIGH_RISK_KEYWORDS`; bridge silme blok | `SECURITY_NEVER_AUTO` engine'de ayrı red branch eksik (guard zincir dokümanı) |
| 9 | **Güvenlik/kimlik/anahtar işlemi** | `require_stronger_auth` / `deny` | `action_policy` `ACCESS_IDENTITY/KEYSTORE` → consent; `DeviceIdentity`, `FileKeyStore`, `LockState` | Firewall→identity/lock tek kapı değil |
| 10 | **Üretim config değişikliği** | `deny` / `ask_confirmation` | `SECURITY_NEVER_AUTO` `critical_system_config`; `change_sensitivity` CRITICAL → `src/core`, `src/policy`, `src/security` | Config değişikliği intent sınıflandırması yok |
| 11 | **Kullanıcı özel verisi (PII)** | `log_only` / `defer_to_private_layer` | Public boundary kuralı; bridge PII routing yok | PII tespiti/filtreleme katmanı yok |

Kategori ataması **öneri** niteliğindedir; kullanıcı override, profil sınırları ve onay kuralları her zaman üstünde kalır (`lumos-karar-sozlesmesi`).

---

## Firewall karar tipleri (taslak — 7 tip)

Aşağıdaki karar tipleri **hedef sözleşmedir**; repo'da birleşik enum veya modül olarak tanımlı değildir.

| Karar | Anlam | Mevcut repo karşılığı (analiz bulgusu) | Tam karşılık var mı? |
|-------|-------|----------------------------------------|----------------------|
| **allow** | Güvenli; yürüt | `final_decision: "allow"` (`lumos_gate`); `may_execute_step_at_runtime` True; `execution_mode: direct_patch` (low risk) | Kısmen — profil/onay matrisine bağlı |
| **ask_confirmation** | Kullanıcı onayı bekle | `pending_approval`, `requires_approval`, `await_user_approval`; `task_dispatch` medium/high risk kuyrukları | Evet (köprü/görev hattında); CLI hattında formel değil |
| **require_stronger_auth** | Kilit, passphrase, consent | `action_policy` koruma+consent; karar sözleşmesi "kilidi aç"; online'da kimlik/kilit şartı | Kısmen — birleşik firewall kararı değil |
| **sandbox_only** | Yalnız tanımlı sandbox | `controlled_bridge` → `workspace/`; `write_interceptor` sandbox_mode + core path yasağı | Kısmen — tüm yazma yolları sandbox'a alınmamış |
| **deny** | Durdur | `mode: no_op`; `decision_kind: blocked`; `is_allowed_for_profile` False; `surface_blocked` | Dağınık; tek `deny` enum yok |
| **log_only** | Yürütme yok, kayıt | `log_policy_blocked`; `record_guard_event` (`write_interceptor`); Lumos audit collector | Audit var; firewall-wide `log_only` sözleşmesi yok |
| **defer_to_private_layer** | Public'te açma | `STEP_TYPE_EXTERNAL` asla; mail/ödeme/cihaz public boundary'de yasak | Politika düzeyinde; kodda explicit karar tipi yok |

**Not:** `lumos_gate` kendi içinde `agent | direct_patch | no_op` + `risk_level: low|medium|high|unknown` + `execution_mode: direct_patch|restricted|pending_approval` kullanır; bu, 7'li firewall sözlüğünün **alt kümesi**dir, birebir eşdeğer değildir.

---

## Mevcut repo karşılığı vs gap (özet)

### Var olan parçalar (canonical — ADR-003)

| Bileşen | Konum | Firewall'a katkı |
|---------|-------|------------------|
| Gate (reasoning öncesi) | `lumos_gate.py` | LLM plan; ham metin executor'a gitmez; `classify_risk`, high→onay, `no_op` |
| Yetki matrisi | `src/task_engine/profiles.py` | `is_allowed_for_profile`, `may_execute_step_at_runtime`, `SECURITY_NEVER_AUTO` |
| Minimal politika | `src/policy/action_policy.py` | Offline görev mutasyonu red; koruma aktifken delete red; identity/keystore consent |
| Offline engine | `src/policy/offline_engine.py` | Network gerektiren intent'ler red |
| Path hassasiyeti | `src/core/change_sensitivity.py` | CRITICAL/HIGH/NORMAL/LOW; `write_interceptor` kullanır |
| Güvenlik çekirdeği | `src/security/*` | identity, keystore, lock, crypto |
| Kontrollü köprü | `controlled_bridge.py` | workspace sandbox; silme/mail/shell blok |
| Görev dispatch | `task_dispatch.py` | task_type→executor; risk→onay kuyruğu |

### Kritik gap'ler (analiz bulgusu)

1. **Birleşik AI Firewall modülü yok** — ADR-001 hipotez; dağınık guard'lar çelişebilir (ADR-004 risk tablosu).
2. **`lumos_gate` ↔ `change_sensitivity` bağlantısı yok** — aynı dosya patch'i için farklı risk sinyalleri.
3. **`classify_risk` sezgisel ve dar** — keyword tabanlı; `unknown` çoğu durumda `restricted`.
4. **`SECURITY_NEVER_AUTO` runtime'da tam enforce değil** — `critical`/`external` step türü red var; `permanent_delete` vb. için ayrı engine branch eksik.
5. **Trust Layer birleşik değil** — skor modeli, kaynak güveni, tutarlı risk birleştirmesi yok.
6. **Tüm entrypoint'ler aynı guard'ı kullanmıyor** — `TaskEngine.run_task` vs köprü vs `kando_core` demo hattı vs CLI.
7. **`packages/kando_policy` ayna drift** — ADR-003; canonical kaynak `src/security` + `src/policy`.

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-006:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Risk sınıflandırma **taslağı** ve onay kuralı dokümantasyonu | Gerçek production auth, SSO, prod key yönetimi |
| `profiles.py` davranış referansı (değiştirmeden) | Ücretli model tier, maliyet routing |
| Gate pattern açıklaması (`lumos_gate` — kontrollü reasoning) | PII işleyen routing kuralları |
| Basit keyword/heuristic risk (`classify_risk` seviyesinde) | Mail prod aksiyonları (ADR-002; public stub sadece grant/sözleşme) |
| Offline stub, controlled bridge sandbox tanımı | Ödeme, domain satın alma, cihaz orkestrasyonu |
| Guard/policy usage map (salt okuma analizi) | Operasyonel backend, prod orchestration |
| ADR karar kayıtları (hipotez/taslak) | Quantum/IBM prod entegrasyonu (ADR-001) |

Public repo'da parçalı guard'ların **"tam AI Firewall ürünü"** gibi sunulması bilinçli olarak yapılmamalıdır (ADR-004 ile aynı ilke).

---

## Karar (taslak — usage map bekliyor)

1. **Mevcut gerçek:** Birleşik AI Firewall yok; guard davranışı `lumos_gate`, `profiles`, `action_policy`, `change_sensitivity`, `src/security` ve ilgili köprü/dispatch katmanlarında **parçalıdır**; katmanlar **kısmen örtüşür**.
2. **Hedef:** Yukarıdaki beş rol, 11 risk kategorisi ve 7 karar tipi taslağı; finalize için guard/policy usage map zorunlu.
3. **Öncelik sırası (ADR-001):** Firewall, Router'dan **önce** temel güvenlik katmanı olarak ele alınmalıdır.
4. **Canonical katmanlar (ADR-003):** Trust/security kaynakları `src/security` ve `src/policy`; firewall tasarımı bu katmanları bypass etmemelidir.
5. **Router ilişkisi (ADR-004):** Router firewall sinyallerini **kullanmalı**; firewall router'ın yerine **geçmemelidir**.
6. **Bu turda kod yok** — yalnızca karar kaydı.

Durum: **Karar guard/policy usage map tamamlanana kadar bekletilir.**

---

## İlk güvenli adım: guard/policy usage map

Büyük refactor veya yeni güvenlik motoru **yapılmadan** önce mevcut guard dokunuş noktalarının haritalanması önerilir.

**Hedef çıktı (ayrı checkpoint veya bu ADR eki — henüz yazılmadı):**

| Giriş noktası | Karar / guard türü | Tükettiği / ürettiği | Not |
|---------------|-------------------|----------------------|-----|
| `src/cli/cli_router.py` | Komut / live brain kapısı | CLI handlers, online/offline | ADR-004 ile ortak |
| `bridge_intent` | chat \| task | Köprü POST | Görev motoruna gitmeden önce |
| `lumos_gate` | agent \| direct_patch \| no_op | LLM reasoning, risk reason | Ham metin executor'a gitmez |
| `task_dispatch` | task_type, risk, onay | Executor kuyrukları | `pending_approval` |
| `profiles.py` | profil × adım izni | `task_engine/engine.py` | `SECURITY_NEVER_AUTO` |
| `action_policy.py` | offline mutasyon, consent | identity/keystore erişimi | Minimal politika |
| `change_sensitivity.py` | path hassasiyeti | `write_interceptor` | Gate ile bağlı değil |
| `controlled_bridge.py` | yüzey blok, sandbox | workspace/ | Mail/shell/silme blok |
| `src/security/*` | kilit, kimlik, keystore | consent, online şartı | Canonical (ADR-003) |

**Import map kapsamı (analiz görevi):** `cli_router` → `bridge_intent` → `lumos_gate` → `task_dispatch` → `profiles` / `may_execute_step_at_runtime` → `action_policy` → `controlled_bridge` → `write_interceptor` / `change_sensitivity` → `src/security` (consent/lock) — kim kimi import ediyor, hangi giriş noktası hangi zinciri tetikliyor.

Usage map tamamlanmadan firewall birleştirme, yeni modül veya davranış değişikliği kararı **verilmez**.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, usage map, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Kod yazma** (firewall birleştirme, yeni modül) | Usage map ve karar finalize edilmedi; kapsam şişmesi |
| **Yeni güvenlik motoru** | Parçalı guard'lar önce haritalanmalı; erken motor regresyon riski |
| **Production auth** | Public sınır; private/professional katman |
| **Mail demo-safe stub (ADR-002)** | ADR-002 — public stub; prod izin akışı ve connector private |
| **Ödeme/domain işlem entegrasyonu** | Public sınır; prod katmanı |
| **Cihaz kontrolü** | Public sınır; demo/sandbox dışında yok |
| **Agent Network kurma** | ADR-001 taslak; firewall öncesi değil |
| **Quantum/IBM tarafına geçme** | ADR-001 — erken hedef değil |

---

## Riskler (analiz bulgusu)

| Risk | Not |
|------|-----|
| Parçalı guard çelişkisi | Gate "allow" + profil "deny" veya tersi mümkün |
| Erken birleştirme / yeni motor | CI/regresyon; onay modeli karmaşıklaşması |
| `classify_risk` yanlış pozitif/negatif | Keyword tabanlı; `unknown`→restricted tutarsızlığı |
| Gate–sensitivity kopukluğu | CRITICAL path'e düşük gate riski |
| `SECURITY_NEVER_AUTO` tam enforce eksik | Sözleşme vs engine gap |
| Public sınır sızıntısı | Prod auth/PII/mail public'e taşınması |
| `src/` vs `packages/kando_*` drift | ADR-003 ayna paketleri |
| Router firewall'sız ilerleme | ADR-001 sırasına aykırı; maliyet/risk kontrolsüzlük |

---

## Sonuç (geçici)

Haziran 2026 repo analizine dayanarak Lumos'ta **birleşik AI Firewall bulunmamaktadır**. Guard davranışı `lumos_gate`, `profiles`, `action_policy`, `change_sensitivity`, `src/security` ve ilgili köprü/dispatch katmanlarında **parçalıdır**; katmanlar kısmen örtüşür. ADR-001 sırasına göre firewall Router'dan **önce** temel güvenlik katmanı olarak ele alınmalıdır. ADR-003'e göre canonical trust/security kaynakları **`src/security`** ve **`src/policy`**'dir. ADR-004'e göre router firewall sinyallerini kullanmalı; firewall router'ın yerine geçmemelidir.

**İlk güvenli adım:** Mevcut guard/policy dokunuş noktalarının usage map / import map olarak çıkarılması. **Bu turda kod yazılmaz; yeni güvenlik motoru kurulmaz.**

## Sonraki gözden geçirme

- Guard/policy usage map checkpoint sonuçları ile ADR revizyonu ve karar finalize
- 11 kategori × 7 karar tipi için resmi firewall sözleşmesi taslağı (ayrı belge veya ADR eki)
- ADR-001 (ileri modüller), ADR-003 (canonical katmanlar), ADR-004 (router usage map) ile çakışma kontrolü
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot kategori seçimi (ör. dosya düzenleme vs düşük riskli sohbet) — usage map sonrası, ayrı onay
