## What and why

<!-- One theme per PR. What changes, and what problem it solves. -->

Closes #

## Local checks

Run from the repo root:

- [ ] `ruff check .` passes
- [ ] `make test` passes

`make test` is the CI-parity entry point — it sets `PYTHONPATH` and
`KANDO_MOCK=1`, which a bare `pytest` does not. A bare `pytest` can report green
while silently **skipping** the tests that matter. See
[CONTRIBUTING.md](../CONTRIBUTING.md#which-interpreter-runs-the-tests).

## Scope

- [ ] Single theme; the diff is as small as the change allows
- [ ] No production secrets, private orchestration, commercial service logic, or
      operational backend infrastructure added to this public repository
      ([CONTRIBUTING.md § Public repository boundary](../CONTRIBUTING.md#public-repository-boundary))
- [ ] Behaviour or onboarding changes link the docs they affect
- [ ] If this touches an authority or automation boundary, the relevant ADR under
      `docs/decisions/` is added or updated

## Merge gate

`main` merges only when **all three** gates hold on the **current head SHA**.
Missing, queued, or in-progress results are not a pass, and the counters reset if
the head changes. Full text:
[CONTRIBUTING.md § Merge gate](../CONTRIBUTING.md#merge-gate).

1. Required CI green — `test`, `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`
2. Security review CheckRun complete and clean
3. Explicit human approval — an agent, bot, or GitHub App review does not count

<!--
Note for agents: opening a PR as a *draft* does not fire the security reviewer's
"PR Opened" trigger. See AGENTS.md.
-->

## Risk and rollback

<!-- What could this break, and how would it be reverted? -->
