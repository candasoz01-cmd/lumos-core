# Backend Domain + HTTPS + Reverse Proxy Geçiş Planı (2026-05-30)

**Status:** Moved to private ops vault (2026-06-19, PR #252 revision)

Full operational plan: `<PRIVATE_OPS_RUNBOOK>` → `.lumos/internal/ops-vault/migration-2026-06-19/backend-domain-https-reverse-proxy-plan-2026-05-30.md`

See also: [`ops-runbooks-private-notice.md`](ops-runbooks-private-notice.md) · [`ops-runbooks-migration-index.md`](ops-runbooks-migration-index.md)

---

## High-level summary (public)

- Migration plan from IP-based HTTP test access to domain + HTTPS + Nginx reverse proxy for the Lumos backend.
- **Target architecture:** Client → HTTPS :443 → Nginx → loopback backend on port 3000; public port 3000 to be closed after HTTPS validation.
- **DNS:** Cloudflare A record (`api` or `lumos-api` subdomain) → `<SERVER_IP>`.
- **SSL options:** Certbot (Let's Encrypt) on origin, or Cloudflare edge TLS — choice depends on proxy mode and subscription status.
- **Priority:** `api.welockai.com` as the production API hostname; IP-based access treated as test-only.
- **Validation milestones:** DNS propagation, Nginx config test, HTTPS health check, panel feed via HTTPS API domain.
- **Operational commands** (SSH, nginx -t, certbot, ufw): `<PRIVATE_OPS_RUNBOOK>` only — not in public repo.
