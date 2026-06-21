# ADR-012: Lumos Security Codex

| Alan | Değer |
|------|-------|
| Durum | **Kabul edildi** (2026-06-21) — taslak paket #440; panel şeffaflık #441; panel policy enforcement #443 |
| Tarih | 2026-06-21 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, [ADR-010](ADR-010-guard-policy-trust-terminology.md), [ADR-011](ADR-011-lock-semantics-decision.md), [action permission matrix](../analysis/lumos-action-permission-matrix.md), [runtime enforcement map](../analysis/lumos-runtime-enforcement-map.md) |

## Amaç

Lumos'un **tek dış yüz** (external facade) olarak davranması, iç katmanlara doğrudan dış komut gitmemesi ve riskli işlemlerde **dur-kanıt-onay** zincirinin resmi sözleşmesini kaydetmek.

Bu belge **dokümantasyon sözleşmesidir**; uygulama haritası: [runtime enforcement map](../analysis/lumos-runtime-enforcement-map.md). İlk kod adımları [next PR plan](../analysis/lumos-security-codex-next-pr-plan.md) ile planlandı.

**Public OSS sınırı:** Bu codex yalnızca açık kaynak Lumos çekirdeğini kapsar; ticari/özel orkestrasyon, üretim sırları veya operasyonel backend detayı **içermez**.

---

## 1. Lumos tek dış kapı (single external gate / facade)

**Kural:** Dış dünya (panel, CLI kullanıcı girişi, HTTP köprü, üçüncü taraf entegrasyon) yalnızca **Lumos yüzeyi** üzerinden sisteme etki eder. İç motorlar (task engine, memory, policy, security) **doğrudan dış komut almaz**.

| Kavram | Anlam |
|--------|-------|
| **Dış yüz** | CLI router, panel read/write köprüsü, tanımlı HTTP endpoint'leri |
| **İç katman** | `task_engine`, `core/state`, `security/*`, `policy/*`, workspace state |
| **Köprü** | Panel → `panel_tasks_server` → `.lumos/` state; reasoning gate (`lumos_gate`) ile sınırlı yürütme |

**Hedef:** Tüm etkili işlem tek izlenebilir zincirden geçer; bypass yolu dokümante edilmedikçe kabul edilmez.

**Repo notu:** Panel sunucusu (`panel/scripts/panel_tasks_server.py`) aynı origin'de statik UI + API sunar; enforcement parçalıdır — panel görev mutasyonları `check_policy` ile hizalanıyor (bkz. enforcement map § Panel, PR #442).

---

## 2. İç katmanlara doğrudan dış komut yok

**Kural:** Dış istemci veya ajan, iç modüllere (ör. doğrudan `TaskEngine.run_task`, `FileKeyStore`, çekirdek state dosyası) **atlamalı komut** gönderemez.

| Yasak örnek | İzinli yol |
|-------------|------------|
| Ham shell → `tasks/tasks.json` yazma | CLI `görev oluştur` veya panel POST `/tasks` (policy + evidence zinciri) |
| LLM çıktısının doğrudan dosyaya yazılması | `write_interceptor` / patch pipeline / profil guard |
| Panel butonunun policy atlaması | `check_policy` + profil matrisi + kullanıcı onayı |

**İstisna (demo/OSS):** Salt okuma (`panel_bridge_state`, `GET /lumos-read-state`) iç katmanı **okur**, **yazmaz**.

---

## 3. Kullanıcı onayı, amaç sınırı, kanıt zorunluluğu

Üçlü sözleşme — `docs/lumos-karar-sozlesmesi.md` ile hizalı:

### 3.1 Kullanıcı onayı (user approval)

| Katman | Davranış |
|--------|----------|
| **Analiz / rapor** (`rapor`) | Okuma, plan, öneri — onay gerekmez |
| **Güvenli yürüt** (`guvenli_yurut`) | Yerel güvenli adımlar (`safe_local`) — genel onaydan bağımsız |
| **Kısıtlı otonom** (`kisitli_otonom`) | `write_local` yalnızca **genel onay açıkken** |
| **Asla** | `external`, `critical`, `SECURITY_NEVER_AUTO` — profil/onaydan bağımsız yasak |

