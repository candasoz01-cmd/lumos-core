# ADR-021 — Meta Çoklu Bağlantı Modeli (Credential ≠ Bağlantı)

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-09)** — kurucu onayı, iki ek şartla |
| Uygulama durumu | **Tamamlandı (2026-08-10)** — S1–S5 main'de + prod'da; kanıt kaydı için bkz. §Kapanış |
| Üst sınır | [ADR-020](ADR-020-meta-communications-exception.md) (salt-okunur, yayın yok), ADR-016 (kimlik ayrımı), [`ROADMAP.md`](../ROADMAP.md) STOP LIST |
| Kapsam | Meta communications bağlantılarının veri modeli, vault sözleşmesi, API ve UI |

## Gereksinim (kurucu, 2026-08-09)

Bir Lumos kullanıcısı **birden fazla Meta Business hesabı → her hesap altında birden
fazla WABA → her WABA altında birden fazla WhatsApp telefon numarası** bağlayabilmeli.
Her bağlantı ayrı kimlik, ad, durum, yetki (granted scopes) ve son doğrulama zamanıyla
görünmeli; sonradan yeni hesap/numara eklenebilmeli. Örnek: bir şirketin satış-TR,
destek-DE, marka başına ayrı numaraları. **Tekil provider kaydıyla devam edilmez.**

## Mevcut durum (2026-08-09 denetimi)

| Katman | Bulgu |
|--------|-------|
| Vault yazma | Yarı-hazır: `vault_ref = metaVaultRef(lumosId, provider, accountId)` (`api/auth/meta/callback.js`) — hesap kimliği anahtarda |
| Vault okuma | **Tekil:** `metaCredentialMetadata(lumosId, provider)` / `resolveMetaCredential(lumosId, provider)` hesap seçici almıyor (`api/_lib/meta_vault.js`) — provider başına tek credential, upsert'te son yazan kazanır |
| Durum API | Provider başına tek durum (`api/integrations/meta/token.js`) |
| UI | Provider başına tek kart (`ui/src/pages/integrations/meta.astro`) |
| WABA/numara | Modelde varlık yok |

## Karar

### 1. İki ayrı varlık — kurucu şartı: credential ≠ bağlantı

