# ADR-006: AI Firewall / Guard Katmanı

| Alan | Değer |
|------|-------|
| Durum | **Kabul edildi** (2026-06-21) — usage map doğrulandı; ADR-010 terminolojisi ile hizalı; birleşik motor **ayrı checkpoint** |
| Tarih | 2026-06-06 (finalize: 2026-06-21) |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-003, ADR-004, ADR-007, ADR-008, [ADR-010](ADR-010-guard-policy-trust-terminology.md) |

## Amaç

Lumos kod tabanında **birleşik AI Firewall** olup olmadığını repo analizine dayalı olarak netleştirmek; hedef firewall (guard) rolünü, kabul edilmiş risk kategorilerini, guard karar tiplerini ve public/private sınırını **kodsuz karar kaydı** olarak belgelemek.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, guard davranışı değişikliği veya yeni güvenlik motoru **kapsam dışıdır**.

**Terminoloji:** Guard, policy, trust, lock, consent, confirmation ve ilişkili kavramlar **[ADR-010](ADR-010-guard-policy-trust-terminology.md)** kabul edilmiş sözlüğüne tabidir. Bu ADR **guard / AI Firewall hedef rolünü** kaydeder; trust durumları ADR-007'ye aittir.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki, onay ve workspace sözleşmesi önceliklidir (`lumos-karar-sozlesmesi`). ADR-001 AI Firewall'ı **hipotez** düzeyinde listeler ve öncelik sırasında **Router'dan önce** konumlandırır. ADR-003 canonical trust/security katmanlarını (`src/security`, `src/policy`) kaydeder. ADR-004 birleşik AI Router'ın olmadığını ve router'ın guard sinyallerini kullanması gerektiğini kaydeder — guard router'ın yerine geçmez. ADR-010 guard/policy/trust terminolojisini **kabul edilmiş sözlük** olarak kayıtlıdır; guard ≠ trust, policy ≠ permission, consent ≠ confirmation ayrımları zorunludur.

**Öncelik sırası (ADR-001, ADR-004, ADR-007, ADR-010 ile hizalı):** AI Firewall (guard) → Trust → Router → Memory → Agent Network.

---

## Mevcut durum (repo analiz bulguları, Haziran 2026 — usage map doğrulandı)

### Birleşik AI Firewall yok

Repo taramasında **tek, merkezi "AI Firewall" modülü tespit edilmemiştir**. Guard davranışı farklı giriş noktalarında, farklı kurallarla uygulanmaktadır (usage map 2026-06-21 ile doğrulandı).

### Parçalı guard / politika katmanları

| Katman | Konum (usage map doğrulandı) | Kısa rol (ADR-010) |
|--------|------------------------------|---------------------|
| LLM reasoning öncesi gate | `packages/kando_runtime/src/kando_runtime/lumos_gate.py` | **guard** — `agent` \| `direct_patch` \| `no_op`; risk; **confirmation** |
| Görev dispatch | `packages/kando_runtime/src/kando_runtime/task_dispatch.py` | **guard** — task_type; `pending_approval` |
| Yetki / onay matrisi | `src/task_engine/profiles.py` | **policy** + **permission** — profil × adım; `SECURITY_NEVER_AUTO` |
| Minimal aksiyon politikası | `src/policy/action_policy.py` | **policy** — offline mutasyon red; **consent** |
| Offline engine | `src/policy/offline_engine.py` | **policy** — network gerektiren intent red |
| Path hassasiyeti | `src/core/change_sensitivity.py` | **guard** — CRITICAL/HIGH/NORMAL/LOW |
| Write interceptor | `src/core/write_interceptor.py` | **guard** + **sandbox** |
| Workspace contract | `src/core/workspace_contract.py` | **guard** + **sandbox** — core path sink'ler |
| Guard audit | `src/core/guard_audit.py` | **guard** — audit kanıtı |
| Device guard | `src/device/device_guard.py` | **guard** + **policy** |
| Güvenlik çekirdeği | `src/security/*` | **trust** sinyalleri — lock, consent, presence (guard değil) |
| Kontrollü köprü | `packages/kando_runtime/src/kando_runtime/controlled_bridge.py` | **guard** + **sandbox** — yüzey blok |

