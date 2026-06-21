# ADR zinciri özeti — 006 → 010 → 011 → 012

Tek sayfa çapraz referans: guard/firewall, terminoloji, lock semantiği ve security codex omurgası.

| ADR | Katman | Karar (kısa) | Zincir ilişkisi |
|-----|--------|--------------|-----------------|
| [ADR-006](../decisions/ADR-006-ai-firewall-guard-layer.md) | Guard / AI Firewall | Birleşik firewall **yok**; parçalı guard; **Guard → Trust → Router** önceliği | Lock enforcement guard değil **trust** katmanında; `koruma_active` session_unlocked |
| [ADR-007](../decisions/ADR-007-trust-engine-layer.md) | Trust Engine | Birleşik motor **yok**; `locked`/`unlocked` trust durumları; koruma kilidi | `session_unlocked` canonical hassas işlem sinyali; Faz 4 hedefi |
| [ADR-010](../decisions/ADR-010-guard-policy-trust-terminology.md) | Terminoloji | `lock`/`trust`/`consent` sözlüğü; drift tablosu | Usage map lock drift'i ADR-011'i tetikledi; bağlam olmadan "lock" yasak |
| [ADR-011](../decisions/ADR-011-lock-semantics-decision.md) | Lock semantiği | **keystore_ready** ≠ **session_unlocked**; tek boolean yasak | Faz 1–3 #436–#438 tamam; Faz 4 trust motor bekliyor |
| [ADR-012](../decisions/ADR-012-lumos-security-codex.md) | Security Codex | C1–C6: tek kapı, onay/kanıt, trash, stop-on-risk | #440 docs; #441 panel şeffaflık; #443 panel policy enforcement |

## Öncelik sırası (sabit)

```
Guard (ADR-006) → Trust (ADR-007) → Router (ADR-004) → …
Terminoloji disiplini (ADR-010) tüm katmanlara tabidir.
Lock iki sinyal (ADR-011) trust tüketimine hazırlanır (Faz 4).
```

## Uygulama durumu (2026-06-21)

| PR | İçerik |
|----|--------|
| #435 | ADR-011 karar belgesi |
| #436 | Faz 1 — `keystore_ready` rename |
| #437 | Faz 2 — CLI `durum`/`hazir` etiket ayrımı |
| #438 | Faz 3 — panel keystore display honesty |
| #440 | ADR-012 Security Codex taslak paketi |
| #441 | Panel codex gate reason + UI warning |
| #443 | Panel `check_policy` enforcement (PR #2) |

## Sonraki checkpoint

- **ADR-011 Faz 4:** Merkezi trust sinyal modelinde `keystore_ready` ve `session_unlocked` ayrı alanlar; ADR-007 § Trust sinyalleri revizyonu.
- **ADR-012 takip:** `SECURITY_NEVER_AUTO` tüm yollar; panel `PUT /tasks.json` policy (ayrı PR).
