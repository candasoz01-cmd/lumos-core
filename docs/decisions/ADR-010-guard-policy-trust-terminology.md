# ADR-010: Guard, Policy, Trust Terminoloji Sözlüğü (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — guard/policy/trust usage map tamamlanmadan finalize edilmez |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-003, ADR-004, ADR-006, ADR-007, ADR-008 |

## Amaç

ADR-003 (canonical memory/security katmanları), ADR-006 (AI Firewall / guard katmanı), ADR-007 (Trust Engine) ve guard/policy usage map analizi sonrasında **guard, policy, trust, lock, permission** ve ilişkili kavramları **tek terminoloji sözlüğünde** netleştirmek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, guard/trust davranışı değişikliği, panel UI, yeni trust engine veya lock semantiği değişikliği **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). Repo analizinde guard, policy, trust, lock, consent ve onay kavramları **farklı giriş noktalarında** farklı isimlerle geçmektedir; bazıları birbirine karıştırılmaktadır (ör. `startup_health._lock_ok` ile runtime `LockState`, panel mock ile CLI `LOCKED`).

ADR-006 guard/firewall hedef rolünü, ADR-007 trust hedef rolünü kaydeder — ancak **ortak terim sözlüğü** henüz yoktu. Bu ADR, usage map ve sonraki ADR revizyonları için **kodsuz referans sözlüğü** sağlar.

**Öncelik sırası (ADR-001, ADR-004, ADR-006, ADR-007 ile hizalı):** AI Firewall (guard) → Trust → Router → Memory → Agent Network.

**İlgili ADR'ler:**

| ADR | Konu | Bu ADR ile ilişki |
|-----|------|-------------------|
| [ADR-003](ADR-003-canonical-memory-security-layers.md) | Canonical memory/security katmanları | Canonical kaynak: `src/security`, `src/policy` |
| [ADR-004](ADR-004-ai-router-routing-layer.md) | AI Router | Router, guard/trust kararlarından **sonra** yönlendirir |
| [ADR-006](ADR-006-ai-firewall-guard-layer.md) | AI Firewall / guard | Guard hedef rolü ve 7 karar tipi |
| [ADR-007](ADR-007-trust-engine-layer.md) | Trust Engine | Trust hedef rolü ve 8 durum |
| [ADR-008](ADR-008-agent-network-boundary.md) | Agent Network sınırı | Dış ajan/ ağ etkisi; guard/trust sinyali besler |

---

## Terminoloji sözlüğü (taslak)

Aşağıdaki tanımlar **hedef terminoloji sözleşmesidir**; repo'da her terim için birleşik enum veya modül **henüz yoktur**. Parantez içindeki konumlar **analiz bulgusudur**, finalize edilmiş mapping değildir.

### guard

**Anlam:** Bir istek, adım veya araç çağrısının **yürütülmeden önce** risk, kapsam, profil ve politika sinyallerine göre **geçip geçemeyeceğine** karar veren veya karar öneren **koruyucu katman**.

**Hedef rol:** Durdur, izin ver, onay iste, sandbox'a yönlendir, private katmana ertele (ADR-006 karar tipleri).

**Repo karşılığı (analiz bulgusu, parçalı):** `lumos_gate`, `profiles.py`, `action_policy.py`, `change_sensitivity.py`, `write_interceptor`, `controlled_bridge`, `task_dispatch`.

**Not:** Guard **tek modül değildir**; birleşik AI Firewall henüz yok (ADR-006).

---

### policy

**Anlam:** Sistem veya workspace için tanımlı **kurallar kümesi** — hangi eylem türlerinin hangi koşullarda izinli, yasak veya onay gerektirdiğini **deklaratif** olarak ifade eder.

**Hedef rol:** Offline/online sınırları, koruma aktifken delete red, identity/keystore erişim kuralları, `SECURITY_NEVER_AUTO` sözleşmesi.