**Analiz bulgusu (doğrulandı):** Katmanlar **kısmen örtüşür**; zincir **doğrusal değil** — `lumos_gate` allow + `profiles` deny kombinasyonları mümkün. `lumos_gate` ile `change_sensitivity` **doğrudan bağlı değildir**. Guard katmanları merkezi trust sinyallerini **tüketmiyor** (ADR-010).

### İlgili ADR durumu

- **ADR-001:** AI Firewall **hipotez**; öncelik sırasında güvenli yönlendirme (routing) ve politika sınırlarından **önce** temel güvenlik katmanı olarak konumlanmalıdır.
- **ADR-003:** Canonical trust/security kaynakları **`src/security`** ve **`src/policy`**; yetki profilleri `task_engine/profiles.py` ile hizalı. Guard tasarımı bu katmanları bypass etmemelidir.
- **ADR-004:** Birleşik AI Router **yok**; router guard sinyallerini **kullanmalı**; guard router'ın yerine **geçmemelidir**.
- **ADR-007:** Birleşik Trust Engine **yok**; trust sinyalleri (`LockState`, `effective_consent`, presence) guard'dan **ayrıdır** — guard ≠ trust.
- **ADR-010:** Terminoloji sözlüğü **kabul edildi**; bu ADR guard karar tiplerini ADR-010 tanımlarıyla hizalar.

### Henüz olmayan alanlar

| Alan | Durum (usage map doğrulandı) |
|------|------------------------------|
| Birleşik risk sınıflandırma (11 kategori) | Yok — dağınık keyword/heuristic |
| Birleşik guard karar sözlüğü (7 tip) | Yok — `lumos_gate` alt kümesi |
| Trust Engine / birleşik güven skoru | Yok — ADR-007 hedef |
| Tüm entrypoint'lerde aynı guard zinciri | Yok — CLI, köprü, task engine, demo hattı ayrı |
| PII tespiti / filtreleme | Yok |
| Production auth / ödeme / mail aksiyonu | Public sınır dışı |

---

## AI Firewall (guard) hedef rolü

**guard** (ADR-010): Bir istek, adım veya araç çağrısının **yürütülmeden önce** risk, kapsam, profil ve politika sinyallerine göre geçip geçemeyeceğine karar veren koruyucu katman.

AI Firewall, Lumos'ta model ve araç çağrıları için **politika, filtre ve sınır katmanı** olarak hedeflenir (ADR-001 hipotezi). Kesin API veya modül adı henüz kararlaştırılmamıştır; birleşik modül **yoktur**.

Hedeflenen işlevler:

1. **Kullanıcı isteğini risk açısından kontrol etmek** — niyet, metin, hedef path ve adım türü sinyallerini birleştirmek.
2. **Hassas veri, dış servis, dosya sistemi, cihaz işlemleri ve geri dönüşsüz aksiyonları sınıflandırmak** — 11 risk kategorisine (aşağıda) map etmek.
3. **Gerektiğinde kullanıcı onayı istemek** — **confirmation** (`ask_confirmation`); `lumos-karar-sozlesmesi` ile uyumlu genel onay, açık komut veya yüksek risk kartı.
4. **Güvenli olmayan veya kapsam dışı işlemleri durdurmak** — `no_op`, `deny`, `SECURITY_NEVER_AUTO`, köprü yüzey blokları.
5. **Trust sinyalleri ve Router ile birlikte çalışmak** — guard "yürütülebilir mi?" sorar; trust "kim / hangi güven durumunda?" sorar (ADR-010: guard ≠ trust); router yönlendirir.

Bu rol ADR-001'deki "AI Firewall → Trust → Router → Memory → Agent Network" öncelik sırasında **guard katmanını** somutlaştırmayı hedefler; router oturmadan guard'ın tek başına üretim vaadi taşımaması gerekir.

