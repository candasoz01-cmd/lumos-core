# PC Remote Hardening — Phase 2 Morning Report

| Field | Value |
|-------|-------|
| Date | 2026-06-22 |
| Base SHA | `c45f6b8` (main) |
| Branch | `harden/pc-remote-phase2` |
| Scope | OpenAI → approval → mobile → relay → bridge chain (stub-only, no OS executor) |

---

## Executive summary

Phase 2 hardens the PC remote approval chain without adding real OS automation. **Replay protection** (`try_consume_approval_token` + Unix `fcntl` lock) is verified with direct and concurrent tests; **Windows** remains a documented gap (no exclusive lock). **Audit JSONL** now covers pending, approved, rejected, expired, stub executed, execute rejected, and approval denied events. **Mobile UI** (inline HTML in `lan_relay.py`) shows plain-language headlines, single-pending focus, large buttons, visible errors, live expiry countdown, and hidden JSON preview by default. **Bridge bypass** regression tests block execute without token consume, wrong token, and `approval_granted` body flag. **OpenAI adapter** tests cover malformed payloads, missing params, and bridge HTTP errors with safe fallback (no partial execute).

**CI:** 1219 passed, 3 skipped (local `make test`).

---

## PRs

| PR | Status | Focus |
|----|--------|-------|
| #519 auto-approve gate + replay consume | **Merged** (pre-sprint) | Dev-only auto-approve, token consume |
| #520 audit/errors/token redaction | **Merged** (pre-sprint) | Audit scaffold, list token redaction |
| #522 wait-approve timeout test | **Merged** (pre-sprint) | Tool-loop demo timeout |
| #518 docs bundle | **Merged** (pre-sprint) | Analysis docs |
| `harden/pc-remote-phase2` | **Open** (this sprint) | Audit completeness, mobile UX P0, bypass tests, adapter edge cases |

---

## Closed risks

| Risk | Mitigation |
|------|------------|
| Sequential token replay | `used=true` after `try_consume_approval_token`; tests: double execute, try_consume direct |
| Concurrent double execute (Unix) | `fcntl.flock(LOCK_EX)` in consume path; test: `test_concurrent_execute_one_wins` |
| Execute without valid token | Gate + consume; bypass tests for no token / wrong token / `approval_granted` flag |
| Reject then re-execute | `status=rejected` blocks validate; test: `test_reject_then_reexecute_fails` |
| Expired approved token | `mark_expired_if_needed` + validate; audit `pending_expired` |
| Audit blind spots | New events: `execute_rejected`, `approval_denied`; tests per event type |
| Mobile UX friction (P0) | Headline from `required_user_action`, focus card, countdown, error banner |
| OpenAI partial execute on error | `safe_fallback: true` on all error stages; malformed/missing-param tests |
| Pending list token leak (default) | Verified: `build_pending_approvals_list` omits token unless `include_approval_token=True` (#520) |

---

## Tests added (phase 2)

| File | New / extended tests |
|------|----------------------|
| `test_pc_remote_approval_security.py` | `test_try_consume_approval_token_marks_used`, `test_try_consume_rejects_expired_approved` |
| `test_pc_remote_audit.py` | reject, expired, execute_rejected (replay + bad token), approval_denied (invalid approve token) |
| `test_pc_remote_bridge_stubs.py` | no token after approve, wrong token, `approval_granted` ignored, all 5 approval commands blocked |
| `test_openai_tool_loop_adapter_mvp.py` | malformed parse, missing URL param, HTTP 500, empty OpenAI output |
| `test_lan_relay_mvp_e2e.py` | mobile UI assertions (headline, error-banner, countdown, focus mode) |

**Total new tests:** ~15 (1219 vs 1204 baseline).

---

## Remaining security gaps

From [mobile-approval-flow-security-review.md](./mobile-approval-flow-security-review.md) and phase 2 findings:

| Gap | Severity | Notes |
|-----|----------|-------|
| **Windows concurrent consume** | High (Windows only) | No `fcntl`; fallback validate+write without exclusive lock — document only in OSS |
| **LAN relay pairing brute-force** | Medium | 6-char code, no rate limit on `/relay/pair` |
| **No TLS on LAN relay** | Medium | Demo MVP; tokens visible on local network |
| **approval_token in relay pending API** | Medium | Relay forwards bridge list with tokens for mobile approve flow |
| **Double POST /approve** | Low | Re-approve idempotent side effect only |
| **High-risk single-tap approve** | Low (UX) | P1: double confirm for `high` risk — out of scope (no new features) |
| **Real OS executor** | Blocker (private) | Stub only in public repo; swap point: `execute_tool_stub` |

---

## OS executor blocker list (private layer)

These cannot be closed in public OSS without private executor:

1. Actual app launch (`pc_open_app`)
2. Browser / URL open (`pc_open_url`)
3. Keyboard injection (`pc_type_text`)
4. Click automation (`pc_suggest_click` — even post-approve, stub returns suggestion only)
5. Native file picker (`pc_request_file_picker`)
6. Screen capture beyond demo snapshot (`pc_read_screen`)
7. Post-approve sandbox / consent UI on desktop
8. Cross-platform file lock for token consume (Windows `msvcrt` or atomic rename)

---

## Windows `fcntl` limitation (OSS)

`try_consume_approval_token` uses `fcntl.flock(LOCK_EX)` on Unix (Linux CI). On Windows, `fcntl` is unavailable; the code falls back to `validate_approval_token` + `consume_pending_record` without an exclusive lock. **Concurrent double-execute is possible on Windows** until a cross-platform lock is implemented in the private layer or a portable helper is added.

Reference: docstring in `pending_approvals.py` → `try_consume_approval_token`.

---

## Files touched (phase 2)

- `packages/kando_bridge/src/kando_bridge/pc_remote_audit.py` — `execute_rejected`, `approval_denied` events
- `packages/kando_bridge/src/kando_bridge/pc_remote_tools.py` — audit on failed execute
- `packages/kando_bridge/src/kando_bridge/pending_approvals.py` — audit constants, Windows note
- `packages/kando_bridge/src/kando_bridge/server.py` — audit on invalid approve token (pc_remote)
- `packages/kando_bridge/src/kando_bridge/lan_relay.py` — mobile UX P0 polish
- `tests/*` — security, audit, bypass, adapter, relay UI

---

## Next single step

Open PR from `harden/pc-remote-phase2` → `main`; merge when CI green.