**Repo karşılığı (analiz bulgusu):** `src/policy/action_policy.py`, `src/policy/offline_engine.py`, `src/policy/rules.py`; yetki matrisi `task_engine/profiles.py` ile hizalı.

**Not:** Policy **karar üretir**; kullanıcı arayüzü veya runtime enforcement ayrı katmandır.

---

### trust

**Anlam:** Kimlik, oturum, kilit, consent, presence ve hassas işlem bağlamında **güven durumunun** (trust state) ve **güven sinyallerinin** hedeflenen birleşik temsili.

**Hedef rol:** Firewall'a sinyal beslemek; router'a public/yerel/private katman bilgisi vermek; hassas işlem öncesi durum kontrolü (ADR-007).

**Repo karşılığı (analiz bulgusu, parçalı):** `src/security/*`, `action_policy`, `CoreState` / `get_durum_parts`, `presence_lock`, panel görünürlük.

**Not:** Birleşik Trust Engine **henüz yok** (ADR-007 hipotez).

---

### lock

**Anlam:** Koruma kilidi — hassas işlem veya kök anahtar erişimi için **runtime'da kilitli veya açık** durum. Passphrase ile açılması gereken koruma katmanı (`lumos-karar-sozlesmesi`: kilidi aç = açık komut).

**Hedef semantik:** `locked` = kök anahtar yüklü değil veya koruma aktif; `unlocked` = passphrase ile kök anahtar yüklü.

**Repo karşılığı (analiz bulgusu):** `src/security/lock.py` (`LockState`), `CoreState.lock_status()`, panel `keystoreState`.

**Drift riski:** `startup_health._lock_ok` keystore **init** durumunu yansıtır; runtime `LockState.unlocked` ile **aynı anlama gelmeyebilir** (aşağıda).

---

### presence

**Anlam:** Kullanıcı **varlık / oturum yakınlığı** sinyali — örn. kamera veya cihaz FSM ile "kullanıcı burada mı" coarse göstergesi.

**Hedef rol:** Trust sinyali; demo düzeyinde guard/trust kararına girdi olabilir.

**Repo karşılığı (analiz bulgusu):** `src/security/presence_lock.py`, `presence_fsm.py`, `get_durum_parts` presence alanı.

**Not:** Public repo'da **demo** düzeyi; üretim cihaz presence kontrolü private katmandadır (ADR-007).

---

### permission

**Anlam:** Belirli bir **eylem türü veya kaynak** için verilmiş izin — profil, lease veya açık kullanıcı onayı ile sınırlı **yetki grant'ı**.

**Hedef rol:** "Bu adım bu profilde çalıştırılabilir mi?" sorusuna yanıt (`may_execute_step_at_runtime`).

**Repo karşılığı (analiz bulgusu):** `task_engine/profiles.py` (rapor / guvenli_yurut / kisitli_otonom); `src/security/permissions.py` (**stub**, lease modeli uygulanmamış).

**Not:** Permission **policy'nin uygulanmış grant yüzeyidir**; policy kuralların kendisidir.

---

### consent

**Anlam:** Kullanıcının **kalıcı veya oturum bazlı** olarak verdiği **rıza / izin kaydı** — özellikle identity, keystore veya koruma alanı erişimi için (`effective_consent`, consent dosyası).

**Hedef rol:** Trust sinyali; `consent_required` durumuna yol açar; onaysız hassas erişim yok.

**Repo karşılığı (analiz bulgusu):** `action_policy` → `consent_required`; `CoreState` / `get_durum_parts` consent önceliği; panel `read_backend_state.py` salt okuma.

**Not:** Consent **tek seferlik onay değildir**; confirmation'dan ayrıdır (aşağıda).

---

### confirmation

**Anlam:** Belirli bir **işlem veya adım** için kullanıcıdan alınan **anlık, bağlama özel onay** — "şu dosyayı şimdi sil", "şu görevi şimdi çalıştır" gibi.

**Hedef rol:** Guard kararı `ask_confirmation`; task kuyruğu `pending_approval`; yüksek risk adımları.

