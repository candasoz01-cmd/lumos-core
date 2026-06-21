# OS Executor Öncesi Zorunlu Güvenlik Kuralları

| Alan | Değer |
|------|-------|
| Durum | **Analiz** — kod yok; private OS executor swap öncesi kapı belgesi |
| Tarih | 2026-06-22 |
| Kapsam | Real OS executor private katmanına geçmeden önce zorunlu güvenlik kuralları |
| İlgili | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [lumos-karar-sozlesmesi.md](../lumos-karar-sozlesmesi.md), [lumos-pc-device-commands-roadmap.md](lumos-pc-device-commands-roadmap.md), [lumos-mobile-approval-mvp-plan.md](lumos-mobile-approval-mvp-plan.md), `src/task_engine/profiles.py`, `src/policy/action_policy.py`, `packages/kando_bridge/src/kando_bridge/pc_remote_tools.py`, `packages/kando_runtime/src/kando_runtime/controlled_bridge.py` |

**Not:** `docs/analysis/mobile-approval-flow-security-review.md` ve `docs/analysis/lumos-audit-log-contract.md` repoda **yoktur**. Mobile onay güvenliği için [lumos-mobile-approval-mvp-plan.md §8](lumos-mobile-approval-mvp-plan.md); audit için `evidence_continuity`, `guard_audit`, `action_policy.log_policy_blocked` referans alınır.

---

## 1. Amaç

Bu belge, **real OS executor** (private katman) devreye girmeden önce Lumos'un otomatik veya onaylı cihaz otomasyonunun hangi sınırlar içinde kalacağını tanımlar.

**Hedef:** Public OSS köprüsünde (`kando_bridge`, `pc_remote_tools`) halihazırda stub + onay kapısı + `surface_blocked` ile korunan yüzey, private executor swap ile **gevşetilmez**. Gerçek OS API çağrıları yalnızca bu kuralların tamamı karşılandıktan sonra ve **tek dış kapı** (ADR-012 C1) üzerinden çalışır.

| Katman | Repo | Executor |
|--------|------|----------|
| **Public OSS** | `lumos-core` | `execute_tool_stub` — simülasyon, şema, onay sözleşmesi |
| **Private / professional** | Ayrı katman | Gerçek OS: uygulama, AX/OCR, klavye/fare, native picker |

**Kural:** Public repoda gerçek cihaz kontrolü commitlenmez. Bu belge private swap öncesi **zorunlu kapı** listesidir.

---

## 2. Asla otomatik (`SECURITY_NEVER_AUTO`) — özet tablo

Kaynak: `src/task_engine/profiles.py` — `SECURITY_NEVER_AUTO` (L47–52), `SECURITY_NEVER_AUTO_MAPPING` (L77–98).

| `SECURITY_NEVER_AUTO` üyesi | Kategori eşlemesi | Policy / yüzey token | Profil/onaydan bağımsız |
|-----------------------------|-------------------|----------------------|-------------------------|
| `permanent_delete` | Dosya silme (kalıcı) | `action_key=permanent_delete`, `policy_action=delete_permanent` | **Evet — asla otomatik** |
| `external_write` | Dış yazma, exfil, pano yazma | `action_key=external_write`, `action_tag=external_write` | **Evet — asla otomatik** |
| `irreversible_user_op` | Terminal, klavye enjeksiyonu, uygulama sonlandırma, otomatik tıklama | `action_key=irreversible_user_op`, `action_tag=irreversible_user_op` | **Evet — asla otomatik** |
| `critical_system_config` | Sistem ayarları, ağ ayarları (firewall/VPN/proxy) | `action_key=critical_system_config`, `action_tag=critical_system_config` | **Evet — asla otomatik** |

**Sözleşme metni:** `SECURITY_BOUNDARY_DESCRIPTION` — *"Asla otomatik: kalıcı silme, dış servise kontrolsüz yazma, geri dönüşsüz kullanıcı işlemi, kritik sistem ayarı değişikliği."*

**Profil matrisi:** `STEP_TYPE_EXTERNAL` ve `STEP_TYPE_CRITICAL` → `DECISION_LAYER_NEVER`; hiçbir profilde (`rapor`, `guvenli_yurut`, `kisitli_otonom`) izinli değil (`may_execute_step_at_runtime` → False).

