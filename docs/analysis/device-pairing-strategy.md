# Cihaz Eşleştirme Stratejisi Karşılaştırması

| Alan | Değer |
|------|-------|
| Durum | **Analiz** — kod yok; karar destek belgesi |
| Tarih | 2026-06-22 |
| Kapsam | Lumos PC ↔ Lumos Mobile onay relay eşleştirmesi |
| İlgili | [lumos-mobile-approval-mvp-plan.md](lumos-mobile-approval-mvp-plan.md), [device-connection-architecture-draft.md](device-connection-architecture-draft.md), [device-connection-information-architecture.md](device-connection-information-architecture.md), [pr-rb-06-lan-relay-verification.md](pr-rb-06-lan-relay-verification.md), [ADR-012](../decisions/ADR-012-lumos-security-codex.md) |

**Public OSS sınırı:** Bu belge açık kaynak foundation katmanını kapsar. RB-06 LAN relay **demo-safe OSS** iskeletidir; TLS, hesap bağlı eşleştirme, push backend ve native Lumos Mobile uygulaması **private / professional katmandadır** ([public-repo-boundary](../memory/public-repo-boundary.md)).

---

## 1. Bağlam

Lumos Mobile onay MVP'si, PC üzerindeki `kando_bridge` köprüsünün (`127.0.0.1:8765`, `KANDO_BRIDGE_SECRET`) bekleyen PC remote onay kayıtlarını mobil istemciye taşır. Telefon doğrudan loopback köprüye erişemez; arada **LAN relay** (`lan_relay.py`, `:8766`) köprü secret'ını Mobile'a sızdırmadan proxy yapar.

Eşleştirme (pairing), Mobile'ın relay üzerinde **relay-scoped oturum** (`relay_token`, `X-Relay-Token`) alması için gereklidir. Onay akışı: pending disk → köprü `GET /pending_approvals` → relay filtre → Mobile poll → `POST /relay/approve` → köprü `POST /approve`.

**RB-06 mevcut durum (doğrulanmış):** 6 karakter `pairing_code` + `GET /relay/discover` + UDP beacon (`8767`) + `POST /relay/pair` → `relay_token` (~32 byte url-safe) + `/relay/mobile?token=…`. Köprü secret beacon/discover yanıtında **yok** ([pr-rb-06-lan-relay-verification.md](pr-rb-06-lan-relay-verification.md)).

**ADR-012 hizası:** Köprü yalnızca loopback; Mobile secret taşımaz; onay açık kullanıcı eylemi; `SECURITY_NEVER_AUTO` otomatik değil; simülasyon gerçek başarı gibi sunulmaz.

---

## 2. Strateji karşılaştırma tablosu

Puanlama **MVP uygunluk** (1 = zayıf, 5 = güçlü) — Internal Alpha / ilk mobil onay hedefi için.

| Strateji | UX | Güvenlik | Uygulama maliyeti | Offline / LAN gereksinimi | Phishing riski | MVP uygunluk (1–5) |
|----------|-----|----------|-------------------|----------------------------|----------------|---------------------|
| **QR kod** | Yüksek — tek tarama, URL+kod birleşimi | Orta–yüksek — kısa ömürlü payload ile iyi; ekran görüntüsü sızıntısı riski | Orta — kamera, QR encode/decode, UI; protokol önce sabitlenmeli | Aynı fiziksel ortam veya güvenilir ekran paylaşımı; internet şart değil | Orta — sahte QR / overlay saldırısı | **2** — v1 planında ertelendi |
| **Pairing code (6 hane)** | Orta — PC ekranından okuma + Mobile girişi | Orta — kısa kod + TTL; brute force LAN'da mümkün (entropy sınırlı) | **Düşük** — RB-06 uygulandı; CLI + web UI | **LAN veya bilinen relay URL**; internet gerekmez | Düşük–orta — sosyal mühendislik («kodu söyle») | **5** — mevcut implementasyon |
| **Token link (URL)** | Yüksek — tek tık / tarayıcı aç | Orta — yüksek entropili token; link sızıntısı = oturum ele geçirme | Düşük–orta — pair sonrası `mobile_url` zaten var; tek başına keşif zayıf | LAN veya linkin ulaştığı kanal (SMS, e-posta = dış kanal) | **Yüksek** — link forwarding, chat log, referrer | **3** — pair **sonrası** UX; keşif için tek başına yetersiz |
| **LAN discovery (UDP / HTTP)** | Yüksek — «PC'yi bul» otomatik; kod girişi azalır | Orta — LAN MITM ve sahte beacon; kod hâlâ ikinci faktör | **Düşük** — RB-06: `GET /relay/discover` + UDP beacon | **Zorunlu aynı LAN** (veya loopback test); internet yok | Düşük — yerel ağ; sahte cihaz listesi | **4** — keşif katmanı; pairing code ile birlikte **5** |

