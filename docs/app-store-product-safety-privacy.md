# App Store — Product Safety & Privacy Positioning

| Field | Value |
|-------|--------|
| **Document type** | Product safety / privacy positioning (docs only) |
| **Audience** | Apple App Review, App Store metadata authors, internal product & legal |
| **Language** | English primary (Apple audience); short Turkish summary at end |
| **Status** | **Positioning draft** — demo-safe; no production secrets |
| **Related** | [`app-store-review-prep.md`](app-store-review-prep.md), [`lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md), [`drafts/BACKLOG.md`](drafts/BACKLOG.md) (LUMOS-0008), [`memory/public-repo-boundary.md`](memory/public-repo-boundary.md) |

---

## 1. Purpose

This document states **what Lumos is and is not** for App Store evaluation: data handling, user approval, AI boundaries, and UX honesty. It complements — but does not replace — the operational review checklist in [`app-store-review-prep.md`](app-store-review-prep.md).

**Core principle:** Lumos does **not** sell the model; it delivers a **safe workflow experience**.

---

## 2. What Lumos does

Lumos is a **personal work layer** that helps users turn scattered conversation and intent into **secure, traceable, actionable workflows**.

| Capability | Description |
|------------|-------------|
| **Task & workflow organization** | Capture, structure, and track personal work items with clear status |
| **Approval-gated actions** | Sensitive steps require explicit user confirmation before execution |
| **Demo / review workspace** | App Review builds use a hosted Demo Workspace with synthetic data only ([`app-store-review-prep.md`](app-store-review-prep.md) §4) |
| **Local-first where possible** | Work that can run on-device or locally does not wait for full cloud connectivity |
| **Transparent limits** | When an action is stubbed, limited, or not connected, the UI says so |

**Differentiation (positioning lines):**

- Not “smarter AI” — **better organized user flow**.
- Lumos transforms scattered user conversation into **secure, traceable, actionable workflows** — a personal work layer, not a generic chatbot wrapper.

---

## 3. What Lumos does NOT do

| Not in scope | Detail |
|--------------|--------|
| **Sell or resell AI models** | Lumos is a workflow and safety layer; it is not a model marketplace |
| **Autonomous production actions** | No unsupervised email send, payment, device control, or external write without user approval |
| **Access reviewer or user production data in review builds** | Review Mode uses synthetic fixtures only; no real customer accounts |
| **Connect to reviewer's personal PC or home devices** | App Store review builds use a hosted demo API — no LAN bridge required |
| **Guarantee outcomes** | Lumos suggests and organizes; the user retains final decision |
| **Children's app / COPPA product** | Not designed as a children's service (see §8) |
| **Medical, financial, or legal advice product** | Not a licensed professional advisor (see §8) |

Public OSS boundary: production orchestration, live integrations, auth secrets, and operational backend details stay **out of the public repo** — see [`memory/public-repo-boundary.md`](memory/public-repo-boundary.md).

---

## 4. Data Lumos processes

| Data category | Typical use | Review / demo build |
|---------------|-------------|---------------------|
| **Account credentials** | Sign-in to Lumos | Review account only; credentials set in App Store Connect, not git |
| **Tasks, notes, approvals** | User workflow state | Synthetic fixtures in Demo Workspace |
| **Chat / assistant text** | Organize intent, draft suggestions | Demo assistant uses canned or bounded replies; no live external API key required in review |
| **Device permissions** | Optional voice/capture demos | Camera/microphone optional; clearly labeled; skippable |
| **Analytics** | Product improvement | Off or anonymized demo-only in review builds |

Lumos does **not** claim to collect data the user did not knowingly provide for the active workflow. Privacy Nutrition Labels must match the **actual review build behavior** (see checklist in [`app-store-review-prep.md`](app-store-review-prep.md) §5).

---

## 5. What requires explicit user approval

Aligned with [`lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md) and LUMOS-0008 (L0 authority matrix: Read · Suggest · Execute (ruled) · Critical approval):

| Action class | Approval model |
|--------------|----------------|
| **Read / analyze / plan** | No state change; information only |
| **Local safe writes** | Allowed within active permission profile |
| **External writes** (email, posts, integrations) | Explicit user approval; stubbed or disconnected in review |
| **Irreversible operations** | Never automatic; user command + clear warning |
| **Permanent delete** | Never automatic; user command only |
| **Permission / profile elevation** | Lumos does not silently expand authority |

**Decision chain (LUMOS-0008):** Understand → Interpret → Assess risk → Obtain approval → Execute. Lumos may refuse or explain limits; it does not bypass consent.

