<!-- markdownlint-disable MD013 -->

# Account Activity Correlation — v1

Durum: ADR-032 sözleşmesi. Kod: `src/account_activity/engine.py`.

Bu, activity tracking değildir. Üçüncü taraf güvenlik uyarısını, onaylı ve
cihaza bağlı oturum özetiyle eşleştirir. Ledger **hesap kilidi değildir**.

## Alanlar

| Parça | Rol | Kapı mı? |
| --- | --- | --- |
| Consent | Kayıt izni; geri çekilince özetler silinir | Evet |
| Device registry | `device_id` + `public_key_fingerprint` (+ opsiyonel `attestation_ref`) | Evet (yoksa kayıt yok) |
| Device activity | Minimal oturum özeti | Sinyal |
| Third-party alert | Yapılandırılmış uyarı (ör. `xAI security email`) | Sinyal |
| Network observation | Hash/sınıf karşılaştırması; düz IP yok | Destekleyici |
| Provenance | Agent, eşleşme, sonuç, kullanıcı kararı | Kanıt; kapı değil |

## Tutulan özet

```text
YYYY-MM-DD HH:MM — servis — cihaz etiketi — ağ sınıfı — oturum türü
```

Örnek: `2026-09-02 06:18 — xAI/Grok — iPhone 15 — mobil ağ — kullanıcı oturumu`

Etiket gösterim içindir. Kimlik `device_id` (public key özeti) ve parmak
izidir.

## Yasak alanlar

`url`, `history`, `title`, `password`, `token`, `cookie`, `content`, `body`,
`ip`, `raw_ip`, `user_agent` ve düz metin IPv4/IPv6.

Ağ için yalnız sınıf (`mobile` / `wifi` / `wired` / `vpn` / `unknown`) ve
isteğe bağlı tuzlu hash. Karşılaştırma sonucu: `same_network` /
`different_network` / `vpn_possible` / `unknown`.

## Verdict

| Seviye | Anlam | Kesin hüküm mü? |
| --- | --- | --- |
| `owner_match` | Kayıtlı cihaz + zaman + servis (± pencere); ağ çelişkisi yok | Hayır |
| `likely_owner` | Üçlü sinyal var ama ağ farklı, veya daha zayıf çoklu sinyal | Hayır |
| `unknown` | Yalnız zaman, kayıt kapalı, veya cihaz bağlı değil | Hayır |
| `suspicious` | Uyarı var, eşleşen kayıtlı cihaz aktivitesi yok veya cihaz çelişiyor | Hayır |

Kayıtlı cihaz sinyali olmadan `owner_match` / `likely_owner` yok. Yalnız
zaman `unknown` kalır. Pencere varsayılan ±10 dk, sıkı ±5 dk; üst sınır
±10 dk. Aynı gün eşlemesi yok.

## Kaynaklar

Sonuç ayrı gösterilir:

1. `xAI security email` (veya başka `source_label`)
2. `Lumos device activity`
3. `network observation`

`explain(correlation_id)` kaynak + sinyal + “kesin hüküm değil” metnini
döner.

## Eylem

`auto_action` daima `none`. `password_change`, `session_revoke`,
`logout_all`, `disable_account` çekirdek tarafından çalıştırılmaz;
`execute_action` → `human_approval_required`. Kullanıcı kararı provenance’a
yazılır, icra edilmez.

## Retention

| Sınıf | Süre |
| --- | --- |
| Sıradan oturum özeti | 14 gün |
| Yüksek risk / `suspicious` | 90 gün |
| Kullanıcı silmesi | hemen |
| Consent revoke | bütün özetler silinir |

## Provenance olayları

`consent_changed` · `device_registered` · `activity_recorded` ·
`alert_ingested` · `correlated` · `user_decided` · `auto_action_refused` ·
`activity_deleted`

Hash zinciri (`prev_hash` / `digest`) kurcalamayı görünür kılar; WORM
değildir.

## Bu dilimin dışı

- Canlı iOS/macOS olay yayını
- Mail gövdesi parse / Mail ürünü (ADR-009, v2 rafı)
- Panel Denetim merceği bağlama (FAZ-1 sonrası)
- Donanım attestation doğrulaması (opak `attestation_ref` var)
- Çoklu cihaz senkronu (v1 dışı)
- Yeni sayfa, yeni entegrasyon, otomatik hesap eylemi
