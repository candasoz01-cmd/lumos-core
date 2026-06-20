# ADR-007: Trust Engine / Trust Layer (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Taslak / karar bekliyor** — trust state usage map tamamlanmadan finalize edilmez |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004, ADR-006 |

## Amaç

Lumos kod tabanında **birleşik Trust Engine / Trust Layer** olup olmadığını repo analizine dayalı olarak netleştirmek; hedef trust rolünü, ilk trust durumlarını, trust sinyallerini ve public/private sınırını **kodsuz karar kaydı** olarak belgelemek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, güvenlik/policy davranışı değişikliği veya yeni trust motoru **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). ADR-001 Trust Engine'i **hipotez** düzeyinde listeler. ADR-003 canonical trust/security katmanlarını (`src/security`, `src/policy`) kaydeder. ADR-006 birleşik AI Firewall'ın olmadığını ve firewall'ın Trust sinyallerini **kullanması gerektiğini** kaydeder — Trust birleşik değildir. ADR-004 birleşik AI Router'ın olmadığını ve router'ın Trust/Firewall kararlarından **sonra** yönlendirme yapması gerektiğini kaydeder. Bu ADR, trust hedefini aynı disiplinle — önce analiz ve haritalama, sonra dar karar — kayıt altına alır.

**Öncelik sırası (ADR-001, ADR-004, ADR-006 ile hizalı):** AI Firewall → **Trust** → Router → Memory → Agent Network. Trust, Firewall'dan sonra; Router'dan önce konumlanmalıdır.

---

## Mevcut durum (repo analiz bulguları, Haziran 2026)

### Birleşik Trust Engine yok

Repo taramasında **tek, merkezi "Trust Engine" veya "Trust Layer" modülü tespit edilmemiştir**. Güven, kimlik, izin, kilit, anahtar ve hassas işlem sınırları farklı giriş noktalarında, farklı kurallarla uygulanmaktadır.

### Parçalı trust / güvenlik katmanları

| Katman | Konum (analiz bulgusu) | Kısa rol |
|--------|------------------------|----------|
| Güvenlik çekirdeği | `src/security/*` | identity, keystore, lock, crypto, presence (demo) |
| Kimlik | `src/security/identity.py` | Ed25519, AES-GCM private key, `lumos_id` |
| Anahtar kasası | `src/security/keystore.py` | Passphrase → root key, `keystore.json` |
| Kilit | `src/security/lock.py` | Runtime `unlocked` + `_root_key` |
| Presence | `src/security/presence_lock.py`, `presence_fsm.py` | Config-driven worker, coarse FSM |
| İzin stub | `src/security/permissions.py` | Lease modeli stub (no-op) |
| Minimal aksiyon politikası | `src/policy/action_policy.py` | Offline mutasyon red; koruma aktifken delete red; identity/keystore consent |
| Offline engine | `src/policy/offline_engine.py` | Network gerektiren intent red |
| Yetki / onay matrisi | `src/task_engine/profiles.py` | Profil × adım türü; `SECURITY_NEVER_AUTO`; `may_execute_step_at_runtime` |
| Durum özeti | `src/core/state.py`, `src/core/startup_health.py` | Snapshot, `get_durum_parts`, consent önceliği |
| Panel görünürlük | `panel/js/app.js`, `panel/js/policy-engine.js` | Sistem/Korumalı Alan/Kimlik/Keystore — dürüst demo etiketleri |
| Salt okuma köprü | `panel/scripts/read_backend_state.py` | identity/keystore/consent salt okuma |

**Analiz bulgusu:** Bu katmanlar **kısmen örtüşür** — örneğin hassas işlem hem `action_policy` (consent, koruma) hem `profiles` (profil × adım) hem `lumos_gate` (risk, `no_op`) hem panel `policy-engine.js` üzerinden değerlendirilir; ancak aralarında tutarlı bir trust durumu veya tek sinyal sözleşmesi yoktur. `startup_health._lock_ok` (keystore init) ile runtime `LockState.unlocked` **aynı semantiği taşımaz** (analiz bulgusu).

### İlgili ADR durumu

