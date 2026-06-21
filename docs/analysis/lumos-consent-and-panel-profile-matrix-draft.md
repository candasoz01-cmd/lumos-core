# Lumos Consent Matrix & Panel Profile Matrix — Taslak

| Alan | Değer |
|------|-------|
| Durum | **Taslak** — docs-only; uygulama yok |
| Tarih | 2026-06-21 |
| İlgili | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [action permission matrix](lumos-action-permission-matrix.md), [runtime enforcement map](lumos-runtime-enforcement-map.md), [computer-use-permission-gate-decision](../memory/computer-use-permission-gate-decision.md) (CU1–CU10) |
| Kapsam | Public Lumos OSS; Kando/Cando iç operasyonu **dışarıda** |

## Amaç

CU1–CU10 Computer Use ilkelerini panel davranışları ve kullanıcı profilleriyle eşlemek. Bu belge **hedef sözleşme taslağıdır**; kod, panel UX veya enforcement değişikliği talep etmez.

**Canonical CU kaynağı:** `docs/memory/computer-use-permission-gate-decision.md` §3 (OD-012, `decision-approved`, `implementation-pending`).

**Canonical yetki profili kaynağı (repo):** `src/task_engine/profiles.py` — `rapor`, `guvenli_yurut`, `kisitli_otonom`.

---

## 1. Kullanıcı profilleri tablosu

Repo'da **Guest / User / Trusted User / Developer / Admin** adları **yoktur**. Aşağıdaki tablo **hedef panel kullanıcı profili** taslağıdır; mevcut kod profilleri ile eşleme sütunu kanıtlıdır.

| Panel profili (hedef) | Repo karşılığı | Durum | Kısa tanım |
|----------------------|----------------|-------|------------|
| **Guest** | `rapor` (kısmi) | **Önerilen / hedef** | Salt okuma, analiz, öneri; uygulama ve dış etki yok |
| **User** | `guvenli_yurut` (kısmi) | **Önerilen / hedef** | Yerel güvenli işler (`safe_local`); genel onay gerekmez |
| **Trusted User** | `kisitli_otonom` + genel onay | **Önerilen / hedef** | Genel onay açıkken `write_local`; dış etki hâlâ kapalı |
| **Developer** | `guvenli_yurut` + sandbox genişletmesi | **Önerilen / hedef** | Demo/sandbox geliştirme; core path yazımı yasak |
| **Admin** | Yok — yalnızca kullanıcı komutu | **Önerilen / hedef** | Kilit/consent/kritik işlemler **SECURITY_NEVER_AUTO**; otomatik admin bypass yok |

### Repo profilleri (bugün enforce)

| Profil | Görünen ad | Karar katmanları |
|--------|------------|------------------|
| `rapor` | rapor (sadece analiz) | analyze, read, plan ✓; uygulama ✗ |
| `guvenli_yurut` | güvenli yürüt | + `safe_local` (genel onaysız) |
| `kisitli_otonom` | kısıtlı otonom | + `write_local` yalnızca `general_approval=True` |

Kaynak: `profiles.py` — `ALL_PROFILES`, `STEP_PERMISSION_MATRIX`, `get_profile_display_name()`.

### Panel ortam değişkeni

Panel read/gate yolu `LUMOS_PROFILE` env ile profil adını **görünürlük** amaçlı taşır; `may_execute_step_at_runtime` panel mutasyonlarında **çağrılmaz** (enforcement map § Panel gap).

---

## 2. Profil × izin tablosu

Sütunlar: panel davranış alanları. Hücreler: **izin seviyesi** + **consent katmanı** (§3 referansı).

**Kısaltmalar:** S=sessiz izin · N=bildirim · 1=tek sefer onay · E=her sefer onay · ⛔=SECURITY_NEVER_AUTO / profil asla

