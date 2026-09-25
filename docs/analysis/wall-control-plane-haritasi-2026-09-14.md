# Lumos Wall — Control Plane Envanter Haritası

> **Kapsam notu (yeniden üretim, 2026-09-25):** Bu belge bir durum tespitidir; karar veya kod
> izni değildir. Harita `lumos-core` `origin/main` @ `c259221` (#887 merge'ü) karşısında
> **baştan** yeniden üretildi; her iddia bu SHA'daki dosya varlığına, `git log` kaydına veya
> GitHub API'deki PR durumuna (2026-09-25) dayanır. `candasoz01-cmd/Lumos` ve `lumos-ios`
> depoları bu üretimin kapsamı dışındadır; onlar hakkında yeni hüküm verilmez (bkz. §Kapsam dışı).
> Bulgular hızla bayatlar; kullanmadan önce yeniden doğrulanmalıdır.

## Tarihçe (kısa)

- **2026-09-14** — İlk harita `origin/main` @ `f17b995` karşısında çıkarıldı.
- **2026-09-23** — `adcd505` karşısında tazelendi: katman 5'e `#840` işlendi, canonical TD
  kaydındaki kayıp (TD-25…TD-32) çapraz bulgu olarak eklendi.
- **2026-09-25** — Bu yeniden üretim. 23 Eylül tazelemesinin `adcd505`'te bile doğru
  olmayan satırları vardı: `#832` (observer) 2026-09-21'de, F7/F8/F9 (`#845`/`#844`/`#847`)
  2026-09-20'de zaten `main`'deydi; `src/security/shadow_watch.py` 2026-09-11'de silinmişti.
  Ders: "dalda" iddiası, ilgili SHA'da dosya varlığı kontrol edilmeden yazılmamalı.

## Durum sözlüğü

| Etiket | Anlam |
|---|---|
| **VAR** | `origin/main`'de çalışan, testli kod; katman görevini bugün karşılıyor |
| **KISMİ** | Parça(lar) main'de var ama katmanın control-plane görevini tek başına karşılamıyor |
| **DALDA BEKLİYOR** | Kod + test yazılmış ama merge edilmemiş; ürün gerçeği sayılmaz |
| **KARAR VAR / KOD YOK** | ADR/sözleşme main'de, uygulaması hiç yazılmamış |
| **EKSİK** | Ne karar ne kod; gerçek boşluk |

Bir katmanda birden çok etiket olabilir: karar durumu ve uygulama durumu her zaman ayrı satırlarda verilir.

---

## Ana tablo — 11 işlev katmanı

| # | Katman | Durum | Tek satır özet |
|---|---|---|---|
| 1 | Kimlik | **KISMİ** + KARAR VAR / KOD YOK | Claim kimliği beyana dayalı (TD-10 bilinçli sınır); ADR-024 çok-özne modeli Accepted, kod izni değil. Onay tarafında `granted_by` artık güvenilir aktörden (`#845`) |
| 2 | Görev sahipliği | **VAR** (kayıtlı kusurla) | `task_claim.py` + `claim_cli` main'de; Duvar v1 bunu tek yazma kapısı olarak kilitledi (ADR-032). `list_claims()` salt-okuma değil; düzeltme `#833` hâlâ açık draft |
| 3 | Yetki | **KISMİ** | ADR-031 grant motoru main'de, opt-in (TD-41); ADR-027 tek-yazıcı Accepted/uygulanmadı; `granted_by` doğrulaması main'de (`#845`) |
| 4 | Onay | **KISMİ** | Onay kayıt deposu v1 main'de (`founder_approval.py` + `claim_cli approval`, `#867`); imza kökü / CheckRun yok; ADR-028 standing ve `confirmation_policy` ayrı parçalar; tek onay omurgası yok |
| 5 | Çalıştırma | **VAR** (sandbox kodu) + KARAR VAR | `observer_sandbox.py` main'de (`#840`, macOS import `#881`). ADR-034 (Accepted 2026-09-21) eski sandbox kararını supersede eder: sandbox artık ana sınır değil, defense-in-depth; birincil yön git subprocess'i azaltmak |
| 6 | Gözlem | **KISMİ** | `wall_observer.py` main'de (`#832`, index git'siz okuma `#876`) ama hiçbir `src/`·`scripts/`·`panel/` yolu çağırmıyor; agent-status v1+v2 okuyucu main'de |
| 7 | Güvenlik sınırı | **KISMİ** | Sır maskeleme, kullanıcı-yüzeyi sızıntı guard'ı, sandbox env-blocklist (`#840`) ve audit-IO fail-closed (`#844`) main'de; gözlemci kendini "OS sandbox'ı değildir" diye tanımlar |
| 8 | Audit / Kanıt | **KISMİ** (belirgin genişledi) | Claim audit + SHA-bağlı attestation + append-only attestation log (`#847`); kanıt günlüğü artık segment silmiyor, before-kaydı yazılamazsa mutasyon durur, silinen içerik arşivlenir (`#886`); bridge paket geçmişi korunur (`#887`). "Tamamlandı"yı dış kanıta bağlayan tek tip alan yok |
| 9 | Devir | **KISMİ** | İmzalı delegation token (claim seviyesi) + doğrulanmış Git bundle teslimi (`scripts/verified_handoff.py`, `#886`); bağlam/sorumluluk taşıyan devir protokolü yok |
| 10 | Kullanıcı kontrolü | **KISMİ** + **EKSİK** uç | Single-reader gateway main'de ama production yolu çağırmıyor (TD-04); Duvar v1 "ekran yok"; HTTP Wall okuma ucu yok ve onu tanımlayan sözleşme de artık main'de değil |
| 11 | Kurtarma / Geri alma | **EKSİK** (dar parçalar hariç) | Stale takeover, HMAC override ve purge yolu olmayan silme arşivi (`#886`) var; sistematik geri alma omurgası için ne karar ne kod var; `#888` açık |

