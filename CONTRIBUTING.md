# Contributing to Lumos Core

Thanks for helping improve the open-source foundation. Keep changes focused and demo-safe.

## Before you start

- **Onboarding:** [docs/getting-started.md](docs/getting-started.md) — Katman A (UI only) vs Katman B (full local bridge)
- **Repo map:** [docs/project-map.md](docs/project-map.md) — layout, entry points, naming

## Local checks

From the repo root (Python deps installed; see getting-started):

```bash
ruff check .
make test
```

`make test` is the CI-parity entry point: it sets `PYTHONPATH` and
`KANDO_MOCK=1`, which a bare `pytest` invocation does not. Optional commit
guard: `make setup-commit-guard`.

### Which interpreter runs the tests

CI runs bare `pytest` ([`ci.yml`](.github/workflows/ci.yml)), and that is
correct there: the workflow installs `requirements.txt` into the job's own
interpreter, so the test runner and the dependencies are the same environment
by construction.

Locally the same command is **not** interchangeable. Bare `pytest` resolves to
whichever `pytest` comes first on your `PATH` — often a system or Homebrew
install — which need not be the interpreter your project dependencies are
installed into. Nothing in the output announces the swap: both runs report the
same pytest version and both print green. The difference surfaces only as tests
that **skip** instead of run.

Using a virtualenv is optional, not required. If you have one, point the run at
it explicitly rather than relying on `PATH`:

```bash
make test PYTEST=".venv/bin/python -m pytest"
```

Measured 2026-08-24: the venv interpreter reported **3 skipped**; bare `pytest`
(Homebrew, Python 3.11) reported **4 skipped**, from the same working tree, with
both runs printing green and reporting the same pytest version. The extra skip
is `tests/test_representative_bot_rig.py::test_resample_ratio`, guarded by
`pytest.importorskip("numpy")`. numpy is an optional dependency, so that skip is
intended behaviour, not a defect; it is absent from `requirements.txt`, so CI
skips it as well. Absolute pass counts move as tests land — the skip difference
is the signal.

`pytest.ini` sets `addopts = -rs`, so every skip prints its reason instead of
collapsing into a bare count. That is what makes an environment difference like
the one above visible without having to go looking for it.

## Pull requests