Kaynak: `src/task_engine/profiles.py` — `is_allowed_for_profile`, `may_execute_step_at_runtime`.

### 3.2 Amaç sınırı (purpose boundary)

- İşlem, kullanıcının **açık talebi** veya onaylı görev kapsamıyla sınırlıdır.
- Belirsiz veya kapsam dışı niyet → **öneri / dur**; boşluk doldurma yok.
- Online modda `live_brain` pending intent / clarification akışı bu sınırı korur.

### 3.3 Kanıt zorunluluğu (evidence requirement)

- Policy blokları loglanır: `policy/action_policy.py` → `log_policy_blocked`, evidence journal.
- Guard olayları: `guard_audit`, `evidence_continuity`.
- Görev/adım sonuçları `result_kind` ile işaretlenir (`tamamlandi`, `simulasyon`, `dogrulanamadi`, …).
- **Teşhis kuralı:** Log/kanıt okunmadan kök neden iddiası yasaktır (operasyonel disiplin).

---

## 4. Mock vs gerçek çıktı ayrımı

**Kural:** Simülasyon, demo veya doğrulanamayan çıktı **gerçek başarı gibi sunulmaz**.

| Sinyal | Anlam |
|--------|-------|
| `simulasyon` | Adım/görev çalıştı; gerçek doğrulama yok |
| `dogrulanamadi` | Yürütme oldu; kanıt üretilemedi |
| `tamamlandi` | Doğrulanabilir adım kanıtlandı |
| Panel mock alanları | Görünürlük/demo — enforcement değil (ADR-010, ADR-011) |

**UI/CLI:** Durum etiketleri kullanıcıya **gerçek/simüle** ayrımını göstermeli; "çalışıyor gibi" ifade codex'e aykırıdır.

**Repo:** `TaskEngine.run_task` doğrulama yoksa `tamamlandi` yerine `simulasyon`/`dogrulanamadi` atar (`task_engine/engine.py`).

---

## 5. Silme ve çöp (trash / deleted items)

**Kural:** Kalıcı silme **otomatik yapılmaz**. Silinen öğeler yalnızca sözleşmeli **`.lumos/trash/`** altına taşınır.

| İlke | Uygulama |
|------|----------|
| Tek çöp hedefi | `workspace_contract.LUMOS_TRASH_DIRNAME = "trash"` |
| Trash kaynak değil | Okuma/kaynak olarak `trash/` kullanılmaz (arşiv/geri yükleme hariç) |
| Kalıcı silme | Yalnızca `user_initiated=True` + açık kullanıcı komutu (`may_perform_permanent_delete`) |
| `SECURITY_NEVER_AUTO` | `permanent_delete` profil matrisinde **asla** |

Panel: `panel_tasks_server` silinen görevleri `trash/*.json` dosyalarına yazar; `GET /tasks/trash` disk çöpünü listeler.

---

## 6. Riskli işlemde dur (stop-on-risk)

**Kural:** Risk sinyali (yüksek hassasiyet, belirsiz hedef, koruma kilidi, offline mod, consent eksikliği, `external`/`critical` adım) → **dur**, kullanıcıya net neden göster, onaysız devam etme.

| Sinyal | Beklenen davranış |
|--------|-------------------|
| `koruma_active` + `delete_task` | Policy red (`action_policy`) |
| Offline mod | Görev mutasyonu red |
| Consent yok | Identity/keystore erişim red |
| Profil dışı adım | `TASK_STOPPED`, `EVENT_POLICY_BLOCKED` |
| LLM gate risk | `mode=no_op` veya `agent` — doğrudan patch yok (`lumos_gate` prompt sözleşmesi) |
| Sandbox + core path | `CoreWriteForbidden` |

**Codex ilkesi:** "Hazır girmişken düzeltelim" veya sessiz kapsam genişletme **yasak**.

