# Consent vs General Approval Ayrımı — Teknik Taslak (Analiz Only)

| Alan | Değer |
|------|-------|
| Durum | **Kapandı** — merge #450 (policy/read ayrımı) + #451 (session_consent CLI) |
| Tarih | 2026-06-21 |
| İlgili | [ADR-010](../decisions/ADR-010-guard-policy-trust-terminology.md), [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [consent matrix draft](lumos-consent-and-panel-profile-matrix-draft.md) |

---

## 1. Eski durum (merge öncesi — tarihsel)

> **Not:** Aşağıdaki drift #450+#451 ile kapandı. Tarihsel kayıt olarak korunur.

Üç ayrı kavram kodda ve UI'da **aynı boolean veya aynı etiket** altında toplanmıştı: **consent**, **general_approval**, **confirmation**.

### CLI — en net karışım

`TaskMutationContext.general_approval` oturum listesi, policy katmanında doğrudan `consent` alanına yazılıyor (`cli_tasks_mutation._task_mutation_policy_context` L53–54).

`genel onay aç` / `genel onay kapat` yalnızca `general_approval[0]` değiştiriyor (`cli_router.py` L145–151); bu bayrak hem TaskEngine'e hem policy `consent`'e gidiyor.

Durum/hazır akışında aynı liste **session consent** olarak kullanılıyor (`cli_readonly._session_consent_from_ctx` → `general_approval` ref).

`startup_health.effective_consent` dosya **veya** oturum bayrağını birleştiriyor; oturum tarafı yorumda açıkça "genel onay aç".

**Testler bu karışımı regresyon olarak kilitlemiş:** `tests/test_consent_flow.py` — `genel onay aç` → `consent_ok=True`.

### Policy katmanı — tek `consent` alanı, çift anlam

`PolicyContext.consent` yalnızca `ACCESS_IDENTITY` / `ACCESS_KEYSTORE` için kullanılıyor (`action_policy.py` L62–63); CLI ise bu alana `general_approval` enjekte ediyor.

### Panel — kısmen ayrı, UI'da yine vekalet

Policy context: dosya tabanlı consent (`consent_ok(base)`). Profil guard: ayrı env `LUMOS_GENERAL_APPROVAL`.

UI/read payload yine karıştırıyor: `consent_proxy_state`, `display_note` "genel onay vekili"; `guidance.lock` consent'e göre `LOCKED`/`UNLOCKED`. `POST /lumos-consent` ise **consent.json** yazar — identity/keystore rızası, genel onay değil.

### Somut çelişki (bugün)

| Durum | consent.json | genel onay | CLI policy `consent` | Panel policy `consent` |
|-------|--------------|------------|----------------------|------------------------|
| B | yok | açık | **True** | False |
| C | var | kapalı | False | **True** |

Kaynak: `lumos-runtime-enforcement-map.md` L87 — ADR-010 drift.

---

## 2. Ayrım önerisi (ADR-010 hizalı tanımlar)

ADR-010 zorunlu ayrım: **consent ≠ confirmation ≠ general_approval**.

| Sinyal | Tanım | Repo hedef karşılığı |
|--------|--------|----------------------|
| **consent** | Identity, keystore, koruma alanı rızası | `consent.json` veya oturum `session_consent` — **general_approval'dan bağımsız** |
| **general_approval** | `kisitli_otonom` oturum yazma kapısı | `profiles.is_allowed_for_profile(..., general_approval)` — **consent yerine geçmez** |
| **confirmation** | Tek işlem / tek kapsam onayı (CU4) | **Merge** #453–#458 — `confirmation_policy`; opt-in |

**Hedef kurallar:**

1. consent yok → identity/keystore policy red.
2. general_approval yok + `kisitli_otonom` → write_local red.
3. general_approval var → CU4/CU7 için yeterli değil.
4. SECURITY_NEVER_AUTO → üç sinyalden bağımsız ⛔.

---

## 3. Etkilenecek dosyalar

| Dosya | Hedef değişiklik |
|-------|------------------|
| `src/policy/action_policy.py` | `PolicyContext` + isteğe bağlı `general_approval` |
| `src/cli/cli_tasks_mutation.py` | `consent` ← `effective_consent(base, session_consent)` |
| `src/core/panel_bridge_state.py` | `general_approval_active`, ayrı consent etiketleri |
| `src/core/startup_health.py` | `session_consent` ≠ genel onay docstring |
| `src/cli/cli_readonly.py` | `_session_consent_from_ctx` GA'dan ayrı |
| `src/core/lumos_runtime.py` | `session_consent` ref ayrı liste |
| `tests/test_consent_flow.py` | GA artık `consent_ok` yükseltmez |

Panel: `GET /lumos-read-state` → `guidance.general_approval_active`, `keystore.consent_ok` ayrı.

---

## 4. UI akışı (eski vs yeni)

### Eski

`genel onay aç` → durum/hazır "consent kayıtlı"; panel hâlâ "Consent alınmadı" (consent.json yok).

### Yeni

1. Consent akışı (kilit / `/lumos-consent`) → "Consent kayıtlı"; identity policy açılır.
2. `genel onay aç` → ayrı satır; durum consent satırını **değiştirmez**.
3. Dış etkili işlem → confirmation (CU4, gelecek).

Panel: consent kartı ≠ genel onay toggle (`LUMOS_GENERAL_APPROVAL`).

---

## 5. Enforcement noktaları (CU4, CU6, CU7)

| Sinyal | Kontrol noktası |
|--------|-----------------|
| consent (dosya) | `panel_bridge_state._panel_policy_context`, `build_panel_read_state` |
| consent (policy) | `action_policy.check_policy` identity/keystore |
| general_approval | `profiles`, `engine`, `panel task_action_gate` |
| CU4 | GA önkoşul; confirmation ayrı | **Merge** #453–#458 (opt-in) |
| CU6 | SECURITY_NEVER_AUTO; consent/GA bağımsız |
| CU7 | Gate `reason` kapı tipi etiketli (hedef) |

Hedef zincir: policy → consent → profil+GA → confirmation → NEVER_AUTO.

---

## 6. Dar PR planı

### PR-1 — Panel read sinyal ayrımı

`general_approval_active`, consent etiketleri, "genel onay vekili" kaldırma.

### PR-2 — CLI policy context (kritik)

`effective_consent` ≠ `general_approval`; test semantiği güncelleme.

### PR-3 — PolicyContext genişletme (opsiyonel)

`general_approval` alanı; identity/keystore yalnızca `consent`.

### PR-4 — Confirmation iskeleti

**Merge** #452–#458 — bkz. [lumos-cu4-confirmation-skeleton-draft.md](lumos-cu4-confirmation-skeleton-draft.md). PR-C6 köprü hizalama açık.

### Başarı ölçütleri

1. consent.json yok + genel onay açık → CLI `consent_ok=False`, TaskEngine GA=True.
2. consent.json var + GA kapalı → identity OK, kisitli_otonom write_local red.
3. Panel: `consent_ok` ≠ `general_approval_active`.
4. Panel profil guard (#449) regresyonsuz.
