# Public ops runbook boundary — canonical kayıt

## Amaç

Operational runbook içeriğinin **public `lumos-core` deposunda** kalıcı olarak tutulmaması için tek kaynak (canonical) sınır kuralı.

Bu kural, [`security-architecture.md`](./security-architecture.md) §Public repo ve workspace `public-github-boundary` kurallarıyla uyumludur.

**Revizyon:** PR #252 (`docs/ops-runbook-visibility-cleanup`) — operasyonel runbook'ların public'ten private ops vault'a taşınması.

---

## Public repoda OLMAMASI gerekenler

Aşağıdaki içerik türleri **asla** public repo'da tam metin olarak bulunmaz:

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

---

## Nerede tutulur

| Konum | Amaç |
|-------|------|
| **`.lumos/internal/ops-vault/`** | Gitignored yerel vault; tam operasyonel runbook içeriği |
| **`docs/ops-runbooks-private-notice.md`** | Public operatör yönlendirmesi |
| **`docs/ops-runbooks-migration-index.md`** | Hangi runbook'un taşındığı (secret içermez) |

Vault erişim notu: `.lumos/internal/ops-vault/README.md` (commit edilmez).

---

## Public dokümanlarda izin verilenler

- **Placeholder referanslar:** `<SERVER_IP>`, `<SSH_PORT>`, `<PRIVATE_OPS_RUNBOOK>`, `<API_BASE_URL>`
- **Yüksek seviye mimari özet:** "Nginx reverse proxy ile HTTPS", "Cloudflare DNS A record"
- **Public domain adları:** Ürün API domain'i (ör. `api.example.com`) — gerçek IP eşlemesi olmadan
- **Stub runbook'lar:** Başlık + taşındı durumu + 5–7 maddelik non-sensitive özet + private notice linki

---

## İlgili kayıtlar

| Kayıt | Bağlantı |
|-------|----------|
| Güvenlik mimarisi | [`security-architecture.md`](./security-architecture.md) |
| Public GitHub sınırı | Workspace kuralı `public-github-boundary` |
| Operatör notice | [`../ops-runbooks-private-notice.md`](../ops-runbooks-private-notice.md) |
| Migration index | [`../ops-runbooks-migration-index.md`](../ops-runbooks-migration-index.md) |
| PR #252 revizyonu | `docs/ops-runbook-visibility-cleanup` branch |

---

## Ajan / geliştirici kuralı

- Public `docs/` altına yeni operasyonel runbook **ekleme**; önce vault'a yaz, public'e stub veya migration index güncellemesi ekle.
- Mevcut public runbook'ta IP, SSH komutu veya canlı infra detayı görülürse → vault'a taşı, public'te stub bırak.
- Commit öncesi doğrulama: gerçek IP adresleri, uzak shell komutları ve root kullanıcı bağlantı dizeleri `docs/` altında **0** olmalıdır.