- **ADR-001:** Trust Engine **hipotez**; öncelik sırasında Firewall'dan **sonra**, Router'dan **önce** konumlanmalıdır. Quantum erken hedef değil.
- **ADR-003:** Canonical trust/security kaynakları **`src/security`** ve **`src/policy`**; yetki profilleri `task_engine/profiles.py` ile hizalı. Trust tasarımı bu katmanları bypass etmemelidir.
- **ADR-004:** Birleşik AI Router **yok**; router Trust/Firewall kararlarından **sonra** yönlendirme yapmalı; Trust tam oturmadan router'ın tek başına üretim vaadi taşımaması gerekir.
- **ADR-006:** Birleşik AI Firewall **yok**; firewall Trust sinyallerini **kullanmalı**; Trust Layer birleşik değil; identity/lock firewall'a tek kapı değil.

### Henüz olmayan alanlar

| Alan | Durum (analiz bulgusu) |
|------|------------------------|
| Birleşik Trust Engine modülü | Yok — ADR-001 hipotez |
| 8 trust durumu sözleşmesi | Yok — dağınık string/enum parçaları |
| 9 trust sinyali birleşik modeli | Yok — lock, consent, presence, profil ayrı |
| Tüm entrypoint'lerde aynı trust zinciri | Yok — CLI, köprü, panel, demo hattı ayrı |
| Birleşik güven skoru | Yok |
| Production auth / cihaz presence | Public sınır dışı |

---

## Trust Engine hedef rolü

Trust Engine (Trust Layer), Lumos'ta kimlik, oturum, kilit, izin, anahtar kasası ve hassas işlem onaylarını **tek sorumluluklu güven karar katmanı** olarak hedeflenir (ADR-001 hipotezi). Kesin API veya modül adı henüz kararlaştırılmamıştır (*taslak*).

Hedeflenen işlevler:

1. **Kullanıcı kimliği ve oturum güvenini temsil etmek** — `DeviceIdentity`, `LockState`, consent; online'da kimlik ve kilit açık olmadan işlem yapılmaması (`lumos-karar-sozlesmesi`).
2. **Koruma kilidi, izinler, anahtar kasası ve hassas işlem onaylarını yönetmek** — `FileKeyStore`, `action_policy`, `profiles.py` (`SECURITY_NEVER_AUTO`), presence demo sınırları.
3. **AI Firewall'a güven sinyali sağlamak** — lock, consent, presence, profil, geri alınabilirlik ve katman sinyallerini firewall kararına beslemek (*ADR-006: firewall Trust sinyallerini kullanmalı*).
4. **AI Router'a hangi işlerin public/yerel/private katmanda çalışabileceğini bildirmek** — `STEP_TYPE_EXTERNAL` / `STEP_TYPE_CRITICAL` blok; `private_layer_required` durumu (*ADR-004: router Trust/Firewall sonrası*).
5. **Hassas işlem yapılmadan önce güven durumunu kontrol etmek** — `may_execute_step_at_runtime`, `check_policy`, `get_durum_parts`; onaysız dış etki veya kritik işlem yok.

Bu rol ADR-001'deki "AI Firewall → Trust → Router → Memory → Agent Network" öncelik sırasında **trust katmanını** somutlaştırmayı hedefler; firewall oturmadan trust'ın tek başına üretim vaadi taşımaması gerekir (*ADR-006 ile hizalı*).

---

## İlk trust durumları (taslak — 8 durum)

Aşağıdaki durumlar **ürün/trust hedef sözleşmesidir**; repo'da birleşik `TrustState` enum'u veya modül olarak tanımlı değildir. Mevcut parçalı eşleşmeler analiz bulgusudur, finalize edilmiş mapping değildir.

