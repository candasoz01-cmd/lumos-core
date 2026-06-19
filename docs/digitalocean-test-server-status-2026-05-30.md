# DigitalOcean Test Sunucusu Durum Notu (2026-05-30)

**Status:** Moved to private ops vault (2026-06-19, PR #252 revision)

Full status note: `<PRIVATE_OPS_RUNBOOK>` → `.lumos/internal/ops-vault/migration-2026-06-19/digitalocean-test-server-status-2026-05-30.md`

See also: [`ops-runbooks-private-notice.md`](ops-runbooks-private-notice.md) · [`ops-runbooks-migration-index.md`](ops-runbooks-migration-index.md)

---

## High-level summary (public)

- Status snapshot for a new DigitalOcean test droplet provisioned for Lumos backend validation.
- **Purpose:** Test/access verification server — not production; small RAM footprint with swap.
- **Backend:** Node backend managed via process manager; health and feed endpoints verified live.
- **Database:** SQLite via Prisma; schema push completed for test environment.
- **Network:** Firewall enabled with selective port allow rules — specific ports in `<PRIVATE_OPS_RUNBOOK>`.
- **SSH:** Root access on `<SSH_PORT>` at `<SERVER_IP>` — connection details in vault only.
- **Validation (2026-05-30):** Health endpoint OK, feed returned test post, PM2 process online.
- **Note:** Previous droplet retained as reference; not deleted during this migration.
