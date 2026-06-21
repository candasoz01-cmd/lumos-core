# PR-RB-07 — OpenAI Tool-Loop Adapter E2E Doğrulama Raporu

**Tarih:** 2026-06-22  
**Repo:** `/Users/candasoz/work_2026/lumos-core`  
**Dal:** `feat/pr-rb-07-openai-tool-loop-adapter` (commit `0f4259a`)  
**PR:** [#516 — feat: OpenAI tool-loop adapter MVP (PR-RB-07)](https://github.com/candasoz01-cmd/lumos-core/pull/516)  
**Genel zincir kararı:** **partial** — adapter → bridge → onay → stub zinciri CI'da kanıtlandı; canlı OpenAI, gerçek mobil UI ve OS executor henüz yok.

---

## 1. Zincir özeti

```mermaid
sequenceDiagram
    participant OAI as OpenAI Responses API
    participant Mock as mock_openai_response_payload
    participant Adp as openai_tool_adapter
    participant Bridge as POST /tools/execute
    participant Disk as .lumos/pending_approvals
    participant Mob as mobile_approval_client
    participant Stub as execute_tool_stub

    alt CI / --mock (varsayılan)
        Mock->>Adp: function_call pc_open_url
    else --live + OPENAI_API_KEY
        OAI->>Adp: responses.create(tools=...)
    end

    Adp->>Adp: parse_openai_tool_calls()
    Adp->>Adp: tool_call_to_execute_body()
    Adp->>Bridge: post_tools_execute (token yok)
    Bridge->>Stub: handle_tools_execute_body()
    Stub->>Disk: _persist_pending_approval()
    Stub-->>Adp: status=pending_approval

    alt auto_approve=True (varsayılan)
        Adp->>Mob: approve_pending(id, token)
        Mob->>Bridge: POST /approve
        Adp->>Bridge: post_tools_execute (+ token)
        Bridge->>Stub: execute_tool_stub (onaylı)
        Stub->>Disk: used=true
        Stub-->>Adp: status=stub, simulated.url
    else auto_approve=False
        Adp-->>Adp: stage=pending (bekle)
    end

    Note over Mob,Stub: LAN relay (RB-06): /relay/approve ayrı testte;<br/>openai adapter doğrudan bridge HTTP kullanır.
```

**Kod giriş noktaları:**

| Adım | Modül | Fonksiyon |
|------|--------|-----------|
| Parse | `openai_tool_adapter.py` | `parse_openai_tool_calls`, `run_openai_response_loop` |
| Bridge POST | `openai_tool_adapter.py` | `post_tools_execute` → `mobile_approval_client.http_json` |
| Execute gövdesi | `pc_remote_tools.py` | `handle_tools_execute_body` → `execute_tool_stub` |
| HTTP route | `server.py` | `BridgeHandler._handle_tools_execute` |
| Onay | `openai_tool_adapter.py` | `approve_and_reexecute` → `approve_pending` |
| Demo CLI | `scripts/openai_tool_loop_demo.py` | `main()` |

---

## 2. Adım adım doğrulama tablosu

| # | Soru | Sonuç | Kanıt |
|---|------|-------|-------|
| 1 | OpenAI tool call üretiliyor mu? | **pass** (mock); **partial** (live) | Mock: `mock_pc_open_url_response()` → `type=function_call`, `name=pc_open_url` (`openai_tool_adapter.py` L58–66). Parse: `test_parse_mock_pc_open_url_shapes` geçti. Live: `fetch_live_openai_response()` OpenAI Responses API çağırır (L345–369); CI'da ağ/API key yok, test edilmedi. |
| 2 | Tool call pending approval oluşturuyor mu? | **pass** | `execute_tool_stub` onay kapısında `_persist_pending_approval` → `status=pending_approval` (`pc_remote_tools.py` L457–483). Test: `test_openai_tool_loop_post_tools_execute_pending`, `test_openai_tool_loop_pending_without_auto_approve`. |
| 3 | Mobile approval görüyor mu? | **partial** | RB-05: `list_pending_pc_remote()` aynı disk kaydını okur (`test_mobile_approval_mvp_e2e_pc_open_url` L137–141). PR-RB-07 e2e **OpenAI → poll list** kombinasyonunu test etmez; varsayılan `auto_approve=True` mobil beklemeyi atlar (`run_tool_call_loop` L271, L301–308). Gerçek Lumos Mobile UI bu PR kapsamı dışında (private). |
| 4 | Approve sonrası bridge komutu çalışıyor mu? | **pass** | `approve_and_reexecute`: onay → token ile tekrar `post_tools_execute` (`openai_tool_adapter.py` L222–263). Test: `test_openai_tool_loop_adapter_mvp_e2e` → `stage=executed`, `execute.ok=True`. Manuel yol: `test_openai_tool_loop_manual_approve_path`. |
| 5 | `pc_open_url` stub tetikleniyor mu? | **pass** | Onay sonrası `execute_tool_stub` → `CMD_OPEN_URL` dalı `simulated.action=open_url`, `simulated.url=...` (`pc_remote_tools.py` L532–533). Test: `test_openai_tool_loop_adapter_mvp_e2e` L159–160 assert `execute["status"]=="stub"`, `simulated["url"]=="https://example.com"`. |
| 6 | Hangi noktalar hâlâ mock/stub? | — | Bkz. §3. |
| 7 | OS executor öncesi eksikler? | — | Bkz. §4. |

---

## 3. Mock / stub noktaları listesi

| Katman | Konum | Davranış |
|--------|--------|----------|
| OpenAI yanıtı | `mock_openai_response_payload`, `mock_pc_open_url_response` | CI ve `--mock` demo; gerçek model çağrısı yok |
| OpenAI canlı mod | `fetch_live_openai_response` | Opsiyonel; `OPENAI_API_KEY` gerekir; pytest kapsamı dışı |
| Tool yürütme | `execute_tool_stub` (`pc_remote_tools.py` L406+) | Tüm komutlar `status=stub`, `stub_only=True`; gerçek OS API yok |
| Bridge HTTP (testler) | `test_openai_tool_loop_adapter_mvp.py` `_dispatch_http` | Canlı `BridgeHandler` sunucusu yok; in-process handler stub |
| Onay otomasyonu | `run_tool_call_loop(..., auto_approve=True)` varsayılan | Programatik `approve_pending`; gerçek mobil kullanıcı beklemesi yok |
| Demo CLI onay | `openai_tool_loop_demo.py` | `--no-auto-approve` ile durabilir; yine poll client/UI yok |
| LAN relay | `openai_tool_loop_demo.py` L33–36, L74–81 | Env set edilir ama `run_openai_response_loop` relay kullanmaz; relay onayı ayrı test (`test_openai_tool_loop_via_lan_relay_approve`) |
| Çok tur tool loop | `tool_result_for_model` | Model'e geri besleme tanımlı (L372–381) ama demo/loop'ta kullanılmıyor |
| `pc_read_screen` vb. | `execute_tool_stub` | Demo snapshot; gerçek ekran okuma yok |

---

## 4. OS executor öncesi eksikler

1. **Executor swap (private katman):** `execute_tool_stub` → gerçek OS executor (`pc_open_url` için `open` / `xdg-open` / platform API). Plan: `lumos-pc-remote-bridge-plan.md` §11 sonraki adım.
2. **Mobil onay UX (auto_approve kaldırma):** Üretim akışında `auto_approve=False` + Lumos Mobile poll/push; OpenAI-origin pending için `requested_by=openai_tool_adapter` izlenebilirliği ve mobil ekran wire'ı.
3. **Canlı uçtan uca:** Çalışan bridge HTTP sunucusu + (opsiyonel) LAN relay + mobil istemci + `--live` OpenAI; mevcut testler in-process stub ile sınırlı.
4. **OpenAI multi-turn loop:** `tool_result_for_model` çıktısının Responses API'ye ikinci tur olarak gönderilmesi; şu an tek tur execute özeti.
5. **OpenAI → mobil poll birleşik test:** `run_openai_response_loop(auto_approve=False)` → `list_pending_pc_remote()` → manuel onay senaryosu için dedicated e2e yok (RB-05 + RB-07 ayrı kanıtlanmış).
6. **PR merge:** #516 açık; `main`'de henüz yok (RB-06 merge `fd46c10` sonrası).

**En kritik 3 boşluk (OS executor öncesi):**

1. `execute_tool_stub` → gerçek platform executor (private swap noktası).
2. Mobil onay yüzeyi — `auto_approve` yerine gerçek kullanıcı onayı (poll UI / push).
3. Canlı stack doğrulaması — bridge sunucusu + relay + isteğe bağlı live OpenAI (pytest dışı smoke).

---

## 5. Test sonuçları

**Komut:**

```bash
pytest tests/test_openai_tool_loop_adapter_mvp.py \
       tests/test_mobile_approval_mvp_e2e.py \
       tests/test_lan_relay_mvp_e2e.py -v
```

**Özet:** 21 test, **21 passed**, 1.25s (2026-06-22, yerel).

| Dosya | Test sayısı | Sonuç |
|-------|-------------|-------|
| `test_openai_tool_loop_adapter_mvp.py` | 7 | 7 passed |
| `test_mobile_approval_mvp_e2e.py` | 4 | 4 passed |
| `test_lan_relay_mvp_e2e.py` | 10 | 10 passed |

**PR-RB-07 odak testleri:**

- `test_openai_tool_loop_adapter_mvp_e2e` — mock OpenAI → pending → approve → stub → `used=true`
- `test_openai_tool_loop_via_lan_relay_approve` — pending → LAN relay `/relay/approve` → stub execute
- `test_openai_tool_loop_manual_approve_path` — `auto_approve=False` → manuel `approve_pending` → stub

---

## 6. PR-RB-07 merge durumu

| Alan | Durum |
|------|--------|
| Dal | `feat/pr-rb-07-openai-tool-loop-adapter` @ `0f4259a` |
| `main` | PR-RB-07 **merge edilmedi** (`main` HEAD: `fd46c10` — PR-RB-06) |
| PR #516 | **OPEN**, mergeable |
| CI (PR branch) | `test`, `ui-smoke`, `ui-e2e`: **SUCCESS**; Bugbot in progress (2026-06-21 snapshot) |
| Değişen dosyalar (vs main) | `openai_tool_adapter.py`, `openai_tool_loop_demo.py`, `test_openai_tool_loop_adapter_mvp.py`, plan docs, `pending_approvals.py` (approval_id entropy) |

**PR tamamlanmış mı?** Kod ve testler MVP için **tamam**; merge bekliyor. Canlı OpenAI ve gerçek OS executor bilinçli olarak kapsam dışı.

---

## 7. Sonraki güvenli adım

**PR #516'yı merge et** (CI yeşil, kapsam OSS/demo-safe). Merge sonrası private katmanda tek adım: `execute_tool_stub` içinde `pc_open_url` için executor swap tasarımı — public repo'ya gerçek OS otomasyonu eklemeden.

---

## Ek: Kod referansları (zincir kanıtı)

**Mock tool call → parse:**

```58:66:packages/kando_bridge/src/kando_bridge/openai_tool_adapter.py
def mock_pc_open_url_response(*, url: str = "https://example.com") -> dict[str, Any]:
    """Canned Responses API output item for CI and ``--mock`` demo."""
    return {
        "id": "fc_mock_pc_open_url",
        "type": "function_call",
        "name": CMD_OPEN_URL,
        "call_id": "call_mock_pc_open_url",
        "arguments": json.dumps({"url": url}, ensure_ascii=False),
    }
```

**Loop: execute → pending veya approve → execute:**

```286:322:packages/kando_bridge/src/kando_bridge/openai_tool_adapter.py
    body = tool_call_to_execute_body(tool_call)
    status, first = post_tools_execute(body, http_fn=http_fn)

    if first.get("status") == "stub" and first.get("ok"):
        return {"ok": True, "stage": "direct", "execute": first, "http_status": status}

    if first.get("status") != "pending_approval":
        return {
            "ok": False,
            "stage": "error",
            ...
        }

    if not auto_approve:
        return {
            "ok": False,
            "stage": "pending",
            ...
        }

    exec_status, loop_out = approve_and_reexecute(
        tool_call,
        first,
        http_fn=http_fn,
        approve_fn=approve_fn,
    )
```

**Stub `pc_open_url` simülasyonu:**

```532:533:packages/kando_bridge/src/kando_bridge/pc_remote_tools.py
    elif command == CMD_OPEN_URL:
        base["simulated"] = {"action": "open_url", "url": str(arguments.get("url") or "")}
```

**E2E test beklentisi:**

```147:166:tests/test_openai_tool_loop_adapter_mvp.py
def test_openai_tool_loop_adapter_mvp_e2e(adapter_bridge_env: Path) -> None:
    """Mock OpenAI → bridge pending → approve → stub execute → used=true."""
    ...
    results = run_openai_response_loop(payload, auto_approve=True)
    ...
    assert result["stage"] == "executed"
    ...
    assert execute["status"] == "stub"
    assert execute["simulated"]["url"] == "https://example.com"
    ...
    assert disk[1]["used"] is True
```
