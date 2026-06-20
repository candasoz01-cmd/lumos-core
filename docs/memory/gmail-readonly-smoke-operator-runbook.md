# Gmail Readonly Live Smoke — Operatör Runbook (Birleşik)

## Bağlam

PR **#413** (Gmail OAuth callback contract), **#414** (Infisical vault adapter + secret read) ve **#415** (Gmail readonly API client + env-gated live smoke) `main`'e merge edildi. CI varsayılanında `LUMOS_GMAIL_SMOKE` set edilmediği için `test_live_gmail_smoke_via_vault` **otomatik skip** olur; canlı Gmail doğrulaması yalnızca operatör makinesinde, vault + OAuth token hazırken yapılır. Public repo'da Google client secret, redirect handler ve token yazma yok — bunlar **private operatör katmanı** işidir.

**Çalışma kökü:** repo kökü (`lumos-core`)

İlgili belgeler: [`vault-infisical-poc-runbook.md`](./vault-infisical-poc-runbook.md), [`gmail-oauth-callback-contract.md`](./gmail-oauth-callback-contract.md)

---

## 1. Gerekli env değişkenleri

| Değişken | Zorunlu | Amaç | Örnek placeholder |
|----------|---------|------|-------------------|
| `LUMOS_VAULT_URL` | Evet (vault + smoke) | Infisical self-host base URL | `https://vault.example.invalid` |
| `LUMOS_VAULT_TOKEN` | Evet | Infisical service token (read-only PoC scope) | `st.xxxx...` |
| `LUMOS_VAULT_PROJECT` | Evet | Infisical workspace/project ID | `ws-uuid-here` |
| `LUMOS_VAULT_ENV` | Evet | Ortam slug | `dev` |
| `LUMOS_VAULT_SECRET_PATH` | Hayır | Secret folder path; varsayılan `/integrations/mail` | `/integrations/mail` |
| `LUMOS_VAULT_TEST_REF` | Hayır (poc-check secret adımı için) | Probe edilecek vault ref | `mail-read:operator@example.invalid` |
| `LUMOS_GMAIL_SMOKE` | Evet (live smoke için) | Canlı Gmail API gate; `1`, `true`, `yes` (case-insensitive) | `1` |
| `LUMOS_GMAIL_SMOKE_ACCOUNT` | Evet (live smoke için) | Smoke hesabı; vault ref'teki `account_id` ile **birebir** eşleşmeli | `operator@example.invalid` |

**Not:** Vault ref şeması `mail-read:{account_id}`; `LUMOS_GMAIL_SMOKE_ACCOUNT` değeri `{account_id}` kısmıdır (prefix yok).

---

## 2. Infisical hazırlığı

### Secret path ve key adlandırma

| Alan | Değer |
|------|-------|
| Secret path | `LUMOS_VAULT_SECRET_PATH` veya varsayılan **`/integrations/mail`** |
| Secret key (Infisical secretKey) | **`mail-read:{account_id}`** — örn. `mail-read:operator@example.invalid` |
| Purpose code (Lumos) | `integration.mail.read` |
| Token intent | `gmail.readonly` |
| OAuth scope (Google) | `https://www.googleapis.com/auth/gmail.readonly` |

Infisical API çağrısı: `GET /api/v3/secrets/raw/{ref}?workspaceId=...&environment=...&secretPath=...` — `ref` doğrudan secret key'dir.

### Token format (secret value)

İki format desteklenir (`extract_access_token`):

1. **Düz string** — OAuth access token doğrudan
2. **JSON** — `{"access_token": "ya29..."}`

Boş, geçersiz JSON veya `access_token` yoksa token çıkarılamaz → live path devreye girmez.

### Workspace / project / env kurulumu

