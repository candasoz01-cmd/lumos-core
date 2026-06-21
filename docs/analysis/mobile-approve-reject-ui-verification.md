# Mobile Approve/Reject UI — Doğrulama Raporu

**Tarih:** 2026-06-22  
**Analiz dalı:** `feat/mobile-approve-reject-ui` (commit `4d6f001`)  
**PR:** [#517](https://github.com/candasoz01-cmd/lumos-core/pull/517) — **OPEN**, henüz `main`'e merge edilmedi  
**Karşılaştırma:** `main` üzerinde `GET /relay/mobile` yok; `auto_approve=True` varsayılan devam ediyor

---

## 1. Doğrulama özeti tablosu

| # | Soru | Sonuç | Kanıt |
|---|------|-------|-------|
| 1 | Auto approve tamamen kaldırıldı mı? | **partial** | Varsayılan bypass kaldırıldı (`auto_approve=False`); dev-only bypass hâlâ mevcut (`--auto-approve`, `auto_approve=True` parametresi). `main`'de varsayılan hâlâ `True`. |
| 2 | Onay verilmezse işlem sonsuza kadar bekliyor mu? | **partial** | Adapter/demo process sonsuza kadar bloklamaz; disk kaydı expire olana kadar kalır. `--wait-approve` ile en fazla `--wait-timeout` (varsayılan 120 sn). |
| 3 | Expire süresi var mı? | **pass** | `DEFAULT_TTL_SECONDS=900`, `expires_at` alanı, `mark_expired_if_needed`, `test_expired_pending_rejected`. |
| 4 | Reject sonrası kayıt nasıl tutuluyor? | **pass** | `status=rejected`, `rejected_at` yazılır; kayıt diskte kalır; `used` değişmez; pending listesinden düşer. |
| 5 | Aynı approval iki kez kullanılabiliyor mu? | **pass** (kod) / **partial** (test) | Yürütme sonrası `used=true`; `validate_approval_token` → `approval_already_used`. Çift-yürütme reddi için ayrı test yok. |
| 6 | Approval token replay koruması var mı? | **pass** (kod) / **partial** (test) | Token eşleşmesi zorunlu; `used` + `expired` + `rejected` kontrolleri. Replay senaryosu için özel test yok. |

**Genel karar:** Dal, mobil onay/reject UI ve varsayılan onay bypass kaldırma hedeflerini **büyük ölçüde karşılıyor**; `main`'e merge edilmedi. Eksikler: çift-kullanım/replay negatif testleri, adapter katmanında sonsuz bekleme yok (tasarım gereği).

---

## 2. Auto approve durumu

### Dal (`feat/mobile-approve-reject-ui`)

`run_tool_call_loop` ve `run_openai_response_loop` varsayılanı **`False`**:

```271:309:packages/kando_bridge/src/kando_bridge/openai_tool_adapter.py
    auto_approve: bool = False,
) -> dict[str, Any]:
    """
    Single tool call: bridge execute → pending (if needed) → approve → stub execute.

    Default ``auto_approve=False`` — user must approve via mobile web UI or CLI.
    ...
    if not auto_approve:
        return {
            "ok": False,
            "stage": "pending",
            "pending": first,
            ...
            "message": "approval_required — call approve_and_reexecute after user consent",
        }
```

Demo CLI: opt-in dev bypass (`--auto-approve`, uyarı ile); varsayılan mobil onay akışı:

```167:210:scripts/openai_tool_loop_demo.py
    if args.auto_approve:
        sys.stderr.write(
            "UYARI / WARNING: --auto-approve dev-only bypass; "
            "use mobile UI for real demos.\n"
        )
    ...
    auto_approve = bool(args.auto_approve)
    results = run_openai_response_loop(payload, auto_approve=auto_approve)
    ...
        if args.wait_approve:
            sys.stderr.write("Waiting for approval (--wait-approve)…\n")
            results = _wait_for_manual_approve(calls, results, timeout=args.wait_timeout)
```

### Repo geneli `auto_approve` taraması

| Konum | Davranış |
|-------|----------|
| `openai_tool_adapter.py` | Varsayılan `False`; `True` ile dev bypass |
| `openai_tool_loop_demo.py` | `--auto-approve` opt-in; varsayılan kapalı |
| `server.py` / `agent_runner.py` | **`auto_approve_safe`** — farklı katman (Kando agent); PC remote bridge ile karıştırılmamalı |
| `kando_direct_patch_client.js` | `auto_approve_safe: true` — patch client, PC remote değil |
| `main` branch | `auto_approve: bool = True` (henüz merge yok) |

### Test kanıtı

- `test_openai_tool_loop_default_stays_pending` — varsayılan çağrıda `stage=="pending"`
- `test_openai_tool_loop_pending_without_auto_approve` — açık `auto_approve=False` ile pending

**Sonuç:** Production/demo varsayılan bypass **kaldırıldı**; kod tabanından tamamen silinmedi (dev-only yol bilinçli bırakılmış).

---

## 3. Bekleme davranışı (poll/wait vs infinite)

### Adapter katmanı — anında dönüş

`run_tool_call_loop` onay beklerken **bloklamaz**; `stage: "pending"` ile döner (`ok: false`).

### Demo CLI — opsiyonel poll

| Mod | Davranış |
|-----|----------|
| Varsayılan ( `--wait-approve` yok ) | Pending oluşturulur, stderr'de mobile UI URL yazılır, process **çıkar** |
| `--wait-approve` | 1 sn aralıkla `approve_pending` poll; `--wait-timeout` (default **120 sn**) sonra `approval_timeout` |

```122:158:scripts/openai_tool_loop_demo.py
def _wait_for_manual_approve(..., timeout: float) -> list[dict]:
    deadline = time.time() + max(1.0, timeout)
    ...
        while time.time() < deadline:
            approve_out = approve_pending(approval_id, approval_token)
            if approve_out.get("accepted"):
                ...
                break
            time.sleep(1.0)
        else:
            final.append({..., "error": "approval_timeout", ...})
```

### Mobile web UI — arka plan poll

`GET /relay/mobile` HTML: 5 sn `setInterval(poll)` → `GET /relay/pending` (sonsuz poll, UI tarafında).

### Disk kaydı

Onay gelmezse kayıt `.lumos/pending_approvals/` altında **`status=pending`** kalır; TTL dolunca `expired` olur (bkz. §4). Bu **disk persistence**, process'in sonsuza kadar beklemesi değil.

**Sonuç:** Process/adapter **sonsuz beklemez**; disk kaydı expire veya manuel reject/approve'a kadar kalabilir.

---

## 4. Expire mekanizması (TTL, expires_at, reject on expired)

### Sabitler ve kayıt oluşturma

```27:27:packages/kando_bridge/src/kando_bridge/pending_approvals.py
DEFAULT_TTL_SECONDS = 900
```

```248:268:packages/kando_bridge/src/kando_bridge/pending_approvals.py
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    now = _utc_now()
    expires = now + timedelta(seconds=max(60, ttl_seconds))
    ...
        "expires_at": _iso(expires),
        "status": STATUS_PENDING,
        "used": False,
```

### Süre dolumu işaretleme ve doğrulama

- `mark_expired_if_needed` — pending + `expires_at` geçmişse → `status=expired`, `expired_at` yazar
- `validate_approval_token` — expired/rejected/used kontrolleri
- `approve_pc_remote_pending` — approve/reject öncesi `mark_expired_if_needed` çağrısı

### Test kanıtı

`tests/test_pc_remote_bridge_stubs.py::test_expired_pending_rejected` — süresi dolmuş onaylı kayıt yürütmede `error=="approval_expired"`.

Mobile UI `expires_at` alanını kartta gösterir (`build_mobile_ui_html`).

**Sonuç:** **15 dakika** (900 sn) TTL; minimum 60 sn. Expire sonrası yürütme reddedilir.

---

## 5. Reject kayıt modeli (status field, used flag)

### Reject akışı

```224:228:packages/kando_bridge/src/kando_bridge/pending_approvals.py
def reject_pending_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    record["status"] = STATUS_REJECTED
    record["rejected_at"] = _iso(_utc_now())
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record
```

Bridge handler (`approve_pc_remote_pending`, `approved=False`) → `reject_pending_record`; yanıt `status: rejected`.

### Used flag

Reject sırasında **`used` set edilmez** (yalnızca stub yürütme sonrası `consume_pending_record` → `used=true`).

### Test kanıtı

| Test | Doğrulama |
|------|-----------|
| `test_mobile_approval_reject_flow` | `accepted`, `closed`; pending listesinde yok |
| `test_reject_via_relay` | Relay `/relay/reject` → `accepted`, `closed`; `count==0` |

Kayıt JSON dosyası diskte kalır; yalnızca `status` ve `rejected_at` güncellenir.

---

## 6. Tek kullanımlık token / replay koruması

### Koruma katmanları

1. **Token eşleşmesi** — `validate_approval_token`: birebir `approval_token` zorunlu
2. **Status kapısı** — yalnızca `status==approved` geçer
3. **Used bayrağı** — `used==True` → `approval_already_used`
4. **Expire** — süre dolmuş → `approval_expired`
5. **Reject** — `approval_rejected`
6. **Tüketim** — başarılı stub yürütme sonrası `consume_pending_record`:

```575:581:packages/kando_bridge/src/kando_bridge/pc_remote_tools.py
    if pending_path is not None and repo_root is not None:
        data = find_pending_by_approval_id(...)
        if data is not None:
            consume_pending_record(data[0], data[1])
```

### Test kanıtı (mevcut)

| Test | Ne doğrular |
|------|-------------|
| `test_openai_tool_loop_adapter_mvp_e2e` | Yürütme sonrası `used is True` |
| `test_openai_tool_loop_via_lan_relay_approve` | Relay onay → execute → `used is True` |
| `test_mobile_approval_invalid_token_rejected` | Yanlış token → `invalid_approval_token` |

### Eksik test

- Aynı token ile **ikinci** `POST /tools/execute` → `approval_already_used` assert'i yok
- Onaylanmış ama henüz tüketilmemiş token ile çift approve denemesi testi yok

**Sonuç:** Kod seviyesinde replay koruması **var**; test kapsamı **kısmi**.

---

## 7. Mobile web UI doğrulama

### Route

```560:565:packages/kando_bridge/src/kando_bridge/lan_relay.py
        def do_GET(self) -> None:
            ...
            if path == "/relay/mobile":
                self._send_html(200, build_mobile_ui_html())
                return
```

`main` branch'te bu route **yok** (grep: 0 eşleşme).

### UI kontrolleri

- **Onayla / Approve** — `btn-ok`, `POST /relay/approve`
- **Reddet / Reject** — `btn-no`, `POST /relay/reject`
- 5 sn poll `GET /relay/pending`
- Relay token: URL query `?token=` veya sessionStorage
- Pair yanıtı: `mobile_url` → `/relay/mobile?token=…`

### Test kanıtı

| Test | Assert |
|------|--------|
| `test_relay_mobile_ui_route` | HTTP 200; HTML'de `/relay/approve` |
| `test_build_mobile_ui_html_contains_controls` | `btn-ok`, `btn-no` |
| `test_pair_returns_mobile_url` | `mobile_url.startswith("/relay/mobile?token=")` |
| `test_openai_tool_loop_via_lan_relay_approve` | Uçtan uca relay approve → execute |

---

## 8. Test sonuçları

**Ortam:** `.venv`, `PYTHONPATH=src:packages/kando_bridge/src:packages/kando_runtime/src`, `KANDO_MOCK=1`

### Hedef test paketi (48 test)

```bash
pytest -q \
  tests/test_openai_tool_loop_adapter_mvp.py \
  tests/test_lan_relay_mvp_e2e.py \
  tests/test_mobile_approval_mvp_e2e.py \
  tests/test_pc_remote_bridge_stubs.py
```

**Sonuç:** **48 passed** (~1.6 sn)

### Tam suite

```bash
make test   # veya: pytest -q (repo kökü)
```

**Sonuç:** **1190 passed, 3 skipped** (~17 sn)

### Dal commit kapsamı (`main..HEAD`)

| Dosya | Değişiklik |
|-------|------------|
| `lan_relay.py` | +197 satır — mobile UI HTML, `/relay/mobile`, pair `mobile_url` |
| `openai_tool_adapter.py` | `auto_approve` varsayılan `False` |
| `openai_tool_loop_demo.py` | `--auto-approve`, `--wait-approve`, mobile URL hint |
| `mobile_approval_client.py` | pair sonrası mobile URL stderr |
| `test_lan_relay_mvp_e2e.py` | mobile UI + reject relay testleri |
| `test_openai_tool_loop_adapter_mvp.py` | default pending + manual approve testleri |

---

## 9. Eksikler ve öneriler

### Blocker / merge öncesi

1. **PR #517 merge edilmedi** — `main` hâlâ `auto_approve=True` ve mobile UI'sız; bu rapor dal davranışını doğrular.

### Doğruluğu etkileyen (test boşlukları)

2. **`approval_already_used` negatif testi** — ikinci yürütme denemesi için `test_pc_remote_bridge_stubs` veya adapter E2E'ye ekleme önerilir.
3. **Replay testi** — onaylanmış token ile approve endpoint'e tekrar POST senaryosu.
4. **`--wait-approve` timeout testi** — demo script'te `approval_timeout` çıktısı unit/integration testi yok.

### İyileştirme / opsiyonel

5. **Reject kayıt retention** — rejected kayıtlar diskte kalır; GC/TTL politikası dokümante edilmeli (şu an yalnızca pending listesi filtreler).
6. **Mobile UI E2E** — HTML route testleri var; tarayıcı/Playwright ile buton tıklama E2E yok (statik string assert yeterli MVP için).
7. **`auto_approve_safe` ayrımı** — operatör dokümantasyonunda PC remote `auto_approve` ile Kando agent `auto_approve_safe` ayrımını netleştir.
8. **Subagent ön rapor** — `docs/analysis/pr-rb-07-openai-tool-loop-verification.md` ile uyumlu; bu rapor 6 soruyu kod+test kanıtıyla genişletir.

---

## Ek: Subagent / önceki analiz referansı

- Önceki taslak: `docs/analysis/pr-rb-07-openai-tool-loop-verification.md` (aynı dal, dar kapsam)
- Plan referansı: `docs/analysis/lumos-mobile-approval-mvp-plan.md` § auto_approve / mobile UI

**Rapor dosyası:** `docs/analysis/mobile-approve-reject-ui-verification.md`
