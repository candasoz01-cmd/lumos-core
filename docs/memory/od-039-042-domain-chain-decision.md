# OD-039/042 — Domain zinciri (izleme → satın alma → redirect)

**Durum:** Kararlar **onaylı** / uygulama **bekliyor**.  
**Kaynak:** [`domain-monitoring-design-decision.md`](./domain-monitoring-design-decision.md) (OD-042), [`domain-redirect-model-decision.md`](./domain-redirect-model-decision.md) (OD-039), [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md) (OD-041).

---

## 1. Zincir akışı (onaylı)

```
[ OD-042: İzleme / rapor ]  →  pasif, bilgi-only
        ↓ kullanıcı karar
[ OD-041: Satın alma onayı ]  →  işlem bazlı açık onay (CA3)
        ↓ onaylı edinim
[ OD-039: Redirect ]  →  301 → welockai.com; ayrı DNS/redirect onayı (CA3)
```

| Adım | OD | Onay modeli |
|------|-----|-------------|
| Müsaitlik / risk sinyali | OD-042 | Oturum izni (okuma/izleme) |
| Domain satın alma / transfer | OD-041 | **İşlem bazlı** — oturum yetmez |
| DNS / redirect kurulumu | OD-039 + OD-041 | **Ayrı işlem onayı** — satın alma ≠ redirect |

---

## 2. Implementation-pending checklist

| # | Madde | Bağımlılık |
|---|--------|------------|
| D1 | Veri kaynağı seçimi (WHOIS / registrar / hibrit) | OD-042 |
| D2 | Rapor vs dashboard UX | OD-042 |
| D3 | Satın alma onay ekranı (ne/nerede/maliyet) | OD-041 |
| D4 | Registrar veya Cloudflare redirect kurulum runbook | OD-039 — **private ops** |
| D5 | SSL, apex/www, rollback | OD-039 |

**Ödeme:** OD-011 kapsam dışı — izleme bilgi-only; satın alma ödeme paketi gelene kadar **simülasyon veya manuel ops**.

---

## 3. Çapraz referans

- [`payment-scope-decision.md`](./payment-scope-decision.md) — ödeme/PSP aktif kapsam dışı
- [`commercial-domain-payments.md`](./commercial-domain-payments.md) — canonical domain kaydı

---

Son güncelleme: 2026-06-20 (envanter ab791c14 §12 #8 — Phase 3)