**Not:** En yüksek MVP skoru **pairing code + LAN discovery birleşimi** için; tabloda ayrı satırlar strateji türlerini izole karşılaştırır.

---

## 3. Her strateji detay

### 3.1 QR kod

#### Nasıl çalışır

PC relay, ekranda QR gösterir; payload tipik olarak `relay_url` + kısa ömürlü `pairing_id` / imzalı challenge içerir. Mobile tarar → otomatik keşif + eşleştirme adımına geçer. IA hedefi: «Cihaz eşleştir» akışında tek seferlik gösterim, ekranda kalıcı değil ([device-connection-information-architecture.md §5.2](device-connection-information-architecture.md)).

#### Artılar / eksiler

| Artılar | Eksiler |
|---------|---------|
| Düşük yazım hatası; hızlı kurulum | Kamera izni, aydınlatma, erişilebilirlik |
| URL + kod tek pakette | QR protokolü OSS'te **tanımlı değil** |
| UX olgun ürünlerde standart | v1 tek PC + tek Mobile için zorunlu değil |
| Pairing code'un sunum katmanı olabilir | Overlay / sahte QR phishing vektörü |

#### Lumos mevcut durum

- [lumos-mobile-approval-mvp-plan.md §7](lumos-mobile-approval-mvp-plan.md): **v1 hayır** — QR, pairing protokolü oturmadan anlamsız.
- RB-06: QR yok; terminalde `pairing=XXXXXX` metin çıktısı.
- Public OSS: QR **sunum katmanı** olarak dokümante edilebilir; prod QR imza/TLS private katman kararı.

---

### 3.2 Pairing code (6 hane)

#### Nasıl çalışır

1. Relay başlatılır → `RelayState.refresh_pairing()` ile 6 karakter A–Z0–9 kod (`secrets.choice`, ~2,1×10⁹ kombinasyon).
2. Mobile keşif sonrası `POST /relay/pair` gövdesinde `pairing_code` gönderir.
3. Kod eşleşir ve TTL geçerliyse (`pairing_expires_at`, varsayılan **600 s**) → `relay_token` (`token_urlsafe(32)`) döner; oturum süresi `max(3600, pairing_ttl × 6)`.
4. Korunan uçlar (`/relay/pending`, `/relay/approve`, `/relay/reject`) `X-Relay-Token` ister.

#### Artılar / eksiler

| Artılar | Eksiler |
|---------|---------|
| RB-06 **uygulandı ve test edildi** (11 e2e) | 6 hane entropy sınırlı — agresif brute force (LAN) |
| Panel/CLI'da gösterimi basit | Kullanıcı kodu yanlış girer / TTL dolar |
| `KANDO_BRIDGE_SECRET` Mobile'a gitmez | Kod ekranda görünür — shoulder surfing |
| ADR-012 loopback modeli korunur | Uzaktan (internet) senaryoda yetersiz tek başına |

#### Lumos mevcut durum

