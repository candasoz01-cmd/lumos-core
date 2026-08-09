# Lumos Credential Gateway (v2)

Vercel projesi **`lumos-credential-gateway`** (lumos01 team) için kaynak kod.
v1 deployment'ının kaynağı kaybolmuştu (repo dışı geçici dizinden deploy edildi);
v2 bu repo'da versiyonlanır ve protokol, tek doğruluk kaynağı olan
`api/_lib/meta_vault.js` + `api/_lib/meta_webhook.js` istemci sözleşmelerinden
türetilmiştir (ADR-021).

## Beş soru (tasarım kaydı)

1. **Giriş noktası:** `POST /api/gateway` (Bearer `LUMOS_CREDENTIAL_GATEWAY_TOKEN`,
   401 fail-closed) + `GET /api/health` (sırsız canlılık).
2. **Dev/test/prod ayrımı:** testler Infisical'ı stub'lar (`fetchImpl` enjeksiyonu);
   prod env'leri yalnız Vercel Production'da. Preview'da env yok → bilinçli 503.
3. **Depolama:** Infisical (machine identity universal auth). Secret path altında
   credential başına bir secret (`CRED__<sanitized vault_ref>`, değer JSON
   `lumos-credential-v2`). Webhook dedupe: `WEBHOOK__<event_key>` (payload saklanmaz).
4. **Geçiş planı:** okuma yolu format-agnostik — path altındaki tüm sırlar taranır,
   JSON parse + alan eşleme; v1 kayıtları alanlar uyuştuğu sürece görünür,
   uyuşmayanlar `unparsed_records` sayacında raporlanır (sessiz kayıp yok).
   Uyumsuz kayıt = ilgili sağlayıcıda yeniden OAuth (kanıtlı, ~2 dk).
5. **Kabul kriterleri:** sözleşme testleri (`tests/test_credential_gateway.test.mjs`)
   yeşil; deploy sonrası `credential.list` gerçek kayıtları döner; lumos-core
   `/api/integrations/meta/connections` fallback'ten çıkar; webhook zinciri kırılmaz.

## Operasyonlar

`credential.upsert | credential.list | credential.metadata | credential.resolve
(provider veya vault_ref ile) | credential.delete | webhook.ingest`

## Deploy

Bu dizinden, `lumos-credential-gateway` projesine link'li olarak:

```bash
vercel deploy --prod --scope lumos01
```

Geri dönüş: Vercel dashboard'dan (veya `vercel rollback`) önceki deployment'a
alias'ı geri al — deployment'lar immutable, veri Infisical'da olduğu için
deploy/rollback veri kaybettirmez.
