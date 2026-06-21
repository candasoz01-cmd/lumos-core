# PR-RB-07 — OpenAI Tool-Loop + Mobile Web UI Doğrulama

**Tarih:** 2026-06-22  
**Dal:** `feat/mobile-approve-reject-ui`  
**Kapsam:** `auto_approve` kaldırma (varsayılan `False`) + LAN relay mobile web UI (`GET /relay/mobile`)

---

## Değişiklik özeti

| Alan | Önce | Sonra |
|------|------|-------|
| `run_tool_call_loop` / `run_openai_response_loop` | `auto_approve=True` varsayılan | **`auto_approve=False`** — pending mobil/CLI onayına kadar kalır |
| Demo CLI | `--no-auto-approve` | **`--auto-approve`** dev-only (uyarı); `--wait-approve` poll |
| Mobile onay yüzeyi | CLI poll only | **`GET /relay/mobile`** responsive web UI (Onayla / Reddet) |
| Pair yanıtı | `relay_token` only | + `mobile_url` → `/relay/mobile?token=…` |

---

## Mobile UI

- **Yol:** `GET /relay/mobile` (LAN relay, varsayılan `:8766`)
- **Pairing:** `POST /relay/pair` → `mobile_url` alanı; telefon: `http://<PC_IP>:8766/relay/mobile?token=…`
- **Davranış:** 5 sn poll `/relay/pending`; `X-Relay-Token` sessionStorage; Onayla → `POST /relay/approve`, Reddet → `POST /relay/reject`
- **Alanlar:** `command`, `risk_level`, `required_user_action`, `expires_at`, `arguments_preview`

---

## Demo akışı (telefon + PC)

1. PC: köprü + relay başlat (`lan_relay_server.py --host 0.0.0.0`)
2. PC: `openai_tool_loop_demo.py --mock` → pending + stderr'de mobile UI URL
3. Telefon (aynı LAN): pair (`mobile_approval_client pair CODE`) → Mobile UI linkini aç
4. Telefon: pending listede **Onayla**
5. PC: `--wait-approve` ile otomatik re-execute veya adapter'ı manuel tamamla

---

## Testler

```bash
PYTHONPATH=src:packages/kando_bridge/src \
  pytest -q tests/test_openai_tool_loop_adapter_mvp.py \
         tests/test_lan_relay_mvp_e2e.py
```

- `test_openai_tool_loop_default_stays_pending` — varsayılan pending
- `test_openai_tool_loop_adapter_mvp_e2e` — manuel `approve_pending` + re-execute
- `test_relay_mobile_ui_route` — HTML 200 + approve button
- `test_pair_returns_mobile_url` — pair yanıtında mobile URL

---

## auto_approve

**Kaldırıldı (varsayılan bypass yok).** Dev-only: `run_*_loop(..., auto_approve=True)` veya demo `--auto-approve`.
