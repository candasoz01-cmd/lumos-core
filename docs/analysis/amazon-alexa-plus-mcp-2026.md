# Alexa+ gerçek MCP sunucusu — Amazon Hackathon 2026

Issue: [candasoz01-cmd/lumos-core#854](https://github.com/candasoz01-cmd/lumos-core/issues/854).
Dal: `amazon-build-ship-shape-2026` (bu dilim onun üzerinde). `main`'e yazılmaz.

## Ne

Lumos, Alexa+ için **MCP spec 2025-11-25 Streamable HTTP** sunucusu sunar.
Tek araç: `propose_lumos_task`. Araç bir görev **önerir**; oluşturmaz, yazmaz,
çalıştırmaz. İnsan onayı Lumos panelinin işidir.

Bu, 16 Eylül yönünden önceki `/alexa-plus-simulasyon` web sayfasının yerine
geçen yarışma kanıtıdır. O sayfa tarihseldir ve nihai demo değildir.

**Ring kapsam dışıdır.**

## Çalıştırma (yerel)

```bash
LUMOS_ALEXA_MCP_TOKEN='choose-a-local-secret' python3 -m alexa_plus_mcp --port 8766
```

Dinleme: `http://127.0.0.1:8766/mcp` (varsayılan yalnız localhost).
Kimlik: `Authorization: Bearer …`. Kimlik yoksa **401** ve `WWW-Authenticate`
yoktur (Alexa+ MCP Toolkit beklentisi).

Tunnel / Alexa+ add-on bağlama (`alexa-ai deploy`, OAuth hesap bağlama) bu
dilimin parçası değildir; kurucu sonraki adımdır, deploy bu PR'da yapılmaz.

## Kanıt

```bash
PYTHONPATH=src KANDO_MOCK=1 python3 -m pytest -q tests/test_alexa_plus_mcp.py
```

Testler `initialize` → `notifications/initialized` → `tools/list` →
`tools/call` yolunu gerçek HTTP üzerinden koşar. Web simülasyonu bu testlerin
kanıtı değildir.
