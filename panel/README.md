# panel/scripts — canlı köprü sunucuları

Statik legacy panel uygulaması **`archive/panel/`** altına taşındı (Seçenek C — PR #319).

Bu dizinde yalnızca **canlı** köprü betikleri kalır:

| Script | Port | Kullanım |
|--------|------|----------|
| `panel_tasks_server.py` | 8766 (varsayılan) | Görev CRUD API — `ui/` E2E, evidence continuity testleri, yerel dev |
| `read_backend_state.py` | — | Salt okuma backend snapshot → panel contract |

**Çalıştırma:**

```bash
python3 panel/scripts/panel_tasks_server.py
```

**Birincil üretim paneli:** `ui/src/pages/panel.astro` → `welockai.com/panel`

**Legacy statik panel + E2E:** `archive/panel/` — `npm run e2e:legacy:*` (kök `package.json`)

Karar: [`docs/memory/od-panel-retirement-option-c-decision.md`](../docs/memory/od-panel-retirement-option-c-decision.md)
