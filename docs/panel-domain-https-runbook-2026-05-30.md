# panel.welockai.com — Domain + HTTPS + Erişim Kontrolü Runbook (2026-05-30)

**Status:** Moved to private ops vault (2026-06-19, PR #252 revision)

Full operational runbook: `<PRIVATE_OPS_RUNBOOK>` → `.lumos/internal/ops-vault/migration-2026-06-19/panel-domain-https-runbook-2026-05-30.md`

See also: [`ops-runbooks-private-notice.md`](ops-runbooks-private-notice.md) · [`ops-runbooks-migration-index.md`](ops-runbooks-migration-index.md)

---

## High-level summary (public)

- Step-by-step runbook for serving the Lumos panel over HTTPS on a dedicated subdomain with access control.
- Uses **Mod C**: pause for user approval before each risky/live step; the runbook alone does not authorize changes.
- **Primary access control:** Cloudflare Access; Nginx basic auth is a temporary fallback only.
- **DNS:** `panel` A record pointing to `<SERVER_IP>`; start DNS-only (grey cloud), enable proxy after Nginx validation.
- **Nginx:** Separate server block for static panel files, distinct from the API reverse proxy block.
- **HTTPS:** TLS termination via Certbot or Cloudflare proxy — decision depends on subscription and origin setup.
- **Panel API base:** Defaults to the public HTTPS API domain; panel static origin moves from local dev server to Nginx in production.
- **SSH / server commands:** Not in public repo — see `<PRIVATE_OPS_RUNBOOK>` at `<SSH_PORT>` on `<SERVER_IP>`.
