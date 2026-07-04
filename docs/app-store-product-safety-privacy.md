# App Store — Product Safety & Privacy (Summary)

| Field | Value |
|-------|--------|
| **Document type** | Apple App Review summary |
| **Audience** | Apple App Review, App Store metadata authors |
| **Language** | English primary; short Turkish at end |
| **Status** | **Positioning draft** — demo-safe; no production secrets |
| **Full internal policy** | [`internal/lumos-product-safety-privacy-policy.md`](internal/lumos-product-safety-privacy-policy.md) |
| **Related** | [`app-store-review-prep.md`](app-store-review-prep.md), [`lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md), [`drafts/BACKLOG.md`](drafts/BACKLOG.md) (LUMOS-0005, LUMOS-0008) |

---

## Core principle

> **Lumos augments human decision-making; it does not replace it.**  
> *(TR: Lumos insanın karar verme sürecini destekler; onun yerine karar vermez.)*

Canonical source: [`internal/lumos-product-safety-privacy-policy.md`](internal/lumos-product-safety-privacy-policy.md).

Lumos does **not** sell the model; it delivers a **safe workflow experience**.

Operational review checklist and Demo Workspace spec: [`app-store-review-prep.md`](app-store-review-prep.md). **v1 Apple entitlements:** enable only what the build uses — [`app-store-review-prep.md`](app-store-review-prep.md) §5 v1 Capability boundary (Apple services).

---

## What Lumos is

Lumos is a **personal work layer** — scattered conversation and intent into **secure, traceable, actionable workflows**.

| Capability | Summary |
|------------|---------|
| **Workflow organization** | Tasks, status, and approval-gated actions |
| **User retains final decision** | Suggestions and drafts until explicit approval |
| **Demo / review builds** | Hosted Demo Workspace with **synthetic data only** ([`app-store-review-prep.md`](app-store-review-prep.md) §4) |
| **Honest limits** | Stubbed or disconnected integrations are labeled in UI |

**Positioning:**

- Not “smarter AI” — **better organized user flow**.
- A workflow and safety layer, not a model marketplace or generic chatbot wrapper.

---

## What Lumos is NOT

| Not in scope | One-line |
|--------------|----------|
| **Model marketplace** | Workflow and safety layer only |
| **Autonomous production actions** | No unsupervised email, payment, device control, or external write |
| **Professional advisor** | Not medical, financial, legal, or children's product |
| **Production data in review** | Synthetic Demo Workspace only; no real customer accounts |
| **Outcome guarantees** | Organizes and suggests; user decides |

Full detail (data categories, approval matrix, AI bounds, UX copy): [`internal/lumos-product-safety-privacy-policy.md`](internal/lumos-product-safety-privacy-policy.md) §3–§7.

---

## Sensitive domains (brief)

| Domain | Lumos position |
|--------|----------------|
| **Children** | Not marketed or designed as a children's app |
| **Health / medical** | Not a medical device or diagnostic product |
| **Finance** | Not advisor, broker, or payment processor |
| **Legal** | Organizational aids only — not legal advice |

If metadata or UI could imply any of the above, revise before submission. Boundaries: internal policy §8.

---

## Apple review risk framing

Apple’s primary concerns are not “does the app use AI?” but:

| Risk area | Lumos mitigation |
|-----------|------------------|
| **Misleading capability claims** | Demo labels, stubbed integrations, honest copy |
| **Unauthorized data access** | Review tenant isolated; synthetic data only |
| **Stability & completeness** | Pre-seeded Demo Workspace; full primary navigation ([`app-store-review-prep.md`](app-store-review-prep.md) §4) |
| **Permission & consent clarity** | Explicit approval for effective actions; optional device permissions skippable |
| **Data location transparency** | User must know what is stored/processed where; store and in-app claims must match actual data flow ([`drafts/lumos-2040-vision-draft.md`](drafts/lumos-2040-vision-draft.md) — storage choice M0 seed) |
| **Review account** | Ops provisions credentials in App Store Connect only — not in git ([`app-store-review-prep.md`](app-store-review-prep.md) §2–§3) |

Paste-ready Review Notes and engineering spec: [`app-store-review-prep.md`](app-store-review-prep.md) — do not duplicate that checklist here.

---

## Cross-references

| Document | Relevance |
|----------|-----------|
| [`internal/lumos-product-safety-privacy-policy.md`](internal/lumos-product-safety-privacy-policy.md) | Full internal product safety & privacy policy |
| [`app-store-review-prep.md`](app-store-review-prep.md) | Demo account, Review Notes, v1 capability boundary (§5), pre-submission checklist |
| [`lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md) | Decision layers, approval rules, never-auto operations |
| [`drafts/BACKLOG.md`](drafts/BACKLOG.md) — **LUMOS-0005** | Hakem modeli — nihai karar kullanıcıda |
| [`drafts/BACKLOG.md`](drafts/BACKLOG.md) — **LUMOS-0008** | L0 authority matrix and decision chain |

---

## Turkish summary (kısa)

**Lumos**, dağınık sohbet ve niyeti **güvenli, izlenebilir, onaylı iş akışlarına** dönüştüren kişisel bir çalışma katmanıdır; model satmaz, **güvenli iş akışı deneyimi** sunar.

> **Lumos insanın karar verme sürecini destekler; onun yerine karar vermez.**

Tam politika: [`internal/lumos-product-safety-privacy-policy.md`](internal/lumos-product-safety-privacy-policy.md). App Store operasyonu: [`app-store-review-prep.md`](app-store-review-prep.md).

---

*Demo-safe document. No production credentials, API keys, or live support addresses committed.*
