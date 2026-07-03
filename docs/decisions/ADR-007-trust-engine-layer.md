# ADR-007: Trust Engine / Trust Layer

| Alan | Değer |
|------|-------|
| Durum | **Kabul edildi** (2026-06-21) — usage map doğrulandı; ADR-010 terminolojisi ile hizalı; birleşik motor **ayrı checkpoint** |
| Tarih | 2026-06-06 (finalize: 2026-06-21) |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004, ADR-006, ADR-008, [ADR-010](ADR-010-guard-policy-trust-terminology.md) |

## Amaç

Lumos kod tabanında **birleşik Trust Engine / Trust Layer** olup olmadığını repo analizine dayalı olarak netleştirmek; hedef trust rolünü, kabul edilmiş trust durumlarını, trust sinyallerini ve public/private sınırını **kodsuz karar kaydı** olarak belgelemek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, güvenlik/policy davranışı değişikliği veya yeni trust motoru **kapsam dışıdır**.

**Terminoloji:** Trust, guard, policy, lock, consent, confirmation ve ilişkili kavramlar **[ADR-010](ADR-010-guard-policy-trust-terminology.md)** kabul edilmiş sözlüğüne tabidir. Bu ADR **trust hedef rolünü** ve 8 trust durumunu kaydeder; guard karar tipleri ADR-006'ya aittir.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). ADR-001 Trust Engine'i **hipotez** düzeyinde listeler. ADR-003 canonical trust/security katmanlarını (`src/security`, `src/policy`) kaydeder. ADR-006 birleşik AI Firewall'ın olmadığını ve firewall'ın Trust sinyallerini **kullanması gerektiğini** kaydeder — Trust birleşik değildir. ADR-004 birleşik AI Router'ın olmadığını ve router'ın Trust/Firewall kararlarından **sonra** yönlendirme yapması gerektiğini kaydeder. ADR-010 guard/policy/trust terminolojisini **kabul edilmiş sözlük** olarak kayıtlıdır; guard ≠ trust, policy ≠ permission, consent ≠ confirmation, locked ≠ denied ayrımları zorunludur.

**Öncelik sırası (ADR-001, ADR-004, ADR-006, ADR-010 ile hizalı):** AI Firewall (guard) → **Trust** → Router → Memory → Agent Network. Trust, Firewall'dan sonra; Router'dan önce konumlanmalıdır.

---

## Mevcut durum (repo analiz bulguları, Haziran 2026 — usage map doğrulandı)

### Birleşik Trust Engine yok

Repo taramasında **tek, merkezi "Trust Engine" veya "Trust Layer" modülü tespit edilmemiştir** (usage map 2026-06-21 ile doğrulandı). Güven, kimlik, izin, kilit, anahtar ve hassas işlem sınırları farklı giriş noktalarında, farklı kurallarla uygulanmaktadır. Aktif kodda `trust` terimi neredeyse yok (1 yorum); trust kavramı **dokümantasyon ve ADR hedefi** düzeyindedir.

### Parçalı trust / güvenlik katmanları

| Katman | Konum (usage map doğrulandı) | Kısa rol (ADR-010) |
|--------|------------------------------|---------------------|
| Güvenlik çekirdeği | `src/security/*` | **trust** sinyalleri — identity, keystore, lock, presence |
| Kimlik | `src/security/identity.py` | **trust** — Ed25519, AES-GCM private key, `lumos_id` |
| Anahtar kasası | `src/security/keystore.py` | **trust** — Passphrase → root key, `keystore.json` |
| Kilit | `src/security/lock.py` | **lock** / **trust** — Runtime `LockState` |
| Presence | `src/security/presence_lock.py`, `presence_fsm.py` | **presence** / **trust** sinyali — demo düzeyi |
| İzin stub | `src/security/permissions.py` | **permission** stub — lease modeli (no-op) |
| Minimal aksiyon politikası | `src/policy/action_policy.py` | **policy** + **consent** — offline mutasyon red; koruma delete red |
| Offline engine | `src/policy/offline_engine.py` | **policy** — network gerektiren intent red |
| Yetki / onay matrisi | `task_engine/profiles.py` | **policy** + **permission** — profil × adım; `SECURITY_NEVER_AUTO` |
| Durum özeti | `src/core/state.py`, `src/core/startup_health.py` | **trust** (görünürlük) — snapshot, `get_durum_parts`, consent önceliği |
| Panel görünürlük | `src/core/panel_bridge_state.py` | **panel görünürlüğü ≠ enforcement** — guidance metinleri |
| Salt okuma köprü | `panel/scripts/read_backend_state.py` | **trust** görünürlük — identity/keystore/consent salt okuma |