**Engine notu:** Task engine branch'te `permanent_delete` ayrı işlenir (`_ENGINE_SECURITY_NEVER_AUTO_MEMBERS`); sözleşme kümesinde kalır, panel/CLI `delete_permanent` yolu açık kullanıcı komutu + confirmation gerektirir (ADR-012 C5, #445+#454).

---

## 3. Kategori bazlı kurallar

### 3.1 Dosya silme

| Alan | Değer |
|------|-------|
| **Risk seviyesi** | **Critical** |
| **Otomatik çalışabilir mi?** | **never** — tüm silme yüzeyi köprüde `surface_blocked` |
| **Onay tipi** | Kalıcı silme: **blocked** (otomatik yasak) + açık kullanıcı komutu + çift onay (`delete_permanent` + CU4 opt-in); trash taşıma: Lumos workspace sözleşmesi dışında OS executor kapsamında **komut yok** |
| **ADR-012 / NEVER_AUTO** | `permanent_delete` |

**Örnek komutlar:**

| Komut / niyet | Sonuç |
|---------------|-------|
| `rm -rf`, `unlink`, `kalıcı sil`, `delete permanently` | **Block** — `surface_blocked` (`pc_remote_tools.py` L137–145, `controlled_bridge.py` L29–40) |
| `sil`, `delete`, `remove`, `trash`, `çöp` (argüman probe) | **Block** — regex yüzeyi |
| `pc_reveal_in_finder` (yalnızca göster) | **Allow** (onaylı, P0) — silme yok |
| `pc_request_file_picker` (kullanıcı seçimi) | **Allow** (onaylı) — yol kullanıcıdan |
| Lumos görev trash (`DELETE_TASK` → `.lumos/trash/`) | Workspace içi; OS executor dışı; kalıcı silme `delete_permanent` ayrı kapı |

---

### 3.2 Uygulama kurma

| Alan | Değer |
|------|-------|
| **Risk seviyesi** | **High** (açma) / **Critical** (kurma/kaldırma) |
| **Otomatik çalışabilir mi?** | **never** — kurma/kaldırma; açma: **approval required** |
| **Onay tipi** | `pc_open_app`, `pc_focus_app` → mobile + explicit (`approval_token`); `pc_quit_app` → **blocked** otomatik, onaylı bile MVP dışı |
| **ADR-012 / NEVER_AUTO** | Kurma/kaldırma → `irreversible_user_op` adayı; `open app` controlled_bridge'de de blocked |

**Örnek komutlar:**

| Komut / niyet | Sonuç |
|---------------|-------|
| `pc_open_app` (stub → private swap) | **Allow** — onay zorunlu (`bridge_high_risk_execute`) |
| `pc_focus_app` | **Allow** — onay zorunlu |
| `pc_quit_app` | **Block** otomatik; v2+ ayrı kapı; `irreversible_user_op` |
| `install`, `brew install`, `apt install`, `uninstall` | **Block** — komut listesinde yok; eklenmez; otomatik asla |
| `open -a`, `launch app`, `uygulama aç` (controlled_bridge probe) | **Block** — `surface_blocked` |

---

### 3.3 Terminal erişimi

| Alan | Değer |
|------|-------|
| **Risk seviyesi** | **Critical** |
| **Otomatik çalışabilir mi?** | **never** — tam blok |
| **Onay tipi** | **blocked** — onay ile bile OSS/public yüzeyde yok; private executor'da da varsayılan kapalı |
| **ADR-012 / NEVER_AUTO** | `irreversible_user_op`; ADR-012 C2 (iç bypass yok) |

**Örnek komutlar:**

| Komut / niyet | Sonuç |
|---------------|-------|
| `terminal`, `shell`, `bash`, `zsh`, `cmd.exe`, `powershell` | **Block** — `surface_blocked` |
| `subprocess`, `exec`, `eval`, ham shell pipe | **Block** — komut şemasında yok |
| `pc_type_text` (klavye enjeksiyonu) | **Approval required** — otomatik **never**; P2; `cu_act_type` |
| `controlled_bridge` `read`/`write`/`ping` | Workspace sandbox; terminal yüzeyi probe'da red |

**İlke:** Shell/exec yüzeyi `surface_blocked` ile **tam red**; gated exec gelecekte bile ayrı ürün kararı + ikinci kapı gerektirir, bu belgede **varsayılan block**.

---

### 3.4 Sistem ayarları

