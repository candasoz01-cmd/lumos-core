# AnchorUSB Core

Encrypted `.vault` container library for AnchorUSB MVP (Week 1–2).

**Local only** — no network, no external notification, no telemetry.

## Features

- `.vault` file format: 256-byte header + AES-256-GCM payload + append-only event log
- Argon2id key derivation from passphrase
- APIs: `create_vault`, `unlock_vault`, `lock_vault`, `vault_status`, `export_report`
- Hash-chained event log: `INITIALIZED`, `UNLOCKED`, `LOCKED`, `IO_SUMMARY`, `ACCESS_DENIED`, `SUSPICIOUS_FLAG`
- **S4 detector:** failed unlock threshold (default 5) sets local `SUSPICIOUS` flag + log event
- **S6 export:** user-initiated JSON report (no secrets)
- **Plugin registry:** built-in `audit` plugin; external plugins require `ANCHORUSB_ENABLE_EXTERNAL_PLUGINS=1`

## Quick start

```bash
# From repo root
cargo build -p anchorusb-cli --release
export PATH="$PWD/target/release:$PATH"

# Create vault (S1)
ANCHORUSB_PASSPHRASE='your-strong-passphrase' \
  anchorusb init --path /tmp/usb-demo/vault.vault

# Unlock (S2)
ANCHORUSB_PASSPHRASE='your-strong-passphrase' \
  anchorusb unlock --path /tmp/usb-demo/vault.vault

# Status (shows suspicious banner if threshold exceeded)
anchorusb status --path /tmp/usb-demo/vault.vault

# Export report (S6 — user-initiated only)
anchorusb export-report --path /tmp/usb-demo/vault.vault --output /tmp/report.json

# Lock (S5)
anchorusb lock
```

Use any directory path instead of a real USB mount; MVP simulates portable storage via file path.

## export-report JSON

The report includes vault metadata (no salt, passphrase, or keys), the full event log chain, `suspicious` flag, `access_denied_count`, and `flags` (e.g. `SUSPICIOUS`, `ACCESS_DENIED_THRESHOLD`). Export never runs automatically.

## Plugins

| Plugin | Default | Enable |
|--------|---------|--------|
| `audit` | on | always (local stderr echo) |
| external / enterprise | off | `ANCHORUSB_ENABLE_EXTERNAL_PLUGINS=1` |

External plugins are never auto-enabled.

## Tests

```bash
cargo test -p anchorusb-core -p anchorusb-cli
```

## Lifecycle stages

| Stage | CLI / API |
|-------|-----------|
| S0 — unknown device | `status` → `not_found` |
| S1 — first setup | `init` |
| S2 — unlock | `unlock` |
| S4 — suspicious detection | failed unlock ×5 → banner + `SUSPICIOUS_FLAG` |
| S5 — lock | `lock` |
| S6 — export report | `export-report` |

## Docs

- [`docs/analysis/secure-device/anchorusb-mvp-plan.md`](../../docs/analysis/secure-device/anchorusb-mvp-plan.md)
- [`docs/analysis/secure-device/anchorusb-technical-architecture.md`](../../docs/analysis/secure-device/anchorusb-technical-architecture.md)
- [`docs/analysis/secure-device/anchorusb-lifecycle.md`](../../docs/analysis/secure-device/anchorusb-lifecycle.md)