**Analiz bulgusu (doğrulandı):** Bu katmanlar **kısmen örtüşür** — örneğin hassas işlem hem `action_policy` (consent, koruma) hem `profiles` (profil × adım) hem `lumos_gate` (risk, `no_op`) hem panel adapter üzerinden değerlendirilir; ancak aralarında tutarlı bir trust durumu veya tek sinyal sözleşmesi yoktur. `startup_health._lock_ok` (keystore init) ile runtime `LockState.unlocked` **aynı semantiği taşımaz** — drift doğrulandı (ADR-010). Guard katmanları merkezi trust sinyallerini **tüketmiyor**.

### İlgili ADR durumu

- **ADR-001:** Trust Engine **hipotez**; öncelik sırasında Firewall'dan **sonra**, Router'dan **önce** konumlanmalıdır. Quantum erken hedef değil.
- **ADR-003:** Canonical trust/security kaynakları **`src/security`** ve **`src/policy`**; yetki profilleri `task_engine/profiles.py` ile hizalı. Trust tasarımı bu katmanları bypass etmemelidir.
- **ADR-004:** Birleşik AI Router **yok**; router Trust/Firewall kararlarından **sonra** yönlendirme yapmalı; Trust tam oturmadan router'ın tek başına üretim vaadi taşımaması gerekir.
- **ADR-006:** Birleşik AI Firewall **yok**; firewall Trust sinyallerini **kullanmalı**; Trust Layer birleşik değil; identity/lock firewall'a tek kapı değil — **guard ≠ trust**.
- **ADR-010:** Terminoloji sözlüğü **kabul edildi**; bu ADR trust durumlarını ADR-010 tanımlarıyla hizalar.

### Henüz olmayan alanlar

| Alan | Durum (usage map doğrulandı) |
|------|------------------------------|
| Birleşik Trust Engine modülü | Yok — ADR-001 hipotez |
| 8 trust durumu sözleşmesi (kod) | Yok — dağınık string/enum parçaları; hedef sözleşme bu ADR'de |
| 9 trust sinyali birleşik modeli | Yok — lock, consent, presence, profil ayrı |
| Tüm entrypoint'lerde aynı trust zinciri | Yok — CLI, köprü, panel, demo hattı ayrı |
| Birleşik güven skoru | Yok |
| Production auth / cihaz presence | Public sınır dışı |

---

## Trust Engine (trust) hedef rolü

**trust** (ADR-010): Kimlik, oturum, kilit, consent, presence ve hassas işlem bağlamında **güven durumunun** (trust state) ve **güven sinyallerinin** hedeflenen birleşik temsili.

Trust Engine (Trust Layer), Lumos'ta kimlik, oturum, kilit, izin, anahtar kasası ve hassas işlem onaylarını **tek sorumluluklu güven karar katmanı** olarak hedeflenir (ADR-001 hipotezi). Kesin API veya modül adı henüz kararlaştırılmamıştır; birleşik modül **yoktur**.

Hedeflenen işlevler:

1. **Kullanıcı kimliği ve oturum güvenini temsil etmek** — `DeviceIdentity`, `LockState`, consent; online'da kimlik ve kilit açık olmadan işlem yapılmaması (`lumos-karar-sozlesmesi`).
2. **Koruma kilidi, izinler, anahtar kasası ve hassas işlem onaylarını yönetmek** — `FileKeyStore`, `action_policy`, `profiles.py` (`SECURITY_NEVER_AUTO`), presence demo sınırları.
3. **AI Firewall'a güven sinyali sağlamak** — lock, consent, presence, profil, geri alınabilirlik ve katman sinyallerini firewall kararına beslemek (*ADR-006: firewall Trust sinyallerini kullanmalı*; guard ≠ trust).
4. **AI Router'a hangi işlerin public/yerel/private katmanda çalışabileceğini bildirmek** — `STEP_TYPE_EXTERNAL` / `STEP_TYPE_CRITICAL` blok; `private_layer_required` durumu (*ADR-004: router Trust/Firewall sonrası*).
5. **Hassas işlem yapılmadan önce güven durumunu kontrol etmek** — `may_execute_step_at_runtime`, `check_policy`, `get_durum_parts`; onaysız dış etki veya kritik işlem yok.
6. **Bağlanmadan önce geçmiş risk kontrolü yapmak** — yeni connector, paket, servis veya cihaz bileşeni eklenmeden önce geçmiş CVE, tekrar eden açık sınıfı, patch disiplini, istenen yetki genişliği ve daha temiz alternatifler değerlendirilir.