**Repo karşılığı (analiz bulgusu):** `task_dispatch` risk→onay; `lumos_gate` `pending_approval`; köprü `await_user_approval`.

---

### elevated confirmation

**Anlam:** Normal confirmation'dan **daha güçlü** onay katmanı — genel onay (`kisitli_otonom` + `general_approval`), passphrase / kilidi aç, veya yüksek risk kartı.

**Hedef rol:** Trust durumu `elevated_confirmation_required` (ADR-007); `require_stronger_auth` (ADR-006).

**Repo karşılığı (analiz bulgusu):** `lumos-karar-sozlesmesi` açık komut kuralları; `unlock_with_passphrase`; `SECURITY_NEVER_AUTO` ile örtüşen hassas işlemler.

---

### sandbox

**Anlam:** Tanımlı **kopya / deneme yazma alanı** — canlı çekirdek state path'lerine doğrudan overwrite yapmaz; workspace sözleşmesiyle sınırlı alan (`controlled_bridge` → `workspace/`).

**Hedef rol:** Guard kararı `sandbox_only`; güvenli dosya denemesi.

**Repo karşılığı (analiz bulgusu):** `controlled_bridge`, `write_interceptor` sandbox_mode, `docs/lumos-guard-sandbox-kopya-siniri.md`.

**Not:** Sandbox **private katman değildir**; public repo'da demo-safe sınır alanıdır.

---

### local demo

**Anlam:** Yerel ortamda çalışan, **üretim güven iddiası taşımayan** önizleme / mock / stub davranış — gerçek motor veya prod entegrasyonu bağlı değilken dürüst etiketlenmiş durum.

**Hedef rol:** Trust durumu `local_demo` (ADR-007); panel "Demo önizleme — gerçek … motoru bağlı değil" metinleri.

**Repo karşılığı (analiz bulgusu):** Panel `mockState`, `policy-engine.js` mirror; köprü yokken salt okuma adapter.

---

### private layer

**Anlam:** Public açık kaynak repo **kapsamı dışında** kalan professional / operasyonel katman — prod auth, mail/OAuth, ödeme, cihaz orkestrasyonu, operasyonel backend.

**Hedef rol:** Guard kararı `defer_to_private_layer`; trust durumu `private_layer_required` (ADR-007).

**Repo karşılığı (analiz bulgusu):** `STEP_TYPE_EXTERNAL` / `STEP_TYPE_CRITICAL` profil blokları; `controlled_bridge` mail/shell blok; public-github-boundary kuralları.

---

### production action

**Anlam:** Gerçek dış etki, prod servis, prod config veya geri alınamaz sonuç doğuran **üretim niteliğinde** eylem — public repo foundation'da **varsayılan olarak yok** veya açıkça private katmana ertelenir.

**Örnekler (hedef sınıflandırma, uygulama yok):** Prod mail gönderimi, prod API yazma, prod key rotasyonu, domain satın alma.

---

### sensitive action

**Anlam:** Identity, keystore, koruma kilidi, PII veya çekirdek path'e dokunan **hassas** eylem — consent, lock veya elevated confirmation gerektirebilir.

**Repo karşılığı (analiz bulgusu):** `action_policy` identity/keystore; `change_sensitivity` CRITICAL/HIGH; `ACCESS_IDENTITY` / `ACCESS_KEYSTORE`.

---

### reversible action

**Anlam:** Geri alınabilir veya trash sözleşmesiyle yumuşatılmış eylem — kalıcı silme otomatiği **değildir**.

**Hedef rol:** `.lumos/trash/` prensibi; onay profiline göre `write_local` veya sandbox.

**Repo karşılığı (analiz bulgusu):** Workspace trash sözleşmesi; otomatik kalıcı silme yasağı (`SECURITY_NEVER_AUTO` dışı reversible silme akışları ayrı).

---

### irreversible action

**Anlam:** Geri alınamaz veya otomatik yapılmaması gereken eylem — **açık komut + tek satır uyarı** ile sınırlı (`lumos-karar-sozlesmesi`).