1. Self-host Infisical (private deploy; repo'da yok)
2. Workspace/project oluştur → ID'yi `LUMOS_VAULT_PROJECT` olarak kullan
3. Environment slug oluştur (örn. `dev`) → `LUMOS_VAULT_ENV`
4. Path **`/integrations/mail`** altında secret oluştur
5. Read-only scoped service token üret → `LUMOS_VAULT_TOKEN`

### Operatör adımları — token yazma (private katman)

> **Private layer:** OAuth callback handler, authorization code → token exchange ve Infisical yazma public repo'da yok. Operatör private katmanda şunları yapar:

1. Google Cloud Console'da OAuth client oluştur (client ID/secret repo'da **yok**)
2. Redirect URI'yi private handler'a bağla (path pattern: `/integrations/mail/oauth/gmail/callback`)
3. Kullanıcı OAuth onayını tamamla → access token al
4. Infisical'da secret oluştur:
   - **Key:** `mail-read:{account_id}` (örn. `mail-read:operator@example.invalid`)
   - **Path:** `/integrations/mail`
   - **Value:** düz access token **veya** `{"access_token":"<token>"}`
5. Token süresi dolmadan smoke çalıştır; expired token → API sessizce boş/mock fallback'e düşebilir

---

## 3. Export adımları

Aşağıdaki bloğu operatör secret store'dan değerleri doldurarak çalıştırın. **Gerçek token'ları commit etmeyin, chat'e yapıştırma, ekran görüntüsüne almayın.**

```bash
cd /path/to/lumos-core

# --- Vault (Infisical PoC) ---
export LUMOS_VAULT_URL="https://vault.example.invalid"
export LUMOS_VAULT_TOKEN="st-your-service-token-here"
export LUMOS_VAULT_PROJECT="your-workspace-id"
export LUMOS_VAULT_ENV="dev"
export LUMOS_VAULT_SECRET_PATH="/integrations/mail"

# poc-check secret probe (opsiyonel ama önerilir)
export LUMOS_VAULT_TEST_REF="mail-read:operator@example.invalid"

# --- Gmail live smoke gate ---
export LUMOS_GMAIL_SMOKE=1
export LUMOS_GMAIL_SMOKE_ACCOUNT="operator@example.invalid"
```

---

## 4. Çalıştırılacak komutlar

### Adım A — Vault PoC check

```bash
./scripts/vault-infisical-poc-check.sh
```

**Beklenen (tam):**

```
OK: Infisical reachable at https://... (HTTP 200)
OK: secret read probe succeeded for ref mail-read:operator@example.invalid (value not printed)
```

**Beklenen (yalnız health — PROJECT/ENV/TEST_REF yoksa):**

```
OK: Infisical reachable at ...
SKIP: secret read step (set LUMOS_VAULT_PROJECT, LUMOS_VAULT_ENV, LUMOS_VAULT_TEST_REF to enable)
```