Bu rol ADR-001'deki "AI Firewall → Trust → Router → Memory → Agent Network" öncelik sırasında **trust katmanını** somutlaştırmayı hedefler; firewall oturmadan trust'ın tek başına üretim vaadi taşımaması gerekir (*ADR-006 ile hizalı*).

---

## Trust durumları (kabul edilmiş hedef sözleşme — 8 durum)

Aşağıdaki durumlar **kabul edilmiş trust hedef sözleşmesidir** (ADR-010 ile uyumlu); repo'da birleşik `TrustState` enum'u veya modül olarak tanımlı değildir. Mevcut parçalı eşleşmeler usage map ile **doğrulanmış analiz bulgusudur**.

| # | Durum | Hedef anlam | ADR-010 ilişkisi | Mevcut repo karşılığı (usage map) | Boşluk |
|---|-------|-------------|------------------|-----------------------------------|--------|
| 1 | **unknown** | Güven sinyalleri yetersiz veya çelişkili | trust (belirsiz) | `lumos_gate` `risk_level: unknown`; `get_durum_parts` kamera `None` → "bilinmiyor" | Birleşik trust durumu değil |
| 2 | **local_demo** | Yerel/mock; üretim güven iddiası yok | **local demo** ≠ production | Panel guidance, arşiv `mockState`; `read_backend_state.py` salt okuma | UX düzeyinde; Trust Engine API yok |
| 3 | **locked** | Hassas işlem korumalı | **locked** ≠ **denied** | `LockState.unlocked=False` → `LOCKED`; panel `keystoreState: "Kilitli"` | `_lock_ok` keystore init — semantik kayma |
| 4 | **unlocked** | Passphrase ile kök anahtar yüklü | **lock** (runtime) | `unlock_with_passphrase` → `UNLOCKED` snapshot | Panelde çoğunlukla guidance |
| 5 | **consent_required** | Kimlik/keystore veya genel onay eksik | **consent** ≠ **confirmation** | `action_policy` → `consent_required`; `effective_consent`; `panel_bridge_state` | Tek trust durumu olarak birleştirilmemiş |
| 6 | **elevated_confirmation_required** | Yüksek risk / genel onay / passphrase | **elevated confirmation** | `kisitli_otonom` + `general_approval`; `pending_approval`; kilidi aç = açık komut | Guard `ask_confirmation` ile örtüşür; adlandırılmamış |
| 7 | **private_layer_required** | Public repo kapsamı dışı iş | **private_layer** | `STEP_TYPE_EXTERNAL/CRITICAL` blok; `controlled_bridge` mail/shell blok | Explicit trust state yok |
| 8 | **denied** | İşlem durduruldu | **locked ≠ denied** | `PolicyResult(False)`, `is_allowed_for_profile` False, `lumos_gate` `no_op` | Dağınık; tek `denied` trust state yok |

Durum ataması kullanıcı override, profil sınırları (**permission**) ve onay kuralları (**confirmation**) altındadır (`lumos-karar-sozlesmesi`).

---

## Trust sinyalleri (kabul edilmiş hedef set — birleşik değil)

Trust hedefinde değerlendirilecek sinyaller (*henüz merkezi trust modeli yok*; usage map doğrulandı):