**Hedef rol:** `SECURITY_NEVER_AUTO`: `permanent_delete`, `external_write`, `irreversible_user_op`, `critical_system_config`.

**Repo karşılığı (analiz bulgusu):** `profiles.py` `SECURITY_NEVER_AUTO`; engine'de tam enforce **gap** (ADR-006).

---

## Zorunlu ayrımlar (karıştırılmamalı)

Aşağıdaki eşitsizlikler **bilinçli terminoloji ayrımıdır**; dokümantasyon ve usage map'te aynı kelime farklı kavram için kullanılmamalıdır.

### guard ≠ trust

| | guard | trust |
|---|-------|-------|
| **Odak** | İstek/adım **yürütülebilir mi?** (risk, profil, politika) | **Kim / hangi güven durumunda?** (kimlik, kilit, consent, presence) |
| **Çıktı** | allow, deny, ask_confirmation, sandbox_only, … (ADR-006) | locked, consent_required, private_layer_required, … (ADR-007) |
| **İlişki** | Guard, trust **sinyallerini tüketir**; trust guard'ın yerine geçmez |

Guard "bu patch'i şimdi uygula mı?" der; trust "kök anahtar yüklü mü, consent var mı?" der. Birleşik modül yok; parçalı katmanlar çelişebilir (ADR-006, ADR-007).

---

### policy ≠ permission

| | policy | permission |
|---|--------|------------|
| **Odak** | **Kural kümesi** — ne izinli, ne yasak, ne onay ister | **Grant / yetki** — bu profilde bu adım çalıştırılabilir mi |
| **Örnek** | Offline mutasyon red; koruma aktifken delete red | `may_execute_step_at_runtime(profile, step_type)` |
| **İlişki** | Policy kuralları tanımlar; permission uygulama anındaki izin yüzeyidir |

Policy değiştirmeden permission stub'ı (`permissions.py`) gerçek lease modeli **değildir**.

---

### consent ≠ confirmation

| | consent | confirmation |
|---|---------|----------------|
| **Odak** | **Kalıcı / oturum rızası** — identity, keystore, koruma alanı | **Tek işlem onayı** — şu adım, şimdi |
| **Süre** | Dosya / state'te tutulabilir; `effective_consent` | Anlık; işlem bazlı |
| **Örnek** | Keystore erişim rızası kaydı | `pending_approval` kuyruğundaki görev onayı |

Consent olmadan hassas alan açılmaz; confirmation olmadan riskli **tek adım** yürütülmez. İkisi birleştirilmemelidir (mail okuma vs gönderim ayrımı ADR-009 ile uyumlu).

---

### local demo ≠ production

| | local demo | production |
|---|------------|------------|
| **İddia** | Üretim güven / entegrasyon iddiası **yok** | Gerçek dış etki, prod servis, prod config |
| **Repo** | Panel mock, stub, demo etiketleri | Public foundation **kapsam dışı**; private layer |
| **Trust durumu** | `local_demo` (ADR-007) | `private_layer_required` veya public'te `denied` |

Local demo'da görünen "Kilitli" / "Açık" metni production lock semantiği **garanti etmez**.

---

### locked ≠ denied

| | locked | denied |
|---|--------|--------|
| **Anlam** | Koruma kilidi kapalı; passphrase ile **açılabilir** durum | İşlem **durduruldu**; profil/policy/guard red |
| **Kurtarma** | `unlock_with_passphrase` (açık komut) | Profil değişimi, farklı adım, private layer — kilidi açmak yetmez |
| **Repo drift** | `LockState.unlocked=False` → LOCKED | `PolicyResult(False)`, `no_op`, `is_allowed_for_profile` False |

Kilitli iken işlem **henüz reddedilmemiş** olabilir — önce unlock veya consent gerekebilir. Denied, guard/policy/profil **nihai red**dir.

---

### sandbox_only ≠ private_layer_required

