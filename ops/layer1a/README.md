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
| `bridge_fail_closed` | `GET /api/bridge/task` | HTTP 401 with `bridge_proxy_unauthorized`; never 200 |

General rule: unexpected HTTP status is `fail`. **Explicit exception:**
bridge HTTP 503 is classified as `unknown` *before* that HTTP rule. A 503
body (including documented `bridge_proxy_*_unconfigured` codes) does not
make the check `pass` or `fail`. Landing 503 remains `fail`.

`bridge_fail_closed` pass is the documented fail-closed 401 from
[`api-surface-v1.md`](../../docs/contracts/api-surface-v1.md):
`bridge_proxy_unauthorized`.

## Acceptance contract

Each check has `result`: `pass` | `fail` | `unknown`.

- `pass` — determinate expected outcome
- `fail` — determinate unexpected outcome (wrong status, secret field, open bridge)
- `unknown` — this run could not evaluate (timeout, DNS, TLS, other request
  error, **or bridge HTTP 503**)

Report `overall`: `pass` | `fail` | `unknown` | `stale`.

- `fail` if any check is `fail`
- `pass` if every check is `pass`
- `stale` if there is no determinate fail, at least one `unknown`, and **that
  unknown check's** `last_success_at` is older than `stale_after_seconds`
  (default 3600 = two 30-minute cron intervals)
- `unknown` if there is no determinate fail, at least one `unknown`, and every
  unknown check is missing a last success or is still within the stale window

`last_success_at` is a **per-check** map, never a single global timestamp.
Each check entry also carries its own `last_success_at`. A pass updates that
check only. Fail or unknown does not clear a previous success for that check.

Each check in the artifact also carries `age_seconds`:
`generated_at - last_success_at` (integer seconds), or `null` when that check
has no history. `age_seconds` is derived at emit time and is **not** written to
cache/state. State stores only per-check `last_success_at`.

The artifact also includes `generated_at` and `run_attempt`
(`GITHUB_RUN_ATTEMPT` or `--run-attempt`).

State persists across runs in `--state` (workflow cache: `layer1a-state.json`).
The workflow restores with `actions/cache/restore@v4` and saves with
`actions/cache/save@v4` under `if: always()`. Cache save needs `actions: write`;
`contents` stays `read`. The pulse step uses `continue-on-error: true`; a missing
artifact still fails the upload step.

**Accepted operational limit:** GitHub Actions cache entries unused for 7 days
are evicted. If `layer1a-state.json` drops, per-check history is missing until
the next `pass` of that check. Missing history is `unknown`, not `stale`.

## Run

```bash
python3 ops/layer1a/run.py --output layer1a-result.json --state layer1a-state.json
```

Exit 0 when `overall` is `pass`; exit 1 otherwise. The JSON is still written.
Stdlib only.

## Cron

`.github/workflows/layer1a.yml` runs every 30 minutes on `main` and on
`workflow_dispatch`. It restores/saves `layer1a-state.json` and uploads
`layer1a-result.json` as a workflow artifact. Script exit codes are preserved;
the job stays green unless artifact upload fails.
