# Panel Tasks API kimlik sözleşmesi — v1 (TD-24 Faz-2)

| Alan | Değer |
| --- | --- |
| Durum | KOD — kütüphane + test; `panel_tasks_server.py` bağlama **yok** (TD-24 Faz-1 / `#829` o dosyayı tutuyor) |
| Borç | [TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md) TD-24 Faz-2 |
| Üst ilişki | Köprü `hmac.compare_digest` + `X-Kando-Token` / `Authorization: Bearer` deseni (`packages/kando_bridge/.../server.py`); [api-surface-v1.md](api-surface-v1.md) kimlik/no-store kuralları |
| Bekleme | HTTP kapısı Faz-1 Origin allowlist merge edilmeden `panel_tasks_server.py`'ye yazılmaz |

Bu sözleşme **tarayıcı Origin kapısı değildir**. Faz-1 yabancı origin'i keser; Faz-2 Origin'süz yerel süreç ve sahte Origin istemcisini keser.

## İki sunum kipi (token taşıma bundan çıkar)

1. **Aynı port.** `panel_tasks_server` statik paneli ve REST'i birlikte verir (`http://127.0.0.1:8766/index.html`). Origin = API origin. Oturum **HttpOnly cookie** adayıdır (`SameSite=Lax`, `Cache-Control: no-store`). Cookie gövdeye/URL'e yazılmaz.
2. **Ayrı origin.** UI `ui/dist` (pid portu) + API başka loopback portu. Cookie paylaşılmaz. Bootstrap **kısa ömürlü opaque exchange code + PKCE (S256)** ile yapılır; başarıda **Bearer oturum** döner. E2E bugün `window.LUMOS_PANEL_TASKS_API_BASE` ile bu kipi kullanır.

Her iki kipte sunucuya giden istekte kimlik başlığı köprü ile aynıdır: `X-Kando-Token` veya `Authorization: Bearer`. Gövde ve sorgu dizesinde token yok.

## Kimlik nesneleri

| Nesne | Ömür | Tek kullanımlık | Taşıma |
| --- | --- | --- | --- |
| Exchange code | kısa (varsayılan 60 sn) | evet; replay `401` | yalnız mint yanıtı / 0600 dosya; log yok |
| PKCE verifier | istemci belleği | challenge ile bağlanır | sunucuya yalnız exchange anında |
| Oturum (opaque) | varsayılan 15 dk | hayır; revoke/rotate var | Bearer / `X-Kando-Token` |
| Servis jetonu | süreç / elle revoke | hayır | CLI/E2E; tarayıcıya gömülmez |

Ham sır diskte düz metin tutulmaz: yalnız SHA-256. Karşılaştırma `hmac.compare_digest`.

## Fail-closed

- Yapılandırılmış sır yoksa mint ve authenticate **red** (`missing_secret`). “Sır yoksa açık” yok.
- Süre dolmuş, revoke edilmiş veya bilinmeyen jeton `invalid_token`.
- Kullanılmış exchange code `replay`.
- PKCE uyuşmazlığı `pkce_mismatch`.
- Başlık/jeton boyutu tavanı aşılırsa `too_large` (varsayılan 512 bayt).
- Mint/exchange hız tavanı aşılırsa `rate_limited`.

HTTP bağlandığında kimlik uçları `Cache-Control: no-store` taşır ([api-surface-v1](api-surface-v1.md) ile aynı kural).

## Mobil / MB-01 hizası

Panel loopback oturumu Google OAuth değildir. Çelişmeme kuralları:

- Opaque handle; JWT/id_token yok.
- Exchange code kısa ömürlü ve tek kullanımlık (replay red).
- PKCE S256 (ayrı origin bootstrap).
- Oturum Bearer; cookie aynı-origin kipinde tercih.
- Token URL/fragment/gövde yok (mobil deep-link `#session=` riski bu yüzeye kopyalanmaz).
- no-store; rate ve size tavanı kütüphanede.

## Bilinçli sınır (bu dilim)

- `panel_tasks_server.py` ve `PanelRuntime.astro` bağlanmadı — Faz-1 dosya sahipliği ve TD-02 (dev panel dosyası) çakışmasın.
- Köprü `KANDO_BRIDGE_SECRET` ile **aynı sırı paylaşmak zorunlu değil**; paylaşılırsa rotasyon iki yüzeyi birden keser. Tercih: `LUMOS_PANEL_TASKS_SECRET`.
- Yerel kötü süreç hâlâ OS kullanıcısıdır; bu sözleşme tarayıcı CSRF + rastgele localhost POST içindir, tam cihaz TEE değildir.
