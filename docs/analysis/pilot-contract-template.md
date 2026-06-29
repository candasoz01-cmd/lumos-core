# Pilot Sözleşmesi — Şablon (Alpha çıkış kapısı)

| Alan | Değer |
|------|-------|
| **Belge türü** | Operasyonel şablon (docs only — hukuki metin değil) |
| **Durum** | **Alpha exit gate — template ready** |
| **P1 ref** | P1-03 |
| **Kullanım** | Closed Pilot başlamadan önce ticari/ops tarafından doldurulur |

---

## Amaç

Internal Alpha sonrası **≤20 kişilik Closed Pilot** için minimum sözleşme iskeleti. Gerçek pilot daveti bu şablon doldurulmadan başlamaz; Alpha fazında yalnızca şablon hazırlığı yeterlidir.

**Kaynak tasarım:** [pilot-user-program-design.md](pilot-user-program-design.md)

---

## Şablon alanları

| Alan | Açıklama | Doldurulacak |
|------|----------|--------------|
| Pilot adı | Program kod adı | `____________` |
| Katılımcı sayısı | Maks. 20 | `___ / 20` |
| Başlangıç tarihi | Closed Pilot kickoff | `YYYY-MM-DD` |
| Bitiş / gözden geçirme | İlk değerlendirme | `YYYY-MM-DD` |
| Katman | OSS stub / private executor (NDA) | ☐ OSS  ☐ Private |
| NDA / gizlilik | Embargo süresi (ör. 30/90 gün) | `____________` |
| Kapsam dışı | Alpha O1–O8, Wave 2, gerçek OAuth | Sabit — değiştirilmez |
| Güvenlik beklentisi | Onay olmadan yürütme yok; `SECURITY_NEVER_AUTO` | Kabul imzası |
| Bulgu raporlama | Kanal + SLA (bkz. support-channel-alpha.md) | `____________` |
| Veri işleme | Pilot verisi silme / retention | `____________` |
| İmza — katılımcı | | `____________` |
| İmza — WeLockAI / ops | | `____________` |

---

## Alpha notu

Bu şablon **P1-03 planlama boşluğunu kapatır**. Gerçek pilot sözleşmesi imzası Closed Pilot kapısıdır; Internal Alpha'da zorunlu değildir.

---

*Son güncelleme: 2026-06-26 — template ready; pilot başlatılmadı.*