- `lan_relay.py`: `_pairing_code()`, `state.pair()`, hata kodları `pairing_expired`, `invalid_pairing_code`.
- Doğrulama: geçerli kod → token; yanlış/süresi dolmuş → 403 ([pr-rb-06-lan-relay-verification.md](pr-rb-06-lan-relay-verification.md)).
- MVP plan D1: **Tek seferlik kod + TLS (v1)** — TLS henüz demo dışı (private).

---

### 3.3 Token link (URL)

#### Nasıl çalışır

Eşleştirme **başarılı** olduktan sonra relay `mobile_url` / `mobile_ui` döner: `/relay/mobile?token=<relay_token>`. Mobile tarayıcı veya uygulama linki açar; sayfa token'ı `sessionStorage`'da tutar ve poll başlatır.

Tek başına «link ile eşleştirme»: uzun ömürlü veya tek kullanımlık URL'nin chat/e-posta ile paylaşılması — keşif olmadan relay adresi bilinmeli.

#### Artılar / eksiler

| Artılar | Eksiler |
|---------|---------|
| Pair sonrası sürtünmesiz UX (RB-06 web UI) | Link **pair öncesi** keşif sağlamaz |
| Yüksek entropili token (256 bit class) | Link iletimi = oturum devri (token theft) |
| Ek client kodu minimal (tarayıcı) | Phishing: sahte «Lumos onay» URL |
| CLI `pair --save-token` ile otomasyon | Referrer / log / paylaşım kanalı sızıntısı |

#### Lumos mevcut durum

- `mobile_ui_path(token=…)` RB-06'da mevcut; **pairing mekanizması değil**, oturum taşıma UX'i.
- IA: eşleştirme kodu tek seferlik UI; token/secret kalıcı panel listesinde **gösterilmez**.
- MVP: link, pairing code **sonrası** adım; birincil strateji olarak önerilmez.

---

### 3.4 Yerel ağ keşfi (LAN discovery)

#### Nasıl çalışır

**HTTP:** `GET /relay/discover` → `pairing_id`, `device_id`, `device_name`, `relay_url`, `requires_pairing`, `pairing_expires_at` (secret yok).

**UDP beacon:** `255.255.255.255:8767` + loopback, ~3 sn aralık, yalnızca `pairing_valid()` iken. Payload: `schema_version`, `pairing_id`, `relay_port`, `pc_name`, `device_id`.

Mobile: beacon dinler veya discover URL çağırır → PC listesi → kullanıcı seçer → pairing code ile pair.

#### Artılar / eksiler

| Artılar | Eksiler |
|---------|---------|
| Manuel IP/URL girişi kalkar | **Aynı LAN zorunlu** — farklı ağ = çalışmaz |
| RB-06 HTTP + UDP **doğrulandı** | Sahte beacon / rogue relay (MITM) |
| Bridge secret taşınmaz | mDNS/Bonjour yok — UDP broadcast kısıtları (VLAN, misafir Wi‑Fi) |
| CI-friendly loopback test | İnternet tüneli / uzaktan onay MVP dışı |

#### Lumos mevcut durum

- `BeaconBroadcaster`, `listen_beacon_once()`, `discover --beacon` CLI.
- Sonraki adım listesinde: mDNS/Bonjour (UDP yerine) — **açık karar**, uygulanmadı.
- [device-connection-architecture-draft.md §5](device-connection-architecture-draft.md): v1 «bağlı cihaz» = aynı LAN / aynı kullanıcı varsayımı.

---

## 4. Tehdit modeli (kısa)

