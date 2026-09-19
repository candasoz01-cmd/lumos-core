# Alexa+ gerçek MCP sunucusu — Amazon Hackathon 2026

Issue: [candasoz01-cmd/lumos-core#854](https://github.com/candasoz01-cmd/lumos-core/issues/854).
Dal: `amazon-build-ship-shape-2026` (bu dilim onun üzerinde). `main`'e yazılmaz.

## Ne

Lumos, Alexa+ için **MCP spec 2025-11-25 Streamable HTTP** sunucusu sunar.
Tek araç: `propose_lumos_task`. Araç bir görev **önerir**; oluşturmaz, yazmaz,
çalıştırmaz. İnsan onayı Lumos panelinin işidir.

Kimlik, Alexa+ MCP Toolkit şeklindedir:

- Streamable HTTP, `POST /mcp`
- Kimlik yoksa **401** ve `WWW-Authenticate` yoktur
- Protected Resource Metadata: `/.well-known/oauth-protected-resource`
- AS metadata: `/.well-known/oauth-authorization-server` (`code_challenge_methods_supported` içinde `S256`)
- İki katman: `client_credentials` (servis: `initialize` / `tools/list`) ve
  `authorization_code` + PKCE S256 (kullanıcı: `tools/call`)
- `resource` parametresi canonical MCP URI'ye bağlıdır
- Dynamic Client Registration yoktur

Yerel `LUMOS_ALEXA_MCP_TOKEN` Bearer'ı yalnız geliştirme kısayoludur; Alexa+
hesap bağlama bu jetonu kullanmaz.

Bu, 16 Eylül yönünden önceki `/alexa-plus-simulasyon` web sayfasının yerine
geçen yarışma kanıtıdır. O sayfa tarihseldir ve nihai demo değildir.

**Ring kapsam dışıdır.**

## Çalıştırma (yerel)

```bash
LUMOS_ALEXA_MCP_TOKEN='choose-a-local-secret' python3 -m alexa_plus_mcp --port 8766
```

Dinleme: `http://127.0.0.1:8766/mcp` (varsayılan yalnız localhost).

## İzin verilen tünel akışı

Sunucu localhost'ta kalır. Tünel, `127.0.0.1:8766` üzerine HTTPS örter.
`0.0.0.0` bind varsayılan olarak kapalıdır.

```bash
python3 -m alexa_plus_mcp --print-tunnel --port 8766
# cloudflared tunnel --url http://127.0.0.1:8766

LUMOS_ALEXA_MCP_TOKEN='choose-a-local-secret' \
LUMOS_ALEXA_OAUTH_CLIENT_ID='from-alexa-console' \
LUMOS_ALEXA_OAUTH_CLIENT_SECRET='from-alexa-console' \
LUMOS_ALEXA_OAUTH_REDIRECT_URIS='https://alexa.amazon.com/api/skill/link/<id>' \
LUMOS_ALEXA_MCP_PUBLIC_URL='https://<tunnel-host>' \
python3 -m alexa_plus_mcp --port 8766
```

`LUMOS_ALEXA_MCP_PUBLIC_URL` tünelde **https** olmak zorundadır. Issuer ve
PRM `resource` bu URL'den okunur; süreç `127.0.0.1` dinlemeye devam eder.

`LUMOS_ALEXA_MCP_ALLOW_REMOTE_BIND=1` yalnız tünelsiz doğrudan uzak bind içindir
ve yine https `PUBLIC_URL` ister.

## Kurucu sonraki adımı (bu PR'da çalıştırılmaz)

`alexa-ai configure`, `alexa-ai new mcp`, hesap bağlama ve `alexa-ai deploy`
Amazon geliştirici hesabı ister. Tünel URL'si hazır olduktan sonra kurucu
eylemidir; bu dilimde CLI login/deploy yok.

## Kanıt

```bash
PYTHONPATH=src KANDO_MOCK=1 python3 -m pytest -q tests/test_alexa_plus_mcp.py
```

Testler Streamable HTTP oturumunu, OAuth 2.1 iki katmanını ve localhost+https
PUBLIC_URL tünel şeklini gerçek HTTP üzerinden koşar. Web simülasyonu bu
testlerin kanıtı değildir.
