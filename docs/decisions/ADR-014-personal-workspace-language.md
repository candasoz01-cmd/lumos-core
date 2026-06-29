# ADR-014: Personal Workspace Language

| Field | Value |
|-------|-------|
| Status | **Accepted** (2026-06-29) |
| Date | 2026-06-29 |
| Related | `docs/lumos-karar-sozlesmesi.md`, public GitHub boundary rules, ADR-003, ADR-004, ADR-010 |

## Context

Lumos serves two audiences with different needs: the individual who works in natural language, and the organization that requires structured, auditable knowledge. Conflating these layers produces either rigid chat UX or unreliable organizational records.

Personal Workspace Language (PWL) is the principle that the **personal layer** and the **organizational layer** remain distinct. Lumos understands the individual in their own terms; organizations receive standardized records derived from that interaction.

This ADR is **documentation only**. It does not introduce new runtime behavior, APIs, or storage schemas in this repository.

## Decision

### Two layers

| Layer | Character | Purpose |
|-------|-----------|---------|
| **Personal** | Natural language, context, intent, personal expression | How the individual thinks, asks, and works |
| **Organizational** | Structured, searchable, auditable records | What the organization can rely on, query, and govern |

### AI normalization, not translation

PWL uses **normalization**, not translation. Normalization preserves meaning, intent, and context while producing a canonical organizational form. Translation would replace the user's voice; normalization transforms conversation into structured knowledge without erasing what was meant.

### Primary goal

The goal of PWL is **not** to generate better conversational answers. It is to **transform conversations into structured knowledge** that organizations can store, search, audit, and act on.

### Responsibility split

- **Lumos** understands the individual: personal phrasing, shorthand, domain-specific terms, and situational context.
- **Organizations** receive standardized records: normalized fields, consistent structure, and provenance suitable for governance.

### Why it matters

PWL separates **human conversation** from **organizational knowledge**. Individuals keep expressive, low-friction interaction; organizations gain reliable records without forcing users into forms or templates at the point of work.

## Consequences

### Positive

- Clear boundary between UX (personal) and compliance (organizational).
- Normalization pipeline can evolve independently of chat quality metrics.
- Aligns with Lumos trust, audit, and workspace contract principles without mixing decision logs with user expression.

### Negative / constraints

- Requires an explicit normalization step; implicit "chat log as record" is insufficient.
- Personal-layer terminology may not map 1:1 to organizational schemas; normalization rules must be documented and versioned.
- Public OSS scope remains demo-safe; production normalization engines and org connectors are out of scope for this repository.

### Out of scope (this ADR)

- Implementation of normalization engines or org export formats.
- Multilingual translation products or locale-specific UI copy strategy.
- Changes to memory graph, router, or trust layers (see ADR-003, ADR-004, ADR-010).

---

*Internal glossary note: team shorthand "hırt" refers to informal personal-layer phrasing—not a product term.*