| # | Durum | Hedef anlam | Mevcut repo karşılığı (analiz bulgusu) | Boşluk |
|---|-------|-------------|----------------------------------------|--------|
| 1 | **unknown** | Güven sinyalleri yetersiz veya çelişkili | `lumos_gate` `risk_level: unknown`; `get_durum_parts` kamera `None` → "bilinmiyor"; köprü yok | Birleşik trust durumu değil |
| 2 | **local_demo** | Yerel/mock; üretim güven iddiası yok | Panel `mockState`, "Demo önizleme — gerçek … motoru bağlı değil"; `read_backend_state.py` salt okuma | UX düzeyinde; Trust Engine API yok |
| 3 | **locked** | Hassas işlem korumalı | `LockState.unlocked=False` → `LOCKED`; panel `keystoreState: "Kilitli"`; `action_policy` koruma+delete | `_lock_ok` keystore init — semantik kayma |
| 4 | **unlocked** | Passphrase ile kök anahtar yüklü | `unlock_with_passphrase` → `UNLOCKED` snapshot | Panelde çoğunlukla mock |
| 5 | **consent_required** | Kimlik/keystore veya genel onay eksik | `action_policy` → `consent_required`; `effective_consent`; panel `policy-engine.js` | Tek trust durumu olarak birleştirilmemiş |
| 6 | **elevated_confirmation_required** | Yüksek risk / genel onay / passphrase | `kisitli_otonom` + `general_approval`; `pending_approval`; kilidi aç = açık komut | Firewall `ask_confirmation` ile örtüşür; adlandırılmamış |
| 7 | **private_layer_required** | Public repo kapsamı dışı iş | `STEP_TYPE_EXTERNAL/CRITICAL` blok; `controlled_bridge` mail/shell blok; public boundary | Explicit trust state yok |
| 8 | **denied** | İşlem durduruldu | `PolicyResult(False)`, `is_allowed_for_profile` False, `lumos_gate` `no_op` | Dağınık; tek `denied` trust state yok |

Durum ataması **öneri** niteliğindedir; kullanıcı override, profil sınırları ve onay kuralları her zaman üstünde kalır (`lumos-karar-sozlesmesi`).

---

## Trust sinyalleri (hedef set — birleşik değil)

Trust hedefinde değerlendirilecek sinyaller (*henüz merkezi trust modeli yok*):

| # | Sinyal | Canonical kaynak (ADR-003) | Repo durumu (analiz bulgusu) |
|---|--------|----------------------------|------------------------------|
| 1 | **Kullanıcı varlığı / presence** | `src/security/presence_lock.py`, `presence_fsm.py` | Kamera worker, `PresenceState`; demo düzeyi |
| 2 | **Oturum durumu** | `LockState`, `CoreState`, `live_brain` | Online/offline `mode`; passphrase env; birleşik oturum modeli yok |
| 3 | **Koruma kilidi** | `src/security/lock.py`, `CoreState.lock_status()` | `LOCKED` / `UNLOCKED`; `get_durum_parts` lock = keystore init — **semantik kayma** |
| 4 | **İzin seviyesi** | `task_engine/profiles.py` | `rapor` / `guvenli_yurut` / `kisitli_otonom`; `permissions.py` stub |
| 5 | **Hassas veri varlığı** | `src/memory/secure_store`, identity/keystore | Şifreli private key; PII tespiti / trust skoru yok |
| 6 | **Anahtar kasası durumu** | `src/security/keystore.py` | `FileKeyStore.is_initialized()`; panel salt okunur |
| 7 | **İşlem geri alınabilir mi?** | `SECURITY_NEVER_AUTO`, trash sözleşmesi | Kalıcı silme otomatik değil; formal sinyal yok; engine enforce gap |
| 8 | **Dış servis etkisi var mı?** | `profiles` `STEP_TYPE_EXTERNAL`, `offline_engine` | External hiçbir profilde yok; merkezi sınıflandırıcı yok |
| 9 | **Production config etkisi var mı?** | `SECURITY_NEVER_AUTO` `critical_system_config`, `change_sensitivity` CRITICAL | CRITICAL path'ler tanımlı; config intent sınıflandırması yok; gate ile sensitivity bağlı değil |

---

## Mevcut repo karşılığı vs gap (özet)

### Var olan parçalar (canonical — ADR-003)

| Bileşen | Konum | Trust'a katkı |
|---------|-------|---------------|
| Kimlik | `src/security/identity.py` | Ed25519, `lumos_id` |
| Anahtar kasası | `src/security/keystore.py` | Passphrase → root key |
| Kilit | `src/security/lock.py` | Runtime unlock durumu |
| Presence | `presence_lock.py`, `presence_fsm.py` | Demo varlık sinyali |
| Minimal politika | `src/policy/action_policy.py` | Consent, koruma, offline mutasyon |
| Yetki matrisi | `task_engine/profiles.py` | `may_execute_step_at_runtime`, `SECURITY_NEVER_AUTO` |
| Durum özeti | `core/state.py`, `startup_health.py` | Snapshot, `get_durum_parts` |
| Panel | `panel/js/app.js` | Sistem/Koruma/Kimlik/Keystore görünürlük |