---

## Risk kategorileri (kabul edilmiş hedef sözleşme — 11 kategori)

Aşağıdaki kategoriler **kabul edilmiş guard hedef sözleşmesidir**; repo'da birleşik karşılıkları henüz tanımlı değildir. Mevcut parçalı eşleşmeler usage map ile **doğrulanmış analiz bulgusudur**.

| # | Kategori | Hedef guard davranışı | Mevcut repo karşılığı (usage map) | Boşluk |
|---|----------|----------------------|-----------------------------------|--------|
| 1 | **Düşük riskli bilgi/sohbet** | `allow` / `log_only` | `bridge_intent` → chat; `OfflineEngineV1`; CLI `unknown` + online | Birleşik kategori yok |
| 2 | **Proje içi okuma/özetleme** | `allow` (read profili) | `profiles.py` READ/ANALYZE; `lumos_gate` özet; `controlled_bridge` read | Okuma/özet firewall sözleşmesi ayrılmamış |
| 3 | **Dosya düzenleme** | `allow` / `ask_confirmation` / `sandbox_only` | `lumos_gate` `direct_patch`; `task_dispatch`; `write_interceptor` + `change_sensitivity` | Gate ↔ sensitivity **kopuk** |
| 4 | **Dış servis yazma** | `deny` / `defer_to_private_layer` | `STEP_TYPE_EXTERNAL` profil blok | Merkezi sınıflandırıcı yok |
| 5 | **Mail gönderme/silme/arşivleme** | `deny` / `defer_to_private_layer` | `controlled_bridge` mail regex blok | ADR-009; demo-safe stub |
| 6 | **Ödeme/domain/satın alma** | `deny` / `defer_to_private_layer` | `kando_core._infer_risk` keyword (demo) | Public sınır dışı |
| 7 | **Cihaz/yerel işlem** | `sandbox_only` / `ask_confirmation` | `OfflineEngineV1` + `PermissionManager` stub; bridge sandbox | Gerçek cihaz kontrolü yok |
| 8 | **Kalıcı silme** | `deny` (otomatik) / `ask_confirmation` (açık komut) | `SECURITY_NEVER_AUTO`; gate HIGH_RISK; bridge silme blok | Engine enforce **gap** |
| 9 | **Güvenlik/kimlik/anahtar işlemi** | `require_stronger_auth` / `deny` | `action_policy` consent; `LockState` | Guard→identity tek kapı değil; **trust** sinyali |
| 10 | **Üretim config değişikliği** | `deny` / `ask_confirmation` | `SECURITY_NEVER_AUTO`; `change_sensitivity` CRITICAL | Intent sınıflandırması yok |
| 11 | **Kullanıcı özel verisi (PII)** | `log_only` / `defer_to_private_layer` | Public boundary kuralı | PII tespiti yok |

Kategori ataması kullanıcı override, profil sınırları (**permission**) ve onay kuralları (**confirmation**) altındadır (`lumos-karar-sozlesmesi`).

---

## Guard karar tipleri (kabul edilmiş hedef sözleşme — 7 tip)

Aşağıdaki karar tipleri **kabul edilmiş guard hedef sözleşmesidir** (ADR-010 `guard` tanımı ile uyumlu); repo'da birleşik enum veya modül olarak tanımlı değildir.

