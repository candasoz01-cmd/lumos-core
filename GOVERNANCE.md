# Governance

This document does **not** invent a new governance model. Lumos Core already has
one, spread across several files; this is the entry point that ties them
together so an outside reader can find it in one hop.

## Decision-making

| Question | Where it is decided | Record |
| --- | --- | --- |
| Architecture and long-lived technical direction | Architecture Decision Records | [`docs/decisions/`](docs/decisions/) — 35 ADRs on `main` |
| Constitutional limits, authority boundaries, high-risk exceptions | Humans, not the merge button | [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md) |
| What may land on `main` | Three-gate merge regime | [CONTRIBUTING.md § Merge gate](CONTRIBUTING.md#merge-gate) |
| What belongs in the public repo at all | Public repository boundary | [CONTRIBUTING.md § Public repository boundary](CONTRIBUTING.md#public-repository-boundary) |
| How automated agents may act | Agent working rules | [`AGENTS.md`](AGENTS.md) |
| Who holds final human authority | Maintainer list | [`MAINTAINERS.md`](MAINTAINERS.md) |

## Who decides

Lumos Core is a **single-maintainer project** today. There is no steering
committee, no voting, and no tiered contributor ladder — and this document does
not pretend otherwise. See [MAINTAINERS.md](MAINTAINERS.md).

The target model is described in
[ADR-027](docs/decisions/ADR-027-controlled-core-writer.md): researchers and
external agents propose, Lumos evaluates, security and test gates run, and a
single controlled writer lands `main`. **That writer does not exist yet.** Until
it does, `main` runs the temporary three-gate regime documented in
CONTRIBUTING.md, where a human merges every pull request.

Stating this openly matters: the interesting property of this project's
governance is that the automation boundary is written down and currently
unfinished, not that it is complete.

## How proposals are made

1. Open an issue describing the problem before writing code for anything
   non-trivial. For a change that alters architecture or an authority boundary,
   expect to be asked for an ADR.
2. For behaviour or onboarding changes, an ADR under `docs/decisions/` is the
   durable record. Follow the numbering and shape of the existing files.
3. Open a focused pull request. One theme per PR. Local checks (`ruff check .`
   and `make test`) pass before review.
4. Merge happens only when all three gates hold on the current head SHA.

## What external contributors can expect

Lumos Core is in early active development and is **not yet a fully
contribution-ready open source product**. External contributions are reviewed on
a controlled basis. Concretely, that means:

- A well-scoped bug fix with a test is the contribution most likely to land.
- A large refactor or a new subsystem, opened without prior discussion, is
  unlikely to be merged regardless of quality.
- Anything touching production secrets, private orchestration, or commercial
  service logic is out of scope for this repository by policy.

No response-time guarantee is offered for issues or pull requests at this stage. Well-scoped bug fixes with tests are prioritized on a best-effort basis.

## Changing this document

Governance changes are recorded as ADRs under `docs/decisions/`, using the same durable process as architecture changes.