| Alan | Değer |
|------|-------|
| **Risk seviyesi** | **Critical** |
| **Otomatik çalışabilir mi?** | **never** |
| **Onay tipi** | **blocked** (otomatik); değişiklik gerekiyorsa kullanıcı OS UI — Lumos executor üzerinden değil |
| **ADR-012 / NEVER_AUTO** | `critical_system_config` |

**Örnek komutlar:**

| Komut / niyet | Sonuç |
|---------------|-------|
| Kullanıcı hesabı oluşturma/silme | **Block** — komut yok |
| Sistem tarih/saat, locale, güvenlik politikası | **Block** — `critical_system_config` |
| `pc_get_battery_status`, `pc_get_system_info` (salt okuma) | **Allow** — read-only OK (onay yok / düşük risk) |
| `pc_volume_set` | **Approval required** — orta risk; otomatik never |
| Erişilebilirlik izni değiştirme (AX/TCC) | **Block** — kritik izin; executor öncesi ayrı checklist |

---

### 3.5 Ağ ayarları

| Alan | Değer |
|------|-------|
| **Risk seviyesi** | **Critical** |
| **Otomatik çalışabilir mi?** | **never** (yapılandırma değişikliği) |
| **Onay tipi** | Firewall / VPN / proxy / DNS → **blocked**; `pc_open_url` (HTTPS) → **approval required** |
| **ADR-012 / NEVER_AUTO** | `critical_system_config` (yapılandırma); `external_write` (dış servise otomatik POST/upload) |

**Örnek komutlar:**

| Komut / niyet | Sonuç |
|---------------|-------|
| Firewall kuralı ekleme/silme | **Block** — `critical_system_config` |
| VPN profili, proxy, DNS override | **Block** |
| `pc_open_url` (`https://…`) | **Allow** — onaylı; URL şema doğrulaması (`_URL_RE`) |
| Otomatik API POST, upload, webhook | **Block** — `external_write`; komut listesinde yok |
| `pc_set_clipboard` (gelecek) | **Block** MVP dışı — exfil/injection riski |

---

## 4. Dosya silme

### 4.1 `permanent_delete` — her zaman never auto

