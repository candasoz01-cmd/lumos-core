# Panel Profile Guard PR — Teknik Taslak

| Alan | Değer |
|------|-------|
| Durum | **Uygulama PR** |
| Tarih | 2026-06-21 |
| Kaynak | Subagent c6ac14bf read-only taslak |
| İlgili | [consent & panel profile matrix](lumos-consent-and-panel-profile-matrix-draft.md), [runtime enforcement map](lumos-runtime-enforcement-map.md), ADR-012 |

**Kapsam:** Minimal — panel mutasyonlarında `may_execute_step_at_runtime` ikinci kapısı + `LUMOS_PROFILE` / `LUMOS_GENERAL_APPROVAL` env wiring. Guest/Admin rol sistemi **yok** (repo'da yalnızca `rapor`, `guvenli_yurut`, `kisitli_otonom`).

**Bugünkü gap:** `task_action_gate` yalnızca `check_policy` çağırıyor; `LUMOS_PROFILE` reason metninde görünüyor, enforce edilmiyor.

---

## 1. Tam olarak hangi dosyalar değişecek?

### Kod (zorunlu — minimal diff)

| Dosya | Gerekçe |
|-------|---------|
| **`src/core/panel_bridge_state.py`** | Tek enforcement merkezi. `task_action_gate` içinde `check_policy` **sonrası** profil kapısı: `LUMOS_PROFILE` allowlist, `general_approval` okuma, `action → step_kind` eşlemesi, `may_execute_step_at_runtime` çağrısı, genişletilmiş `reason`. |
| **`src/task_engine/profiles.py`** | İsteğe bağlı: `panel_action_to_step_kind(action, *, full_doc_replace)` helper — matris tek kaynak kalır. |
| **`panel/scripts/panel_tasks_server.py`** | `do_PUT` → `full_doc_replace=True`; `_post_delete_permanent` → `profile_guard=False` (minimal 2 satır). |

### Kod (dokunulmaz)

| Dosya | Gerekçe |
|-------|---------|
| **`src/policy/action_policy.py`** | Offline/koruma/consent kuralları ayrı katman; bu PR profil matrisini **ekler**, policy'yi değiştirmez. |

### Test (zorunlu)

| Dosya | Gerekçe |
|-------|---------|
| **`tests/test_panel_bridge_codex_gate.py`** | Profil guard birim testleri |
| **`tests/test_panel_put_tasks_json_policy_gate.py`** | `write_local` eşlemesi sonrası `guvenli_yurut` PUT red |
| **`tests/test_panel_restore_policy_gate.py`** | Online restore için `guvenli_yurut` env |

### Dokümantasyon

| Dosya | Gerekçe |
|-------|---------|
| **`docs/analysis/lumos-runtime-enforcement-map.md`** | Panel gap satırı güncelleme |

---

## 2. Hangi davranış değişecek?

### Değişmeyecek (bilinçli)

- **`check_policy` birinci kapı:** offline mutasyon red, koruma+delete red, consent+identity red — aynı kalır.
- **Salt okuma:** `GET /tasks`, trash, evidence, `build_panel_read_state` — etkilenmez.
- **`POST /tasks/delete-permanent`:** Mevcut `confirm` + `may_perform_permanent_delete` korunur; profil guard bu endpoint'e **uygulanmaz**.
- **Guest/Admin, CU gateway, observe/act modu, trust motor** — kapsam dışı.

### Yeni ikinci kapı (`may_execute_step_at_runtime`)

```
check_policy → (red ise dur) → profil allowlist → general_approval oku → action→step_kind → may_execute_step_at_runtime → enabled/reason
```

**`action → step_kind` eşlemesi:**

| Policy action | step_kind | Mantık |
|---------------|-----------|--------|
| `CREATE_TASK`, `COMPLETE_TASK` | `safe_local` | Tek görev CRUD; `guvenli_yurut` onaysız izinli |
| `DELETE_TASK` (soft delete) | `safe_local` | Trash'e taşıma + `tasks.json` güncelleme |
| `PUT /tasks.json` (gate: `CREATE_TASK`, `full_doc_replace=True`) | `write_local` | Tam doküman replace; yalnız `kisitli_otonom` + genel onay |

**Env wiring:**

| Env | Davranış |
|-----|----------|
| `LUMOS_PROFILE` | Allowlist: `rapor`, `guvenli_yurut`, `kisitli_otonom`. Geçersiz/bilinmeyen → red. Default gösterim: `rapor`. |
| `LUMOS_GENERAL_APPROVAL` | `1`/`true`/`yes` → `general_approval=True`. Yoksa `False`. |

---

## 3. Eski davranış → yeni davranış (somut senaryolar)

### A — Offline

| İstek | Eski | Yeni |
|-------|------|------|
| `POST /tasks` | Red (`offline_mode`) | Aynı — birinci kapı |

### B — Online + yanlış/geçersiz profil

| Ortam | İstek | Eski | Yeni |
|-------|-------|------|------|
| `online`, `LUMOS_PROFILE=rapor` | `POST /tasks` | **İzinli** | **Red** — `rapor` + `safe_local` |
| `online`, `LUMOS_PROFILE=admin` | `POST /tasks` | **İzinli** | **Red** — profil allowlist dışı |

### C — Online + `guvenli_yurut`

| Ortam | İstek | Eski | Yeni |
|-------|-------|------|------|
| `online` + `guvenli_yurut` | `POST /tasks`, complete, soft delete | İzinli | **İzinli** (`safe_local`) |
| Aynı | `PUT /tasks.json` | İzinli | **Red** — `write_local` |

### D — Online + `kisitli_otonom` genel onay yok

| Ortam | İstek | Eski | Yeni |
|-------|-------|------|------|
| `online` + `kisitli_otonom`, onay yok | `POST /tasks` | İzinli | **Red** |
| Aynı | `GET /tasks` | İzinli | **İzinli** — mutasyon değil |

### E — Online + `kisitli_otonom` + genel onay

| Ortam | İstek | Eski | Yeni |
|-------|-------|------|------|
| `online` + `kisitli_otonom` + `LUMOS_GENERAL_APPROVAL=true` | create, PUT, delete | Policy geçince izinli | Create/PUT izinli; delete koruma env'ine bağlı |

### F — Koruma

| Ortam | İstek | Eski | Yeni |
|-------|-------|------|------|
| `online`, `guvenli_yurut`, koruma aktif | `POST /tasks/delete` | Red | Aynı — policy birinci |
| `online`, unlocked, `rapor` | `POST /tasks/delete` | İzinli | **Red** — profil ikinci kapı |

### G — Kalıcı silme (kapsam dışı)

| Ortam | İstek | Eski | Yeni |
|-------|-------|------|------|
| `online`, unlocked, `confirm=true` | `POST /tasks/delete-permanent` | Policy + confirm | **Aynı** (profil guard uygulanmaz) |

---

## 4. Hangi CU maddelerini enforce edecek?

| CU | PR kapsamı | Nasıl / ne kadar |
|----|------------|------------------|
| **CU1** | **Kısmi** | Uygulama adımları varsayılan `rapor` profilde kapalı |
| **CU2** | **Enforce etmez** | Lumos gateway yok |
| **CU3** | **Kısmi** | Profil + step_kind dar proxy |
| **CU4** | **Kısmi** | `kisitli_otonom` için `general_approval` zorunluluğu |
| **CU5** | **Enforce etmez** | observe/act mod ayrımı yok |
| **CU6** | **Kısmi** | `external`/`critical` her profilde red; kalıcı silme P2 engine branch bu PR'da değil |
| **CU7** | **Kısmi** | Gate `reason`: mod, profil, policy, profil red nedeni |
| **CU8** | **Enforce etmez** | Kanıt/simülasyon değişmez |
| **CU9** | **Uyum** | Public-safe |
| **CU10** | **Kısmi (mevcut)** | Policy `koruma_active` env fallback; LockState doğrulaması yok |

---

## 5. Yanlış pozitif riski

| Risk | Etki | Azaltma |
|------|------|---------|
| Demo kırılması (`online` + varsayılan `rapor`) | Yüksek | Test fixture'larda `LUMOS_PROFILE=guvenli_yurut` |
| `guvenli_yurut` + PUT red | Orta | Reason'da `write_local` açıklaması |
| `kisitli_otonom` onaysız red | Düşük–orta | `[PROFILE_BLOCKED]` etiketi |
| Geçersiz `LUMOS_PROFILE` typo | Orta | Allowlist mesajı |
| `consent.json` ≠ `general_approval` | Orta | Ayrı env; ADR-010 tam ayrım ayrı PR |
| Kalıcı silmeye profil guard eklenmesi | Yüksek | `profile_guard=False` delete-permanent path |

---

## 6. Rollback planı

| Adım | Aksiyon |
|------|---------|
| 1 | PR revert (`git revert <sha>`) |
| 2 | Davranış `check_policy`-only'ye döner |
| 3 | CI: panel gate testleri yeşil (pre-PR davranış) |
| 4 | Deploy: `LUMOS_PROFILE` / `LUMOS_GENERAL_APPROVAL` kaldırılabilir |
| 5 | Docs revert varsa enforcement map gap notu geri gelir |

**Risk:** Revert sonrası panel yine `online`+`rapor` ile mutasyona açık — bilinen güvenlik gap'i geri döner.

---

## PR sınır özeti

**Yapılacak:** `task_action_gate` → `may_execute_step_at_runtime`; env wiring; test güncellemesi.

**Yapılmayacak:** Guest/Admin; LockState panel entegrasyonu; CU gateway; SECURITY_NEVER_AUTO P2 engine branch; CLI consent vs general_approval tam ayrımı.

**Başarı ölçütü:**

- `online` + `rapor` → mutasyon red
- `online` + `guvenli_yurut` → create/complete/delete izinli; PUT red
- `online` + `kisitli_otonom` + onay → write_local mutasyonlar izinli
- Offline / koruma / confirm davranışları regresyonsuz
- CI yeşil