| | sandbox_only | private_layer_required |
|---|--------------|------------------------|
| **Anlam** | Yalnız tanımlı **sandbox path**'e yaz / dene | İş **public repo'da açılmaz**; professional katman gerekir |
| **Public repo** | Demo-safe workspace sınırı **içinde** kalır | Mail, prod auth, ödeme, cihaz — **public'te yok** |
| **Guard kararı** | ADR-006 `sandbox_only` | ADR-006 `defer_to_private_layer` |

Sandbox, canlı çekirdek state'i koruyan **yerel kopya alanıdır**; private layer, ürün katmanı **ayrımıdır**. Bir dosyayı sandbox'a yazmak private layer'a geçiş **değildir**.

---

### panel görünürlüğü ≠ runtime enforcement

| | panel görünürlüğü | runtime enforcement |
|---|-------------------|---------------------|
| **Odak** | Kullanıcıya durum **göstermek** (Sistem, Koruma, Kimlik, Keystore) | CLI, köprü, task engine'de **gerçekten durdurmak / izin vermek** |
| **Kaynak** | `read_backend_state.py`, `policy-engine.js`, mockState | `action_policy`, `profiles`, `lumos_gate`, `LockState` |
| **Risk** | Mock veya mirror **runtime ile senkron olmayabilir** | Tek doğru enforcement **henüz tek zincir değil** |

Panelde "consent var" görünmesi, köprü hattında aynı consent'in enforce edildiği **anlamına gelmez**. Usage map bu ayrımı zorunlu kılar.

---

## Repo drift riskleri (terminoloji kayması)

Usage map ve ADR revizyonlarında **özellikle** kontrol edilmesi gereken kaymalar (analiz bulgusu):

| Risk | Açıklama | Etkilenen terimler |
|------|----------|-------------------|
| **runtime `LockState` vs `startup_health._lock_ok`** | Biri runtime unlock; diğeri keystore init — aynı "lock" kelimesi | lock, trust, locked |
| **Panel consent vekili (proxy)** | `policy-engine.js` runtime consent'i mirror eder; senkron garantisi yok | consent, panel görünürlüğü, trust |
| **CLI/runtime LOCKED ayrımı** | CLI durum metni ile `LockState` / `get_durum_parts` farklı öncelik | lock, locked, trust |
| **Panel mock durumları** | Köprü yokken mockState; `local_demo` ile production karışabilir | local demo, lock, trust |
| **`packages/kando_policy` ayna drift** | Canonical `src/security` + `src/policy` dışında paralel kopya (ADR-003) | policy, trust |
| **Gate allow + profil deny** | `lumos_gate` allow, `profiles` red — aynı adım için guard ≠ policy uygulaması | guard, policy, permission |
| **`SECURITY_NEVER_AUTO` enforce gap** | Sözleşme terimi var; engine'de tam branch eksik | irreversible action, policy |

Bu tablo **teşhis listesidir**; bu ADR drift'i **düzeltmez**, yalnızca isimlendirme disiplini sağlar.

---

## Terim → katman eşlemesi (özet, taslak)

| Terim | Birincil hedef katman | Canonical kaynak (ADR-003) | Birleşik modül |
|-------|----------------------|----------------------------|----------------|
| guard | AI Firewall (hedef) | Dağınık giriş noktaları | Yok (ADR-006) |
| policy | Policy | `src/policy` | Parçalı |
| trust | Trust Engine (hedef) | `src/security` + sinyal tüketicileri | Yok (ADR-007) |
| lock | Trust / security | `src/security/lock.py` | Var (semantik kayma riski) |
| presence | Trust sinyali | `presence_lock`, `presence_fsm` | Demo |
| permission | Yetki | `profiles.py`, `permissions.py` stub | Profil matrisi var |
| consent | Trust / policy | `action_policy`, consent state | Parçalı |
| confirmation | Guard / task | `task_dispatch`, `lumos_gate` | Parçalı |
| sandbox | Guard / bridge | `controlled_bridge`, interceptor | Kısmen |

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-010:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Bu terminoloji sözlüğü (taslak) | Gerçek production auth, prod lock/presence |
| Demo-safe guard/trust **kavram** ayrımları | Üretim permission lease modeli |
| `local_demo`, `sandbox`, `private_layer_required` **tanımları** | Prod mail, ödeme, cihaz enforcement |
| Drift risk tablosu (analiz bulgusu) | Operasyonel backend, prod orchestration |
| ADR-003/006/007/008 referansları | PII işleyen trust skoru / routing |