---

## Katman detayları

### 1. Kimlik — kim konuşuyor?
- **Karar:** ADR-024 çok-özne kimlik modeli — Accepted; belge "kod izni değildir" der.
- **Uygulama:** Claim sahibi kimliği beyana dayalıdır; `docs/TECHNICAL_DEBT.md` TD-10 bunu bilinçli v1 güven sınırı olarak kaydeder. Doğrulanmış ajan kimliği yok.
- **Değişen (2026-09-20):** Onay kayıtlarında `granted_by` artık istek gövdesinden değil, güvenilir aktör sabitlerinden gelir (`src/policy/confirmation_policy.py`, `tests/test_granted_by_actor.py`) — `candasoz01-cmd/lumos-core#845` · MERGED. Bu onay kaydının kaynağını sabitler; ajan kimliğini doğrulamaz.

### 2. Görev sahipliği — işi kim aldı?
- **Uygulama (main):** `src/lumos_board/task_claim.py` (935 sat.) + `claim_cli.py` — atomik claim/lease, TTL/heartbeat, QUEUED kuyruk, HMAC imzalı override, append-only audit. Test: `tests/test_lumos_board_task_claim.py` (764 sat.).
- **Sözleşme:** `docs/contracts/task-claim-v1.md`; üstünde `docs/contracts/lumos-wall-v1.md` + ADR-032 (Accepted 2026-09-19): "`claim_cli` tek yetkili yazma/claim kapısıdır; Duvar claim durumunu tüketir ve gösterir, ayrı claim üretmez."
- **Kayıtlı kusur:** `list_claims()` `_locked_state()` üzerinden exclusive lock alır ve state yazar (`task_claim.py:629-652`). Düzeltme `candasoz01-cmd/lumos-core#833` · OPEN (draft) · GitHub API · 2026-09-25.