| Karar | Anlam | ADR-010 ilişkisi | Mevcut repo karşılığı (usage map) | Tam karşılık |
|-------|-------|------------------|-----------------------------------|--------------|
| **allow** | Güvenli; yürüt | Guard çıktısı | `lumos_gate` allow; `may_execute_step_at_runtime` True | Kısmen |
| **ask_confirmation** | Kullanıcı onayı bekle | **confirmation** | `pending_approval`, `task_dispatch` risk kuyrukları | Evet (köprü/görev); CLI formel değil |
| **require_stronger_auth** | Kilit, passphrase, consent | **elevated confirmation** | `action_policy` consent; kilidi aç komutu | Kısmen — trust sinyali karışımı |
| **sandbox_only** | Yalnız tanımlı sandbox | **sandbox** ≠ private layer | `controlled_bridge`, `write_interceptor` sandbox_mode | Kısmen |
| **deny** | Durdur | **locked ≠ denied** (ADR-010) | `no_op`, `is_allowed_for_profile` False, `surface_blocked` | Dağınık |
| **log_only** | Yürütme yok, kayıt | Guard audit | `guard_audit`, `write_interceptor` log | Audit var; firewall-wide sözleşme yok |
| **defer_to_private_layer** | Public'te açma | **private_layer_required** (ADR-007) | `STEP_TYPE_EXTERNAL`; bridge mail/shell blok | Politika düzeyinde |

**Not:** `lumos_gate` kendi içinde `agent | direct_patch | no_op` + `risk_level` + `execution_mode` kullanır; bu, 7'li guard sözlüğünün **alt kümesi**dir. `require_stronger_auth` trust/kilit sinyalleriyle örtüşür — guard kararı trust durumunu **tüketmeli**, yerine geçmemelidir (ADR-010).

---

## Terminoloji uyumu (ADR-010)

Bu ADR'de geçen kavramlar ADR-010 zorunlu ayrımlarına tabidir:

| Ayrım | Guard katmanı bağlamı |
|-------|----------------------|
| **guard ≠ trust** | Guard yürütme öncesi karar; `LockState`, consent, presence **trust** sinyalleridir — guard katmanları merkezi tüketim yapmıyor |
| **policy ≠ permission** | `action_policy` / profil matrisi **policy**; `may_execute_step_at_runtime` **permission** |
| **consent ≠ confirmation** | Keystore/identity rızası ≠ `pending_approval` tek adım onayı |
| **sandbox_only ≠ defer_to_private_layer** | Sandbox demo-safe workspace; private layer prod mail/ödeme/cihaz |
| **locked ≠ denied** | Kilit açılabilir durum ≠ guard/policy nihai red |
| **panel görünürlüğü ≠ runtime enforcement** | Panel durumu guard kararını garanti etmez |

Tam sözlük: [ADR-010](ADR-010-guard-policy-trust-terminology.md). Giriş noktası haritası: [usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md).

---

## Mevcut repo karşılığı vs gap (özet — usage map doğrulandı)

### Var olan parçalar (canonical — ADR-003)

| Bileşen | Konum | Guard'a katkı (ADR-010) |
|---------|-------|-------------------------|
| Gate | `lumos_gate.py` | **guard** — LLM plan; `classify_risk`; high→**confirmation** |
| Dispatch | `task_dispatch.py` | **guard** — task_type; `pending_approval` |
| Yetki matrisi | `profiles.py` | **policy** + **permission** |
| Minimal politika | `action_policy.py` | **policy**; **consent** kuralları |
| Path hassasiyeti | `change_sensitivity.py` | **guard** — gate'ten kopuk |
| Write interceptor | `write_interceptor.py` | **guard** + **sandbox** |
| Workspace contract | `workspace_contract.py` | **guard** sink'leri |
| Kontrollü köprü | `controlled_bridge.py` | **guard** + **sandbox** |
| Güvenlik çekirdeği | `src/security/*` | **trust** sinyalleri (guard değil) |

### Kritik gap'ler (usage map doğrulandı)

1. **Birleşik AI Firewall modülü yok** — parçalı guard'lar çelişebilir.
2. **`lumos_gate` ↔ `change_sensitivity` bağlantısı yok** — CRITICAL path + düşük gate riski mümkün.
3. **`classify_risk` sezgisel ve dar** — keyword tabanlı.
4. **`SECURITY_NEVER_AUTO` runtime'da tam enforce değil** — engine branch eksik (ADR-010 drift tablosu).
5. **Trust sinyalleri guard tarafından merkezi tüketilmiyor** — ADR-007 hedef.
6. **Tüm entrypoint'ler aynı guard zincirini kullanmıyor** — CLI, köprü, task engine, demo hattı ayrı.
7. **`packages/kando_policy` ayna drift** — canonical `src/policy` (ADR-003).

