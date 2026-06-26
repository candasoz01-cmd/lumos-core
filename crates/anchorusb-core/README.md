# AnchorUSB Core

Encrypted `.vault` container library for AnchorUSB MVP (Week 1).

**Local only** — no network, no external notification, no telemetry.

## Features

- `.vault` file format: 256-byte header + AES-256-GCM payload + append-only event log
- Argon2id key derivation from passphrase
- APIs: `create_vault`, `unlock_vault`, `lock_vault`, `vault_status`
- Hash-chained event log: `INITIALIZED`, `UNLOCKED`, `LOCKED`, `IO_SUMMARY`, `ACCESS_DENIED`

## Quick start

```bash
# From repo root
cargo build -p anchorusb-cli --release
export PATH="$PWD/target/release:$PATH"

# Create vault (S1)
ANCHORUSB_PASSPHRASE='your-strong-passphrase' \
  anchorusb init --path /tmp/usb-demo/vault.vault

# Unlock (S2) — passphrase via env for scripts; omit for interactive prompt
ANCHORUSB_PASSPHRASE='your-strong-passphrase' \
  anchorusb unlock --path /tmp/usb-demo/vault.vault

# Status
anchorusb status --path /tmp/usb-demo/vault.vault

# Lock (S5)
anchorusb lock
```

Use any directory path instead of a real USB mount; Week 1 simulates portable storage via file path.

## Tests

```bash
cargo test -p anchorusb-core
```

## Lifecycle stages (Week 1)

| Stage | CLI / API |
|-------|-----------|
| S0 — unknown device | `status` → `not_found` |
| S1 — first setup | `init` |
| S2 — unlock | `unlock` |
| S5 — lock | `lock` |

S3–S7 (detection, export, recovery) are Week 2+.

## Docs

- [`docs/analysis/secure-device/anchorusb-mvp-plan.md`](../../docs/analysis/secure-device/anchorusb-mvp-plan.md)
- [`docs/analysis/secure-device/anchorusb-technical-architecture.md`](../../docs/analysis/secure-device/anchorusb-technical-architecture.md)
- [`docs/analysis/secure-device/anchorusb-lifecycle.md`](../../docs/analysis/secure-device/anchorusb-lifecycle.md)