| Tehdit | Etkilenen strateji | Mevcut kontrol (RB-06 / ADR-012) | Kalan boşluk |
|--------|-------------------|----------------------------------|--------------|
| **Token theft** | Token link, pair sonrası URL | `relay_token` TTL; invalid/expired reddi | HTTPS/TLS yok (demo); token sessionStorage — XSS |
| **MITM on LAN** | Discovery, HTTP relay | Bridge secret PC loopback'te kalır | Plain HTTP relay; sahte relay / beacon |
| **Brute force pairing code** | Pairing code | TTL 600 s; tek aktif kod; 403 hata | 6 hane ~36⁶; rate limit **yok** (RB-10 adayı) |
| **QR / ekran sızıntısı** | QR, pairing code ekranı | Kısa TTL; kod yenileme (`refresh_pairing`) | Shoulder surfing; screenshot paylaşımı |
| **Phishing link** | Token link | — | Kullanıcı eğitimi; güvenilir cihaz rozeti (IA) |
| **Replay onay** | Tümü (onay katmanı) | `approval_token` tek kullanımlık; `used` bayrağı | Relay compromise → pending listeleme / onay |

**ADR-012 ilkesi:** Emin olunmayan kanalda «güvenli» iddiası yok; demo relay **production güven** değildir. Consent / lock / profil onaydan bağımsız — pairing ≠ tam trust ([device-connection-architecture-draft.md §3.3](device-connection-architecture-draft.md)).

---

## 5. MVP önerisi

### Önerilen yaklaşım: **LAN discovery + 6 haneli pairing code**

**Gerekçe:**

1. **Repo gerçeği:** RB-06 bu kombinasyonu uygular ve e2e ile doğrulanmıştır; sıfırdan alternatif protokol gereksiz gecikme ([özellik öncesi hazır çözüm](../.cursor/rules/ozellik-oncesi-hazir-cozum-taramasi.mdc) — mevcut OSS iskelet).
2. **MVP plan hizası:** QR ve push v1 **hayır**; manuel/tek seferlik kod yeterli ([lumos-mobile-approval-mvp-plan.md §7](lumos-mobile-approval-mvp-plan.md)).
3. **Güvenlik minimumu:** İki adım — (a) LAN'da PC keşfi, (b) kullanıcı onaylı kod girişi — `KANDO_BRIDGE_SECRET` exfil olmadan relay oturumu.
4. **UX:** Discovery IP yazımını kaldırır; kod girişi Internal Alpha için kabul edilebilir.
5. **Public sınır:** OSS'te demo relay + dokümantasyon; TLS, rate limit, native app **private PR-RB-07+**.

### MVP akış (özet)

```
PC: köprü (loopback) + relay başlat → ekranda pairing kodu
Mobile: discover (beacon veya /relay/discover) → PC seç → kodu gir → pair
Mobile: relay_token ile /relay/pending poll → onay/red
```

### MVP'de bilinçli olarak olmayanlar

- QR tarama
- Push (FCM/APNs)
- Hesap / `DeviceIdentity` bağlı eşleştirme
- İnternet üzerinden uzaktan relay
- mDNS (UDP beacon yeterli demo)
- Pairing rate limit (RB-10 sonrası)

### MVP one-liner

> **Internal Alpha'da LAN discovery (HTTP + UDP beacon) ile PC bulunur, 6 haneli pairing code ile relay oturumu açılır; RB-06 akışı değiştirilmeden private Lumos Mobile istemcisine taşınır.**

---

## 6. Uzun vadeli öneri

### Hibrit yol haritası

| Faz | Keşif | Eşleştirme | Trust |
|-----|-------|------------|-------|
| **v1 — Internal Alpha** | UDP + `/relay/discover` | 6 hane pairing code | Relay token (cihaz oturumu) |
| **v2 — Beta** | mDNS/Bonjour + panel «Cihaz eşleştir» | QR = pairing code **sunum katmanı** (aynı protokol) | TLS relay; pairing rate limit |
| **v3 — Prod** | Hesap halkası içi cihaz envanteri | Account-bound pairing (`DeviceIdentity` / Ed25519 mutual confirm) | Revoke, multi-device registry, push yalnızca «pending var» |

**QR rolü:** Yeni protokol değil; v2'de pairing code + `relay_url` payload'ının QR ile iletimi ([device-connection-information-architecture.md §5.2](device-connection-information-architecture.md)). Keşif yine LAN; QR «ikinci ekran yok» senaryosunda kod girişini bypass eder.

