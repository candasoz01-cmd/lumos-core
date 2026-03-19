# ADIM 1 — Proje haritası

*Oluşturulma: 2025-03-19. Düzeltme + sağlamlaştırma modu — harita çıkarma.*

---

## 1. Kök dizin (ls özeti)

```
lumos-core/
├── .cursor/          # Cursor kuralları (rules, settings)
├── .githooks/        # pre-commit vb.
├── .github/          # CI workflow (ci.yml)
├── .gitignore
├── .lumos/           # Çalışma anı state (tasks, presence, aliases, …) — canlı veri
├── Makefile          # make test, setup-commit-guard vb.
├── README.md
├── YARIN_DEVAM.txt   # Not dosyası
├── archive/          # Eski main.py yedekleri (refactor_history)
├── backend/          # Node/Express API (feed, post; Prisma)
├── config/           # settings.yaml, permissions.json, contacts.json
├── docs/             # Dokümantasyon (çok sayıda .md)
├── examples/         # Kullanım örnekleri (kando-post-card, lumos senaryoları)
├── logs/             # Log dosyaları (örn. lumos_evolution.jsonl)
├── lumos-quantum/    # Boş/placeholder (sadece .DS_Store görüldü)
├── lumos.py          # Giriş noktası (root)
├── package-lock.json # Root’ta — niyet net değil
├── panel/            # Frontend panel (HTML/CSS/JS)
├── patch_*.sh        # patch_ttl.sh, patch_memory.sh
├── bootstrap*.sh     # bootstrap.sh, bootstrap_dev.sh
├── pyproject.toml
├── pytest.ini
├── scripts/          # Yardımcı scriptler (smoke, demo, analyze_evolution, legacy)
├── src/              # Ana Python uygulaması (Lumos core)
├── test_api.sh       # API test scripti
├── tests/            # Pytest testleri
└── web/              # web/app.py (ayrı web arayüzü?)
```

---

## 2. src/ — ne var, ne işe yarıyor

| Dizin | İşlev (kısa) |
|-------|----------------|
| **cli/** | Komut ayrıştırma (cli_parse), yönlendirme (cli_router), read-only/tasks/notes komutları |
| **context/** | Çalışma bağlamı (context.py) — ince modül |
| **core/** | Çekirdek: state, workspace_contract, lumos_runtime, engine, startup_health, decision/patch/brain/live_brain, log, version, inviolable |
| **device/** | Cihaz: device_guard, device_perception, intent_surface_mapper, contacts, system_monitor, device_action_policy |
| **engine/** | Model erişimi: base_engine, model_client, online_engine |
| **memory/** | Bellek: memory, secure_store, session_memory, schema |
| **policy/** | Karar/offline: offline_engine, decision, rules |
| **security/** | Güvenlik: presence_lock, identity, keystore, crypto, lock, permissions, aliases, request_signer, presence_fsm, entropy |
| **task_engine/** | Görev motoru: engine, profiles, action_registry, device_tasks, observation_engine, planner, queue, executors/, observation/, verification/ |
| **tools/** | Yardımcı: file_classifier, run_classify |
| **ui/** | TUI: tui.py |
| **scripts/** | src içi scriptler (örn. init_keystore) |
| **lumos_core/** | Paket tanımı (egg-info ile birlikte) |
| **main.py** | Ana giriş (CLI/web yönlendirme) |

---

## 3. Panel (frontend)

| Dosya | İşlev |
|-------|--------|
| **index.html** | Tek sayfa giriş |
| **css/app.css** | Stiller |
| **js/app.js** | Ana uygulama mantığı (~52KB) |
| **js/backend-bridge.js** | Backend ile iletişim |
| **js/contracts.js** | Veri sözleşmeleri |
| **js/feed-api.js** | Feed API çağrıları |
| **js/fixtures.js** | Test/örnek veri |
| **js/state_inject.js** | State enjeksiyonu |
| **scripts/read_backend_state.py** | Backend state okuma |

Panel altında çok sayıda .md (BACKEND_*, PANEL_*, CHECKPOINT) — dokümantasyon/geçmiş.

---

## 4. Backend (Node)

- **index.js** — Ana sunucu (~12KB)
- **prisma/** — Şema/DB
- **package.json** — Bağımlılıklar
- **.env** — Ortam (commit dışı)

---

## 5. Config

- **config/settings.yaml** — Ayarlar
- **config/permissions.json** — İzinler
- **config/contacts.json** — Kişiler

---

## 6. Scripts (kök scripts/)

- **analyze_evolution.py**, **demo_decision.py**, **legacy_runner.py**
- **dev_check.sh**, **run.sh**, **smoke_cli.sh**, **smoke_presence.sh**, **smoke_web.sh**, **test.sh**
- **cli_test_commands.txt**
- **legacy/** — Eski scriptler

---

## 7. Temizlik adayları (ADIM 2 için not)

- **.bak / .bak_* / backup / broken** dosyalar:
  - **archive/refactor_history/** — 12 adet eski main.py yedeği (bilinçli arşiv)
  - **src/context/** — context.py.bak, .bak_gate, .bak_unlock
  - **src/core/** — lumos.py.bak_unlock
  - **src/engine/** — model_client.py.bak_full
  - **src/memory/** — memory.py.bak, .bak2; schema.py.bak; secure_store.py.bak2
  - **src/policy/** — offline_engine.py.bak, .bak_fallback_cli, .bak_lock_cli, .bak_unlock; rules.py.bak, .bak_gate
  - **src/security/** — keystore.py.bak2; **security.bak_lock/** — tüm klasör yedek
  - **src/scripts/** — init_keystore.py.bak_fix
- **lumos-quantum/** — Neredeyse boş; niyet net değil.
- **Root package-lock.json** — Proje çoğunlukla Python; backend kendi package-lock’una sahip; root’taki gereksiz olabilir.
- **YARIN_DEVAM.txt** — Geçici not; commit’e girmemesi veya silinmesi tercih edilebilir.
- **PROJE_DOSYA_LISTESI.txt** — Eski liste; .lumos/ ve __pycache__ karışık; güncellenebilir veya kaldırılabilir.

---

## 8. Kritik akış (ADIM 3 için referans)

- **Girdi:** CLI (`src/main.py` → `cli/`) veya web (`web/app.py`) veya panel (panel → backend).
- **Karar/çekirdek:** `core/` (state, workspace_contract, engine, lumos_runtime), `policy/offline_engine`, `task_engine/`.
- **Güvenlik kilidi:** `security/presence_lock`, `security/keystore`, `security/identity`.
- **Çıktı:** CLI çıktısı, web yanıtı, panel (backend → feed-api → app.js).

Bu doküman ADIM 2 (temizlik) ve ADIM 3 (kritik akış sabitleme) için giriş referansı olarak kullanılabilir.
