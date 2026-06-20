# Public mail strategy boundary — canonical kayıt

## Amaç

Mail ve iletişim kanalları **strateji / ürün otomasyon modeli** içeriğinin public
`lumos-core` deposunda kalıcı olarak tutulmaması için tek kaynak (canonical) sınır kuralı.

Bu kural, [`security-architecture.md`](./security-architecture.md) §Public repo,
[`docs/decisions/ADR-002-mail-inbox-intelligence.md`](../decisions/ADR-002-mail-inbox-intelligence.md)
ve workspace `public-github-boundary` kurallarıyla uyumludur.

**Revizyon:** OD-031 strategy migration (2026-06-20) — tam strateji belgelerinin
public'ten private strategy vault'a taşınması.

---

## Public repoda OLMAMASI gerekenler

Aşağıdaki içerik türleri **asla** public repo'da tam metin olarak bulunmaz:

| Kategori | Örnekler |
|----------|----------|
| **Tam otomasyon / kural motoru** | Kural-kapsamlı otomatik yanıt, kişi/domain/konu kuralları, çakışma algoritması |
| **Granüler izin matrisi (ürün spec)** | `send_reply`, `archive`, `label`, `delete` seviyeleri ve oturum vs işlem ayrımı detayı |
| **Çok kanallı yol haritası** | Telegram, WhatsApp, Messenger, SMS genişleme planı |
| **Provider / vault seçimi** | Gmail OAuth seçimi, Infisical yol haritası, credential şeması, purpose kodları |
| **Uygulama checklist (M1–M7)** | Pilot sırası, smoke prosedürü, private impl paketi adımları |
| **Private orchestration** | Connector pilot sırası, vault bridge operasyon modeli, production endpoint |

---

## Nerede tutulur

| Konum | Amaç |
|-------|------|
| **`.lumos/internal/strategy-vault/`** | Gitignored yerel vault; tam strateji belgeleri |
| **`docs/mail-strategy-private-notice.md`** | Public operatör yönlendirmesi |
| **`docs/mail-strategy-migration-index.md`** | Hangi belgenin taşındığı (secret içermez) |

Vault erişim notu: `.lumos/internal/strategy-vault/README.md` (commit edilmez).

---

## Public dokümanlarda izin verilenler

- **ADR-002 seviyesi:** varsayılan kapalı izin, onaysız okuma/gönderim yok, demo-safe stub
- **Placeholder referanslar:** `<PRIVATE_MAIL_STRATEGY_DOC>`, `<PRIVATE_MAIL_DAR_V1_DOC>`
- **Stub belgeler:** Başlık + taşındı durumu + kısa non-sensitive özet + private notice linki
- **Open decisions indeksi:** OD satırları redakte; Infisical/Gmail/provider detayı yok

---

## İlgili kayıtlar

| Kayıt | Bağlantı |
|-------|----------|
| Mail ADR (public demo-safe) | [`../decisions/ADR-002-mail-inbox-intelligence.md`](../decisions/ADR-002-mail-inbox-intelligence.md) |
| Güvenlik mimarisi | [`security-architecture.md`](./security-architecture.md) |
| Public GitHub sınırı | Workspace kuralı `public-github-boundary` |
| Operatör notice | [`../mail-strategy-private-notice.md`](../mail-strategy-private-notice.md) |
| Migration index | [`../mail-strategy-migration-index.md`](../mail-strategy-migration-index.md) |

---

## Ajan / geliştirici kuralı

- Public `docs/memory/` altına yeni mail strateji belgesi **ekleme**; önce vault'a yaz, public'e stub veya migration index güncellemesi ekle.
- Mevcut public belgede provider seçimi, vault ürün adı, tam otomasyon spec veya M1–M7 checklist görülürse → vault'a taşı, public'te stub bırak.
- Commit öncesi doğrulama: `Infisical`, `Gmail OAuth seçildi`, `send_reply`, kanal roadmap (Telegram/WhatsApp) public `docs/memory/mail-integration*` ve `od-031*` stub'larında **0** olmalıdır.