| # | Sinyal | ADR-010 terimi | Canonical kaynak (ADR-003) | Repo durumu (usage map) |
|---|--------|----------------|----------------------------|-------------------------|
| 1 | **Kullanıcı varlığı / presence** | **presence** | `src/security/presence_lock.py`, `presence_fsm.py` | Kamera worker, `PresenceState`; demo düzeyi |
| 2 | **Oturum durumu** | **trust** (oturum) | `LockState`, `CoreState`, `live_brain` | Online/offline `mode`; passphrase env; birleşik oturum modeli yok |
| 3 | **Koruma kilidi** | **lock** | `src/security/lock.py`, `CoreState.lock_status()` | `LOCKED` / `UNLOCKED`; `get_durum_parts` lock = `_lock_ok` — **semantik kayma doğrulandı** |
| 4 | **İzin seviyesi** | **permission** | `task_engine/profiles.py` | `rapor` / `guvenli_yurut` / `kisitli_otonom`; `permissions.py` stub |
| 5 | **Hassas veri varlığı** | **sensitive action** bağlamı | `src/memory/secure_store`, identity/keystore | Şifreli private key; PII tespiti / trust skoru yok |
| 6 | **Anahtar kasası durumu** | **trust** (keystore) | `src/security/keystore.py` | `FileKeyStore.is_initialized()`; panel salt okunur |
| 7 | **İşlem geri alınabilir mi?** | **reversible action** | `SECURITY_NEVER_AUTO`, trash sözleşmesi | Kalıcı silme otomatik değil; formal sinyal yok; engine enforce gap |
| 8 | **Dış servis etkisi var mı?** | **private_layer** / **production action** | `profiles` `STEP_TYPE_EXTERNAL`, `offline_engine` | External hiçbir profilde yok; merkezi sınıflandırıcı yok |
| 9 | **Production config etkisi var mı?** | **irreversible action** | `SECURITY_NEVER_AUTO` `critical_system_config`, `change_sensitivity` CRITICAL | CRITICAL path'ler tanımlı; config intent sınıflandırması yok; gate ile sensitivity bağlı değil |

---

## Trust Preflight: Dependency & Connector History Check

**Türkçe adı:** Bağlanmadan Önce Geçmiş Kontrolü.

**Kural:** Lumos'a yeni bir connector, paket, servis, cihaz bileşeni veya dış araç bağlanmadan önce yalnızca "şu an çalışıyor mu?" sorusu sorulmaz. Parçanın geçmiş risk ve kırılma hafızası da kontrol edilir.

Bu kontrol, "yamalı lastik" riskini görünür kılar: geçmişte aynı yerden patlamış, çok patch yemiş, gereğinden fazla yetki isteyen veya geçici çözümle ayakta duran bileşenler doğrudan güvenilir kabul edilmez.

### Preflight soruları

| # | Soru | Beklenen karar etkisi |
|---|------|-----------------------|
| 1 | Son 12-24 ayda kritik CVE veya ciddi güvenlik olayı var mı? | Riskli ise sandbox / sınırlı yetki / alternatif değerlendirme |
| 2 | Aynı sınıf hata tekrar etmiş mi? | Tekil olay mı, tasarım alışkanlığı mı ayrılır |
| 3 | Güvenlik yamaları hızlı mı çıkmış, gecikmiş mi? | Bakım güveni ve vendor/maintainer disiplini değerlendirilir |
| 4 | Bağımlılık veya modül çok patch yemiş mi? | Kırılgan alanlar ekstra izlenir |
| 5 | Eski auth yöntemi veya zayıf token modeli kullanıyor mu? | Modern auth / vault / kısa ömürlü token şartı aranır |
| 6 | Gereğinden fazla yetki istiyor mu? | En dar scope veya connector reddi |
| 7 | Log'a secret, token, PII veya ham istek yazma alışkanlığı var mı? | Redaction ve audit şartı |
| 8 | "Geçici çözüm" olarak kalmış kritik kod var mı? | `Needs Decision` veya izolasyon |
| 9 | Daha temiz, daha az yetkili veya daha iyi bakılan alternatif var mı? | Alternatif tercih edilebilir |

### Çıktı sınıfları

