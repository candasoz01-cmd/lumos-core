# Public repo boundary — canonical kayıt

## Amaç

Public `lumos-core` deposunda **kalıcı olarak tutulmaması gereken** strateji, operasyon ve prod entegrasyon içeriğinin tek kaynak (canonical) sınır kuralı.

Bu kural şunlarla uyumludur:

- [`security-architecture.md`](./security-architecture.md) §Public repo
- [`docs/decisions/ADR-002-mail-inbox-intelligence.md`](../decisions/ADR-002-mail-inbox-intelligence.md)
- Workspace `public-github-boundary` kuralları

**Revizyon:** OD-031 Phase 2 Step 4 (2026-06-21) — mail strateji + ops runbook sınırları birleştirildi; public kod stub gerçeği eklendi. Önceki ayrı dosyalar stub yönlendiricisine indirildi.

---

## Bölüm A — Mail / iletişim kanalları stratejisi

Mail ve iletişim kanalları **strateji / ürün otomasyon modeli** içeriği public repoda tam metin olarak bulunmaz.

### Public repoda OLMAMASI gerekenler (mail)

| Kategori | Örnekler |
|----------|----------|
| **Tam otomasyon / kural motoru** | Kural-kapsamlı otomatik yanıt, kişi/domain/konu kuralları, çakışma algoritması |
| **Granüler izin matrisi (ürün spec)** | `send_reply`, `archive`, `label`, `delete` seviyeleri ve oturum vs işlem ayrımı detayı |
| **Çok kanallı yol haritası** | Telegram, WhatsApp, Messenger, SMS genişleme planı |
| **Provider / vault seçimi** | Gmail OAuth seçimi, vault ürün adı, credential şeması, purpose kodları (tam spec) |
| **Uygulama checklist (M1–M7)** | Pilot sırası, smoke prosedürü, private impl paketi adımları |
| **Private orchestration** | Connector pilot sırası, vault bridge operasyon modeli, production endpoint |

### Nerede tutulur (mail)

| Konum | Amaç |
|-------|------|
| **`.lumos/internal/strategy-vault/`** | Gitignored yerel vault; tam strateji belgeleri |
| **`docs/mail-strategy-private-notice.md`** | Public operatör yönlendirmesi |
| **`docs/mail-strategy-migration-index.md`** | Hangi belgenin taşındığı (secret içermez) |

---

## Bölüm B — Operasyonel runbook'lar

Operational runbook içeriği public repoda tam metin olarak bulunmaz.

### Public repoda OLMAMASI gerekenler (ops)

| Kategori | Örnekler |
|----------|----------|
| **Gerçek IP / hostname** | Droplet public IP, origin IP, internal host |
| **SSH erişimi** | Port numaraları, uzak shell komutları, key path'leri, root kullanıcı bağlantıları |
| **Sunucu erişimi** | Web console adımları, authorized_keys yönetimi |
| **Firewall / ağ** | `ufw`, `iptables`, port allow listeleri (canlı değerlerle) |
| **Web sunucu ops** | Nginx site config snippet'leri (canlı path/domain/IP ile), Certbot komutları |
| **SSH daemon ops** | `sshd_config`, port değişiklikleri, servis restart adımları |
| **Deployment notları** | `/opt/...` path'leri, PM2/systemd canlı komutları, rsync/scp hedefleri |
| **Canlı infra durumu** | Droplet RAM/hostname, health URL'leri (IP ile), test kullanıcı/post detayları |
| **Operatör smoke adımları** | Canlı OAuth token, vault export, secret path, prod credential |

### Nerede tutulur (ops)

| Konum | Amaç |
|-------|------|
| **`.lumos/internal/ops-vault/`** | Gitignored yerel vault; tam operasyonel runbook içeriği |
| **`docs/ops-runbooks-private-notice.md`** | Public operatör yönlendirmesi |
| **`docs/ops-runbooks-migration-index.md`** | Hangi runbook'un taşındığı (secret içermez) |

Vault erişim notları (commit edilmez):

- `.lumos/internal/strategy-vault/README.md`
- `.lumos/internal/ops-vault/README.md`

---

