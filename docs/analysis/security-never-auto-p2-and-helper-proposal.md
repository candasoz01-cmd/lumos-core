# SECURITY_NEVER_AUTO — P2 task engine analizi, helper önerisi, action_risk akışı

| Alan | Değer |
|------|-------|
| Durum | **Güncellendi** — engine branch **merge** #463 (dar kapsam); helper uygulandı; tam küme eşlemesi açık |
| Tarih | 2026-06-21 (sync: post-#463) |
| Referans | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [branch scan](lumos-security-never-auto-branch-scan.md), `src/task_engine/profiles.py`, `src/task_engine/engine.py` |
| Kapsam | Öneri + gap haritası; **engine branch merge #463** (dar: `permanent_delete` store/panel; step tag eşlemesi sınırlı) |

## Özet

`SECURITY_NEVER_AUTO` dört üyeli sözleşme kümesi (`permanent_delete`, `external_write`, `irreversible_user_op`, `critical_system_config`) `profiles.py` ve `inviolable.py` içinde sabit. P0/P1 panel yolları #444–#446 ile kapandı. **P2 engine branch merge #463 (dar kapsam):** `TaskEngine.run_task` içinde küme üyeleri için branch + `is_security_never_auto()` / `get_security_never_auto_member()` helper; **`permanent_delete` engine dışı** (store/panel yolu). `external`/`critical` step türleri matris üzerinden duruyor; üç üyenin tam step kind/action policy eşlemesi **hâlâ sınırlı**. Bu belge hook noktalarını, merge edilen davranışı, helper API'sini ve kalan gap'leri kaydeder.

---

## Bölüm 1 — P2: TaskEngine `run_task` branch analizi

### 1.1 Küme tanımı (kaynak)

```47:52:src/task_engine/profiles.py
SECURITY_NEVER_AUTO = frozenset({
    "permanent_delete",      # kalıcı silme
    "external_write",        # dış servislere kontrolsüz yazma
    "irreversible_user_op",  # kullanıcı adına geri dönüşsüz işlem
    "critical_system_config", # kritik sistem ayarı değişikliği
})
```

Bu stringler **step `kind` değildir**; sözleşme / inviolable sabitleridir. `STEP_PERMISSION_MATRIX` yalnızca `analyze`, `read`, `plan`, `safe_local`, `write_local`, `external`, `critical` türlerini bilir.

### 1.2 Bugün ne enforce ediliyor?

| Üye | Mevcut koruma | Yeterlilik |
|-----|---------------|------------|
| `permanent_delete` | `TaskStore.delete()` → `may_perform_permanent_delete(user_initiated)`; panel `delete-permanent` #445 | Store/CLI/panel yolu; engine adım executor'ına map yok |
| `external_write` | Dolaylı: `STEP_TYPE_EXTERNAL` → `DECISION_LAYER_NEVER`; `ActionRegistry` external/critical red; offline_engine | Step `kind=external` ile sınırlı; ayrı `external_write` action/kind yok |
| `irreversible_user_op` | Dolaylı: `STEP_TYPE_CRITICAL` never layer; bridge/cursor yüksek risk gate (ayrı modül) | Sözleşme terimi engine'de lookup yok |
| `critical_system_config` | Dolaylı: `critical` step + `change_sensitivity` CRITICAL etiket (gate kopuk) | Config intent sınıflandırması yok |

**`run_task` guard zinciri (merge #463):**

```479:486:src/task_engine/engine.py
    def _is_step_allowed_runtime(self, step: TaskStep) -> bool:
        return may_execute_step_at_runtime(
            self.permission_profile, step.kind, self.general_approval
        )
```

`may_execute_step_at_runtime` → profil matrisi. **Ek:** `run_task` döngüsünde `_step_security_never_auto_member(step)` → küme üyesi ise `BLOCK_SECURITY_NEVER_AUTO` ile durdurma (`permanent_delete` engine scope dışı).

**Helper (merge #463):** `is_security_never_auto()` / `get_security_never_auto_member()` — `profiles.py`; `include_permanent_delete=False` engine branch için.

**ActionRegistry savunması** (executor seviyesi):

```60:62:src/task_engine/action_registry.py
        if kind in (STEP_TYPE_EXTERNAL, STEP_TYPE_CRITICAL):
            return False, "", "Bu adım türü yürütülmez (güvenlik).", False
```

### 1.3 Olası hook noktaları (kalan gap)

| Konum | Ne yapılabilir (gelecek) | Risk |
|-------|---------------------------|------|
| `engine.py` `_is_step_allowed_runtime` | Step metadata / action tag → `is_security_never_auto(tag)` red | ~~Yanlış tag → false positive~~ → helper merge #463; matris ile çift guard izlenmeli |
| `engine.py` `run_task` döngüsü (L512 öncesi) | Ayrı `SECURITY_NEVER_AUTO` branch + `EVENT_POLICY_BLOCKED` + `block_reason=security_never_auto` | **Merge #463** — dar kapsam; `permanent_delete` hariç |
| `engine.py` `_execute_step` / `ActionRegistry.execute` | Executor kaydı öncesi action alanı kontrolü | Eylem alanı × step kind drift |
| `profiles.py` yeni step türleri | `external_write` vb. için ayrı `STEP_TYPE_*` | Matris + inviolable + test genişlemesi; breaking change |
| `action_policy.py` | Yeni action sabitleri (`EXTERNAL_WRITE`, …) panel/CLI gate | Policy katmanı genişler; profil matrisinden bağımsız ikinci kaynak |

**Dar merge (#463) kapsamı:** Engine branch yalnızca `step.kind` / `step.action_key` ile küme üyesi eşleşen adımları durdurur; `permanent_delete` store/panel yolunda kalır. Tam küme × action eşlemesi **açık**.

### 1.4 Gap özeti (P2 — post-#463)

- Engine branch **merge** #463 — `external_write`, `irreversible_user_op`, `critical_system_config` step tag eşleşince durdurulur; `permanent_delete` engine dışı.
- Tam küme × action policy / step kind resmi eşleme tablosu **açık**; helper erken eşleşmeyen yollar hâlâ risk taşır.
- CLI `general_approval` ↔ policy `consent` semantik karışımı → **Kapandı** #450+#451

---

## Bölüm 2 — `is_security_never_auto()` helper (merge #463)

### 2.1 Lookup API — uygulandı (`profiles.py`)

```python
# MERGE #463 — src/task_engine/profiles.py

def is_security_never_auto(
    *,
    step_kind: str | None = None,
    action_key: str | None = None,
    action_tag: str | None = None,
    policy_action: str | None = None,
    include_permanent_delete: bool = True,
) -> bool:
    ...

def get_security_never_auto_member(...) -> str | None:
    """Engine branch: include_permanent_delete=False."""
```

**Eşleme tablosu (kısmi — tam policy eşlemesi açık):**

| Girdi türü | Örnek değer | Küme üyesi |
|------------|-------------|------------|
| `step_kind` | `critical` | dolaylı (never layer; küme üyesi değil) |
| `action_tag` | `permanent_delete` | doğrudan |
| `policy_action` | (henüz yok) | gelecek: `permanent_delete_task` vb. |

### 2.2 Call site'lar (bugün)

| Call site | Amaç | Durum |
|-----------|------|-------|
| `TaskEngine._step_security_never_auto_member` | Engine branch red | **Merge #463** |
| `TaskStore.delete` | Tek satır sözleşme assert | `may_perform_permanent_delete` |
| `panel_tasks_server` kalıcı silme | Policy + küme birleşik mesaj | #445 `check_policy` + confirm |
| `action_policy.check_policy` | Yeni action → küme | Hardcoded action list — **açık** |
| `write_interceptor` / bridge | Dış yazma tag | Regex + risk gate (cursor_bridge) — **açık** |
| Test / `inviolable.verify_core_constants` | Küme bütünlüğü | `test_security_never_auto_engine.py` (#463) |

### 2.3 Dar merge sınırları (#463)

1. **`permanent_delete` engine dışı** — kalıcı silme yalnızca `TaskStore.delete(user_initiated=True)` ve panel onaylı endpoint (#445).
2. **Step tag eşlemesi sınırlı** — küme üyesi string'i `step.kind` veya `step.action_key` ile birebir eşleşmeli; resmi action×küme tablosu açık.
3. **Geniş enforcement** (policy katmanı, bridge, sensitivity zinciri) — ayrı onay; bu PR'da **yok**.

---

## Bölüm 3 — action_risk akışı: rapor → onay → kod yolu (ADR-012)

ADR-012 C3 ve `lumos-karar-sozlesmesi.md` karar katmanları ile runtime yolların karşılaştırması.

### 3.1 Hedef zincir (codex)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Rapor/      │ ──► │ Öneri/plan   │ ──► │ Kullanıcı onayı │ ──► │ Kod yürütme  │
│ analiz      │     │ (taslak)     │     │ (açık/genel)    │     │ (profil içi) │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
     rapor              plan/suggest      genel onay /            safe_local /
     analyze/read       öner ama bekle    passphrase /            write_local
                                           açık komut              (kisitli_otonom)
                                                                    ───────────► ASLA: external,
                                                                                 critical,
                                                                                 SECURITY_NEVER_AUTO
```

### 3.2 Mevcut kod yolu (bugün)

| Aşama | Codex katmanı | Kod girişi | Enforcement |
|-------|---------------|------------|-------------|
| **Rapor** | Sadece cevap / analiz | CLI `durum`, `gorevler`; profil `rapor`; step `analyze`/`read` | ✓ `may_execute_step_at_runtime` izinli |
| **Öneri** | Öner ama bekle | step `plan`; Brain pending intent | ✓ Uygulama adımı yok; write_local genel onay kapalıyken durur |
| **Onay** | Açık onayla uygula | `general_approval`; session_consent (#451); panel `/lumos-consent`; confirmation opt-in (#453–#458) | ~~CLI consent=GA drift~~ → **Kapandı** #450; panel policy+profil #443–#449 |
| **Kod yolu** | Uygulama | `TaskEngine.run_task` → `_execute_step` → `ActionRegistry` | ✓ Profil matrisi + registry external/critical red |
| **Asla** | SECURITY_NEVER_AUTO | `TaskStore.delete(user_initiated)`; panel delete-permanent #445; engine branch #463 (dar) | Kısmi — tam küme eşlemesi açık |

**Policy katmanı (eylem düzeyi, step kind'dan bağımsız):**

| Action | Gate | Dosya |
|--------|------|-------|
| `create_task` … `cancel_task` | offline red | `action_policy.check_policy` |
| `delete_task` | koruma+delete red | aynı |
| Panel mutasyonları | `task_action_gate` → `check_policy` | `panel_bridge_state.py` (#443+) |

### 3.3 Desired vs current (ADR-012)

| Beklenti (ADR-012) | Bugün | Gap |
|--------------------|-------|-----|
| Rapor profili hiç uygulama yapmaz | ✓ Matris | — |
| Genel onay olmadan write_local yok | ✓ Engine guard + panel profil (#449) | — |
| Panel = CLI policy zinciri | ✓ #443–#458 | Confirmation opt-in; LockState env vekili |
| Riskli işlemde dur + kanıt | ✓ `EVENT_POLICY_BLOCKED`, evidence | Trust motor (ADR-007) eksik |
| SECURITY_NEVER_AUTO tüm yollar | Parçalı | Engine branch **merge #463** (dar); tam eşleme açık |
| action_risk sınıflandırması birleşik | Dağınık | cursor_bridge risk_level; action_policy risk yok; tek `action_risk` modülü **yok** |

**Not:** Repoda `action_risk` adlı sembol yok. Codex anlamında **action_risk flow** = karar katmanları + policy + profil matrisi + (gelecek) birleşik risk etiketi. Hedef: ADR-007 trust sinyalleri + ADR-006 firewall tablosu ile birleşik `action_risk` sınıfı — **Faz 4**, bu turda uygulanmaz.

### 3.4 Sonraki adımlar (onay sınıflandırması)

1. ~~`lumos-action-permission-matrix.md` panel satırını #443–#446 ile güncelle~~ — yapıldı.
2. Tam küme × action eşleme tablosu docs kilidi — **ONAY GEREKİYOR** (davranış genişlemesi riski).
3. Policy/bridge call site'larına helper — **ONAY GEREKİYOR** (enforcement expansion).
4. Trust Faz 4 / `action_risk` — **ONAY GEREKİYOR**; bu turda başlatılmaz.

---

## İlgili belgeler

- [lumos-security-never-auto-branch-scan.md](lumos-security-never-auto-branch-scan.md) — P0/P1 kapandı (#444–#446)
- [lumos-runtime-enforcement-map.md](lumos-runtime-enforcement-map.md) — panel gate güncellendi
- [ADR-012](../decisions/ADR-012-lumos-security-codex.md) — checkpoint tablosu

## Disiplin

Engine branch + helper **merge #463** (dar kapsam). Trust motor, panel LockState, tam küme policy eşlemesi ve köprü wiring **dokunulmadı** — ayrı checkpoint.