---

## Codex maddeleri — özet tablo

| # | Madde | Kısa ifade |
|---|-------|------------|
| C1 | Tek dış kapı | Lumos yüzeyi dışında etkili komut yok |
| C2 | İç bypass yok | İç modüllere doğrudan dış yazma/komut yok |
| C3 | Onay + amaç + kanıt | Profil matrisi, genel onay, evidence/log |
| C4 | Mock ayrımı | `simulasyon` ≠ `tamamlandi`; demo etiketli |
| C5 | Trash kuralı | Tek `trash/`; kalıcı silme kullanıcı komutu |
| C6 | Stop-on-risk | Risk sinyalinde dur; onaysız devam yok |

---

## İlişkili analiz belgeleri

| Belge | İçerik |
|-------|--------|
| [lumos-action-permission-matrix.md](../analysis/lumos-action-permission-matrix.md) | Eylem alanı × izin seviyesi matrisi |
| [lumos-runtime-enforcement-map.md](../analysis/lumos-runtime-enforcement-map.md) | Repo'da bugün ne enforce ediliyor / gap |
| [lumos-security-codex-next-pr-plan.md](../analysis/lumos-security-codex-next-pr-plan.md) | Minimal uygulama PR planı |
| [security-never-auto-p2-and-helper-proposal.md](../analysis/security-never-auto-p2-and-helper-proposal.md) | P2 engine gap, helper taslağı, action_risk akışı (analyze-only) |

---

## Takip checkpoint'leri

| Checkpoint | Durum |
|------------|-------|
| ADR-012 taslak paket (codex + companion analizler) | **Tamamlandı** — #440 (2026-06-21) |
| Panel şeffaflık — gate reason + UI codex uyarısı | **Tamamlandı** — #441 (2026-06-21) |
| Panel policy enforcement (`check_policy`, gate `enabled`) | **Tamamlandı** — #443 |
| Panel `PUT /tasks.json` policy gate | **Tamamlandı** — #444 |
| Panel `POST /tasks/delete-permanent` policy + confirm | **Tamamlandı** — #445 |
| Panel `POST /tasks/restore` CREATE_TASK gate | **Tamamlandı** — #446 |
| `SECURITY_NEVER_AUTO` tüm silme/yazma yolları | **P2 gap** — engine branch; analiz: [security-never-auto-p2-and-helper-proposal.md](../analysis/security-never-auto-p2-and-helper-proposal.md) |
| Trust motor (ADR-007) kanıt zinciri genişletmesi | Bekliyor — Faz 4 |

---

## Açık sorular (kabul sonrası)

1. `SECURITY_NEVER_AUTO` tam runtime branch'i tüm silme/yazma yollarında var mı? (enforcement map gap — bilinçli takip)
2. Trust motor (ADR-007) finalize olunca codex C3 kanıt zinciri genişletilecek mi? (Faz 4 checkpoint)
3. Panel `PUT /tasks.json` tam doküman yazımı policy zincirine bağlanacak mı? → **Evet** — #444 (`CREATE_TASK` gate). Kalıcı silme (#445) ve restore (#446) aynı checkpoint'te kapandı.

---

## Durum geçişi

| Aşama | Koşul |
|-------|-------|
| **Taslak** | Belge + companion analizler (#440) |
| **İnceleme** | Gap'ler kapatma planı onayı |
| **Kabul** (2026-06-21) | Codex paketi merge; panel şeffaflık merge; enforcement planı PR #2 ile yürürlükte |

---

## Sonuç

Lumos Security Codex (C1–C6) resmi sözleşme olarak kayıt altına alındı. İlk uygulama: docs paketi (#440), panel codex şeffaflığı (#441), panel görev mutasyonlarında `check_policy` hizalaması (#442). Tam trust motor ve `SECURITY_NEVER_AUTO` tüm yollar **bilinçli sonraki checkpoint'ler**; bu ADR kod refactor veya kapsam genişletmesi talep etmez.