**Token link rolü:** Pair **sonrası** deep link / PWA kısayolu; birincil eşleştirme kanalı değil. Token asla push payload'ında taşınmaz (MVP plan D7).

**Hesap bağlı pairing:** `DeviceIdentity` (Ed25519) ile karşılıklı imza — [device-connection-architecture-draft.md §3.1](device-connection-architecture-draft.md) kimlik hazırlığı mevcut; **çoklu cihaz protokolü repo'da tanımlı değil** (private katman).

### Public vs private

| Öğe | OSS (`lumos-core`) | Private |
|-----|-------------------|---------|
| LAN relay demo, pairing code, beacon | ✓ | — |
| Native Mobile app, TLS termination | — | ✓ |
| QR UI, cihaz envanteri paneli | IA doküman | ✓ uygulama |
| Account-bound / uzaktan tünel | — | ✓ |
| Push backend | — | ✓ |

### Uzun vadeli one-liner

> **Uzun vadede LAN discovery + pairing code protokolü korunur; QR güven yükseltmesi ve hesap bağlı `DeviceIdentity` karşılıklı onayı ile multi-device registry'ye evrilir — prod TLS ve revoke private katmanda.**

---

## 7. Açık kararlar

| # | Konu | Seçenekler | MVP / tavsiye | Katman |
|---|------|------------|---------------|--------|
| P1 | Pairing code uzunluğu | 6 / 8 hane | 6 hane — RB-06 ile uyumlu; v2'de 8 + rate limit değerlendir | OSS |
| P2 | Keşif birincil kanal | UDP beacon / HTTP discover / mDNS | MVP: UDP+HTTP; v2: mDNS ekle | OSS → private ops |
| P3 | TLS zorunluluğu | Plain HTTP demo / TLS relay | MVP demo plain; prod **TLS zorunlu** | Private |
| P4 | QR zamanlaması | v1 / v2 / v3 | **v2** — protokol sabitlendikten sonra sunum | Private UI |
| P5 | Token link paylaşımı | Yalnızca same-device / QR içi deep link | Pair sonrası local deep link; chat ile paylaşım **discourage** | IA + private |
| P6 | Brute force koruma | Yok / IP rate limit / exponential lockout | RB-10 sonrası dar rate limit | OSS |
| P7 | Eşleştirme ↔ `DeviceIdentity` | Bağımsız relay token / imzalı pair challenge | v3 account-bound; MVP **bağımsız** | Private |
| P8 | Multi-device registry | Tek mobile / cihaz listesi / revoke UX | MVP tek cihaz; IA «Bağlı cihazlar» empty state | Private + IA |
| P9 | Uzaktan (WAN) onay | MVP dışı / tünel / relay cloud | **MVP dışı** — bilinçli defer | Private |
| P10 | Execute tetikleyici | Adapter poll vs Mobile execute | MVP: **Mobile yalnızca approve** (plan D2) | OSS sözleşme |

---

## Referanslar

| Kaynak | İçerik |
|--------|--------|
| `packages/kando_bridge/src/kando_bridge/lan_relay.py` | Pairing code, beacon, relay token, HTTP uçları |
| [lumos-mobile-approval-mvp-plan.md](lumos-mobile-approval-mvp-plan.md) | v1 QR/push hayır; PR-RB-06 akış diyagramı |
| [pr-rb-06-lan-relay-verification.md](pr-rb-06-lan-relay-verification.md) | Discovery, pairing, approval transport PASS |
| [device-connection-architecture-draft.md](device-connection-architecture-draft.md) | Trust states, pairing varsayımları |
| [device-connection-information-architecture.md](device-connection-information-architecture.md) | Eşleştirme yolculuğu, panel görünürlük |
| [ADR-012](../decisions/ADR-012-lumos-security-codex.md) | Loopback, onay, consent, public sınır |

---

*Son güncelleme: 2026-06-22 — eşleştirme stratejisi karşılaştırması (analiz only, kod yok)*