| Profil | Read | Analyze | Suggest | Computer Use | External Write | File Operations | Email | Social Media | Critical System Config |
|--------|------|---------|---------|--------------|----------------|-----------------|-------|--------------|------------------------|
| **Guest** (`rapor`) | S | S | S | ⛔ kapalı (CU1) | ⛔ | read only | read/propose | read/propose | read only |
| **User** (`guvenli_yurut`) | S | S | S | N → 1 (okuma modu S; dış etki 1) | ⛔ | safe_local: S/N; write_local: ⛔ | propose | propose | read; unlock: E + kullanıcı komutu |
| **Trusted User** (`kisitli_otonom` + genel onay) | S | S | S | N → 1 (CU4; genel onay CU için yeterli değil) | ⛔ | write_local: 1 (genel onay önkoşul) | propose | propose | read; config: ⛔ |
| **Developer** (hedef) | S | S | S | 1 (sandbox scope, CU3) | ⛔ | sandbox write: 1; core path: ⛔ | — | — | read |
| **Admin** (hedef) | S | S | S | E (CU7) | ⛔ | trash restore: 1; permanent delete: E + ⛔ | ⛔ | ⛔ | E + kullanıcı komutu; otomatik ⛔ |

### `profiles.py` step türü eşlemesi

| Panel sütunu | Step kind / sözleşme |
|--------------|----------------------|
| Read, Analyze | `read`, `analyze` |
| Suggest | `plan` |
| File Operations (yerel) | `safe_local`, `write_local` |
| External Write, Email, Social Media | `external` + `SECURITY_NEVER_AUTO.external_write` |
| Critical System Config | `critical` + `SECURITY_NEVER_AUTO.critical_system_config` |
| Computer Use (dış etki) | OD-012 mod: dış-etkili-aksiyon; profil matrisinde ayrı step türü **yok** (gap) |

### Panel yüzeyi bugün (kanıt)

