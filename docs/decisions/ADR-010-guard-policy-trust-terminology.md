# ADR-010: Guard, Policy, Trust Terminoloji Sözlüğü

| Alan | Değer |
|------|-------|
| Durum | **Kabul edildi** (2026-06-21) — usage map doğrulandı; lock semantiği birleştirme **ayrı checkpoint** |
| Tarih | 2026-06-06 (finalize: 2026-06-21) |
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

## Terminoloji sözlüğü (kabul edilmiş)

Aşağıdaki tanımlar **kabul edilmiş terminoloji sözleşmesidir**. Usage map (2026-06-21) terim→modül eşlemesini doğruladı; birleşik guard/trust **motoru yoktur**. Parantez içindeki konumlar **usage map ile doğrulanmış repo karşılıklarıdır**.

### guard

**Anlam:** Bir istek, adım veya araç çağrısının **yürütülmeden önce** risk, kapsam, profil ve politika sinyallerine göre **geçip geçemeyeceğine** karar veren veya karar öneren **koruyucu katman**.

**Hedef rol:** Durdur, izin ver, onay iste, sandbox'a yönlendir, private katmana ertele (ADR-006 karar tipleri).

**Repo karşılığı (usage map doğrulandı):** `lumos_gate`, `task_dispatch`, `write_interceptor`, `workspace_contract`, `device_guard`, `guard_audit`, `change_sensitivity`, `controlled_bridge`; profil matrisi ile birlikte.

**Not:** Guard **tek modül değildir**; en yoğun terim (~194 eşleşme, 28+ dosya). Birleşik AI Firewall yok (ADR-006).

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

**Repo karşılığı (usage map doğrulandı):** Aktif kodda `trust` terimi neredeyse yok (1 yorum); sinyaller `LockState`, `effective_consent`, `presence_lock`, `get_durum_parts`, `panel_bridge_state`.

**Not:** Birleşik Trust Engine yok (ADR-007 hedef). Trust **dokümantasyon ve hedef rol** terimi; guard katmanları merkezi trust sinyallerini **tüketmiyor**.

---

### lock

**Anlam:** Koruma kilidi — hassas işlem veya kök anahtar erişimi için **runtime'da kilitli veya açık** durum. Passphrase ile açılması gereken koruma katmanı (`lumos-karar-sozlesmesi`: kilidi aç = açık komut).

**Hedef semantik:** `locked` = kök anahtar yüklü değil veya koruma aktif; `unlocked` = passphrase ile kök anahtar yüklü.

**Repo karşılığı (analiz bulgusu):** `src/security/lock.py` (`LockState`), `CoreState.lock_status()`, panel `keystoreState`.

**Drift (usage map doğrulandı):** `_lock_ok` = keystore init; `LockState.unlocked` = passphrase yüklü — **farklı anlam, aynı kelime**. Birleştirme **ayrı checkpoint**; bu ADR düzeltmez.

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