---

## 6. How AI output is bounded

| Boundary | Implementation principle |
|----------|-------------------------|
| **No authority from user text alone** | Prompt content cannot override security, identity, or permission layers |
| **Suggestions, not commands** | AI output is presented as draft or recommendation until the user approves |
| **Stubbed or demo paths in review** | Chat in Review Mode does not require a live external model API key |
| **Honest uncertainty** | When confidence is low, Lumos states limits rather than filling gaps |
| **No hidden automation** | Effective actions require visible approval steps |

Lumos delivers **workflow safety and traceability**, not unconstrained model access.

---

## 7. UX copy — avoid misleading users

Use language that matches actual capability:

| Prefer | Avoid |
|--------|-------|
| “Draft,” “suggest,” “organize,” “pending your approval” | “Automatically sent,” “guaranteed,” “always correct” |
| “Demo — not connected” for stubbed integrations | Implying live Gmail/Slack/payment without connection |
| “Demo Workspace” banner in review builds | Presenting sample data as the user’s real account |
| Clear permission prompts with skip option | Dark patterns that hide optional nature of camera/mic |
| “Your decision” / “Approve or reject” on actions | Implying Lumos acts on the user’s behalf without consent |

App Store screenshots and description must reflect **Review Mode / demo behavior** where applicable, not unreleased production integrations.

---

## 8. Sensitive domains — boundaries

| Domain | Lumos position |
|--------|----------------|
| **Children** | Not marketed or designed as a children’s app. No COPPA-targeted collection model in this positioning. |
| **Health / medical** | Not a medical device or diagnostic product. Any future health-adjacent features require separate legal review and explicit scope — **none claimed in current App Store positioning**. |
| **Finance** | Not a financial advisor, broker, or payment processor. Payment flows are stubbed or absent in review builds. |
| **Legal** | Not a lawyer or legal authority. Outputs are organizational aids, not legal advice. |

If metadata or UI could imply any of the above, revise before submission.

---

## 9. Apple review risk framing

Apple’s primary concerns are not “does the app use AI?” but:

| Risk area | Lumos mitigation |
|-----------|------------------|
| **Misleading capability claims** | Demo labels, stubbed integrations, honest copy (§7) |
| **Unauthorized data access** | Review tenant isolated; synthetic data only; no production user access |
| **Stability & completeness** | Demo Workspace pre-seeded; full primary navigation in review ([`app-store-review-prep.md`](app-store-review-prep.md) §4) |
| **Permission & consent clarity** | Explicit approval for effective actions; optional device permissions |
| **Account sign-in for review** | Ops must provision review account **before** submission — see [`app-store-review-prep.md`](app-store-review-prep.md) §2–§3 |

For paste-ready Review Notes and engineering spec, use [`app-store-review-prep.md`](app-store-review-prep.md) — do not duplicate that checklist here.

---

## 10. Cross-references

| Document | Relevance |
|----------|-----------|
| [`app-store-review-prep.md`](app-store-review-prep.md) | Demo account placeholders, Review Notes template, Demo Workspace spec, pre-submission checklist |
| [`lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md) | Decision layers, approval rules, never-auto operations |
| [`drafts/BACKLOG.md`](drafts/BACKLOG.md) — **LUMOS-0008** | L0 authority matrix and decision chain |
| [`memory/public-repo-boundary.md`](memory/public-repo-boundary.md) | What must not appear in public git (secrets, prod ops) |
| [`analysis/support-channel-alpha.md`](analysis/support-channel-alpha.md) | Support email still TBD until ops activates a mailbox |

---

## 11. Turkish summary (kısa)

**Lumos**, dağınık sohbet ve niyeti **güvenli, izlenebilir, onaylı iş akışlarına** dönüştüren kişisel bir çalışma katmanıdır; model satmaz, **güvenli iş akışı deneyimi** sunar.

- **Yapmaz:** Onaysız dış aksiyon, çocuk uygulaması iddiası, tıbbi/finansal/hukuki danışmanlık ürünü, inceleme build’inde gerçek kullanıcı verisine erişim.
- **Onay:** Dış yazma ve geri dönüşsüz işlemler açık kullanıcı onayı olmadan yapılmaz ([`lumos-karar-sozlesmesi.md`](lumos-karar-sozlesmesi.md), LUMOS-0008).
- **App Store operasyonu:** [`app-store-review-prep.md`](app-store-review-prep.md) — kimlik bilgileri yalnızca App Store Connect’te; repoda placeholder.

---

*Demo-safe document. No production credentials, API keys, or live support addresses committed.*