Public repo'da parçalı guard/trust parçalarının **"tam ürün terminolojisi = tam ürün garantisi"** gibi sunulması bilinçli olarak yapılmamalıdır.

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent, kilit alanları **dokunulmaz**; bu ADR o sınırları gevşetmez veya genişletmez.

---

## Karar (taslak — usage map bekliyor)

1. **Mevcut gerçek:** Guard, policy, trust, lock, consent ve onay terimleri repo'da **parçalı ve çelişkili** kullanılmaktadır; birleşik sözlük yoktu.
2. **Hedef:** Bu ADR'deki sözlük ve zorunlu ayrımlar, usage map ve ADR-006/007 revizyonları için **referans terminoloji** olarak kullanılır.
3. **Canonical katmanlar (ADR-003):** Policy → `src/policy`; trust/security sinyalleri → `src/security`; yetki → `profiles.py` — terminoloji bu konumları bypass etmez.
4. **Guard/trust/router sırası:** ADR-006 (guard) → ADR-007 (trust) → ADR-004 (router) — terimler bu sırayla karıştırılmaz.
5. **Bu turda kod yok** — yalnızca karar kaydı; lock semantiği, panel UI ve yeni motor **değiştirilmez**.

Durum: **Karar guard/policy/trust usage map tamamlanana kadar bekletilir.**

---

## Ne yapılmamalı (bu ADR kapsamında)

| Yapılmaması gereken | Gerekçe |
|---------------------|---------|
| Kod, import, davranış değişikliği | Yalnızca terminoloji ADR'si |
| Lock semantiği birleştirme (`_lock_ok` vs `LockState`) | Ayrı checkpoint; usage map sonrası |
| Panel UI / mock kaldırma veya değiştirme | Görünürlük ≠ enforcement ayrımı korunur |
| Yeni trust engine veya guard birleştirme | ADR-006/007 usage map öncesi |
| Abartılı ürün vaadi | Teslim veya tam enforcement taahhüdü yok |
| Terimleri tek enum'a zorla map etme | Hipotez/taslak düzeyinde kal |

---

## Sonuç (geçici)

Haziran 2026 repo analizi ve ADR-003/006/007 usage map çalışması sonrasında **guard, policy, trust, lock, permission, consent, confirmation** ve ilişkili kavramlar bu ADR'de **kodsuz terminoloji sözlüğü** olarak toplanmıştır. **guard ≠ trust**, **policy ≠ permission**, **consent ≠ confirmation**, **local demo ≠ production**, **locked ≠ denied**, **sandbox_only ≠ private_layer_required**, **panel görünürlüğü ≠ runtime enforcement** ayrımları açıkça kayıtlıdır.

Repo drift riskleri (`LockState` / `_lock_ok`, panel consent proxy, CLI LOCKED, panel mock) usage map ile doğrulanmalıdır. **Bu turda kod yazılmaz; lock semantiği değiştirilmez; yeni trust engine kurulmaz.**

## Sonraki gözden geçirme

- Guard/policy/trust usage map sonuçları ile terim→kod eşlemesinin revizyonu
- ADR-006 (7 karar tipi) ve ADR-007 (8 trust durumu) ile terim çakışma kontrolü
- ADR-003 canonical katmanlar ve ADR-008 agent network sınırı ile uyum
- Lock semantiği birleştirme kararı — **ayrı ADR veya checkpoint**; bu belge otomatik uygulama içermez
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
