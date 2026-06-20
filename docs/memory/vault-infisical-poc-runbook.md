# Infisical self-host PoC — operatör runbook (public-safe)

**Durum:** V1a `implementation-partial` — adapter + health check public; deploy private operatör katmanında.

## Önkoşullar

- Self-host Infisical (tek node PoC yeterli) — **private deploy**, repo'da yok
- Operatör ortam değişkenleri (asla commit edilmez):
  - `LUMOS_VAULT_URL` — örn. `https://vault.example.invalid`
  - `LUMOS_VAULT_TOKEN` — Infisical service token (scoped, read-only PoC)

## Health check

```bash
export LUMOS_VAULT_URL="https://your-infisical-host"
export LUMOS_VAULT_TOKEN="your-service-token"
./scripts/vault-infisical-poc-check.sh
```

Beklenen: `OK: Infisical reachable ...`

## Lumos adapter

- Kod: `src/integrations/vault/adapter.py` — `InfisicalVaultAdapter`
- Env yoksa **fails closed** (`is_configured()` → false)
- Amaç kodları: `src/integrations/vault/purpose_codes.py`

## Gmail OAuth (read-only skeleton)

- `src/integrations/mail/providers/gmail_oauth.py` — scope `gmail.readonly`
- Google OAuth client credentials **Google Cloud Console'da** — repo'da yok
- Vault configured + read grant → vault-backed read path (public repo mock-friendly)

## Private operatör işleri (repo dışı)

1. Infisical self-host kurulum + backup
2. Google OAuth client oluşturma + redirect URI
3. Mail OAuth token'ı Infisical secret olarak kaydetme
4. Canlı Gmail API çağrısı (M5 / private katman)

## Rollback

Infisical PoC başarısız → OpenBao alternatif ([`od-vault-v1-technology-selection.md`](./od-vault-v1-technology-selection.md) §6).