| Sonuç | Anlam | Trust davranışı |
|-------|-------|-----------------|
| **Clean enough** | Geçmiş risk kabul edilebilir | Normal connector değerlendirmesine geçer |
| **Patch-sensitive** | Geçmişte aynı sınıf sorunlar var | Sandbox, dar scope, ek audit ve review date gerekir |
| **High-risk history** | Kritik tekrar, kötü bakım veya aşırı yetki var | Varsayılan red veya private/izole PoC |
| **Insufficient evidence** | Geçmiş kanıtı yok veya belirsiz | `Needs Decision`; güven varsayılmaz |

Bu bölüm **kod veya otomatik tarayıcı eklemez**. Trust Faz 4 için hedef sözleşmedir; uygulanması ayrı PR/karar konusudur.

---

## Terminoloji uyumu (ADR-010)

Bu ADR'de geçen kavramlar ADR-010 zorunlu ayrımlarına tabidir:

| Ayrım | Trust katmanı bağlamı |
|-------|----------------------|
| **guard ≠ trust** | Guard "yürütülebilir mi?" sorar; trust "kim / hangi güven durumunda?" sorar — guard katmanları merkezi trust sinyallerini tüketmiyor |
| **policy ≠ permission** | `action_policy` / profil matrisi **policy**; `may_execute_step_at_runtime` **permission** |
| **consent ≠ confirmation** | Keystore/identity rızası ≠ `pending_approval` tek adım onayı |
| **locked ≠ denied** | Kilit açılabilir durum ≠ guard/policy nihai red |
| **local demo ≠ production** | Panel guidance / arşiv mock üretim güven iddiası taşımaz |
| **panel görünürlüğü ≠ runtime enforcement** | `panel_bridge_state` guidance; runtime `LockState` / `action_policy` ayrı |

Tam sözlük: [ADR-010](ADR-010-guard-policy-trust-terminology.md). Giriş noktası haritası: [usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md).

---

## Mevcut repo karşılığı vs gap (özet — usage map doğrulandı)

### Var olan parçalar (canonical — ADR-003)

| Bileşen | Konum | Trust'a katkı (ADR-010) |
|---------|-------|-------------------------|
| Kimlik | `src/security/identity.py` | **trust** — Ed25519, `lumos_id` |
| Anahtar kasası | `src/security/keystore.py` | **trust** — Passphrase → root key |
| Kilit | `src/security/lock.py` | **lock** / **trust** — Runtime unlock durumu |
| Presence | `presence_lock.py`, `presence_fsm.py` | **presence** / **trust** sinyali — demo |
| Minimal politika | `src/policy/action_policy.py` | **policy** + **consent** kuralları |
| Yetki matrisi | `task_engine/profiles.py` | **policy** + **permission** |
| Durum özeti | `core/state.py`, `startup_health.py` | **trust** görünürlük — snapshot, `get_durum_parts` |
| Panel adapter | `core/panel_bridge_state.py` | **panel görünürlüğü** — guidance |

### Kritik gap'ler (usage map doğrulandı)

1. **Birleşik Trust Engine modülü yok** — ADR-001 hipotez; ADR-006 "Trust Layer birleşik değil".
2. **8 durum / 9 sinyal hedef sözleşme olarak kodda yok** — dağınık parçalar; bu ADR sözleşmeyi kaydeder.
3. **Lock semantiği çift anlamlı** — runtime `LockState` vs `startup_health._lock_ok` — drift doğrulandı.
4. **`permissions.py` stub** — izin lease modeli uygulanmamış.
5. **Firewall ↔ Trust tek kapı yok** — ADR-006: identity/lock firewall'a doğrudan bağlı değil; guard ≠ trust.
6. **Giriş noktası tutarsızlığı** — CLI, köprü, panel aynı trust state üretmiyor.
7. **`packages/kando_policy` ayna drift** — ADR-003; canonical `src/security` + `src/policy`.

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-007:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Trust state/sinyal **hedef sözleşmesi** ve ADR karar kayıtları (kabul edilmiş) | Gerçek production auth, SSO, prod key yönetimi |
| `src/security` demo-safe foundation (local keystore, identity stub) | Cihaz presence kontrolü (üretim) |
| `profiles.py` davranış referansı (değiştirmeden) | Mail prod aksiyon izinleri (ADR-002; public stub grant modeli ayrı) |
| Panel koruma/kimlik/keystore **görünürlük** (dürüst demo metinleri) | Ödeme, domain, cihaz orkestrasyonu |
| `action_policy` + consent dosyası modeli | PII işleyen routing / trust skoru |
| Usage map ve ADR karar kayıtları (kabul edilmiş) | Operasyonel backend, prod orchestration |
| `presence_lock` demo (kamera) | Quantum/IBM prod entegrasyonu (ADR-001) |