- One clear theme per PR; keep diffs small
- Local checks (`ruff` + `pytest`) should pass before you open a PR
- Merge into `main` only when the [merge gate](#merge-gate) holds
- Link related docs when you change behavior or onboarding paths
- **Reporting issues:** pilot / destek raporları için ORAA şablonu — [docs/templates/support-report-oraa.md](docs/templates/support-report-oraa.md)

### Merge gate

Target architecture ([ADR-027](docs/decisions/ADR-027-controlled-core-writer.md),
[Constitution §11](docs/CONSTITUTION.md)): researchers and external agents
propose; Lumos evaluates; Lumos security/test gates run; a **single controlled
Lumos writer** lands `main`. Humans are the final authority on the constitution,
authority limits, and high-risk exceptions — not the merge button on every PR.

That writer does not exist yet. Until it does, `main` uses the **temporary
three-gate regime** below. “A human merges every PR” is the current safety
stand-in, not the permanent model.

`main` is merged only when **all three** gates hold on the **current head
SHA**. Missing, queued, in-progress, or non-success results are not a pass.
If the head changes, the counters reset. Human approval is SHA-bound: it is
asked only after gates 1–2 are SUCCESS on that SHA, and it does not carry
over to a later SHA.

1. **Required CI green** (today’s test gate; **physical**). GitHub CheckRuns
   from [`.github/workflows/ci.yml`](.github/workflows/ci.yml): `test`,
   `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`. These five names are on
   `main` `required_status_checks`, owned by GitHub Actions **app_id 15368**.
   Name proof: `candasoz01-cmd/lumos-core#806` head `279492c9` · Checks API ·
   2026-08-27T07:04:13Z. This integration cannot GET branch protection
   (HTTP 403). That 403 is **not** evidence the list is empty; the user
   confirmed the five checks independently. Do not “fix” a 403 by treating
   `required_status_checks` as empty.
2. **Security review complete and clean** (today’s security gate; **written
   contract**, not a GitHub required check). This is a real CheckRun produced
   by the Cursor Security Reviewer automation, not only a PR review or
   comment. Verified name: `Cursor Security Agent: Security Reviewer`
   (GitHub app `cursor` / 1210556; `candasoz01-cmd/lumos-core#755` head
   `596253e` and `#762` · Checks API · 2026-08-19T17:31Z; present on
   `#806`). A missing run is pending. The marketplace template triggers are
   **PR Opened** and **PR Pushed**: opening a *draft* does not fire PR
   Opened; PR Pushed fires only on new commits to an *existing* PR. The
   CheckRun is **not** in `required_status_checks`. That is conscious:
   Cursor App access was not expanded.
3. **Explicit human approval** (temporary stand-in for the controlled writer
   plus high-risk authority). An agent, bot, or GitHub App review does not
   count. GitHub’s required-review counter cannot tell a human from an agent;
   this gate is a written norm. **Required review count is 0 by decision**,
   not by omission. Raising it to 1 would let an agent review satisfy the
   counter. `require_last_push_approval` is not used. With write access,
   `cursor[bot]` can merge while `auto_merge` is null: `#777`, `#804`,
   `#805`; `#806` was merged by `candasoz01-cmd`. Tentative phrasing is not
   approval.

Agent-facing counterpart: [`AGENTS.md`](AGENTS.md).

Scheduled [`layer1a.yml`](.github/workflows/layer1a.yml) (`pulse`) and manual
[`prod-smoke.yml`](.github/workflows/prod-smoke.yml) are not pull-request merge
gates.

**Physical lock (GitHub Settings, not this file):** Gate 1 is now enforced by
GitHub `required_status_checks` (the five `ci.yml` jobs, app 15368). Gate 2
is not a required check. Gate 3 cannot be fully enforced by GitHub’s review
counter. Docs PRs must not PATCH/PUT branch protection, rulesets, or
auto-merge. Do not add `standing-class` to `required_status_checks`. Do not
raise the required review count. Do not enable Merge Queue or Automations
“Automatically Approve PRs”.

GitHub `allow_auto_merge` is **false**; rulesets are `[]`; GraphQL
`autoMergeAllowed` is false (`candasoz01-cmd/lumos-core` · GitHub API ·
2026-08-27T07:03:53Z). Cursor Cloud Agents dashboard has **no** agent
auto-merge switch
([cloud-agent settings](https://cursor.com/docs/cloud-agent/settings.md)).

**Standing class (ADR-028 gate 0):** `python -m standing_merge.classify` on
changed paths. The CheckRun trust root is
`github.event.pull_request.base.sha`, not the PR checkout: extract
`src/standing_merge` from that SHA into a separate directory. If the
classifier is missing on the base SHA, fail closed (no fallback). Feed
paths NUL-delimited (`git diff -z`) after `--`. A path that starts with
`-` is excluded. Hard-exclusion (prefix, file, path token, leading dash)
first. Unlisted paths are excluded (fail-closed). Only allowlisted `docs/`
and `tests/` paths that miss the hariç rules can be eligible. CheckRun
`standing-class` fails when the class is excluded. That failure forbids
standing merge; it does not forbid a human merge. Do **not** add
`standing-class` to GitHub `required_status_checks` — that would block
human-approved excluded PRs too. Physical lock for standing still needs a
separate merge-authority model; Gate 1’s CI lock does not close that gap.
Incident: `#777` / [TD-20](docs/TECHNICAL_DEBT.md).

Live verification of this record: `candasoz01-cmd/lumos-core` · GitHub API /
Checks API · 2026-08-27T07:04:13Z (auto-merge / rulesets ·
2026-08-27T07:03:53Z).

## Public repository boundary

This repo is the **public OSS foundation**. Do not add production secrets, private orchestration, commercial service logic, or operational backend infrastructure. Demo-safe code, docs, placeholders, and foundation tooling belong here; professional Lumos layers stay private unless explicitly approved for public exposure.
