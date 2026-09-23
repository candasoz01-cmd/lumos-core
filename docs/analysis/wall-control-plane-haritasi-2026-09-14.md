# Lumos Wall — Control Plane Envanter Haritası

> **Kapsam notu (2026-09-14):** Bu belge bir durum tespitidir; karar veya kod izni değildir.
> Taranan kaynaklar: `lumos-core` `origin/main` @ `f17b995`, `candasoz01-cmd/Lumos` (dizin: `Lumos-main`)
> `origin/main` @ `98eeb68`, `lumos-ios` (dizin: `Lumos`) çalışma kopyası, ve lumos-core'un
> merge edilmemiş uzak dalları. Yerel `main` origin'in 15 commit gerisindedir; tüm "main"
> iddiaları `origin/main`'e göredir. Bulgular hızla bayatlar; kullanmadan önce yeniden doğrulanmalıdır.

> **Tazeleme (2026-09-23):** Harita `lumos-core` `origin/main` @ `adcd505` karşısında yeniden
> doğrulandı. İki değişiklik kaydedildi: **(1)** katman 5'in sandbox kodu `#840` ile main'e indi,
> **(2)** canonical teknik borç kaydından TD-25…TD-32 düşmüş ve iki numara yeniden kullanılmıştır
> (çapraz bulgu 7). Tazeleme yalnız durum tespitidir; TD kayıtlarının geri taşınması ve
> numaralandırması bu belgenin işi **değildir** — ayrı iş: `candasoz01-cmd/lumos-core#882`.

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
| 1 | Kimlik | **KISMİ** + KARAR VAR / KOD YOK | Kimlik beyana dayalı (self-asserted, TD-10 bilinçli sınır); çok-özne modeli ADR-024 Accepted ama "kod izni değil" |
| 2 | Görev sahipliği | **VAR** (kayıtlı kusurla) | `task_claim.py` main'de, 28 testli, sahada canlı kullanılmış; `list_claims()` salt-okuma değil (kusur kayıtlı, düzeltme dalda) |
| 3 | Yetki | **KISMİ** | ADR-031 grant motoru kodlu + testli (opt-in); ADR-027 tek-yazıcı Accepted/uygulanmadı; `granted_by` aktör doğrulaması dalda, main'de `None` |
| 4 | Onay | **KISMİ** | Dört ayrı katmanda dağınık çalışan parçalar (ADR-028, Decision Gate, confirmation_policy, v2 durumları); tek onay omurgası yok; Decision Queue görünümü yazılmadı |
| 5 | Çalıştırma | **VAR** (sandbox) + KARAR VAR | Bilinçli tasarım: Wall kaydeder, yürütmez (`gates.py`). Observer sandbox ADR-033 Accepted; **sandbox kodu 2026-09-22'de main'e indi** (`#840`); ölçüm probe'u main'de |
| 6 | Gözlem | **KISMİ** / KOD DALDA | Durum raporlama (agent-status v1+v2 okuyucu) main'de; gözlem sözleşmesi main'de; `wall_observer.py` bilinçli merge dışı (#832) |
| 7 | Güvenlik sınırı | **KISMİ** | Sır maskeleme + sızıntı guard'ı + fail-closed sürüm reddi main'de; sandbox env-blocklist dalda; "gözlemci yetki sınırı DEĞİLDİR" uyarısı kayıtlı |
| 8 | Audit / Kanıt | **KISMİ** | Append-only audit (claim+gateway) ve SHA-bağlı attestation main'de; fail-closed audit-IO ve attestation log sertleştirmeleri dalda |
| 9 | Devir | **KISMİ** | İmzalı delegation token main'de; ADR-008 HANDOFF kaydı vizyon notu (karar değil); bağlam taşıyan devir protokolü yok |
| 10 | Kullanıcı kontrolü | **KISMİ** + **EKSİK** uç | Single-reader gateway main'de ama hiçbir production yolu çağırmıyor; görünürlük dilimi dalda (TD-31 blokajı); HTTP Wall okuma ucu hiç yazılmadı |
| 11 | Kurtarma / Geri alma | **EKSİK** (dar parçalar hariç) | Stale takeover, HMAC override, INVALID izolasyonu gibi noktasal parçalar var; sistematik geri alma omurgası için ne karar ne kod var |

---

## Katman detayları

### 1. Kimlik — kim konuşuyor?
- **Karar:** ADR-024 çok-özne kimlik modeli (insan/Lumos/cihaz/agent/servis) — Accepted 2026-08-17; belge açıkça "kod izni değildir" der.
- **Uygulama:** Claim sahibi kimliği beyana dayalıdır; `task-claim-v1.md` §Güven sınırı bunu TD-10 olarak bilinçli açık sınır kaydeder. Doğrulanmış ajan kimliği yok.
- **Dalda:** `granted_by` güvenilir-aktör doğrulaması `origin/cursor/f7-granted-by-trusted-actor-830d` (`src/policy/confirmation_policy.py` + `tests/test_granted_by_actor.py`); main'de `confirmation_policy.py:229` `granted_by`'ı `None` başlatır.

### 2. Görev sahipliği — işi kim aldı?
- **Uygulama (main):** `src/lumos_board/task_claim.py` (935 sat.) — atomik claim/lease (`flock` + atomic rename), TTL/heartbeat, QUEUED kuyruk + otomatik promotion, HMAC-SHA256 imzalı manuel override, append-only audit. CLI: `src/lumos_board/claim_cli.py`; `AGENTS.md` bunu zorunlu iş akışı yapar.
- **Test:** `tests/test_lumos_board_task_claim.py` (764 sat., 28 test). TD-04 kapanış kanıtı: gerçek çok-ajanlı kullanım. Canlı veri: `Lumos/.lumos/board/claims.json` + `claim_events.jsonl` (son olay 2026-09-13).
- **Kayıtlı kusur:** `list_claims()` gerçekte salt-okuma değil — `_locked_state()` çıkışta state + audit yazar, exclusive lock tutar (`task_claim.py:629-652`; #832'de keşfedildi). Düzeltme `origin/cursor/claim-list-readonly` dalında (+96 sat. test): `candasoz01-cmd/lumos-core#833` · OPEN (draft) · `ec7f3df2080b2f38b941422df45cc74e3d69cd17` · GitHub API · 2026-09-23. Kusur `origin/main` @ `adcd505`'te hâlâ canlıdır (`task_claim.py:629-652`).
- **Sözleşme:** `docs/contracts/task-claim-v1.md` (13 normatif kural).

### 3. Yetki — ne yapabilir?
- **Karar:** ADR-027 tek-yazıcı çekirdek (Accepted, uygulanmadı; bugünkü fiili hali "GitHub merge + geçici insan kapısı"). ADR-029 earned responsibility. ADR-030 görev ayrılığı.
- **Uygulama (main):** `src/policy/task_execution_grant.py` (1185 sat., ADR-031: Task Registry + Capability Token + Immutable Ledger; testli, opt-in). `src/dashboard_health/responsibility.json` tek gerçek grant kaydı (`granted_by: "founder"`, `delegable: false`, `self_expand_authority` denied).
- **Dalda:** `granted_by` aktör doğrulaması (bkz. katman 1).
- **Boşluk:** Grant motoru var ama Wall katmanlarıyla (claim, status, gateway) tek yetki modeli altında birleşmiş değil; her parça kendi sınırını kendi taşıyor.

### 4. Onay — insan kapısı nerede?
Dört ayrı yerde, birbirine referanslı ama tek omurga yok:
- **İlke (karar):** ADR-008 §Karar ilkeleri #4 `SECURITY_NEVER_AUTO` (taslak); #8 "karşılıklı denetim, sıfır kontrol" (yatay AI→AI komut yok).
- **Yetki (karar + yürürlük):** ADR-028 standing low-risk merge onayı — Accepted ve yürürlükte; yüksek risk insan kapısında kalır.
- **Uygulama (Lumos repo main):** `.lumos/wall/gates.py` Decision Gate — `MERGE/DEPLOY/SPEND/EXTERNAL_MSG/DELETE` eylemleri, `PENDING/APPROVED/REJECTED`; docstring: "kararı KAYDEDER, eylemi YÜRÜTMEZ"; `SINGLE_APPROVER = "cando"`. Testler: `tests/test_command_wall_m2_gates.py` vd. M2.4 (record+queue) worktree'de, merge edilmedi.
- **Uygulama (lumos-core main):** `src/policy/confirmation_policy.py` + panel onay testleri; agent-status v2 `awaiting_decision`/`decision_ref` okuyucusu (bkz. katman 6).
- **Boşluk:** OD-063 Decision Queue görünümü decision-approved / implementation-authorized (minimal, 2026-08-25) ama görünüm yazılmadı; elle işleyen karşılığı `Lumos-main/docs/ops/karar-kuyrugu.md`.

### 5. Çalıştırma — eylemi kim, hangi kafeste koşturur?
- **Bilinçli tasarım kararı:** Wall v0 eylem yürütmez; Decision Gate kayıt katmanıdır (subprocess yok, merge/deploy tetiklenmez). Bu bir eksik değil, kayıtlı sınırdır.
- **Karar (main):** ADR-033 observer sandbox — Accepted 2026-09-05; "runtime sandbox yok" durumunu ve motor kararını (A=sandbox) kaydeder; #832 head'i merge adayı değildir der. `docs/contracts/agent-wall-observer-sandbox-v0.md` (v0.1'de ölçümle motor kararı).
- **Uygulama (main):** yalnız ölçüm aracı — `scripts/wall_sandbox_capability_probe.py` (392 sat., fail-closed kanıt; PR #838) + `tests/test_agent_wall_observer_sandbox_contract.py` (12 test).
- **Uygulama (main, 2026-09-22):** `src/lumos_board/observer_sandbox.py` (1118 sat., bubblewrap, credential env-blocklist: `SSH_/AWS_/GH_/OPENAI_/ANTHROPIC_...`, cgroup-v2 enforcement, seccomp keyring kapatma) + `tests/test_observer_sandbox.py` (1909 sat.) — `candasoz01-cmd/lumos-core#840` · MERGED · `adcd505` · GitHub API · 2026-09-23. 2026-09-14 envanterinde "dalda bekliyor" olarak kayıtlıydı; artık ürün gerçeğidir.
- **Açık dilim:** modül macOS'ta import edilemiyordu (`ctypes` `AttributeError`); düzeltme `candasoz01-cmd/lumos-core#881` · OPEN · `6041a2b5350ee054e0100d1d4dcd95ca93088492` · GitHub API · 2026-09-23. Linux davranışını değiştirmez.

### 6. Gözlem — ne oluyor, kim bekliyor?
- **Karar (main):** `docs/contracts/agent-wall-observation-v1.md` (PR #831) — S1 OUT_OF_SCOPE/FOREIGN_SCOPE, S2 SILENT_DRIFT, S3 STALE_CLAIM; beyan vs türetilmiş sinyal ayrımı; çıktı `.lumos/logs/wall_observations.jsonl`. Belge, uygulamanın ayrı dilim olduğunu açıkça yazar.
- **Uygulama (main):** `src/lumos_board/agent_status.py` (305 sat., salt-okunur projeksiyon, sır maskeleme, stale sinyali; 11 test) + `src/core/agent_status_contract.py` (330 sat., v1+v2 okuyucu; v2 durumları `blocked`/`awaiting_decision` + `wait_reason`/`decision_ref`; 14+22 test, doküman↔kod iki yönlü türetme testi dahil; PR #804).
- **Dalda (bilinçli):** `src/lumos_board/wall_observer.py` (833 sat.) + `tests/test_wall_observer.py` (917 sat.) — `origin/codex/agent-wall-observer-faz1`; ADR-033 gereği merge adayı değil. Modül docstring'i kalıcı riski kaydeder: "gözlemci bir yetki sınırı DEĞİLDİR" (`.gitattributes` clean-filter üzerinden kod çalıştırma riski ölçülmüş).
- **Bitişik:** ADR-032 Shadow Watch Accepted (2026-09-02), kernel kodu `src/security/shadow_watch.py` var, gate bağlantısı yok; Board lease soyunu (`claim_id`/`parent_claim_id`) korelasyon sinyali olarak tanımlar.
- **Tetikleyici kanıt:** ADR-008 §Gözlem (2026-08-24): altı oturumun üçü insan onayı bekliyordu ve hiçbir kaynak bunu göstermiyordu → OD-063'ün saha gerekçesi.

### 7. Güvenlik sınırı — kapsam dışına çıktı mı?
- **Uygulama (main):** sır maskeleme (`agent_status.mask_secretlike`, gateway regex'leri); kullanıcı-yüzeyi sızıntı guard'ı `tests/test_user_surface_no_internal_fields.test.mjs` (`agent_id`/`session_id`/`workspace_path` kullanıcıya sızmaz — "yalnız Agent Wall görür"); sözleşme sürümlerinde fail-closed red (bilinmeyen versiyon reddedilir); panel consent kapıları (`8d10bcd`, `b03f476`).
- **Dalda:** sandbox env-blocklist (katman 5); audit-IO fail-closed (katman 8).
- **Kayıtlı sınır:** gözlem katmanı güvenlik sınırı sayılmaz (wall_observer docstring'i) — güvenlik sınırı iddiası yalnız sandbox + yetki katmanı birleşince kurulabilir; bu birleşim henüz yok.

### 8. Audit / Kanıt — "tamamlandı"yı ne destekliyor?
- **Uygulama (main):** task_claim append-only audit (`lumos.task_claim_event.v1`); gateway audit şeması + rollback izi; `src/standing_merge/classify.py` `SemanticAttestation` — SHA'ya bağlı insan attestation'ı, head SHA eşleşmezse düşer, hard-exclusion asla attestation'la terfi etmez (fail-closed); `.github/workflows/standing-class.yml` üç katmanlı trust root (Incident #777/TD-20 sonrası).
- **Dalda:** fail-closed audit-IO (`origin/cursor/f8-audit-io-fail-closed-830d`) ve append-only attestation log (`origin/cursor/f9-standing-attest-record-830d`) — merge edilmedi.
- **Boşluk:** "Tamamlandı" iddiasını dış kanıta (test koşumu, canlı uç, merge SHA) bağlayan tek tip kanıt alanı Wall şemalarında yok; agent-status v2 `decision_ref` yalnız bekleme tarafını tipler.

### 9. Devir — iş el değiştirince ne kaybolur?
- **Uygulama (main):** `task_claim.py` `DelegationVerifier` (imzalı delegation token, `lumos.delegation_token.v1`) — alt-görev devri claim seviyesinde çalışır ve testlidir. Lumos repo'da `tests/test_agent_wall_sandbox_mvp_handoff.py`.
- **Karar değil, vizyon:** ADR-008 `TYPE: HANDOFF` kayıt tipi ve Handoff Notları kategorisi §Board=Ortak Durum bölümünde — bu bölüm "vizyon notu, kasten commit edilmemiş karar" etiketlidir.
- **Boşluk:** Devirde bağlam+sorumluluk taşıyan protokol (ne biliniyordu, ne bekliyor, kim onaylayacak) yok; bugün devir = claim'in el değiştirmesi.

### 10. Kullanıcı kontrolü — kullanıcı ne görür, neye onay verir?
- **Karar (kilitli, kanonik):** `Lumos/docs/canonical/decisions.md` §Orkestrasyon yüzeyi — üç seviye: Yürütme (gizli) / Durum / Karar; Seviye 3 yalnız dış etki + geri alınabilirlik (`[Yayınla]`/`[Beklet]`); Sade Mod varsayılan. Agent Wall'un iç operatör yüzeyi olmasının kanonik gerekçesi (ADR-019/OD-062 ile tutarlı).
- **Uygulama (main, çağrılmıyor):** `src/lumos_board/coordination_gateway.py` (541 sat., 14 test) — tek-okuyucu kapısı: ajanlar kullanıcıya doğrudan konuşmaz, olay yazar; token-backed reader lease özetler. **Hiçbir production yolu çağırmıyor** (TD-04 notu) → kod var, ürün gerçeği yok.
- **Uygulama (Lumos repo main):** `.lumos/wall/lumos_wall.py` + `index.html` — salt-okunur operatör paneli (stdlib, port 8321); M1 frozen şema `agent-session-status m1/1.0.0`.
- **Dalda:** `src/lumos_board/wall.py` (303 sat., `WallState` WORKING/WAITING/BLOCKED/NEEDS_DECISION, salt-okunur CLI özeti) — #807, TD-31 ADR numara çakışması yüzünden bloke (`ADR-025` iki ayrı belgeye verilmiş).
- **EKSİK:** HTTP Wall okuma ucu hiç yazılmadı. `docs/contracts/wall-surface-portability-v1.md` (main, PR #836) bunu tanımlar ("Wall tek mantıksal yüzeydir, sözleşmesi HTTP API'dir"; adaptörlere dosya erişimi/`lumos_board` import'u/subprocess yasak) ve araç adaptörlerinden önce yazılmasını şart koşar; ADR'si de yok (TD-31/TD-32 blokajı; 2026-09-23 itibarıyla bu iki TD kaydının kendisi de main'de yok — çapraz bulgu 7).

### 11. Kurtarma / Geri alma — yanlış gidince ne olur?
- **Noktasal parçalar (main):** gateway stale-reader takeover + audit-rollback izi; task_claim HMAC imzalı manuel override (`OVERRIDDEN` durumu); session_store INVALID izolasyonu (Lumos repo).
- **Karar yok, kod yok:** "Bu eylem geri alınabilir mi, nasıl geri alınır, kim geri alır" sorusunu Wall seviyesinde cevaplayan şema, sözleşme veya ADR bulunamadı. Kanonik yüzey kararı (Seviye 3) geri alınabilirliği onay ölçütü yapar ama geri alma mekanizması tanımsız.

---

## Çapraz bulgular

1. **İsim çatallanması (karar kaydı gerekebilir):** ADR-008 koordinasyon **veri katmanına** resmi ad olarak `Lumos Board` verir (Command Wall reddedilmiş, 2026-07-16). ADR-019 + `00-command-wall.md` **operatör yüzeyine** `Lumos Agent Wall` der (Command Wall emekli, 2026-08-08). İki karar iki farklı bileşene ait ve çelişmiyor; ama gündelik dilde "Wall" ikisini birden karşılıyor. Frozen teknik adlar (`.lumos/wall/`, `LUMOS_COMMAND_WALL_STATE_DIR`, `test_command_wall_*`) ADR-018 gereği eski adı taşımaya devam ediyor.
2. **Doküman–kod drift'i (doğrulanmış):** `docs/contracts/agent-status-v2.md` origin/main'de hâlâ "Kod yazılmadı / Kod karşılığı: Yok" der; oysa v2 okuyucu kodu ve türeme testleri PR #804 ile main'dedir (#803 dokümanı #804 koddan önce merge olmuş, sonra güncellenmemiş). Sözleşmenin kendi kuralı: ayrışmada kod esas alınır, doküman güncellenir.
3. **Yerel çalışma kopyaları geride:** yerel `main` origin'in 15 commit gerisinde; bu envanter sırasında bir keşif hattı bu yüzden ADR-033'ü "main'de yok" sanmıştı. Tüm Wall değerlendirmeleri `origin/main`'e karşı yapılmalı.
4. **Repo/dizin adlandırması:** `work_2026/Lumos` dizini `lumos-ios` remote'una bakar; kanonik `candasoz01-cmd/Lumos` `work_2026/Lumos-main` dizinindedir. Canlı Board verisi (`.lumos/board/`, son olay 2026-09-13) lumos-ios dizininde durmaktadır.
5. **Merge blokajlarının ikisi de süreçsel:** TD-31/TD-32 ADR numara çakışması (#807 görünürlük dilimi bunun arkasında); içerik reddi değil. **Tazeleme (2026-09-23):** bu iki kaydın kendisi de artık `origin/main`'de yoktur (çapraz bulgu 7) — yani blokajın gerekçesi canonical kayıttan düşmüş, blokaj sürmektedir.
6. **Dalda bekleyen güvenlik/gözlem kütlesi:** `wall_observer.py` (833+917 sat.), claim-list-readonly düzeltmesi (`#833`), f7/f8/f9 sertleştirmeleri, OD-064 rol ilkesi (`#841`), WebMCP dilimleri (`#834`/`#835`) — hâlâ dalda, ürün gerçeği değil; bir kısmı (observer) ADR-033 gereği **bilinçli** dışarıda. **Tazeleme (2026-09-23):** `observer_sandbox.py` bu kütleden çıktı (`#840` merge edildi, katman 5).

7. **Canonical teknik borç kaydı delinmiş (doğrulanmış, yeni):** `docs/TECHNICAL_DEBT.md` AGENTS.md'ye göre canonical kaynaktır. `ed9ca2f` (2026-09-04, `origin/main`'in doğrulanmış atası — `git merge-base --is-ancestor` ile teyitli) **TD-01…TD-32** içeriyordu; bugünkü `origin/main` @ `adcd505` **TD-01…TD-26** içeriyor. Düşüren commit `73d6f58` (2026-09-11, *"revert(devpost): restore submitted state except approved security fixes"*). Ardından **TD-25 ve TD-26 numaraları başka konulara yeniden atanmıştır** (bugün TD-25 = ADR-033 Account Activity Correlation, TD-26 = `run_lumos_gate` unknown-risk kapısı), yani aynı kimlik iki farklı borcu işaret etmektedir. Üç somut sonuç: **(a)** `#807`'nin merge-blocker gerekçesi (TD-31) canonical kayıtta yok; **(b)** `#834`/`#835` artık var olmayan TD-27/TD-28 satırlarını düzenledikleri için `mergeable_state: dirty` ve doğrudan merge edilemiyor — ikisi de salt doküman değil, `main`'de karşılığı sıfır olan kod + test taşıyor; **(c)** ölçülmüş bilinçli sınırlar (eski TD-25 replay ayrışması, eski TD-29 duvar-saati sınırı) kayıtsız kaldı. Geri taşıma ve numara tahsisi ayrı iştir: `candasoz01-cmd/lumos-core#882`.

## Haritadan okunan gerçek boşluklar (EKSİK sınıfı)

- HTTP Wall okuma ucu (katman 10) — sözleşme main'de, tek satır kod yok; portability sözleşmesi araç adaptörlerinden önce bunu şart koşuyor.
- Geri alma omurgası (katman 11) — ne karar ne kod.
- Tek onay omurgası (katman 4) — parçalar dört yerde; Decision Queue görünümü yetkili ama yazılmamış.
- Doğrulanmış ajan kimliği (katman 1) — TD-10 bilinçli açık; ADR-024 kapıyı açar, kod izni vermez.
- Bağlam taşıyan devir protokolü (katman 9).
- "Tamamlandı" iddiasını dış kanıta bağlayan tek tip kanıt alanı (katman 8).
