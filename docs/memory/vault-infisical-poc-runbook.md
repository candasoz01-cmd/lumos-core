# Infisical self-host PoC — operatör runbook (public-safe)

**Durum:** V1a `implementation-partial` — adapter + health check + secret read public; deploy private operatör katmanında.

## Önkoşullar

- Self-host Infisical (tek node PoC yeterli) — **private deploy**, repo'da yok
- Operatör ortam değişkenleri (asla commit edilmez):
  - `LUMOS_VAULT_URL` — örn. `https://vault.example.invalid`
  - `LUMOS_VAULT_TOKEN` — Infisical service token access kısmı (scoped, read-only PoC)
  - `LUMOS_VAULT_PROJECT` — Infisical workspace/project ID
  - `LUMOS_VAULT_ENV` — ortam slug (örn. `dev`, `prod`)
  - `LUMOS_VAULT_SECRET_PATH` — opsiyonel; varsayılan `/integrations/mail`
  - `LUMOS_VAULT_TEST_REF` — opsiyonel PoC script secret probe ref (örn. `mail-read:operator@example.invalid`)

## Health check

```bash
export LUMOS_VAULT_URL="https://your-infisical-host"
export LUMOS_VAULT_TOKEN="your-service-token"
./scripts/vault-infisical-poc-check.sh
```

Beklenen: `OK: Infisical reachable ...`

## Secret read probe (opsiyonel)

Health check geçtikten sonra, proje/env/ref env'leri set ise script ikinci adımda secret okur (değer yazdırılmaz):

```bash
export LUMOS_VAULT_PROJECT="your-workspace-id"
export LUMOS_VAULT_ENV="dev"
export LUMOS_VAULT_TEST_REF="mail-read:operator@example.invalid"
# export LUMOS_VAULT_SECRET_PATH="/integrations/mail"  # varsayılan
./scripts/vault-infisical-poc-check.sh
```

Beklenen: `OK: secret read probe succeeded for ref ... (value not printed)`

Infisical secret key = Lumos vault ref (`mail-read:{account_id}`); path = `LUMOS_VAULT_SECRET_PATH`.

## Lumos adapter

- Kod: `src/integrations/vault/adapter.py` — `InfisicalVaultAdapter`
- Env yoksa **fails closed** (`is_configured()` → false)
- `resolve_credential(ref, purpose)` → health + `GET /api/v3/secrets/raw/{ref}` → `CredentialResolution.secret_value`
- Hata kodları: `vault_env_not_configured`, `vault_project_env_not_configured`, `vault_unreachable`, `vault_timeout`, `secret_not_found`
- Amaç kodları: `src/integrations/vault/purpose_codes.py`

## Gmail OAuth (read-only skeleton)

- `src/integrations/mail/providers/gmail_oauth.py` — scope `gmail.readonly`
- Google OAuth client credentials **Google Cloud Console'da** — repo'da yok
- Vault configured + read grant → vault-backed read path (default mock; `LUMOS_GMAIL_SMOKE=1` ile canlı API)
- **OAuth callback contract (PR1):** [`gmail-oauth-callback-contract.md`](./gmail-oauth-callback-contract.md) — types `src/integrations/mail/oauth_contract.py`; post-OAuth ref `mail-read:{account_id}`. **Infisical secret read (PR2)**; **Gmail readonly smoke (PR3)** env-gated; HTTP handler + token write private operatör.

## Private operatör işleri (repo dışı)

1. Infisical self-host kurulum + backup
2. Google OAuth client oluşturma + redirect URI
3. Mail OAuth token'ı Infisical secret olarak kaydetme (`mail-read:{account_id}` key, `/integrations/mail` path)
4. Canlı Gmail API çağrısı (M7 / PR3 smoke — env-gated, CI dışı)

## M7 — Gmail readonly smoke (PR3, operatör-only)

**CI default:** kapalı. Canlı çağrı yalnız operatör makinesinde, vault + OAuth token hazırken.

### Önkoşullar

1. PR2 vault env'leri set (`LUMOS_VAULT_URL`, `LUMOS_VAULT_TOKEN`, `LUMOS_VAULT_PROJECT`, `LUMOS_VAULT_ENV`)
2. Infisical'da `mail-read:{account_id}` secret — OAuth access token (düz string veya JSON `access_token`)
3. Smoke gate env'leri:

```bash
export LUMOS_GMAIL_SMOKE=1
export LUMOS_GMAIL_SMOKE_ACCOUNT="operator@example.invalid"
# vault env'leri (yukarıdaki gibi)
```

### Çalıştırma

```bash
pytest tests/test_gmail_api_smoke.py::test_live_gmail_smoke_via_vault -q
```

Beklenen: test geçer veya inbox boşsa boş liste döner; secret/token çıktıda görünmez.

### Kod yüzeyi

- `src/integrations/mail/providers/gmail_api_client.py` — `users.messages.list` (`q=is:unread`) + metadata-only get
- `src/integrations/mail/providers/gmail_oauth.py` — `LUMOS_GMAIL_SMOKE=1` iken vault token ile canlı API; aksi halde mock özet
- Unit testler: `tests/test_gmail_api_smoke.py` (mock); live test `@pytest.mark.skipif` ile gate'li

## Rollback

Infisical PoC başarısız → OpenBao alternatif ([`od-vault-v1-technology-selection.md`](./od-vault-v1-technology-selection.md) §6).