### 3. Yetki — ne yapabilir?
- **Karar:** ADR-027 tek-yazıcı çekirdek — Accepted (mimari), **uygulanmadı**; bugünkü fiili hal GitHub merge + geçici insan kapısı. ADR-029, ADR-030 çerçeve kararları.
- **Uygulama (main):** `src/policy/task_execution_grant.py` (1185 sat., ADR-031) — opt-in, varsayılan kapalı (TD-41). `src/dashboard_health/responsibility.json` grant kaydı.
- **Boşluk:** Grant motoru, claim, onay deposu ve gateway tek yetki modeli altında birleşmiş değil.

### 4. Onay — insan kapısı nerede?
- **Yetki (karar + yürürlük):** ADR-028 standing low-risk merge onayı; yüksek risk insan kapısında kalır.
- **Uygulama (main, yeni):** `src/lumos_board/founder_approval.py` (334 sat.) + `claim_cli approval` — altı alanlı onay kaydı (`approval_id`, `task`, `gate`, `action`, `head_sha`, `approved_by`) — `candasoz01-cmd/lumos-core#867` · MERGED (2026-09-20). Duvar v1 eşleme tablosu: imza kökü ve CheckRun yok; override HMAC'i ayrı mekanizma.
- **Uygulama (main):** `src/policy/confirmation_policy.py` (onay politikası; `granted_by` bkz. katman 1); agent-status v2 `awaiting_decision` / `decision_ref` okuyucusu (katman 6).
- **Boşluk:** Onay parçaları hâlâ ayrı yerlerde; Duvar v1 madde 7 "otomatik `FOUNDER_REVIEW` tetikleyicisi yok" der (KISMİ). Bu üretimde `lumos-core`'da bir Decision Queue görünümü bulunmadı.

### 5. Çalıştırma — eylemi kim, hangi kafeste koşturur?
- **Tasarım sınırı:** Duvar kaydeder ve gösterir; eylem yürütmez (`lumos-wall-v1.md` §Teknik kilit).
- **Karar (main):** ADR-034 — Accepted 2026-09-21: eski "A — sandbox birincil sınır" kararını supersede eder. Birincil yön: git subprocess kullanımını kademeli kaldırıp `.git/index` + doğrudan okuma. Mevcut jail defense-in-depth olarak kalır; Linux `bwrap` yeniden ölçülmeden zorunlu ana sınır ilan edilmez; TOCTOU açık risk. ADR-034 "Uygulama durumu: Yok — kod izni değildir" der; ilk dilim (index okuma) `#876` ile indi (katman 6).
- **Uygulama (main):** `src/lumos_board/observer_sandbox.py` (1124 sat.) + `tests/test_observer_sandbox.py` — `candasoz01-cmd/lumos-core#840` · MERGED (2026-09-22); macOS import düzeltmesi `#881` · MERGED (2026-09-23).
- **Silinenler:** Eski ADR-033 (sandbox) metni, `docs/contracts/agent-wall-observer-sandbox-v0.md` ve `scripts/wall_sandbox_capability_probe.py` `73d6f58` (2026-09-11) ile main'den çıktı. Bugünkü ADR-033 başka bir konudur (çapraz bulgu 3).

### 6. Gözlem — ne oluyor, kim bekliyor?
- **Sözleşme (main):** `docs/contracts/agent-wall-observation-v1.md` — S1 OUT_OF_SCOPE/FOREIGN_SCOPE, S2 SILENT_DRIFT, S3 STALE_CLAIM; beyan vs türetilmiş sinyal ayrımı.
- **Uygulama (main):** `src/lumos_board/wall_observer.py` (1082 sat.) + `tests/test_wall_observer.py` — `candasoz01-cmd/lumos-core#832` · MERGED (2026-09-21); index'i git çağırmadan okuma `#876` · MERGED (2026-09-21), desteklenmeyen biçimde fail-closed.
- **Uygulama (main):** `src/lumos_board/agent_status.py` (salt-okunur projeksiyon) + `src/core/agent_status_contract.py` (v1+v2 okuyucu, `#804`).
- **Boşluk:** `wall_observer` modülünü `src/`, `scripts/` veya `panel/` altında çağıran bir yol yok; gözlem kodu var, çalışan gözlem hattı yok.

