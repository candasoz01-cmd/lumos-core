# Leftover cleanup & final src layout

## 1. Check: `src/src` and `src/security.bak_lock`

- **src/src** — **Not present** (already removed or never in this tree). No code references.
- **src/security.bak_lock** — **Not present**. No code imports it; only mentioned in docs as legacy backup.
- `.gitignore` already contains `src/security.bak_lock/` and `src/src/` so they stay ignored if reintroduced.

**Action:** Nothing to remove; both directories are absent.

## 2. Removal

Skipped — no directories to remove.

## 3. Tests after cleanup

```
python3 -m pytest -q
115 passed in 8.69s
```

## 4. Final src layout

```
src/
├── main.py                    # stub → lumos_core.interactive_cli
├── scripts/                   # README only (logic in lumos_core.scripts)
├── .lumos/                    # runtime (if present)
└── lumos_core/                # single top-level package
    ├── ai_providers/
    ├── context/
    ├── core/
    ├── device/
    ├── engine/
    ├── memory/
    ├── policy/
    ├── scripts/
    ├── security/
    │   └── entropy/
    │       └── providers/
    ├── system/
    ├── tools/
    └── ui/
```

- **76** `.py` files under `src` (excluding `__pycache__` and `*.bak*`).
- No `src/src` or `src/security.bak_lock` in the tree.
