# AnchorUSB repository governance decision

| Field | Value |
|-------|-------|
| Status | Recorded |
| Maturity | M2 |
| Owner | Security / repository governance owner pending |
| Date | 2026-07-04 |
| Review Date | 2026-08-01 |
| Related ADR | ADR-007, ADR-008, ADR-012 |
| Related Epic | Secure Device Framework |
| Supersedes | `scripts/anchorusb/` untracked binary ambiguity |

## Decision

AnchorUSB is a Secure Device Framework member and product-grade AnchorUSB work should target a separate repository when promoted:

- target repository name: `lumos-anchorusb`
- its own README
- its own CODEOWNERS
- its own CI
- its own release/versioning flow
- its own security review

`lumos-core` may keep public-safe Secure Device Framework documentation and existing tracked Rust reference crates while extraction is not active. This does not make local POC binaries part of the Lumos core repository contract.

## Binary governance rule

Compiled binaries must not be added to `lumos-core` without an explicit repository decision.

Every allowed binary must document:

- source code path
- build command
- owner
- version
- reason for being in the repository
- verification method or checksum/provenance note

Without those fields, the binary is a local artifact and stays untracked/ignored.

## Current AnchorUSB artifact handling

`scripts/anchorusb/bin/` is a local POC output area. It is ignored by `.gitignore` and is not canonical source.

The current local artifact:

```text
scripts/anchorusb/bin/anchorusb-touchid
```

is treated as a local compiled POC binary. It is not staged, not committed, and not part of the release surface.

## Out of scope

- creating the separate repository
- moving files out of `lumos-core`
- deleting local POC files
- changing Rust crates
- changing runtime behavior
- implementing AnchorUSB production security

## Principle

AnchorUSB may be researched inside Lumos, but product-grade binaries must have ownership, provenance, build path, release path, and security review before entering any repository.