**Reason kodları (PR-C0 — tanımlandı, uygulama bekliyor):** `confirmation_required`, `confirmation_expired`, `confirmation_scope_mismatch`, `confirmation_preview_required`, gate parçası `[CONFIRMATION_BLOCKED]`. Detay: [ADR-012 §7](ADR-012-lumos-security-codex.md#7-confirmation-reason-kodları-pr-c0--tanımlandı-uygulama-bekliyor), [CU4 confirmation skeleton draft](../analysis/lumos-cu4-confirmation-skeleton-draft.md).

**Not:** `pending_action` (consent/GA akışı) ≠ `pending_confirmation` (CU4 işlem onayı) — alan adları birleştirilmemelidir.

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

## Terim → katman eşlemesi (kabul edilmiş özet)

Usage map (2026-06-21) ile doğrulandı. Tam giriş noktası tablosu: [usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md).

| Terim | Birincil hedef katman | Canonical kaynak (ADR-003) | Birleşik modül |
|-------|----------------------|----------------------------|----------------|
| guard | AI Firewall (hedef) | `lumos_gate`, `task_dispatch`, `write_interceptor`, `workspace_contract`, `device_guard`, `guard_audit` | Yok (ADR-006) |
| policy | Policy | `src/policy`, `profiles.py` matrisi, `device_action_policy` | Kısmen (matris) |
| trust | Trust Engine (hedef) | Sinyaller: `LockState`, `effective_consent`, `presence_lock`, `panel_bridge_state` | Yok (ADR-007); kod terimi yok |
| lock | Trust / security | `src/security/lock.py`, `_lock_ok` (farklı semantik) | Var (`LockState`); **drift doğrulandı** |
| presence | Trust sinyali | `presence_lock`, `presence_fsm` | Demo |
| permission | Yetki | `profiles.py`, `permissions.py` stub | Profil matrisi var; stub lease gerçek değil |
| consent | Trust / policy | `effective_consent`, `action_policy`, `panel_bridge_state` | Parçalı |
| confirmation | Guard / task | `pending_approval`, `lumos_gate`, `task_dispatch` | Parçalı |
| sandbox | Guard / bridge | `workspace_contract`, `write_interceptor`, `controlled_bridge` | Kısmen |

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-010:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Bu terminoloji sözlüğü (kabul edilmiş) | Gerçek production auth, prod lock/presence |
| Demo-safe guard/trust **kavram** ayrımları | Üretim permission lease modeli |
| `local_demo`, `sandbox`, `private_layer_required` **tanımları** | Prod mail, ödeme, cihaz enforcement |
| Drift risk tablosu (analiz bulgusu) | Operasyonel backend, prod orchestration |
| ADR-003/006/007/008 referansları | PII işleyen trust skoru / routing |

Public repo'da parçalı guard/trust parçalarının **"tam ürün terminolojisi = tam ürün garantisi"** gibi sunulması bilinçli olarak yapılmamalıdır.

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent, kilit alanları **dokunulmaz**; bu ADR o sınırları gevşetmez veya genişletmez.

---

## Guard / policy / trust kullanım kararları

Usage map bulgularına dayalı **terminoloji seçimleri** (kod değişikliği yok):

| Kavram | Kabul edilen kullanım | Kaçınılacak karışım |
|--------|----------------------|---------------------|
| **guard** | Yürütme öncesi koruyucu katman; modül adı veya audit sink olarak (`lumos_gate`, interceptor, contract guard) | Trust durumu veya lock ile aynı kelime |
| **policy** | Deklaratif kural kümesi (`action_policy`, profil matrisi, device policy) | Runtime grant (`may_execute_step`) ile aynı terim |
| **trust** | Hedef rol ve ADR-007 trust **durumları**; kodda sinyal kaynakları (`LockState`, consent, presence) | Aktif kodda `trust` identifier aramak |
| **lock** | Runtime `LockState` veya açık `_lock_ok` bağlamında; bağlam belirtilmeden "lock" | `_lock_ok` ≡ `LockState.unlocked` varsayımı |
| **consent** | Kalıcı/oturum rıza (`effective_consent`, consent dosyası) | Tek işlem `pending_approval` |
| **confirmation** | İşlem bazlı onay (`pending_approval`, gate risk) | Consent kaydı ile birleştirme |

**Zincir gerçeği:** Giriş noktaları doğrusal değil; `lumos_gate` allow + `profiles` deny kombinasyonları mümkün. Terminoloji bu parçalılığı gizlemez.

---

## Karar

1. **Mevcut gerçek (doğrulandı):** Guard, policy, lock, consent ve onay terimleri repo'da **parçalı**; birleşik guard/trust motoru yok; `trust` aktif kodda neredeyse yok.
2. **Kabul edilen sözlük:** Bu ADR'deki tanımlar ve zorunlu ayrımlar, ADR-006/007 revizyonları ve sonraki dokümantasyon için **referans terminoloji** olarak kullanılır.
3. **Canonical katmanlar (ADR-003):** Policy → `src/policy`; trust/security sinyalleri → `src/security`; yetki → `profiles.py` — terminoloji bu konumları bypass etmez.
4. **Guard/trust/router sırası:** ADR-006 (guard) → ADR-007 (trust) → ADR-004 (router) — terimler bu sırayla karıştırılmaz.
5. **guard ≠ trust (kod kanıtı):** Guard "yürütülebilir mi?" sorar; trust sinyalleri ayrı modüllerde — merkezi tüketim yok.
6. **policy ≠ permission:** Kurallar `action_policy` / matris; grant `may_execute_step_at_runtime`.
7. **panel görünürlüğü ≠ runtime enforcement:** Canlı panel path `panel_bridge_state`; arşiv `policy-engine.js` runtime ile senkron değil.
8. **Bu ADR kod değiştirmez** — lock semantiği, panel UI ve yeni motor bu belge kapsamında **değiştirilmez**.

Kaynak: [`docs/analysis/ADR-010-guard-policy-trust-usage-map.md`](../analysis/ADR-010-guard-policy-trust-usage-map.md) (checkpoint tamamlandı, 2026-06-21).

---

## Takip checkpoint'leri (bu ADR dışı)

| Checkpoint | Neden ayrı | Bu ADR'de yapılan |
|------------|------------|-------------------|
| Lock semantiği (`_lock_ok` vs `LockState`) | Farklı anlam doğrulandı; ürün/kod kararı gerekir | Drift kaydı; düzeltme yok |
| ADR-006 finalize | Guard/firewall karar metni | **Tamamlandı** (2026-06-21) |
| ADR-007 finalize | Trust engine hedef durumları | Sinyal haritası usage map'te |
| `SECURITY_NEVER_AUTO` enforce gap | Engine branch eksik | Sözleşme terimi kayıtlı |
| `packages/kando_policy` import drift | ADR-003 canonical | Terminoloji etkilenmez |

---

## Mevcut guard/policy/trust kullanım haritası

Haziran 2026 repo taraması (2026-06-21) — **salt okuma analizi**; tam tablolar ve drift doğrulaması:

→ **[ADR-010 guard/policy/trust usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md)**

Özet: birleşik guard/trust motoru yok; `trust` aktif kodda neredeyse yok; `_lock_ok` ≠ `LockState` drift doğrulandı; gate + profil + policy parçalı zincir.

---

## Ne yapılmamalı (bu ADR kapsamında)

| Yapılmaması gereken | Gerekçe |
|---------------------|---------|
| Kod, import, davranış değişikliği | Yalnızca terminoloji ADR'si |
| Lock semantiği birleştirme (`_lock_ok` vs `LockState`) | Ayrı checkpoint; usage map sonrası |
| Panel UI / mock kaldırma veya değiştirme | Görünürlük ≠ enforcement ayrımı korunur |
| Yeni trust engine veya guard birleştirme | ADR-006/007 finalize ayrı iş |
| Abartılı ürün vaadi | Teslim veya tam enforcement taahhüdü yok |
| Terimleri tek enum'a zorla map etme | Birleşik motor yok; parçalı repo gerçeği |

---

## Sonuç

Haziran 2026 repo analizi ve usage map (2026-06-21) sonrasında **guard, policy, trust, lock, permission, consent, confirmation** ve ilişkili kavramlar bu ADR'de **kabul edilmiş kodsuz terminoloji sözlüğü** olarak kayıtlıdır. **guard ≠ trust**, **policy ≠ permission**, **consent ≠ confirmation**, **local demo ≠ production**, **locked ≠ denied**, **sandbox_only ≠ private_layer_required**, **panel görünürlüğü ≠ runtime enforcement** ayrımları zorunludur.

Repo drift riskleri (`LockState` / `_lock_ok`, panel consent proxy, CLI LOCKED, panel mock) usage map ile **doğrulandı** — bkz. [usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md). Lock semantiği birleştirme ve engine enforce **takip checkpoint'lerinde**; bu ADR kod veya lock davranışı değiştirmez.

### CU4 confirmation merge notu (2026-06-21, #452–#458)

PR-C zinciri merge edildi; **confirmation** artık ayrı sinyal olarak `policy.confirmation_policy` modülünde. **Opt-in:** `LUMOS_CONFIRMATION_ENABLED=true|1|yes` — varsayılan no-op. Gate sırası: policy → profil (`may_execute_step_at_runtime`, #449) → confirmation (3. kapı). PR-C6 köprü namespace ve varsayılan-on kararı **açık**. Bkz. [CU4 skeleton](../analysis/lumos-cu4-confirmation-skeleton-draft.md), [ADR-012 §7](ADR-012-lumos-security-codex.md).

## Sonraki gözden geçirme

- ADR-007 (8 trust durumu) finalize — ADR-010 + ADR-006 terminolojisine referans
- Lock semantiği birleştirme — **ayrı ADR veya checkpoint**
- ADR-003 canonical katmanlar ve ADR-008 agent network sınırı ile uyum
- `SECURITY_NEVER_AUTO` enforce gap — ADR-006 risk tablosu ile birlikte
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
