# OD-010 — CI tamamlanma ve doc-only sınıflandırma

**Durum:** **`implementation-complete`**.  
**Kaynak:** [`workflow-decision-alignment.md`](./workflow-decision-alignment.md) §8 (OD-010).  
**İndeks:** `open-decisions-needs-review.md` OD-010.

---

## 1. Karar özeti

| Senaryo | Tamamlanma kriteri |
|---------|-------------------|
| **Kod / commit / push / merge** | CI yeşil **zorunlu** — local test yetmez |
| **Yalnızca docs / analiz** (kod yok, push yok) | Pre-commit veya salt-okuma kanıt yeterli |
| **Docs PR merge** | Merge öncesi CI yeşil **zorunlu** |

**Sabit:** «CI yeşil olmadan tamamlandı denmez» kuralı **kod yolunda** gevşetilmez.

---

## 2. Doc-only tanımı

**Doc-only** when all true:

1. No changes to `src/`, `tests/`, `packages/`, `ui/` runtime, or `.github/workflows/` CI behavior
2. Only `docs/**` or analysis output
3. No push, or merge PR passed CI

**Not doc-only:** workflow changes, dependencies, source/tests.

---

## 3. Kod yolu

`commit-oncesi-zincir.mdc`: RUN → VERIFY → LINT → GIT → CI RISK → COMMIT → PUSH

---

Son güncelleme: 2026-06-20