### Kritik gap'ler (analiz bulgusu)

1. **Birleşik Trust Engine modülü yok** — ADR-001 hipotez; ADR-006 "Trust Layer birleşik değil".
2. **8 durum / 9 sinyal hedef sözleşme olarak kodda yok** — dağınık parçalar.
3. **Lock semantiği çift anlamlı** — runtime `LockState` vs `startup_health._lock_ok`.
4. **`permissions.py` stub** — izin lease modeli uygulanmamış.
5. **Firewall ↔ Trust tek kapı yok** — ADR-006: identity/lock firewall'a doğrudan bağlı değil.
6. **Giriş noktası tutarsızlığı** — CLI, köprü, panel aynı trust state üretmiyor.
7. **`packages/kando_policy` ayna drift** — ADR-003; canonical `src/security` + `src/policy`.

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-007:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Trust state/sinyal **taslağı** ve ADR karar kayıtları | Gerçek production auth, SSO, prod key yönetimi |
| `src/security` demo-safe foundation (local keystore, identity stub) | Cihaz presence kontrolü (üretim) |
| `profiles.py` davranış referansı (değiştirmeden) | Mail prod aksiyon izinleri (ADR-002; public stub grant modeli ayrı) |
| Panel koruma/kimlik/keystore **görünürlük** (dürüst demo metinleri) | Ödeme, domain, cihaz orkestrasyonu |
| `action_policy` + consent dosyası modeli | PII işleyen routing / trust skoru |
| Trust state usage map (salt okuma analizi) | Operasyonel backend, prod orchestration |
| `presence_lock` demo (kamera) | Quantum/IBM prod entegrasyonu (ADR-001) |

Public repo'da parçalı guard/trust parçalarının **"tam Trust Engine ürünü"** gibi sunulması bilinçli olarak yapılmamalıdır (ADR-006 ile aynı ilke).

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent, kilit alanları **dokunulmaz**; bu ADR o sınırları gevşetmez veya genişletmez.

---

## Karar (taslak — usage map bekliyor)

1. **Mevcut gerçek:** Birleşik Trust Engine yok; trust davranışı `src/security`, `src/policy`, `action_policy`, `permissions`, `lock`, `presence_lock`, `identity`, `keystore` ve `profiles` üzerinde **parçalıdır**; katmanlar kısmen örtüşür.
2. **Hedef:** Yukarıdaki beş rol, 8 trust durumu ve 9 trust sinyali taslağı; finalize için trust state usage map zorunlu.
3. **Canonical katmanlar (ADR-003):** Trust/security kaynakları `src/security` ve `src/policy`; trust tasarımı bu katmanları bypass etmemelidir.
4. **Firewall ilişkisi (ADR-006):** AI Firewall Trust sinyallerini **kullanmalı**; Trust birleşik olmadığı için firewall şu an parçalı sinyallerle çalışır.
5. **Router ilişkisi (ADR-004):** AI Router Trust/Firewall kararlarından **sonra** yönlendirme yapmalı.
6. **Öncelik sırası (ADR-001):** Firewall → **Trust** → Router.
7. **Bu turda kod yok** — yalnızca karar kaydı.

Durum: **Karar trust state usage map tamamlanana kadar bekletilir.**

---

## İlk güvenli adım: trust state usage map

Büyük refactor veya yeni trust motoru **yapılmadan** önce mevcut trust sinyali üretim/tüketim noktalarının haritalanması önerilir.

**Hedef çıktı (ayrı checkpoint veya bu ADR eki — henüz yazılmadı):**

| Giriş noktası | Trust sinyali / durum | Tükettiği / ürettiği | Not |
|---------------|----------------------|----------------------|-----|
| `CoreState.snapshot` / `get_durum_parts` | lock, consent, presence | Panel, CLI durum | Consent > lock > presence önceliği |
| `action_policy.check_policy` | consent, koruma, delete | identity/keystore erişimi | Minimal politika |
| `may_execute_step_at_runtime` | profil × adım | `TaskEngine` | `SECURITY_NEVER_AUTO` |
| `unlock_with_passphrase` / `do_lock` | unlocked / locked | Runtime kök anahtar | Açık komut: kilidi aç |
| `presence_lock` lifecycle | presence | `presence.json`, FSM | Demo düzeyi |
| `read_backend_state.py` | identity, keystore, consent | Panel adapter | Salt okuma |
| `lumos_gate` | risk, no_op | Köprü reasoning | Trust sinyali tüketimi kısmen |
| `controlled_bridge` | sandbox, yüzey blok | workspace/ | Mail/shell/silme blok |
| `panel/js/policy-engine.js` | consent mirror | Panel UX | Runtime ile senkron riski |