---

## Public / private sınır

Bu depo Lumos'un **public açık kaynak temelidir** (`public-github-boundary`). ADR-006:

| Public repo'da kalabilir | Private / professional katmanda kalır |
|--------------------------|----------------------------------------|
| Risk sınıflandırma **hedef sözleşmesi** ve onay kuralı dokümantasyonu | Gerçek production auth, SSO, prod key yönetimi |
| `profiles.py` davranış referansı (değiştirmeden) | Ücretli model tier, maliyet routing |
| Gate pattern açıklaması (`lumos_gate`) | PII işleyen routing kuralları |
| Basit keyword/heuristic risk (`classify_risk` seviyesinde) | Mail prod aksiyonları |
| Offline stub, controlled bridge **sandbox** tanımı | Ödeme, domain satın alma, cihaz orkestrasyonu |
| Usage map ve ADR karar kayıtları (kabul edilmiş) | Operasyonel backend, prod orchestration |

Public repo'da parçalı guard'ların **"tam AI Firewall ürünü"** gibi sunulması bilinçli olarak yapılmamalıdır.

---

## Guard / policy kullanım kararları

Usage map bulgularına dayalı **guard terminoloji seçimleri** (kod değişikliği yok; ADR-010 ile uyumlu):

| Kavram | Kabul edilen kullanım | Kaçınılacak karışım |
|--------|----------------------|---------------------|
| **AI Firewall / guard** | Yürütme öncesi koruyucu katman toplamı; modül adı olarak `lumos_gate`, interceptor, contract guard | Trust durumu, lock veya birleşik motor varsayımı |
| **firewall kararı** | 7 tip hedef sözleşme (`allow` … `defer_to_private_layer`) | Trust durumu (`locked`, `consent_required`) ile aynı enum |
| **risk kategorisi** | 11 kategori hedef sınıflandırma | Birleşik skor veya tek modül iddiası |
| **onay** | **confirmation** (işlem bazlı) veya **elevated confirmation** (passphrase, genel onay) | **consent** (kalıcı rıza) ile birleştirme |

**Zincir gerçeği:** Giriş noktaları doğrusal değil; gate allow + profil deny mümkün. Guard terminolojisi bu parçalılığı gizlemez.

---

## Karar

1. **Mevcut gerçek (doğrulandı):** Birleşik AI Firewall yok; guard davranışı `lumos_gate`, `task_dispatch`, `profiles`, `action_policy`, `change_sensitivity`, `write_interceptor`, `workspace_contract`, `controlled_bridge` ve ilgili katmanlarda **parçalıdır**; katmanlar kısmen örtüşür; zincir doğrusal değil.
2. **Kabul edilen hedef sözleşme:** Yukarıdaki beş guard rolü, 11 risk kategorisi ve 7 guard karar tipi — ADR-010 terminolojisi ile hizalı **referans guard sözleşmesi** olarak kullanılır.
3. **Terminoloji (ADR-010):** Guard terimleri ADR-010 sözlüğüne tabidir; guard ≠ trust; policy ≠ permission; consent ≠ confirmation; sandbox_only ≠ defer_to_private_layer.
4. **Öncelik sırası:** Guard (AI Firewall) → Trust (ADR-007) → Router (ADR-004) → Memory → Agent Network.
5. **Canonical katmanlar (ADR-003):** Policy → `src/policy`; trust sinyalleri → `src/security`; guard giriş noktaları canonical katmanları bypass etmemelidir.
6. **Router ilişkisi (ADR-004):** Router guard sinyallerini **kullanmalı**; guard router'ın yerine **geçmemelidir**.
7. **Bu ADR kod değiştirmez** — birleşik motor, lock semantiği birleştirme ve engine enforce **ayrı checkpoint**.

Kaynak: [`docs/analysis/ADR-010-guard-policy-trust-usage-map.md`](../analysis/ADR-010-guard-policy-trust-usage-map.md) (checkpoint tamamlandı, 2026-06-21).