(Secret adımı skip olsa bile exit code **0** — smoke öncesi secret probe için üç env'i set edin.)

### Adım B — Live pytest smoke

```bash
pytest tests/test_gmail_api_smoke.py::test_live_gmail_smoke_via_vault -q
```

**Beklenen:** `1 passed` (skip veya fail olmamalı)

### Adım C — Post-PASS tanı (repo API, dosya değişikliği yok)

Pytest PASS sonrası canlı verinin mock olmadığını doğrulamak için:

```bash
python3 -c "
import os, sys
sys.path.insert(0, 'src')
from integrations.mail.providers.gmail_oauth import GmailOAuthConnector
from integrations.mail.vault_credential import DemoVaultCredentialBridge
aid = os.environ.get('LUMOS_GMAIL_SMOKE_ACCOUNT', '').strip()
rows = GmailOAuthConnector(vault_bridge=DemoVaultCredentialBridge()).list_unread_summaries(account_id=aid, limit=3)
print('count=', len(rows))
for r in rows:
    print({'message_id': r.message_id, 'subject': r.subject_preview[:60], 'from': r.from_preview[:40]})
"
```

Vault bağlantı durumu (secret değeri yazdırmaz):

```bash
python3 -c "
import os, sys
sys.path.insert(0, 'src')
from integrations.mail.vault_credential import DemoVaultCredentialBridge, mail_read_credential_ref
aid = os.environ.get('LUMOS_GMAIL_SMOKE_ACCOUNT', '').strip()
print(DemoVaultCredentialBridge().connection_hint(mail_read_credential_ref(aid)))
"
```

---

## 5. PASS kriterleri

### Pytest PASSED ≠ gerçek Gmail başarısı

| Durum | pytest | Gerçek Gmail? |
|-------|--------|---------------|
| `LUMOS_GMAIL_SMOKE` yok | **SKIP** | Hayır |
| Vault yapılandırılmamış | **SKIP** | Hayır |
| pytest **PASSED**, boş inbox + mock fallback | PASSED | **Hayır (false positive riski)** |
| pytest **PASSED** + tanı çıktısı canlı Gmail imzası taşıyor | PASSED | **Evet** |

**Kritik kod davranışı:** `LUMOS_GMAIL_SMOKE=1` olsa bile Gmail API boş liste dönerse veya çağrı sessizce başarısız olursa connector **mock vault-backed özetlere** düşer; pytest yine geçebilir. Operatör **3 checkbox** ile doğrulamalıdır.

### Operatör doğrulama — 3 checkbox

Post-PASS tanı çıktısında **her mesaj** için:

- [ ] **`message_id` opak Gmail ID** — Google'dan gelen kısa alfanumerik ID (örn. `18c4f2a1b3d4e5f6`); `demo-msg-*` değil
- [ ] **`message_id` `vault-mail-read:` ile başlamıyor** — mock fallback imzası: `vault-mail-read:{account}-001`
- [ ] **`subject_preview` içinde `[vault-backed]` yok** — mock konu satırı: `[vault-backed] Okunmamış özet`

**Boş inbox senaryosu:** Okunmamış mail yoksa `count=0` ve boş liste **gerçek başarı** sayılır; mock satırlar (`[vault-backed]`) görülmemeli. Mock satır görülüyorsa FAIL.

**Ek güvenlik assert (pytest'te de var):** çıktıda `access_token` metni veya token değeri görünmemeli.

---

## 6. FAIL kriterleri

### pytest skip nedenleri

| Skip mesajı | Sebep | Düzeltme |
|-------------|-------|----------|
| `LUMOS_GMAIL_SMOKE not set — operator-only live Gmail smoke` | Smoke gate kapalı | `export LUMOS_GMAIL_SMOKE=1` |
| `LUMOS_GMAIL_SMOKE_ACCOUNT required for live smoke` | Hesap env yok | `export LUMOS_GMAIL_SMOKE_ACCOUNT="..."` |
| `vault env not configured for smoke account` | Vault env eksik veya secret çözülemedi | Vault env + Infisical secret kontrol |

### poc-check FAIL

| Çıktı | Sebep |
|-------|-------|
| `FAIL: LUMOS_VAULT_URL and LUMOS_VAULT_TOKEN must be set` | URL veya token export edilmemiş |
| `FAIL: Infisical health check returned HTTP XXX` | URL yanlış, token geçersiz, Infisical down |
| `FAIL: secret read probe returned HTTP XXX` | Yanlış project/env/path/ref; secret yok (404) |

### False-positive PASS (pytest geçti ama canlı Gmail yok)

| Belirti | Muhtemel neden |
|---------|----------------|
| `message_id` → `vault-mail-read:...` | `LUMOS_GMAIL_SMOKE` set değil veya token çıkarılamadı |
| `subject_preview` → `[vault-backed]` | Live API çağrısı yapılmadı veya boş döndü → mock fallback |
| `message_id` → `demo-msg-001` | Vault bridge yapılandırılmamış; stub path |
| Gerçek konu/from beklenirken placeholder | Expired/invalid token; Gmail API sessiz hata |

### Adapter hata kodları (`InfisicalVaultAdapter.resolve_credential`)

| `error` kodu | Anlam | Tipik tetik |
|--------------|-------|-------------|
| `vault_env_not_configured` | URL veya token yok | `LUMOS_VAULT_URL` / `LUMOS_VAULT_TOKEN` eksik |
| `vault_project_env_not_configured` | Project veya env yok | `LUMOS_VAULT_PROJECT` / `LUMOS_VAULT_ENV` eksik |
| `unknown_purpose_code` | Bilinmeyen purpose | Yanlış purpose (mail-read ref'te olmaz) |
| `vault_unreachable` | `/api/status` veya bağlantı hatası | Host down, firewall, yanlış URL |
| `vault_timeout` | Zaman aşımı | Ağ gecikmesi, Infisical yavaş |
| `secret_not_found` | HTTP 404 veya boş value | Secret key/path/env yanlış |
| `secret_fetch_failed` | HTTP ≠ 404 hata veya parse hatası | Yetki, API hatası, bozuk yanıt |

`connection_hint` çıktısında `boundary: vault_env_set_credential_unresolved` + `error` alanı → credential çözülemedi.

---

## 7. Ekran görüntüsü alınacak satırlar

### Alınacak (kanıt paketi)

1. **poc-check:** `OK: Infisical reachable ...` satırı
2. **poc-check (varsa):** `OK: secret read probe succeeded for ref mail-read:... (value not printed)`
3. **pytest:** `1 passed` satırı (skip/fail olmamalı)
4. **Post-PASS tanı:** `count=N` ve mesaj satırları — yalnızca `message_id`, kısaltılmış `subject`, kısaltılmış `from` (3 checkbox yeşil)

### Alınmayacak

- `export` satırlarındaki gerçek token/URL değerleri
- `printenv`, `env`, `set` çıktısı
- `curl` response body (poc-check zaten body yazdırmaz — yine de ham curl çıktısı almayın)
- Infisical UI'da secret **value** alanı
- Google OAuth ekranındaki authorization code veya access token
- Terminal scrollback'te Bearer header veya JSON token içeren satırlar

**Maskeleme:** URL host adı görünebilir; token her zaman `***` ile kapatılmalı.

---

## 8. Güvenlik uyarıları

1. **`printenv` / `env` kullanmayın** — tüm shell secret'ları sızar
2. **Ham `curl` ile secret endpoint'ine body loglamayın** — poc-check script'i zaten value yazdırmaz; onu kullanın
3. **Token asla ekran görüntüsüne girmez** — export, Infisical UI, OAuth callback query
4. **Repo'ya commit yok** — env dosyası, `.env`, token dump
5. **Chat / ticket'e token yapıştırmayın** — yalnızca hata kodu ve maskeleme
6. **Scope dar tutulmuş:** yalnız `gmail.readonly`; metadata-only get (Subject, From, Date); tam mail gövdesi okunmaz
7. **CI'da live smoke çalışmaz** — kasıtlı; operatör makinesi dışında canlı token gerektiren adım yok

---

## Hızlı operatör akışı (tek sıra)

```bash
cd /path/to/lumos-core
# (§3 export bloğunu önce çalıştır)
./scripts/vault-infisical-poc-check.sh
pytest tests/test_gmail_api_smoke.py::test_live_gmail_smoke_via_vault -q
python3 -c "import os,sys; sys.path.insert(0,'src'); from integrations.mail.providers.gmail_oauth import GmailOAuthConnector; from integrations.mail.vault_credential import DemoVaultCredentialBridge; aid=os.environ.get('LUMOS_GMAIL_SMOKE_ACCOUNT','').strip(); rows=GmailOAuthConnector(vault_bridge=DemoVaultCredentialBridge()).list_unread_summaries(account_id=aid,limit=3); print('count=',len(rows)); [print({'message_id':r.message_id,'subject':r.subject_preview[:60],'from':r.from_preview[:40]}) for r in rows]"
# 3 checkbox doğrula → ekran görüntüsü al (§7)
```
