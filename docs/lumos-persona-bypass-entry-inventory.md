# Lumos Persona — Giriş yüzeyi sınıflandırması (public)

| Alan | Değer |
|------|-------|
| Durum | **Public özet** — davranış değişikliği yok |
| Tarih | 2026-06-07 |
| İlgili PR | [#100](https://github.com/candasoz01-cmd/lumos-core/pull/100), [#101](https://github.com/candasoz01-cmd/lumos-core/pull/101), [#102](https://github.com/candasoz01-cmd/lumos-core/pull/102) |
| Persona | [lumos-persona-layers.md](lumos-persona-layers.md) · Checkpoint: [lumos-persona-security-checkpoint.md](lumos-persona-security-checkpoint.md) · Gap: [lumos-persona-security-implementation-gaps.md](lumos-persona-security-implementation-gaps.md) |

## Amaç

[lumos-persona-layers.md](lumos-persona-layers.md) ilkesine göre dış etkili iş yalnızca **doğrulanmış Lumos kanalı** üzerinden iç katmanlara ulaşmalıdır. Bu belge, public foundation kapsamında **hangi giriş sınıflarının güvenlik kontrolüne alınması gerektiğini** özetler.

**Bu belgede yok:** dosya yolu, modül/CLI/HTTP adı, fonksiyon adı, bypass tarifi, protokol veya anahtar detayı.

> **İç envanter:** Satır satır giriş tablosu ve kod referansları **internal/private security inventory** kapsamındadır; bu public repo’da tutulmaz. Konum ve kurallar: [lumos-persona-internal-inventory-policy.md](lumos-persona-internal-inventory-policy.md).

---

## Persona özeti

- **Tek giriş:** Kando ve Cando işi yalnızca Lumos üzerinden kabul eder.
- **Cando read-only:** Recipe/runbook öneri/rapor; otomatik yazma veya dış aksiyon yok.
- **Offline:** Reconnect’te otomatik dış gönderim yok; onay ve doğrulama gerekir.
- **Secret:** Lumos ana secret deposu değil; gateway iletişimi sonuç odaklı olmalıdır.

---

## Giriş sınıfları (kontrol hedefi)

Her sınıfta Lumos gate / policy / onay zincirinin tutarlı uygulanması hedeflenir.

| # | Sınıf | Kontrol odağı | Checkpoint | Gap |
|---|-------|---------------|------------|-----|
| 1 | **Köprü / gateway** | Dış HTTP geçitleri; tam gate vs kısmi yönlendirme, onay sonrası yürütme | [§1](lumos-persona-security-checkpoint.md#1-lumos-tek-dış-geçit) | [#1](lumos-persona-security-implementation-gaps.md#1-lumos-dışından-kandoya-komut-cli-taskengine-bypass) |
| 2 | **Yerel CLI / görev motoru** | Terminalden görev oluşturma, mutasyon, motor yürütmesi | [§1](lumos-persona-security-checkpoint.md#1-lumos-tek-dış-geçit) | [#1](lumos-persona-security-implementation-gaps.md#1-lumos-dışından-kandoya-komut-cli-taskengine-bypass) |
| 3 | **Cando recipe** | Read-only rutinlerin kanal doğrulaması ve yabancı giriş reddi | [§2](lumos-persona-security-checkpoint.md#2-kando-cando-doğrudan-dış-komut-iş-dosya-veri) | [#2](lumos-persona-security-implementation-gaps.md#2-cando-doğrudan-dosya-komut-yabancı-giriş-ve-lumos-kanalı) |
| 4 | **Offline / push** | Otomatik dış aksiyon, kuyruk flush, reconnect senaryoları | [§3](lumos-persona-security-checkpoint.md#3-offline-kuyruk-otomatik-push-sync-pr-mail-api) | [#3](lumos-persona-security-implementation-gaps.md#3-offline-kuyruk-internet-gelince-otomatik-dış-aksiyon-yok) |
| 5 | **Secret / imza** | Kimlik doğrulama, keystore, sonuç odaklı gateway sözleşmesi | [§4](lumos-persona-security-checkpoint.md#4-lumos-secret-ana-deposu-değil), [§6](lumos-persona-security-checkpoint.md#6-anti-lumos-taklit-yüksek-seviye) | [#4](lumos-persona-security-implementation-gaps.md#4-lumos-secret-ana-deposu-değil-sonuç-odaklı-iletişim), [#5](lumos-persona-security-implementation-gaps.md#5-sahte-lumos-imzası-iç-mesaj-reddi-anti-taklit) |

Ek yüzey: panel görev durumu yazımı köprü gate’inden ayrı denetlenir (sınıf 1–2 ile ilişkili).

---

## Kontrol durumu (2026-06-07)

| Sınıf | Durum |
|-------|--------|
| Köprü / gateway | Kısmi gate; invariant test bekliyor |
| CLI / görev motoru | Gate zinciri eksik |
| Cando recipe | Kanal doğrulama yok |
| Offline / push | Otomatik dış aksiyon riski |
| Secret / imza | Sözleşme henüz enforce edilmiyor |

Sayısal satır envanteri yalnızca internal belgede; public özet sınıf düzeyindedir.

---

## Kapsam

**Bu PR (#102):** Public-safe giriş sınıfı özeti; detay envanter repo dışına taşındı.

**PR #101:** Checkpoint ve gap kayıtları.

**Sonraki faz:** Tek kapı invariant testleri, Cando yabancı giriş reddi, offline auto-push yok, gateway sonuç-only contract — [checkpoint](lumos-persona-security-checkpoint.md).

---

## Ne yapılmaz

Kod/test/recipe değişikliği; güvenlik gevşetmesi; bypass tarifi; `lumos-karar-sozlesmesi` implementasyonu.

**Sonraki adım:** Gap #1 için CLI–gate hizası davranış testi taslağı (ayrı PR; internal envanter girdisi).
