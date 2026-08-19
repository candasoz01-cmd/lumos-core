# Layer 1A — read-only production pulse

| Field | Value |
| --- | --- |
| Status | FAZ-2 infrastructure slice (Option B, 2026-08-19) — draft until this contract holds |
| Scope | This directory + `.github/workflows/layer1a.yml` |
| Board task | `OPS-LAYER1A` |

Five deterministic GET checks, a 30-minute cron, and a JSON artifact.
No secrets, no LLM, no panel writes. This slice does not send Slack, email, or
panel notifications. GitHub's default Actions failure mail/web notification may
still fire when the workflow job is red — "no notifications" is not absolute.

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

## Acceptance contract

Each check has `result`: `pass` | `fail` | `unknown`.

- `pass` — determinate expected outcome
- `fail` — determinate unexpected outcome (wrong status, secret field, open bridge)
- `unknown` — this run could not evaluate (timeout, DNS, TLS, other request error)

Report `overall`: `pass` | `fail` | `unknown` | `stale`.

- `fail` if any check is `fail`
- `pass` if every check is `pass` (sets `last_success_at` to `checked_at`)
- `stale` if there is no determinate fail, at least one `unknown`, and
  `last_success_at` is older than `stale_after_seconds` (default 3600 = two
  30-minute cron intervals)
- `unknown` if there is no determinate fail, at least one `unknown`, and
  `last_success_at` is missing or still within the stale window

`last_success_at` persists across runs in `--state` (workflow cache:
`layer1a-state.json`). A fail or unknown run does not clear a previous success
timestamp.

## Run

```bash
python3 ops/layer1a/run.py --output layer1a-result.json --state layer1a-state.json
```

Exit 0 when `overall` is `pass`; exit 1 otherwise. The JSON is still written.
Stdlib only.

## Cron

`.github/workflows/layer1a.yml` runs every 30 minutes on `main` and on
`workflow_dispatch`. It restores/saves `layer1a-state.json` and uploads
`layer1a-result.json` as a workflow artifact.