## Bölüm C — Public kod stub gerçeği (demo-safe)

Public repoda **demo-safe foundation stub** kodu vardır; bu **ürün / prod entegrasyonu değildir**.

| Yol | Public'te ne var | Prod / private impl |
|-----|------------------|---------------------|
| **`src/integrations/mail/`** | Grant modeli (`read`, `notify`), OAuth callback **sözleşme tipleri** (`oauth_contract.py`), vault credential **ref** iskeleti, demo connector arayüzü | HTTP OAuth handler, token exchange, canlı Gmail API connector, panel UX, kural motoru |
| **`src/integrations/vault/`** | Amaç kodu iskeleti, vault adapter **arayüzü**, demo/read-only adapter | Self-host vault PoC operasyonu, credential yazma, production secret yönetimi |

**Hizalı kayıtlar:** ADR-002 §Public kod gerçeği; PR #413–#415 (contract + adapter + env-gated smoke — smoke operatör adımları ops vault'ta). Vault dar v1 tasarım çerçevesi: [`od-vault-dar-v1-design.md`](./od-vault-dar-v1-design.md).

**Drift uyarısı:** Stub kod varlığı «mail ürünü hazır» veya «canlı OAuth prod'da» anlamına gelmez. Onaylı private impl paketi ve operatör runbook'ları tamamlanmadan prod kapsam sayılmaz.

---

## Public dokümanlarda izin verilenler

- **ADR-002 seviyesi:** varsayılan kapalı izin, onaysız okuma/gönderim yok, demo-safe stub referansı
- **Placeholder referanslar:** `<PRIVATE_MAIL_STRATEGY_DOC>`, `<PRIVATE_MAIL_DAR_V1_DOC>`, `<PRIVATE_OPS_RUNBOOK>`, `<SERVER_IP>`, `<SSH_PORT>`
- **Stub belgeler:** Başlık + taşındı durumu + kısa non-sensitive özet + private notice linki
- **Open decisions indeksi:** OD satırları redakte; provider/vault/operatör detayı yok
- **Yüksek seviye mimari özet (ops):** "Nginx reverse proxy ile HTTPS", "Cloudflare DNS A record" — gerçek IP olmadan

---

## İlgili kayıtlar

| Kayıt | Bağlantı |
|-------|----------|
| Mail ADR (public demo-safe) | [`../decisions/ADR-002-mail-inbox-intelligence.md`](../decisions/ADR-002-mail-inbox-intelligence.md) |
| Güvenlik mimarisi | [`security-architecture.md`](./security-architecture.md) |
| Mail operatör notice | [`../mail-strategy-private-notice.md`](../mail-strategy-private-notice.md) |
| Mail migration index | [`../mail-strategy-migration-index.md`](../mail-strategy-migration-index.md) |
| Ops operatör notice | [`../ops-runbooks-private-notice.md`](../ops-runbooks-private-notice.md) |
| Ops migration index | [`../ops-runbooks-migration-index.md`](../ops-runbooks-migration-index.md) |
| Eski stub yönlendiricileri | [`public-mail-strategy-boundary.md`](./public-mail-strategy-boundary.md), [`public-ops-runbook-boundary.md`](./public-ops-runbook-boundary.md) |

---

## Ajan / geliştirici kuralı

- Public `docs/` altına yeni **tam strateji** veya **operasyonel runbook** ekleme; önce ilgili vault'a yaz, public'e stub veya migration index güncellemesi ekle.
- Mevcut public belgede provider seçimi, vault operasyon adımı, tam otomasyon spec, M1–M7 checklist, IP/SSH/canlı infra detayı görülürse → vault'a taşı, public'te stub bırak.
- **Commit öncesi doğrulama (mail stub'ları):** `Infisical`, `Gmail OAuth seçildi`, `send_reply`, kanal roadmap (Telegram/WhatsApp) public `docs/memory/mail-integration*` ve `od-031*` stub'larında **0** olmalıdır.
- **Commit öncesi doğrulama (ops):** gerçek IP adresleri, uzak shell komutları ve root kullanıcı bağlantı dizeleri `docs/` altında **0** olmalıdır.