Public repo'da parçalı guard/trust parçalarının **"tam Trust Engine ürünü"** gibi sunulması bilinçli olarak yapılmamalıdır (ADR-006 ile aynı ilke).

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent, kilit alanları **dokunulmaz**; bu ADR o sınırları gevşetmez veya genişletmez.

---

## Trust / guard kullanım kararları

Usage map bulgularına dayalı **trust terminoloji seçimleri** (kod değişikliği yok; ADR-010 ile uyumlu):

| Kavram | Kabul edilen kullanım | Kaçınılacak karışım |
|--------|----------------------|---------------------|
| **Trust Engine / trust** | Hedef rol ve 8 trust **durumu**; kodda sinyal kaynakları (`LockState`, consent, presence) | Aktif kodda `trust` identifier aramak veya birleşik motor varsayımı |
| **trust durumu** | 8 durum hedef sözleşme (`locked` … `denied`) | Guard karar tipi (`allow`, `deny`, `sandbox_only`) ile aynı enum |
| **trust sinyali** | 9 sinyal hedef seti; canonical `src/security` + `src/policy` | Guard katmanı ile aynı terim |
| **lock** | Runtime `LockState` veya açık `_lock_ok` bağlamında; bağlam belirtilmeden "lock" | `_lock_ok` ≡ `LockState.unlocked` varsayımı |
| **consent** | Kalıcı/oturum rıza (`effective_consent`, consent dosyası) | Tek işlem `pending_approval` (**confirmation**) |

**Zincir gerçeği:** Giriş noktaları doğrusal değil; gate allow + profil deny veya policy allow + lock kapalı kombinasyonları mümkün. Trust terminolojisi bu parçalılığı gizlemez.

---

## Karar

1. **Mevcut gerçek (doğrulandı):** Birleşik Trust Engine yok; trust davranışı `src/security`, `src/policy`, `action_policy`, `permissions`, `lock`, `presence_lock`, `identity`, `keystore` ve `profiles` üzerinde **parçalıdır**; katmanlar kısmen örtüşür; `trust` aktif kodda neredeyse yok.
2. **Kabul edilen hedef sözleşme:** Yukarıdaki beş trust rolü, 8 trust durumu ve 9 trust sinyali — ADR-010 terminolojisi ile hizalı **referans trust sözleşmesi** olarak kullanılır.
3. **Terminoloji (ADR-010):** Trust terimleri ADR-010 sözlüğüne tabidir; guard ≠ trust; policy ≠ permission; consent ≠ confirmation; locked ≠ denied; panel görünürlüğü ≠ runtime enforcement.
4. **Canonical katmanlar (ADR-003):** Trust/security kaynakları `src/security` ve `src/policy`; trust tasarımı bu katmanları bypass etmemelidir.
5. **Firewall ilişkisi (ADR-006):** AI Firewall Trust sinyallerini **kullanmalı**; Trust birleşik olmadığı için firewall şu an parçalı sinyallerle çalışır — guard ≠ trust.
6. **Router ilişkisi (ADR-004):** AI Router Trust/Firewall kararlarından **sonra** yönlendirme yapmalı.
7. **Öncelik sırası:** Guard (ADR-006) → **Trust** (bu ADR) → Router (ADR-004).
8. **Bu ADR kod değiştirmez** — birleşik motor, lock semantiği birleştirme ve engine enforce **ayrı checkpoint**.

Kaynak: [`docs/analysis/ADR-010-guard-policy-trust-usage-map.md`](../analysis/ADR-010-guard-policy-trust-usage-map.md) (checkpoint tamamlandı, 2026-06-21).

---

## Takip checkpoint'leri (bu ADR dışı)