**MetaCredential** (OAuth sonucu; vault'ta yaşar, Lumos yalnız opak referans tutar):

```jsonc
MetaCredential {
  vault_ref,              // opak; secret değeri Lumos yüzeyine asla çıkmaz
  lumos_id, provider, provider_account_id,
  granted_scopes, expires_at, auth_mode
}
```

**MetaConnection** (kullanıcıya görünen bağlantı satırı):

```jsonc
MetaConnection {
  connection_id,          // conn_<ulid> — KALICI İÇ KİMLİK (kurucu şartı #1)
  lumos_id, provider,
  provider_account_id, business_id, waba_id, phone_number_id,
  display_name,           // kullanıcı düzenler ("Satış TR")
  status,                 // bağlantı BAŞINA: authorized | connected_readonly |
                          // expired | revoked | awaiting_credentials | ...
  granted_scopes,
  credential_ref,         // MetaCredential'a REFERANS (kurucu şartı #2)
  last_verified_at, created_at
}
```

**Kurucu şartı #1 — kalıcı iç kimlik:** `connection_id` oluşturulduktan sonra
değişmez. Provider tarafındaki kimlikler (hesap/WABA/telefon ID'si) değişse,
yeniden bağlansa veya provider kaydı silinip yeniden oluşsa bile `connection_id`
ve ona bağlı geçmiş/audit kaydı **korunur**; yeni provider kimliği aynı satıra
güncelleme olarak işlenir, tarihçe event olarak tutulur.

**Kurucu şartı #2 — credential çoğaltılmaz:** Bir OAuth credential'ı birden fazla
bağlantıyı (aynı hesabın birden çok WABA'sı, bir WABA'nın birden çok numarası)
besleyebilir. Bağlantı satırları credential'a `credential_ref` ile **referans verir**;
token/credential kopyalanmaz. Credential yenilenirse/revoke edilirse ona referans
veren TÜM bağlantıların durumu birlikte güncellenir (`expired`/`revoked`).

### 2. Vault sözleşmesi ekleri (private servis — ayrı iş)

- `credential.list(owner_lumos_id, provider?)` → `[{vault_ref, provider_account_id, expires_at, ...}]` (secret'sız metadata)
- `credential.resolve` **`vault_ref` ile** (hesap-kapsamlı; bugünkü owner+provider tekil çözümü geçiş süresince korunur)
- `credential.upsert` değişmez (zaten `vault_ref` anahtarlı)

### 3. API

- `GET /api/integrations/meta/connections` → bağlantı listesi (secret'sız)
- `POST /api/integrations/meta/sync` → `connection_id` parametreli; doğrulama
  sonucu `last_verified_at` günceller
- Callback **üzerine yazmaz:** `(provider, provider_account_id)` eşleşirse mevcut
  credential güncellenir, yoksa yeni credential yaratılır; bağlantı satırları ayrı
  adımda türetilir. WhatsApp OAuth sonrası WABA'lar ve numaraları listelenir →
  **kullanıcı hangilerini bağlayacağını seçer** → seçilen her numara ayrı
  `MetaConnection` olur.

### 4. UI

Provider kartı → **bağlantı listesi**: her satırda ad, durum rozeti, son doğrulama,
Doğrula/Kaldır; üstte "Yeni bağlantı ekle" (OAuth'u yeniden başlatır). Boş durumda
bugünkü tek "Bağla" düğmesi.

## Dilimler (küçük PR'lar — her biri test+CI+merge sonrası main doğrulamalı)

| Dilim | İçerik |
|-------|--------|
| S1 | Vault sözleşme ekleri — public adapter (+ private servis tarafı ayrı operasyon işi) |
| S2 | `MetaConnection` modeli + `connections` API (tekil uçlar geçiş süresince korunur) |
| S3 | UI bağlantı listesi (mevcut Facebook bağlantısı ilk satır olarak migrate) |
| S4 | WhatsApp WABA/numara enumerasyonu + kullanıcı seçim akışı (sandbox: WABA `1533094525525137`, test phone_number_id `1274066459120730`) |
| S5 | Bağlantı-başına doğrulama + `last_verified_at` + vitrin hizası |

## Sınırlar

- Secret/token hiçbir API yanıtında ve UI'da yer almaz; yalnız opak referans.
- Mesaj gönderme/yayın yok (ADR-020 ilk teslim yasağı aynen).
- **Gerçek telefon numarası bağlama kurucu onay kapısında** — bu ADR onu açmaz.
- Tekil→çoklu geçişte mevcut Facebook bağlantısı veri kaybı olmadan taşınır.

## Kapanış — salt-okunur ilk katman kanıt kaydı (2026-08-10)

Kapsam notu: bu bölüm 2026-08-10 gecesi itibarıyla gözlenen durumu kaydeder;
karar metnine yeni norm eklemez.

### Teslim edilen dilimler (uygulama durumu)

| Dilim | PR | Not |
|-------|----|-----|
| S1 vault adapter | #701 | `listMetaCredentials` + `resolveMetaCredentialByRef` |
| S2 connections API | #702 | açık etiketli fallback + kesintide 503 |
| S3 UI bağlantı listesi | #703 | GEÇİŞ MODU rozeti (gateway sonrası kalktı) |
| Gateway v2 kaynağı | #705, #706 | `services/credential-gateway/` — v1'in kayıp kaynağı yerine repoda; Infisical depolama; format-agnostik okuma v1 kayıtlarını okudu |
| S4a WhatsApp app kimlik ayrımı | #704 | whatsapp = 1046 Business app |
| S4c numara enumerasyonu | #707 | numara başına kalıcı `connection_id` |
| S5 last_verified_at | #708 | gateway `connection.upsert/list`, `stored_last_known` |
| Pages ayrı provider | #709, #710 | 1046 + yalnız `pages_show_list`; 1544 facebook değişmedi |
| Instagram bağlantı satırı | #711 | Instagram Login, yalnız `instagram_business_basic` |

### Canlı kanıt (2026-08-10 01:48–01:51, welockai.com/integrations/meta)

- whatsapp: Test Number `+1 555-669-8723` / WABA `1533094525525137` — doğrulandı
- pages: We Lock AI - ChatLumos `1197434016795571` (`pages_show_list`) — doğrulandı
- instagram: `@candasoz01` / `28431580439779647` (MEDIA_CREATOR,
  `instagram_business_basic`) — doğrulandı
- facebook: kimlik hattı authorized; senkron `0 hesap kaydı` — `public_profile`
  kapsamında beklenen davranış (Sayfa kayıtları pages hattında)

### Bu kapanışın DIŞINDA kalanlar (çözülmüş sayılmaz)

- App Review / Business verification: yapılmadı; app'ler dev-mode'da, erişim
  admin/tester hesaplarıyla sınırlı.
- Gerçek WhatsApp telefon numarası bağlama, ücret doğuran ve geri dönüşsüz
  işlemler: kurucu onay kapısında.
- Mesaj gönderme/yayınlama: ADR-020 sınırı aynen; yazma yetkileri ayrı bir
  ADR'ın konusudur ve o ADR açılmadı.
- ChatLumos marka Instagram hesabı: yok; açılırsa mevcut modelde ikinci
  bağlantı satırı olarak eklenir.