### 7. Güvenlik sınırı — kapsam dışına çıktı mı?
- **Uygulama (main):** sır maskeleme (`agent_status`, gateway); kullanıcı-yüzeyi sızıntı guard'ı `tests/test_user_surface_no_internal_fields.test.mjs`; sözleşme sürümlerinde fail-closed red; sandbox credential env-blocklist (`#840`); audit I/O hatasında fail-closed (`#844`, `tests/test_audit_io_fail_closed.py`).
- **Kayıtlı sınır:** `wall_observer.py` docstring'i: "Bu gözlemci bir işletim sistemi sandbox'ı değildir; eşzamanlı depo mutasyonlarına karşı izolasyon sağlamaz." ADR-034 de sandbox'ı ana sınır saymaz. Güvenlik sınırı iddiası hâlâ kurulamaz.

### 8. Audit / Kanıt — "tamamlandı"yı ne destekliyor?
- **Uygulama (main):** task_claim append-only audit; gateway audit izi; `src/standing_merge/classify.py` SHA-bağlı attestation + `attestation_log.py` append-only kayıt (`#847`, F9); audit-IO fail-closed (`#844`, F8).
- **Uygulama (main, 2026-09-25):** `#886` — `src/lumos_board/evidence_policy.py` (paylaşılan saklama politikası; değerlendirme silme yürütmez), `src/core/evidence_settings.py` (`evidence_archive/`, purge yolu yok), `src/core/evidence_continuity.py` (sınırlı rotasyonla segment silme kaldırıldı), `src/core/trash_evidence.py` (çöp taşımada manifest + doğrulama). Before-kaydı yazılamazsa panel/görev yazımı durur. `#887` — `src/core/bridge_evidence.py`: bridge özetleri değiştirilmeden önce saklanır.
- **Açık:** `candasoz01-cmd/lumos-core#888` (doğrudan patch ve rollback geçmişini arşivde tutmak) · OPEN · 2026-09-25.
- **Boşluk:** Duvar v1 madde 5 "kanıt zorunluluğu" KISMİ: `attach_pr` var, commit/test/log kanıt alanı yok.

### 9. Devir — iş el değiştirince ne kaybolur?
- **Uygulama (main):** `task_claim.py` `DelegationVerifier` — imzalı delegation token ile alt-görev devri (claim seviyesi).
- **Uygulama (main, yeni):** `scripts/verified_handoff.py` (`pack` / `receive` / `check`, `#886`) — temiz HEAD'in Git bundle'ı, alıcı tarafında hash doğrulamalı geri yükleme makbuzu. Bu kod/depo teslimidir, bağlam teslimi değildir.
- **Boşluk:** Devirde bağlam + sorumluluk taşıyan protokol (ne biliniyordu, ne bekliyor, kim onaylayacak) yok.

### 10. Kullanıcı kontrolü — kullanıcı ne görür, neye onay verir?
- **Uygulama (main, çağrılmıyor):** `src/lumos_board/coordination_gateway.py` (541 sat.) — tek-okuyucu kapısı; production yolu çağırmıyor (TD-04 açık).
- **Karar (main):** Duvar v1 — "hukuk bu dilimde; ekran yok"; görsel Duvar ayrı onaylı sonraki dilim.
- **Kapanmış dal:** `wall.py` görünürlük dilimi — `#807` kapalı, dal duruyor; ADR numara çakışması TD-38'e kayıtlı.
- **Uygulama (main, dar):** `#886` ile panelde saklama ayarı (yalnız `customer` profilinde görünür; yeni silme kopyalarını kapatır, mevcut arşivi silmez).
- **EKSİK:** HTTP Wall okuma ucu yok. Onu tanımlayan `docs/contracts/wall-surface-portability-v1.md` (`#836`) `73d6f58` ile main'den silindi; bugün bu uç için main'de ne sözleşme ne kod var.