| Checkpoint | Neden ayrı | Bu ADR'de yapılan |
|------------|------------|-------------------|
| Birleşik Trust Engine modülü | Parçalı sinyaller önce sözleşme; motor regresyon riski | Hedef rol + 8 durum + 9 sinyal kayıtlı |
| Lock semantiği (`_lock_ok` vs `LockState`) | Farklı anlam doğrulandı; ürün/kod kararı gerekir | ADR-010 drift referansı |
| ADR-006 finalize | Guard/firewall karar metni | **Tamamlandı** (2026-06-21) |
| ADR-010 finalize | Terminoloji sözlüğü | **Tamamlandı** (2026-06-21) |
| `SECURITY_NEVER_AUTO` enforce gap | Engine branch eksik | Sözleşme terimi kayıtlı |
| Guard–trust merkezi tüketim | Import/kod kararı | Kopukluk doğrulandı |

---

## Mevcut guard/policy/trust kullanım haritası

Haziran 2026 repo taraması (2026-06-21) — **salt okuma analizi**; tam tablolar, import zinciri ve drift doğrulaması:

→ **[ADR-010 guard/policy/trust usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md)**

Özet: birleşik trust motoru yok; `trust` aktif kodda neredeyse yok; `_lock_ok` ≠ `LockState` drift doğrulandı; guard katmanları trust sinyallerini merkezi tüketmiyor.

---

## Ne yapılmamalı (bu ADR kapsamında)

| Yapılmaması gereken | Gerekçe |
|---------------------|---------|
| Kod yazma (trust birleştirme, yeni modül) | Sözleşme kayıtlı; motor ayrı checkpoint |
| Yeni trust motoru | Parçalı sinyaller önce enforce edilmeli |
| Gerçek auth sistemi | Public sınır; private/professional katman |
| Secret/key yönetimi kurma | Prod key yönetimi public repo'da olmamalı |
| Cihaz presence kontrolü | Public sınır; demo `presence_lock` dışında yok |
| Lock semantiği birleştirme (`_lock_ok` vs `LockState`) | Ayrı checkpoint; usage map sonrası onay |
| Panel UI / mock kaldırma veya değiştirme | Görünürlük ≠ enforcement ayrımı korunur |
| Trust = guard varsayımı | ADR-010 zorunlu ayrım |
| Terimleri tek enum'a zorla map etme | Birleşik motor yok; parçalı repo gerçeği |

---

## Riskler (usage map doğrulandı)

| Risk | Not |
|------|-----|
| Parçalı trust çelişkisi | Farklı katmanlar farklı trust kararı verebilir |
| Gate allow + profil deny uyuşmazlığı | `lumos_gate` "allow" + `profiles` red mümkün |
| Lock semantiği kayması | `durum` lock_ok ≠ `LockState.unlocked` — drift doğrulandı |
| Panel guidance ile CLI LOCKED uyuşmazlığı | Köprü yokken panel adapter vs runtime kilidi |
| Public/private sınır sızıntısı | Prod auth/secret/presence public'e taşınması |
| Erken Trust motoru / refactor | CI/regresyon; onay modeli karmaşıklaşması |
| `SECURITY_NEVER_AUTO` tam enforce gap | Sözleşme vs engine (ADR-006) |
| Guard–trust karışımı | Lock/consent trust sinyali sanılabilir — ADR-010 ayrımı |

---

## Sonuç

Haziran 2026 repo analizi ve usage map (2026-06-21) sonrasında Lumos'ta **birleşik Trust Engine bulunmamaktadır**. Trust davranışı parçalıdır; **8 trust durumu** ve **9 trust sinyali** ADR-010 terminolojisi ile hizalı **kabul edilmiş hedef sözleşme** olarak kayıtlıdır. ADR-001 sırasına göre Trust, Firewall'dan **sonra**, Router'dan **önce** konumlanmalıdır. Guard ≠ trust; birleşik motor kurulumu, lock semantiği birleştirme ve engine enforce **takip checkpoint'lerindedir**; bu ADR kod değiştirmez.

## Sonraki gözden geçirme

- Lock semantiği birleştirme — **ayrı ADR veya checkpoint**
- `SECURITY_NEVER_AUTO` enforce gap — engine branch (kod değişikliği ayrı iş)
- Guard–trust merkezi sinyal tüketimi — dar import/kod kararı ayrı onay
- ADR-004 router finalize — trust sinyali tüketimi
- ADR-003 canonical katmanlar ve ADR-008 agent network sınırı ile uyum
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