| Yetenek | Konum | Enforcement |
|---------|-------|-------------|
| Salt okuma payload | `panel_bridge_state.build_panel_read_state()` | Read-only |
| Görev listele / trash listele | `GET /tasks`, `GET /tasks/trash` | Read |
| Görev CRUD | `POST /tasks`, complete, delete, restore | `task_action_gate` → `check_policy` |
| Tam doküman yazım | `PUT /tasks.json` | CREATE_TASK gate (#444) |
| Kalıcı silme | `POST /tasks/delete-permanent` | Policy + confirm (#445) |
| Consent / kilit API | `POST /lumos-consent` | consent.json; passphrase diske yazılmaz |
| Evidence | `GET /evidence/*` | Journal salt okuma |
| Profil matrisi | — | **Panelde yok** |

Kaynak: `panel/scripts/panel_tasks_server.py`, `src/core/panel_bridge_state.py`, [runtime enforcement map](lumos-runtime-enforcement-map.md).

---

## 3. Consent Matrix

CU4, CU6, CU7 ve ADR-010 (`consent` ≠ `confirmation` ≠ `general_approval`) ile hizalı **hedef** consent katmanları.

| Consent katmanı | Kod / sözleşme karşılığı | Örnek panel davranışları |
|-----------------|--------------------------|---------------------------|
| **Silent allowed** | Karar katmanı `analiz`; step `read`/`analyze`/`plan`; profil `rapor+` | Dashboard okuma, görev listesi, trash listesi, evidence görüntüleme, durum/guidance |
| **Notification required** | `safe_local` under `guvenli_yurut`; sandbox yazım öncesi codex uyarısı | Panel codex banner; gate `reason` metni; simulasyon etiketi gösterimi (C4) |
| **Single approval required** | `general_approval=True` (kisitli_otonom); işlem bazlı onay (CU4) | Genel onay CLI/panel consent; görev oluştur/tamamla (online + consent); Computer Use oturumu başlatma (hedef) |
| **Every-time approval required** | Yüksek risk; mod geçişi okuma→dış-etki (CU5) | Kalıcı silme confirm body; Computer Use çok adımlı ara onay (needs-review OD-012); Admin kritik config |
| **SECURITY_NEVER_AUTO** | `profiles.py` kümesi; profilden bağımsız | Aşağıdaki tablo |

### SECURITY_NEVER_AUTO — consent bağımsız

| Üye | Eylem alanları | Consent katmanı | CU |
|-----|----------------|-----------------|-----|
| `permanent_delete` | File (kalıcı silme) | E + açık kullanıcı komutu; otomatik ⛔ | CU6 |
| `external_write` | External, Email, Social, Calendar | ⛔ profil bypass yok; işlem onayı bile otomatik değil | CU4, CU6 |
| `irreversible_user_op` | Payment, domain, geri dönüşsüz | ⛔ | CU6 |
| `critical_system_config` | Security settings (kilit, keystore, consent reset) | E + kullanıcı komutu; ⛔ otomatik | CU6, CU10 |

Kaynak: `profiles.py` `SECURITY_NEVER_AUTO`; `core/inviolable.py`; ADR-012 §5 trash.

### Computer Use consent zinciri (hedef — OD-012 §5)

```
[ CU7: ne / nerede / etki görünürlüğü ]
        ↓
[ Profil + görev kapsamı (CU3) ]
        ↓
[ Mod: okuma-gözlem | dış-etkili (CU5) ]
        ↓
[ CU4: işlem bazlı onay — genel onay yetmez ]
        ↓
[ CU10: online → kimlik + kilit/presence ]
        ↓
[ Lumos gateway (CU2) ]
        ↓
[ CU8: gerçek kanıt raporu ]
```

**Durum:** OD-012 `implementation-pending` — zincir **belgede onaylı**, kod/panel **henüz uygulanmadı**.

---

## 4. CU1–CU10 ile çelişkiler (kanıtlı)

Aşağıdaki liste **repo/docs kanıtına** dayanır; tahmin değildir.

| # | CU ilkesi | Çelişki / gap | Kanıt |
|---|-----------|---------------|-------|
| C1 | **CU1** — CU varsayılan kapalı | Computer Use entegrasyonu yok; panel CU modu tanımsız — **henüz uygulanmadı** (beklenen); ancak panel `safe_local` eşdeğeri yokken `PUT /tasks.json` tam yazım mümkün | OD-012 `implementation-pending`; enforcement map C1 kısmi |
| C2 | **CU2** — yalnızca Lumos geçidi | Panel sunucusu doğrudan `.lumos/tasks.json` yazar; tek yüz ama profil guard atlanır | `panel_tasks_server._write_doc`; enforcement map: profil matrisi panelde yok |
| C3 | **CU3** — görev kapsamı zorunlu | Panel mutasyonları görev kapsamı / step kind doğrulamaz; yalnızca `action_policy` snapshot | `task_action_gate` → `check_policy` only |
| C4 | **CU4** — dış etkili açık onay | `general_approval` CLI'da policy `consent` ile eşleniyor — semantik drift; CU işlem onayı ile karışabilir | enforcement map § cli_tasks_mutation; ADR-010 consent≠confirmation |
| C5 | **CU5** — okuma / dış etki mod ayrımı | Panel tek HTTP yüzey; mod geçişi UI/endpoint ayrımı **yok** | OD-012 needs-review; panel routes |
| C6 | **CU6** — SECURITY_NEVER_AUTO | Küme üyeleri `run_task` içinde tek branch'te toplanmıyor; `external_write` vb. step kind değil | [security-never-auto-p2-and-helper-proposal.md](security-never-auto-p2-and-helper-proposal.md) §1.2–1.4 |
| C7 | **CU7** — ne/nerede/etki görünürlüğü | Panel gate `reason` var; Computer Use oturumu yok; mock/guidance alanları CLI runtime ile birebir değil | ADR-011 panel mock drift; `panel_bridge_state._CODEX_PANEL_WARNING` |
| C8 | **CU8** — gerçek kanıt | `simulasyon` etiketi TaskEngine'de var; panel status map uyumlu — **kısmi uyum** | ADR-012 C4; `_TASK_STATUS_MAP` |
| C9 | **CU9** — public repo sınırı | Bu belge public-safe; çelişki **yok** (uyum) | public-github-boundary kuralları |
| C10 | **CU10** — online kimlik/kilit | Panel `_panel_policy_context`: `LUMOS_SESSION_UNLOCKED` env yoksa `koruma_active=True`; runtime `LockState` doğrulanmaz | `panel_bridge_state.py` L49–54; ADR-011 keystore_ready≠session_unlocked |
| — | **Profil × panel** | `LUMOS_PROFILE` yalnızca metin; `may_execute_step_at_runtime` panelde çağrılmıyor | enforcement map § panel_tasks_server gap |
| — | **Trust motor** | Birleşik trust yok; CU10 sinyalleri parçalı | ADR-007; ADR-010 usage map |

---

## 5. Enforcement önerileri (yalnızca öneri — uygulama yok)

Ayrı bölüm; kod veya PR talep etmez.

### 5.1 Panel profil guard

1. Panel mutasyonlarında `may_execute_step_at_runtime(LUMOS_PROFILE, step_kind, general_approval)` çağrısı — `check_policy` **sonrası** ikinci kapı.
2. `LUMOS_PROFILE` için allowlist: yalnızca `rapor`, `guvenli_yurut`, `kisitli_otonom`.
3. Guest/User/Trusted hedef adları UI katmanında; backend canonical profil adları korunur.

### 5.2 Consent semantik ayrımı (ADR-010)

1. `consent` (identity/keystore erişimi) ≠ `general_approval` (kisitli_otonom write_local) — CLI panel context'te ayrı alanlar.
2. Computer Use **confirmation** (işlem onayı) üçüncü alan; genel onay CU4'e göre yeterli sayılmaz.

### 5.3 Computer Use mod kapısı (OD-012 uygulama paketi)

1. Panel/CLI'da `mode=observe|act` ayrı endpoint veya görev metadata — sessiz yükseltme engeli (CU5).
2. `act` modu: CU7 preview zorunlu → CU4 onay → CU10 lock/consent snapshot → gateway (CU2).
3. Varsayılan `observe`; oturum süresi ve kapsam UI'da görünür (CU3).

### 5.4 SECURITY_NEVER_AUTO P2

1. Engine `_is_step_allowed_runtime` öncesi action-tag → `SECURITY_NEVER_AUTO` lookup (öneri: [security-never-auto-p2-and-helper-proposal.md](security-never-auto-p2-and-helper-proposal.md)).
2. Panel kalıcı silme yolu mevcut (#445); engine executor map'i tamamlanmadan "tam CU6" iddiası yapılmaz.

### 5.5 Trust / lock (ADR-011, CU10)

1. Panel policy context'te runtime `LockState` veya eşdeğer trust snapshot — env fallback yerine.
2. `keystore_ready` ve `session_unlocked` ayrı panel göstergeleri; mock tek boolean birleştirmesi kaldırılır (hedef).

### 5.6 Dokümantasyon zinciri

1. Bu taslak → onay sonrası `lumos-action-permission-matrix.md` companion güncellemesi.
2. CU1–CU10 enforcement satırları runtime map'e eklenir (Computer Use satırı: hedef / gap).

---

## İlgili belgeler

| Belge | Rol |
|-------|-----|
| [computer-use-permission-gate-decision.md](../memory/computer-use-permission-gate-decision.md) | CU1–CU10 canonical |
| [ADR-012](../decisions/ADR-012-lumos-security-codex.md) | C1–C6 codex |
| [ADR-010](../decisions/ADR-010-guard-policy-trust-terminology.md) | Terminoloji |
| [ADR-011](../decisions/ADR-011-lock-semantics-decision.md) | Lock sinyalleri |
| [ADR-006](../decisions/ADR-006-ai-firewall-guard-layer.md) | Guard hedef rolü |
| [ADR-007](../decisions/ADR-007-trust-engine-layer.md) | Trust hedef rolü |
| [lumos-action-permission-matrix.md](lumos-action-permission-matrix.md) | Eylem × profil |
| [lumos-runtime-enforcement-map.md](lumos-runtime-enforcement-map.md) | Bugün enforce |

---

## Durum

| Maddeler | Durum |
|----------|-------|
| Profil tablosu (Guest–Admin) | Taslak — repo eşlemesi işaretlendi |
| Profil × izin tablosu | Taslak — panel kanıtı referanslı |
| Consent matrix | Taslak — ADR-010/CU hizalı |
| CU çelişkileri | Kanıtlı liste |
| Enforcement önerileri | Öneri only |

**Sonraki adım (onay sonrası):** Companion güncelleme + panel profil guard PR planı (`lumos-security-codex-next-pr-plan.md` ile hizala).