**Import map kapsamı (analiz görevi):** `CoreState` → `action_policy` → `profiles` / `may_execute_step_at_runtime` → `lock` / `keystore` / `identity` → `presence_lock` → `read_backend_state` → panel → köprü (`lumos_gate`, `controlled_bridge`) — kim kimi import ediyor, hangi giriş noktası hangi trust sinyalini üretiyor veya tüketiyor.

Usage map tamamlanmadan trust birleştirme, yeni modül veya davranış değişikliği kararı **verilmez**.

---

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, usage map, audit ve kullanıcı onayı olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| **Kod yazma** (trust birleştirme, yeni modül) | Usage map ve karar finalize edilmedi; kapsam şişmesi |
| **Yeni trust motoru** | Parçalı sinyaller önce haritalanmalı; erken motor regresyon riski (ADR-006 ile hizalı) |
| **Gerçek auth sistemi** | Public sınır; private/professional katman |
| **Secret/key yönetimi kurma** | Prod key yönetimi public repo'da olmamalı |
| **Cihaz presence kontrolü** | Public sınır; demo `presence_lock` dışında yok |
| **Mail demo-safe stub (ADR-002)** | ADR-002 — public stub; prod izin akışı ve connector private |
| **Ödeme/domain işlem entegrasyonu** | Public sınır; prod katmanı |
| **Agent Network kurma** | ADR-001 taslak; trust öncesi değil |
| **Quantum/IBM tarafına geçme** | ADR-001 — erken hedef değil |

---

## Riskler (analiz bulgusu)

| Risk | Not |
|------|-----|
| Parçalı trust çelişkisi | Farklı katmanlar farklı trust kararı verebilir |
| Gate allow + profil deny uyuşmazlığı | `lumos_gate` "allow" + `profiles` red mümkün |
| Lock semantiği kayması | `durum` lock_ok ≠ `LockState.unlocked` |
| Panel mock ile CLI LOCKED uyuşmazlığı | Köprü yokken panel mock vs runtime kilidi |
| Public/private sınır sızıntısı | Prod auth/secret/presence public'e taşınması |
| Erken Trust motoru / refactor | CI/regresyon; onay modeli karmaşıklaşması |
| `SECURITY_NEVER_AUTO` tam enforce gap | Sözleşme vs engine (ADR-006) |

---

## Sonuç (geçici)

Haziran 2026 repo analizine dayanarak Lumos'ta **birleşik Trust Engine bulunmamaktadır**. Trust davranışı `src/security`, `src/policy`, `action_policy`, `permissions`, `lock`, `presence_lock`, `identity`, `keystore` ve `profiles` üzerinde **parçalıdır**; katmanlar kısmen örtüşür. ADR-001 sırasına göre Trust, Firewall'dan **sonra**, Router'dan **önce** konumlanmalıdır. ADR-003'e göre canonical trust/security kaynakları **`src/security`** ve **`src/policy`**'dir. ADR-006'ya göre AI Firewall Trust sinyallerini kullanmalıdır. ADR-004'e göre AI Router Trust/Firewall kararlarından sonra yönlendirme yapmalıdır.

**İlk güvenli adım:** Mevcut trust sinyali dokunuş noktalarının trust state usage map olarak çıkarılması. **Bu turda kod yazılmaz; yeni trust motoru kurulmaz; büyük refactor yapılmaz.**

## Sonraki gözden geçirme

- Trust state usage map checkpoint sonuçları ile ADR revizyonu ve karar finalize
- 8 durum × 9 sinyal için resmi trust sözleşmesi taslağı (ayrı belge veya ADR eki)
- ADR-001 (ileri modüller), ADR-003 (canonical katmanlar), ADR-004 (router), ADR-006 (firewall usage map) ile çakışma kontrolü
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- Pilot trust durumu seçimi (ör. `consent_required` vs `locked`) — usage map sonrası, ayrı onay
