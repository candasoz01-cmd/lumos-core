# Lumos Persona — Internal Inventory Policy (public)

| Alan | Değer |
|------|-------|
| Durum | **Public policy** — davranış değişikliği yok |
| Tarih | 2026-06-07 |
| İlgili PR | [#102](https://github.com/candasoz01-cmd/lumos-core/pull/102) (public giriş sınıfı özeti) |
| Public sınıf özeti | [lumos-persona-bypass-entry-inventory.md](lumos-persona-bypass-entry-inventory.md) |
| Checkpoint / gap | [lumos-persona-security-checkpoint.md](lumos-persona-security-checkpoint.md) · [lumos-persona-security-implementation-gaps.md](lumos-persona-security-implementation-gaps.md) |

## Amaç

Public foundation repo (`lumos-core`) **detaylı giriş envanteri** (satır satır bypass haritası, dosya yolu, modül/CLI/HTTP adı, fonksiyon adı) taşımaz. Bu belge, detay envanterin nerede tutulacağını ve public/private sınırını tanımlar.

## Public repo kapsamı

- Giriş **sınıfı** özeti (5 sınıf + panel ilişkisi) — bkz. [lumos-persona-bypass-entry-inventory.md](lumos-persona-bypass-entry-inventory.md) (PR #102).
- Checkpoint soruları, gap kayıtları, salt okuma test planı.
- Odaklı davranış / read-only pytest (ör. `tests/test_persona_security_simdi_checkpoint.py`) — **detay tablo içermez**.

## Internal / private kapsamı

Aşağıdaki içerik **yalnızca internal/private** katmanda tutulur:

- 22+ satırlık (veya eşdeğer) **detaylı bypass / giriş envanteri tablosu**
- Dosya yolu, endpoint, CLI komutu, modül ve fonksiyon referansları
- Bypass tarifi veya “nasıl atlanır” operasyonel notları
- Protokol, anahtar veya wire-format detayı

### Önerilen konumlar (birini seç; public’e commit etme)

| Seçenek | Konum | Not |
|---------|--------|-----|
| **A — Private repo** | Professional / private Lumos repo altında `docs/security/persona-entry-inventory.md` (veya eşdeğer) | Ekip erişimi, sürüm kontrolü private remote’ta |
| **B — Yerel gitignored** | `.lumos/internal/persona-security-inventory/` (içerik dosyaları) | Tek geliştirici veya yerel audit; **asla** `lumos-core` public remote’a push edilmez |

`.lumos/internal/` zaten `.gitignore` ile hariç tutulur; envanter dosyalarının yanlışlıkla stage edilmemesi için bu politika açıkça kayıtlıdır.

## Public repo’da yapılmaz

- Detaylı envanter markdown veya JSON commit etmek
- Bypass haritasını issue/PR gövdesine yapıştırmak (public)
- Public test veya dokümana gerçek secret, token veya production URL koymak

## İlişki (PR #102)

[PR #102](https://github.com/candasoz01-cmd/lumos-core/pull/102) public-safe **giriş sınıfı** özetini ekledi; detay envanter redakte edildi. Bu politika belgesi, redaksiyonun kalıcı kuralını sabitler: detay envanter → internal/private veya gitignored `.lumos/internal/`.

## Sonraki adımlar

- Internal envanter güncellemeleri private/yerel kanalda yapılır.
- Public tarafta: checkpoint “Şimdi” read-only testleri ve sınıf düzeyi gap takibi ([implementation gaps](lumos-persona-security-implementation-gaps.md)).
- Sonraki faz: tek kapı invariant, offline auto-push yok, gateway sonuç-only contract — [checkpoint](lumos-persona-security-checkpoint.md).

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki ve kilit alanları bu politika ile gevşetilmez.
