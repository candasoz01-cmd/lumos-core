# Security Policy

## Supported versions

Lumos Core is in early active development and has **no tagged releases yet**.

| Version | Supported |
| --- | --- |
| `main` (latest commit) | Yes |
| Any fork or vendored copy | No |
| Older commits on `main` | No — fixes land on `main` only |

Once the first release is tagged, replace this table with a real version /
end-of-support matrix.

## Reporting a vulnerability

**Please do not open a public GitHub issue, pull request, or discussion for a
suspected vulnerability.** Public disclosure before a fix exists puts users at
risk.

Use the channel below.

### Primary channel — GitHub Private Vulnerability Reporting

Use the **Report a vulnerability** button on this repository's **Security** tab,
or go directly to
[`/security/advisories/new`](https://github.com/candasoz01-cmd/lumos-core/security/advisories/new).

Reports filed this way are visible only to the maintainers. They stay private
until an advisory is published, and no contact address has to be exposed
publicly.

No email address is published for security reports, by design: a
single-maintainer project is better served by one channel that is actually
monitored than by a mailbox that may not be. If you cannot use GitHub private
reporting, say so in a public issue **without any vulnerability details** and
ask for another channel.

### What to include

The more of this you can provide, the faster a fix lands:

- Affected component or path (for example `src/security/...`, `api/...`, `services/credential-gateway/...`)
- Commit SHA or branch you tested against
- Steps to reproduce, ideally a minimal case
- Observed impact, and what an attacker would gain
- Any suggested remediation, if you have one

Please do not include real user data, production credentials, or third-party
personal information in a report.

## Response targets

| Stage | Target |
| --- | --- |
| Acknowledge receipt | within 5 business days |

This is an acknowledgement target, not a resolution SLA. Assessment, status
updates, remediation and release timing are handled on a best-effort basis; no
fixed delivery guarantee is offered at this stage of the project.

## Scope

**In scope**

- Source code in this repository (`candasoz01-cmd/lumos-core`) on `main`
- Build, CI, and packaging configuration in this repository, including
  `.github/workflows/`
- Documented behaviour of the local bridge and panel as described in
  `docs/getting-started.md`

**Out of scope**

- Hosted We Lock AI / Lumos production services and their infrastructure.
  These are **not** covered by the Apache-2.0 license granted here (see
  [NOTICE](NOTICE)) and are not part of this repository's security surface.
  If you encounter a suspected issue there without actively testing the hosted
  service, you may report it through the same private GitHub channel. This does
  not authorize testing against hosted systems; obtain written authorization
  before any security testing outside your own installation.
- Findings that require a compromised local machine or an already-privileged
  local attacker
- Missing hardening headers or similar findings with no demonstrated impact
- Automated scanner output submitted without a reproduction

## Coordinated disclosure

We ask reporters to allow up to 90 calendar days between acknowledgement of a
valid report and public disclosure so a fix or mitigation can ship. If active
exploitation or immediate user harm changes the risk, the reporter and
maintainer should coordinate an earlier disclosure date.

Credit for valid reports is offered by default. Tell us the name or handle you
would like used, or say you prefer to stay anonymous.

## No bounty

This project does **not** operate a paid bug bounty. Reports are handled on a
good-faith basis only.