### 11. Kurtarma / Geri alma — yanlış gidince ne olur?
- **Noktasal parçalar (main):** gateway `READER_STALE_TAKEOVER`; task_claim HMAC imzalı manuel override (`OVERRIDDEN`); silinen içeriğin purge yolu olmayan arşivi ve doğrulanmış çöp taşıma (`#886`).
- **Karar yok, kod yok:** "Bu eylem geri alınabilir mi, nasıl, kim geri alır" sorusunu Wall seviyesinde cevaplayan şema, sözleşme veya ADR bulunamadı. `#888` rollback geçmişini korumaya yöneliktir; geri alma mekanizması değildir.

---

## Çapraz bulgular

1. **İsim çatallanması kapandı:** ADR-032 + `lumos-wall-v1.md`: "Duvar = Lumos Board'un iç operasyon yüzü"; katmanın resmi adı Lumos Board'dur (ADR-008), Duvar ikinci bir katman değildir.
2. **Doküman–kod drift'i (agent-status v2):** `docs/contracts/agent-status-v2.md` main'de hâlâ "Kod yazılmadı / Kod karşılığı: Yok" der; v2 okuyucu `#804` ile main'dedir. Bu PR belgeyi koda hizalar.
3. **ADR numaraları yeniden kullanılmış:** Eski haritadaki "ADR-032 Shadow Watch" ve "ADR-033 observer sandbox" bugün main'de yok. Bugün ADR-032 = Lumos Duvar v1, ADR-033 = Account Activity Correlation, ADR-034 = observer git yürütme bağlamı (eski sandbox kararını supersede eder). `73d6f58` (2026-09-11) ile silinenler: eski sandbox ADR'si, sandbox v0 sözleşmesi, capability probe betiği, wall-surface-portability sözleşmesi, `src/security/shadow_watch.py`. Numara tahsisinin kayıtsızlığı TD-39'da kayıtlı.
4. **Canonical TD kaydı onarıldı:** Kayıp TD-25…TD-32 `#885` ile TD-33…TD-41 olarak geri taşındı (eşleme `docs/TECHNICAL_DEBT.md` içinde): eski TD-31 → TD-38, eski TD-32 → TD-39 (numara tahsis mekanizması). Önceki haritanın çapraz bulgu 7'si artık açık bulgu değil, tarihçedir.
5. **Dalda bekleyenler (2026-09-25, GitHub API):** `#833` claim-list salt-okuma (draft), `#834` / `#835` WebMCP dilimleri (eski TD-28/TD-27 → bugün TD-36/TD-35), `#841` OD-064 rol ilkesi (draft), `#888` patch/rollback geçmişi. Observer, sandbox ve F7/F8/F9 artık dalda değildir.
6. **Kod var, hat yok:** Gözlem (`wall_observer`) ve kullanıcı kontrolü (`coordination_gateway`) katmanlarında modüller main'de, ama hiçbir production yolu çağırmıyor. Bu iki katman "KISMİ"de kalıyorsa sebep kodun yokluğu değil bağlantının yokluğudur.

## Haritadan okunan gerçek boşluklar (EKSİK sınıfı)

- HTTP Wall okuma ucu (katman 10) — kod yok; tanımlayan sözleşme de main'den silinmiş.
- Geri alma omurgası (katman 11) — ne karar ne kod.
- Tek onay omurgası (katman 4) — onay deposu v1 geldi ama imza kökü, CheckRun ve otomatik kurucu kapısı yok.
- Doğrulanmış ajan kimliği (katman 1) — TD-10 bilinçli açık; ADR-024 kod izni vermez.
- Bağlam taşıyan devir protokolü (katman 9).
- "Tamamlandı" iddiasını dış kanıta bağlayan tek tip kanıt alanı (katman 8, Duvar v1 madde 5).
- Gözlem ve gateway'in production'a bağlanması (katman 6 ve 10).

## Kapsam dışı

Önceki sürümler `candasoz01-cmd/Lumos` (Decision Gate, operatör paneli, oturum deposu) ve
`lumos-ios` çalışma kopyası hakkında da satırlar içeriyordu. Bu yeniden üretim o depoları
taramadı; oradaki bileşenlerin bugünkü durumu hakkında hüküm verilmez ve eski satırlar
doğrulanmış kabul edilmemelidir.
