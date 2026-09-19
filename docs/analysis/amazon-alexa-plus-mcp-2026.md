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
LUMOS_ALEXA_MCP_TOKEN='choose-a-local-secret' \
LUMOS_ALEXA_OAUTH_CLIENT_ID='from-alexa-console' \
LUMOS_ALEXA_OAUTH_CLIENT_SECRET='from-alexa-console' \
LUMOS_ALEXA_OAUTH_REDIRECT_URIS='https://alexa.amazon.com/api/skill/link/<id>' \
LUMOS_ALEXA_MCP_PUBLIC_URL='https://<tunnel-host>' \
python3 -m alexa_plus_mcp --port 8766
```

Dinleme: `http://127.0.0.1:8766/mcp` (varsayılan yalnız localhost).
Uzak tünel için `LUMOS_ALEXA_MCP_ALLOW_REMOTE_BIND=1` gerekir.

## Kurucu sonraki adımı (bu PR'da yapılmaz)

`alexa-ai configure`, `alexa-ai new mcp`, hesap bağlama ve `alexa-ai deploy`
Amazon geliştirici hesabı ve canlı tünel ister. Bu dilim sunucuyu o şekle
uydurur; add-on kaydı ve deploy kurucu eylemidir.

## Kanıt

```bash
PYTHONPATH=src KANDO_MOCK=1 python3 -m pytest -q tests/test_alexa_plus_mcp.py
```

Testler Streamable HTTP oturumunu ve OAuth 2.1 iki katmanını gerçek HTTP
üzerinden koşar. Web simülasyonu bu testlerin kanıtı değildir.