- `SECURITY_NEVER_AUTO` üyesi; profil ve genel onaydan **bağımsız** otomatik yasak.
- Policy yüzeyi: `DELETE_PERMANENT = "delete_permanent"` (`action_policy.py` L24).
- Panel: `POST /tasks/delete-permanent` — policy + confirmation (#445+#454).
- Engine: `include_permanent_delete=False` branch'te ayrı guard; sözleşme kümesinden çıkarılmaz.

### 4.2 Trash vs kalıcı silme

| Yol | Davranış | Otomatik |
|-----|----------|----------|
| **Trash** (`.lumos/trash/`) | Görev/workspace soft-delete; geri yükleme mümkün | Lumos panel/CLI — OS executor dışı |
| **Kalıcı silme** | Geri alınamaz | **Asla otomatik**; açık komut + uyarı + confirmation |
| **OS dosya silme** | `rm`, `unlink`, trash verb probe | **Block** — `surface_blocked` |

### 4.3 Lumos trash prensibi

ADR-012 C5 ve `lumos-karar-sozlesmesi.md` §2:

1. Tek çöp hedefi: `.lumos/trash/` (`workspace_contract.LUMOS_TRASH_DIRNAME`).
2. Trash **aktif state kaynağı değildir**; okuma/kaynak olarak kullanılmaz.
3. Kalıcı silme yalnızca `user_initiated=True` + açık kullanıcı komutu.
4. OS executor **trash dışı dosya yok etme** komutu içermez; silme fiilleri regex ile reddedilir.

---

## 5. Uygulama kurma

### 5.1 Install / uninstall

| Kural | Açıklama |
|-------|----------|
| **Asla otomatik** | Paket yöneticisi, installer, `brew`/`apt`/`msi` yüzeyi komut şemasında **yok** ve eklenmez |
| **Onay yetersiz** | Mobile onay bile install/uninstall için yeterli sayılmaz — ürün kararı gerektirir (v2+ ayrı kapı) |
| **NEVER_AUTO** | `irreversible_user_op` + `critical_system_config` (sistem geneli etki) |

### 5.2 Açma / odaklama (izinli sınıf)

| Komut | Otomatik | Onay |
|-------|----------|------|
| `pc_open_app` | **never** | Mobile + explicit, tek kullanımlık token |
| `pc_focus_app` | **never** | Mobile + explicit |
| `pc_media_play_pause` | Salt okuma benzeri düşük risk — P0'da onaysız **değil**; roadmap onay gerektirmez ama executor swap öncesi profil tercihi netleştirilmeli | no (roadmap) |

**İlke:** Install/uninstall **always approval, likely never auto for install** — bu belgede install için **asla otomatik** (NEVER listesinde §12 kural 6).

---

## 6. Terminal erişimi

### 6.1 Mevcut köprü koruması

`controlled_bridge.surface_blocked` ve `pc_remote_tools._probe_blocked` aynı regex ailesini kullanır:

```
terminal | shell | bash | zsh | cmd.exe | powershell
rm -rf | sudo rm | unlink | kalıcı sil | delete permanently
sil | delete | remove | trash | çöp
(+ controlled_bridge: open app, mail, calendar)
```

### 6.2 Tam blok vs gated

| Mod | Davranış | Executor öncesi |
|-----|----------|-----------------|
| **Tam blok (varsayılan)** | Shell/terminal token → `surface_blocked` | **Zorunlu** — değişmez |
| **Gated exec (gelecek)** | Dar allowlist, audit, ikinci onay | Bu belge kapsamı **dışı**; ayrı ADR gerekir |

### 6.3 İlgili yüksek risk komutlar

- `pc_type_text` — terminal değil ama `irreversible_user_op` adayı; otomatik **never**, onay + token tüketimi zorunlu (P2).
- Ham `workspace` write (`controlled_bridge` `write`) — sandbox altında; terminal probe geçemez.

---

## 7. Sistem ayarları

### 7.1 `critical_system_config` eşlemesi

| OS executor yüzeyi | Sınıf |
|--------------------|-------|
| Hesap/parola/TCC/AX izin değişikliği | **blocked** |
| Boot/login item, launch daemon | **blocked** |
| Sistem ses (`pc_volume_set`) | onaylı; otomatik never |
| Pil, aktif pencere, ekran durumu (okuma) | read-only OK |

### 7.2 Policy bağlantısı

- `action_policy.check_policy`: offline → mutasyon red; `koruma_active` + `delete_task` → red.
- `STEP_TYPE_CRITICAL` → profil matrisinde **asla**.
- Executor swap bu policy zincirini **atlamaz**; ADR-012 C1 tek dış kapı.

---

## 8. Ağ ayarları

### 8.1 Firewall, proxy, VPN

| İşlem | Otomatik | Onay | Asla |
|-------|----------|------|------|
| Firewall kuralı değiştirme | never | — | **Evet** |
| VPN bağlantısı/profil | never | — | **Evet** |
| Sistem proxy ayarı | never | — | **Evet** |
| DNS override | never | — | **Evet** |
| HTTPS URL açma (`pc_open_url`) | never | mobile + explicit | Hayır (onaylı izinli) |
| Dış API otomatik yazma | never | — | **Evet** (`external_write`) |

### 8.2 Köprü sınırı

- Loopback bind (`127.0.0.1`) + `KANDO_BRIDGE_SECRET` — Mobile secret taşımaz ([lumos-mobile-approval-mvp-plan.md §3](lumos-mobile-approval-mvp-plan.md)).
- LAN relay OSS demo; üretim tüneli private katman.

---

## 9. Onay zorunluluğu matrisi

| İşlem | Auto | Mobile onay | İkinci onay | Asla |
|-------|:----:|:-----------:|:-----------:|:----:|
| Kalıcı dosya silme (OS) | — | — | — | ✓ |
| Lumos trash taşıma | — | panel/CLI | — | — |
| Lumos `delete_permanent` | — | ✓ | ✓ (CU4 opt-in) | otomatik ✓ |
| Dosya silme fiili (probe) | — | — | — | ✓ |
| Uygulama install/uninstall | — | — | — | ✓ |
| `pc_open_app` / `pc_focus_app` | — | ✓ | — | otomatik ✓ |
| `pc_quit_app` | — | ✓ (v2+) | ✓ | otomatik ✓ |
| Shell / terminal / subprocess | — | — | — | ✓ |
| `pc_type_text` | — | ✓ | ✓ (önerilen) | otomatik ✓ |
| Sistem ayarı değiştirme | — | — | — | ✓ |
| `pc_volume_set` | — | ✓ | — | otomatik ✓ |
| Firewall / VPN / proxy / DNS | — | — | — | ✓ |
| `pc_open_url` | — | ✓ | — | otomatik ✓ |
| Dış servise otomatik yazma | — | — | — | ✓ |
| Salt okuma (ekran, pil, pencere) | ✓* | — | — | — |
| `pc_reveal_in_finder` | — | ✓ | — | otomatik ✓ |
| `pc_suggest_click` (öneri, tıklamaz) | — | ✓ | — | otomatik ✓ |
| Otomatik `pc_click` (gelecek) | — | — | — | ✓ |

\* Salt okuma: düşük risk; hassas içerik (pano, ekran) için conditional onay — [roadmap §4](lumos-pc-device-commands-roadmap.md) `pc_get_clipboard_text`.

**Onay sözleşmesi:** `approval_token` tek kullanımlık; red sonrası otomatik yeniden deneme **yok** (RB-04, mobile MVP §8).

---

## 10. Executor başlamadan checklist

Private OS executor swap **yalnızca** aşağıdaki maddelerin tamamı geçtikten sonra yapılır.

### 10.1 Sözleşme ve kod hizası

- [ ] `SECURITY_NEVER_AUTO` dört üyesi runtime'da tutarlı red — Wave 1 #496–#498 kapandı (ADR-012)
- [ ] `surface_blocked` regex'i private executor girişinde de probe ediliyor (`validate_command_arguments` / `_probe_blocked`)
- [ ] `COMMAND_SPECS` dışında komut kabul edilmiyor (`unknown_command`)
- [ ] `stub_only: true` flag'i swap sonrası profil bazlı kaldırılıyor; dokümantasyon güncel

### 10.2 Onay hattı

- [ ] RB-04 pending disk + `approval_token` + `consume_pending_record` çalışıyor
- [ ] Onaylı komutlar onaysız yürütülemiyor (`approval_required: true` → gate)
- [ ] Red sonrası otomatik retry yok
- [ ] Mobile relay secret exfil yok (`KANDO_BRIDGE_SECRET` Mobile'da yok)

### 10.3 NEVER yüzey kapıları

- [ ] Shell/terminal/subprocess → **block**
- [ ] Silme fiilleri (trash verb dahil) → **block**
- [ ] Install/uninstall yüzeyi → **komut yok**
- [ ] Firewall/VPN/proxy/DNS → **komut yok**
- [ ] `pc_quit_app`, otomatik `pc_click` → **MVP dışı / block**

### 10.4 Audit ve kanıt

- [ ] Policy blokları loglanıyor (`log_policy_blocked` → `logs/log.txt` + evidence journal)
- [ ] Onay/red olayları izlenebilir (pending record + EC v1)
- [ ] Stub vs gerçek ayrımı kullanıcıya görünür (`simulasyon` ≠ `tamamlandi`) — ADR-012 C4

### 10.5 P0 executor ilk dalga sınırı

İlk swap yalnızca roadmap P0 (7 komut): `pc_read_screen_state`, `pc_get_active_window`, `pc_open_url`, `pc_open_app`, `pc_request_file_picker`, `pc_media_play_pause`, `pc_reveal_in_finder` — [roadmap §6](lumos-pc-device-commands-roadmap.md).

- [ ] P0 dışı komutlar private'ta da stub veya red
- [ ] P2 komutları (`pc_type_text` vb.) swap edilmedi

### 10.6 Public boundary

- [ ] Gerçek OS executor kodu public `lumos-core` commit'inde **yok**
- [ ] Diff public remote'a gidecekse boundary review yapıldı

---

## 11. OSS vs private layer

| Konu | OSS (`lumos-core`) | Private katman |
|------|-------------------|----------------|
| Tool şeması | ✓ `pc_remote_tools.py` | Tüketir; genişletme OSS PR ile |
| Stub yürütme | ✓ `execute_tool_stub` | `execute_tool_stub` → **real executor** swap |
| Onay kapısı | ✓ pending disk, HTTP uçları | Aynı sözleşme |
| `surface_blocked` | ✓ regex probe | **Aynı red listesi** — gevşetilmez |
| Mobile onay UI | Demo (web/CLI) | Native Lumos Mobile |
| LAN relay | OSS demo | Üretim tüneli |
| Platform API (AX, OCR, ShellExecute) | **Yok** | macOS / Windows implementasyon |
| `SECURITY_NEVER_AUTO` | ✓ `profiles.py` tek kaynak | Import/sync; override yok |
| Audit | EC v1, guard_audit, policy log | Genişletilmiş execution audit (private) |

**Swap noktası:** `execute_tool_stub` fonksiyonunun private implementasyonla değiştirilmesi; HTTP/şema/onay sözleşmesi **değişmez**.

---

## 12. Asla otomatik kurallar — tam liste

Aşağıdaki kurallar profil (`rapor`, `guvenli_yurut`, `kisitli_otonom`), genel onay (`general_approval`) ve mobile onaydan **bağımsız** olarak otomatik yürütme için **yasaktır**.

| # | Kural | NEVER_AUTO / kaynak |
|---|-------|---------------------|
| 1 | Kalıcı dosya silme (`delete_permanent`, OS `unlink`/`rm`) | `permanent_delete` |
| 2 | Trash verb probe ile tüm silme yüzeyi (OS executor) | `permanent_delete` + `surface_blocked` |
| 3 | Dış servise kontrolsüz yazma (API POST, upload, webhook) | `external_write` |
| 4 | Pano yazma (`pc_set_clipboard` vb.) | `external_write` |
| 5 | Geri dönüşsüz kullanıcı işlemi — otomatik klavye (`pc_type_text`) | `irreversible_user_op` |
| 6 | Uygulama install/uninstall otomatik | `irreversible_user_op` + `critical_system_config` |
| 7 | `pc_quit_app` otomatik | `irreversible_user_op` |
| 8 | Otomatik UI tıklama (`pc_click`) | `irreversible_user_op` |
| 9 | Shell / terminal / subprocess otomatik | `irreversible_user_op` + `surface_blocked` |
| 10 | Kritik sistem ayarı değiştirme otomatik | `critical_system_config` |
| 11 | Firewall kuralı değiştirme otomatik | `critical_system_config` |
| 12 | VPN / proxy / DNS override otomatik | `critical_system_config` |
| 13 | Kullanıcı hesabı / TCC / AX izin değiştirme otomatik | `critical_system_config` |
| 14 | `STEP_TYPE_EXTERNAL` adımlar | `DECISION_LAYER_NEVER` |
| 15 | `STEP_TYPE_CRITICAL` adımlar | `DECISION_LAYER_NEVER` |
| 16 | Onay red sonrası otomatik yeniden deneme | ADR-012 C6 / mobile MVP §8 |
| 17 | `KANDO_BRIDGE_SECRET` Mobile'a otomatik/sync ile taşıma | mobile MVP §3 |
| 18 | Credential exfil otomatik | ADR-012 C6 |

**Toplam asla otomatik kural sayısı: 18**

**NEVER kategorileri (5 kullanıcı kategorisi + sözleşme kümesi):**

1. **Dosya silme** — kalıcı silme ve OS silme yüzeyi
2. **Uygulama kurma** — install/uninstall; otomatik açma bile onaysız değil
3. **Terminal erişimi** — shell/exec tam blok
4. **Sistem ayarları** — `critical_system_config`
5. **Ağ ayarları** — firewall/VPN/proxy/DNS; ayrıca `external_write`

**Canonical `SECURITY_NEVER_AUTO` üyeleri (4):** `permanent_delete`, `external_write`, `irreversible_user_op`, `critical_system_config`

---

## Kaynak dosya özeti

| Dosya | Rol |
|-------|-----|
| `src/task_engine/profiles.py` | `SECURITY_NEVER_AUTO`, mapping, profil matrisi |
| `src/policy/action_policy.py` | `DELETE_PERMANENT`, `check_policy`, `is_never_auto_policy_action` |
| `docs/decisions/ADR-012-lumos-security-codex.md` | C1–C6 codex |
| `docs/lumos-karar-sozlesmesi.md` | Karar katmanları, trash, açık onay |
| `packages/kando_bridge/.../pc_remote_tools.py` | `_BLOCKED_SURFACE_RE`, `COMMAND_SPECS`, onay kapısı |
| `packages/kando_runtime/.../controlled_bridge.py` | `surface_blocked`, workspace sandbox |
| `docs/analysis/lumos-pc-device-commands-roadmap.md` | P0/P1/P2, NEVER aday komutlar |

---

## Sonraki adım (tek)

Private repoda P0 salt okuma executor'ını (`pc_read_screen_state`, `pc_get_active_window`) swap etmeden önce §10 checklist'ini madde madde doğrula; OSS'te değişiklik gerekmiyorsa yalnızca private tarafta uygula.
