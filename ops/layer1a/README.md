# Layer 1A — read-only production pulse

| Field | Value |
| --- | --- |
| Status | FAZ-2 infrastructure slice (Option B, 2026-08-19) |
| Scope | This directory + `.github/workflows/layer1a.yml` |
| Board task | `OPS-LAYER1A` |

Five deterministic GET checks, a 30-minute cron, and a JSON artifact.
No secrets, no LLM, no panel interaction, no notifications.

## Checks

Default base URL: `https://welockai.com` (override: `LAYER1A_BASE_URL` or `--base-url`).

| id | Request | Pass |
| --- | --- | --- |
| `landing` | `GET /` | HTTP 200 |
| `panel` | `GET /panel` | HTTP 200 |
| `integrations` | `GET /integrations` | HTTP 200 |
| `auth_readiness` | `GET /auth/readiness` | HTTP 200, JSON `ok: true`, no secret values |
| `bridge_fail_closed` | `GET /api/bridge/task` | HTTP 401 or 503 with a documented proxy error code; never 200 |

`bridge_fail_closed` accepts the documented fail-closed codes from
[`api-surface-v1.md`](../../docs/contracts/api-surface-v1.md):
`bridge_proxy_unconfigured`, `bridge_proxy_auth_unconfigured`,
`bridge_proxy_secret_unconfigured`, `bridge_proxy_unauthorized`.

## Run

```bash
python3 ops/layer1a/run.py --output layer1a-result.json
```

Exit 0 when every check passes; exit 1 when any check fails (the JSON is
still written). Stdlib only.

## Cron

`.github/workflows/layer1a.yml` runs every 30 minutes on `main` and on
`workflow_dispatch`. It uploads `layer1a-result.json` as a workflow artifact.
There is no Slack/email/panel notification path.
