# Destek Kanalı — Alpha / Pilot

| Alan | Değer |
|------|-------|
| **Belge türü** | Operasyonel kayıt (docs only) |
| **Durum** | **P1-04 kapalı — özel Slack kanalı aktif** |
| **P1 ref** | P1-04 |
| **Kullanım** | Internal Alpha ve Closed Pilot yazılı destek hattı |

---

## Amaç

Yazılı destek kanalı ve **best-effort SLA** tanımı. Closed Pilot için
`#lumos-pilot-support` özel Slack kanalı, `support@` adresinin eşdeğeri olarak
kullanılır.

---

## Kanal tanımı

| Kanal | Adres / yol | Durum |
|-------|-------------|-------|
| Pilot desteği | [Özel Slack `#lumos-pilot-support`](https://lumos-3on9360.slack.com/archives/C0BK7R25NMS) | **Aktif** — davetle erişim |
| E-posta | `support@<DOMAIN_TBD>` | **Deferred** — özel Slack eşdeğeri aktif |
| Ekip içi (Alpha) | `#lumos-pilot-support` | **Aktif** |
| Güvenlik bulgusu | Aynı özel kanalda `[P0]` etiketi; gizli anahtar/veri yazılmaz | **Aktif pilot intake** |
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

- Internal Alpha: özel kanal + `make test` / CI izleme yeterli.
- Closed Pilot: `#lumos-pilot-support` yazılı destek kanalı olarak aktiftir.
- Kanala yalnız ops ekibi ve davetli pilot katılımcıları alınır.
- Token, parola, kişisel veri veya ham güvenlik kanıtı kanala yazılmaz; yalnız
  olay özeti ve güvenli kanıt referansı paylaşılır.

**İlgili:** [pilot-contract-template.md](pilot-contract-template.md) · [support-report-oraa.md](../templates/support-report-oraa.md) · [p0-p1-triage-list.md](p0-p1-triage-list.md) P1-04

---

*Son güncelleme: 2026-07-22 — özel `#lumos-pilot-support` kanalı aktif; P1-04 kapalı.*
