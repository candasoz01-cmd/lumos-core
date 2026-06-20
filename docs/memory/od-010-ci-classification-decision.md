# OD-010 — CI tamamlanma ve doc-only sınıflandırma

**Durum:** **`implementation-complete`**.  
**Kaynak:** [`workflow-decision-alignment.md`](./workflow-decision-alignment.md) §8 (OD-010).  
**İndeks:** `open-decisions-needs-review.md` OD-010.

---

## 1. Karar özeti

| Senaryo | Tamamlanma kriteri |
|---------|-------------------|
| **Kod / commit / push / merge** | CI yeşil **zorunlu** — local test yetmez |
| **Yalnızca docs / analiz** (kod yok, push yok) | Pre-commit veya salt-okuma kanıt yeterli; **CI sınıflandırması uygulanmaz** |
| **Docs PR merge** | Merge öncesi CI yeşil **zorunlu** (public repo) |

**Sabit:** «CI yeşil olmadan tamamlandı denmez» kuralı **kod yolunda** gevşetilmez.

---

## 2. Doc-only / analysis-only tanımı

Aşağıdakilerin **tamamı** sağlanırsa görev **doc-only** sayılır:

1. `src/`, `tests/`, `packages/`, `ui/` (runtime kod), `.github/workflows/` (CI davranış değişikliği) **dokunulmadı**
2. Yalnızca `docs/**`, `.cursor/rules/**` (opsiyonel) veya analiz çıktısı
3. Push/merge **yapılmadı** veya merge PR'si CI'dan geçti

**Doc-only değildir:** Workflow ekleme/değiştirme, dependency, Python/JS kaynak, test dosyası.

---

## 3. Doğrulama zinciri (kod yolu)

`commit-oncesi-zincir.mdc`: **RUN → VERIFY → LINT → GIT → CI RISK → COMMIT → PUSH**

Push sonrası en güncel CI run yeşil değilse iş bitmiş sayılmaz.

---

## 4. Uygulama

- `project-workflow.md` §5 — bu sınıflandırma referansı eklendi
- OD-010 indeks → **closed** (implementation-complete)

---

Son güncelleme: 2026-06-20
