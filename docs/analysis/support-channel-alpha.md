# Destek Kanalı — Alpha / Pilot Şablonu

| Alan | Değer |
|------|-------|
| **Belge türü** | Operasyonel şablon (docs only) |
| **Durum** | **Alpha exit gate — template ready** |
| **P1 ref** | P1-04 |
| **Kullanım** | Closed Pilot öncesi destek/ops tarafından doldurulur |

---

## Amaç

Yazılı destek kanalı ve **best-effort SLA** tanımı için minimum iskelet. Alpha fazında kanal adresi TBD kalabilir; şablon planlama boşluğunu kapatır.

---

## Kanal tanımı

| Kanal | Adres / yol | Durum |
|-------|-------------|-------|
| E-posta | `support@<DOMAIN_TBD>` (onaylı format — adres TBD) | ☐ Aktif |
| Ekip içi (Alpha) | Slack / dahili kanal | Alpha döneminde yeterli |
| Güvenlik bulgusu | Ayrı güvenlik hattı (TBD) | ☐ Tanımlı |
| Durum sayfası | `status.welockai.com` (TBD) | ☐ Yok |

---

## SLA şablonu (best-effort)

| Öncelik | Tanım | Hedef yanıt | Hedef çözüm |
|---------|-------|-------------|-------------|
| **P0 — güvenlik** | Veri sızıntısı, onay bypass, yetkisiz yürütme | 24 saat (iş günü) | Acil patch / devre dışı |
| **P1 — blokaj** | Panel/köprü tamamen kullanılamaz | 48 saat | Geçici yol veya fix |
| **P2 — genel** | UX, dokümantasyon, özellik isteği | 5 iş günü | Backlog |
| **P3 — öneri** | İyileştirme | En iyi çaba | Planlama |

*Alpha döneminde SLA **best-effort**; ticari taahhüt değildir.*

---

## Alpha notu

- Internal Alpha: ekip içi kanal + `make test` / CI izleme yeterli.
- Closed Pilot: bu şablon doldurulmuş ve `support@` (veya eşdeğeri) yayında olmalıdır.

**İlgili:** [pilot-contract-template.md](pilot-contract-template.md) · [p0-p1-triage-list.md](p0-p1-triage-list.md) P1-04

---

*Son güncelleme: 2026-06-26 — template ready; kanal TBD.*
