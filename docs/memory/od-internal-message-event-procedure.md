# OD-026 — Doğrulanmamış iç mesaj olay prosedürü (taslak)

**Durum:** **`needs-review`** → **`decision-approved`** (prosedür ilkesi) / **`implementation-pending`** (operasyonel detay private).  
**Kaynak:** [`internal-agent-layers.md`](./internal-agent-layers.md) §7; OD-006/007 ile hizalı.

---

## 1. Onaylı prosedür ilkesi

| Olay | Davranış |
|------|----------|
| Doğrulanmamış iç mesaj | **Reddet**; yürütme yok |
| Yetkisiz kaynak → Bando | **Güvenlik olayı** (incident) — OD-006 |
| Kayıt | Append-only olay kaydı (EC v1 ruhu); PII/secret loga yazılmaz |
| Kullanıcıya | Görünmez — iç katman; yalnızca Lumos dili dış yüzde |

---

## 2. Implementation-pending (private)

| # | Madde |
|---|--------|
| I1 | Mesaj formatı doğrulama hook'u |
| I2 | Olay kaydı şeması (public'te tanım yok) |
| I3 | Anahtar döngüsü / imza hatası eskalasyonu — OD-007 private |
| I4 | Bando raporlama kanalı |

---

## 3. OD eşleme

| OD | Durum |
|----|--------|
| OD-026 | decision-approved / implementation-pending |
| OD-006 | decision-approved / implementation-pending |
| OD-007 | decision-approved / implementation-pending — protokol private |

---

Son güncelleme: 2026-06-20 (envanter ab791c14 §12 #10 — Phase 3)