---

## Takip checkpoint'leri (bu ADR dışı)

| Checkpoint | Neden ayrı | Bu ADR'de yapılan |
|------------|------------|-------------------|
| Birleşik AI Firewall modülü | Parçalı guard önce sözleşme; motor regresyon riski | Hedef rol + 7 karar tipi kayıtlı |
| Lock semantiği (`_lock_ok` vs `LockState`) | Trust sinyali; ürün/kod kararı gerekir | ADR-010 drift referansı |
| ADR-007 finalize | Trust engine hedef durumları | guard ≠ trust ayrımı |
| `SECURITY_NEVER_AUTO` enforce gap | Engine branch eksik | Risk tablosu + gap kaydı |
| Gate–sensitivity birleştirme | Import/kod kararı | Kopukluk doğrulandı |
| `packages/kando_policy` import drift | ADR-003 canonical | Terminoloji etkilenmez |

---

## Mevcut guard/policy/trust kullanım haritası

Haziran 2026 repo taraması (2026-06-21) — **salt okuma analizi**; tam tablolar, import zinciri ve drift doğrulaması:

→ **[ADR-010 guard/policy/trust usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md)**

Özet: birleşik guard/trust motoru yok; guard en yoğun terim; gate + profil + policy parçalı zincir; gate–sensitivity kopukluğu doğrulandı.

---

## Ne yapılmamalı (bu ADR kapsamında)

| Yapılmaması gereken | Gerekçe |
|---------------------|---------|
| Kod yazma (firewall birleştirme, yeni modül) | Sözleşme kayıtlı; motor ayrı checkpoint |
| Yeni güvenlik motoru | Parçalı guard önce enforce edilmeli |
| Production auth / mail prod / ödeme / cihaz | Public sınır |
| Trust engine veya guard birleştirme | ADR-007 + ayrı onay |
| Terimleri tek enum'a zorla map etme | Birleşik motor yok; parçalı repo gerçeği |
| Guard = trust varsayımı | ADR-010 zorunlu ayrım |

---

## Riskler (usage map doğrulandı)

| Risk | Not |
|------|-----|
| Parçalı guard çelişkisi | Gate allow + profil deny mümkün |
| Erken birleştirme / yeni motor | CI/regresyon; onay modeli karmaşıklaşması |
| `classify_risk` yanlış pozitif/negatif | Keyword tabanlı |
| Gate–sensitivity kopukluğu | CRITICAL path + düşük gate riski |
| `SECURITY_NEVER_AUTO` tam enforce eksik | Sözleşme vs engine gap |
| Guard–trust karışımı | Lock/consent guard kararı sanılabilir — ADR-010 ayrımı |
| Public sınır sızıntısı | Prod auth/PII/mail public'e taşınması |
| Router guard'sız ilerleme | ADR-001 sırasına aykırı |

---

## Sonuç

Haziran 2026 repo analizi ve usage map (2026-06-21) sonrasında Lumos'ta **birleşik AI Firewall bulunmamaktadır**. Guard davranışı parçalıdır; **11 risk kategorisi** ve **7 guard karar tipi** ADR-010 terminolojisi ile hizalı **kabul edilmiş hedef sözleşme** olarak kayıtlıdır. ADR-001 sırasına göre guard Router'dan **önce** temel güvenlik katmanıdır. Guard ≠ trust; birleşik motor kurulumu ve engine enforce **takip checkpoint'lerindedir**; bu ADR kod değiştirmez.

## Sonraki gözden geçirme

- ADR-007 finalize — trust engine hedef durumları; ADR-010 + ADR-006 guard ayrımı
- Lock semantiği birleştirme — **ayrı ADR veya checkpoint**
- `SECURITY_NEVER_AUTO` enforce gap — engine branch (kod değişikliği ayrı iş)
- Gate–sensitivity hizalama — dar import/kod kararı ayrı onay
- ADR-004 router finalize — guard sinyali tüketimi
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
