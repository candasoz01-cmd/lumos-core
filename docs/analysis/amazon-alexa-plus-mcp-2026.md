# Alexa+ gerçek MCP sunucusu — Amazon Hackathon 2026

Issue: [candasoz01-cmd/lumos-core#854](https://github.com/candasoz01-cmd/lumos-core/issues/854).
Çalışma dalı: `amazon-build-ship-shape-2026`. Bu dilim geçerli MCP kodunu
güncel `origin/main` üzerine yeniden oturtur; `main`'e merge/deploy yok.

## 2026-09-21 — güncel main'e göre durum

Canlı doğrulama: `git fetch origin main amazon-build-ship-shape-2026` ·
2026-09-21T15:36Z.

| Ref | SHA |
| --- | --- |
| `origin/main` | `ea83c33803c1441638ed2452b0a0dd548a002cf0` |
| `origin/amazon-build-ship-shape-2026` | `a55f01d790dc60e82e9272248d97d6481d329633` |
| merge-base | `e928580576fa9b8e40c9e44b27b96ff2793b8e8a` |

Amazon dalı main'den **94 commit geride**, main'den **9 commit ileride**.
Üç yollu birleşmede çakışan yollar yalnız `package.json` ve `ui/package.json`
(otomatik birleşir). `conftest.py` yalnız Amazon tarafında değişmiş.

### 9 commit — geçerli / bayat

| SHA | Sonuç | Not |
| --- | --- | --- |
| `84c5709c` `feat: add Alexa+ task approval simulation` | **bayat / tarihsel kalıntı** | 16 Eylül yönünden önceki web simülasyonu. Yarışma kanıtı değil. Dosyalar kilit testi için durur; genişletilmez. Amazon `package.json` e2e kancası **alınmaz** — `e2e:webmcp:mock` (`d48b83b3`) geriler. |
| `7bb47f6d` `Merge main into amazon-build-ship-shape-2026` | **bayat birleşim** | 2026-09-14 anlık görüntüsü; artık 94 commit geride. Taşınmaz. |
| `13043b94` MCP Streamable HTTP sunucusu | **geçerli** | `src/alexa_plus_mcp/{__init__,__main__,protocol,server}.py` + ilk testler |
| `82745222` historical-sim / Ring kilit testleri | **geçerli** | Ring kapsam dışı; simülasyon kopyası tarihsel kilitli |
| `9238b3c4` `LUMOS_ALEXA_MCP_TOKEN` local credential | **geçerli** | `conftest.py` |
| `f0a14988` OAuth 2.1 two-tier | **geçerli** | `oauth.py` + protocol/server/test |
| `64cfe4fc` conftest OAuth env sadeleştirmesi | **geçerli** | TOKEN dışı env listeden çıkarıldı |
| `98928b62` localhost HTTPS tünel şekli | **geçerli** | `--print-tunnel`; https `PUBLIC_URL` |
| `a55f01d7` Merge PR #859 | **birleşim kaydı** | İçerik yukarıdaki geçerli commit'lerde. `candasoz01-cmd/lumos-core#859` · MERGED · `a55f01d7` · GitHub API · 2026-09-19T14:55:34Z |

Bu dalda taşınan: MCP sunucusu, OAuth/protocol/server, MCP testleri,
`LUMOS_ALEXA_MCP_TOKEN` sınıflandırması, tarihsel simülasyon dosyaları
(kanıt kilidi; npm e2e kancası yok). Amazon'un `package.json` /
`ui/package.json` farkı **alınmadı**.

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
