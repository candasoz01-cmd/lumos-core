# DigitalOcean SSH Erişim Kurtarma Notu

**Status:** Moved to private ops vault (2026-06-19, PR #252 revision)

Full recovery notes: `<PRIVATE_OPS_RUNBOOK>` → `.lumos/internal/ops-vault/migration-2026-06-19/digitalocean-ssh-recovery.md`

See also: [`ops-runbooks-private-notice.md`](ops-runbooks-private-notice.md) · [`ops-runbooks-migration-index.md`](ops-runbooks-migration-index.md)

---

## High-level summary (public)

- Recovery plan for restoring SSH access to a DigitalOcean droplet without destroy, rebuild, or base-image restore.
- **Symptom:** External SSH on default port timing out; Web Console authentication intermittently failing.
- **Goal:** Regain SSH with minimum changes; read service state before any write.
- **In-droplet checks:** ssh service status, enable/start ssh, port listen state, firewall status — details in `<PRIVATE_OPS_RUNBOOK>`.
- **Rules:** No destroy/rebuild; no risky system changes without snapshot; data-loss operations prohibited.
- **External test:** From operator machine via SSH to `<SERVER_IP>` on `<SSH_PORT>` — command in vault only.
- **Key management:** authorized_keys verification steps documented in `<PRIVATE_OPS_RUNBOOK>`.
