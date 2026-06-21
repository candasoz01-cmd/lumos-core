# Lumos Audit Log Sözleşmesi

| Alan | Değer |
|------|-------|
| Durum | **Taslak sözleşme** — uygulama yok; PR-RB-10 öncesi referans |
| Şema | `lumos.audit_event.v1` (önerilen) |
| Depolama | `.lumos/logs/` (workspace sözleşmesi) |
| İlgili | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [lumos-karar-sozlesmesi.md](../lumos-karar-sozlesmesi.md), [pc-remote-pending-approval-contract.md](pc-remote-pending-approval-contract.md), `pending_approvals.py`, `pc_remote_tools.py`, `lan_relay.py` |

---

## 1. Amaç ve kapsam

### 1.1 Amaç

Lumos audit log, **etkili komutların kim tarafından, hangi cihazda, hangi onay zinciriyle ve hangi sonuçla** geçtiğini **append-only** ve **içerik-güvenli** biçimde kaydeder. Amaç:

- ADR-012 **C1 (tek dış kapı)** ve **C3 (onay + amaç + kanıt)** izlenebilirliğini desteklemek
- PC remote, köprü onayı ve mobil onay akışlarında **teşhis ve hesap verebilirlik** sağlamak
- Kullanıcı içeriği ve özel veriyi **bilinçli olarak dışarıda bırakmak**

Audit log **kanıt zincirinin tamamlayıcısıdır**; `evidence_continuity.jsonl`, `log.txt`, `lumos_audit` (görev pipeline) ve pending onay JSON'larından **ayrı** tutulur.

### 1.2 Kapsam dahil

| Yüzey | Audit kapsamı |
|-------|----------------|
| **PC remote köprü** (`POST /tools/execute`, `POST /approve`) | Komut isteği, onay bekleme, onay/red, yürütme sonucu |
| **LAN relay** (`/relay/pending`, `/relay/approve`, `/relay/reject`) | Mobil cihaz kimliği ile onay kararı (köprüye iletilen) |
| **Mobil onay istemcisi** | Onaylayan cihaz kimliği (`approver_device`) — relay üzerinden |
| **Task engine / panel** (dar) | Yalnızca köprü dışı etkili komutlar için ayrı `source` etiketi; mevcut `lumos_audit` ile hizalı genişleme |

### 1.3 Kapsam dışı

| Alan | Neden |
|------|-------|
| Pending onay JSON (`pending_approvals/`) | **Operasyonel state** — audit değil; TTL ve token doğrulama kaynağı |
| Ham kullanıcı mesajları, sohbet içeriği | Gizlilik — `lumos.chat_turn.v1` ayrı telemetri; audit'e taşınmaz |
| Gerçek OS otomasyonu detayı | Private katman; public OSS yalnızca stub olayları |
| Üretim backend, ödeme, kimlik sırları | Public GitHub sınırı |

### 1.4 Sınır: pending ≠ audit

`build_pc_remote_pending_record()` tam `arguments` içerir; bu **onay öncesi işlem state'idir**. Audit sözleşmesi bu dosyayı **kaynak olarak okuyabilir** ancak audit satırına `arguments` tam içeriğini **kopyalamaz**. Yalnızca `arguments_preview` (redakte) ve kimlik alanları taşınır.

---

## 2. Audit olay tipleri

Her satır tek bir `event_type` taşır. Bir komut yaşam döngüsü birden fazla satır üretebilir.

| `event_type` | Ne zaman | Tipik `result_status` |
|--------------|----------|------------------------|
| `command_requested` | `POST /tools/execute` alındı; doğrulama geçti | `received` |
| `approval_pending` | Onay gerektiren komut; pending JSON yazıldı | `pending` |
| `approval_granted` | `POST /approve` veya relay approve; `status=approved` | `approved` |
| `approval_rejected` | Onay reddedildi | `rejected` |
| `approval_expired` | TTL doldu; `mark_expired_if_needed` | `expired` |
| `command_executed` | Token doğrulandı; stub/gerçek yürütme başarılı | `success` |
| `command_failed` | Doğrulama, gate veya yürütme hatası | `failed` |
| `command_blocked` | Policy, `SECURITY_NEVER_AUTO`, surface block | `blocked` |

**Korelasyon:** Aynı `approval_id` veya `command_id` ile ilişkili satırlar birleştirilir. `correlation_id` (UUID) isteğe bağlı; çok adımlı akışlarda önerilir.

**Kaynak etiketleri (`source`):**

| Değer | Anlam |
|-------|-------|
| `pc_remote` | Köprü `POST /tools/execute` |
| `openai` | Model tool call → adapter → köprü |
| `mobile` | LAN relay üzerinden mobil onay/red |
| `panel` | Panel onay kartı veya panel tetiklemeli execute |
| `cli` | CLI adapter |
| `task_engine` | Görev motoru köprüsü (geniş faz) |

---

## 3. Zorunlu alanlar şeması

**Şema sürümü:** `lumos.audit_event.v1`  
**Format:** JSONL — her satır tek JSON nesnesi, UTF-8, `ensure_ascii=false` kabul edilir.

### 3.1 Çekirdek alanlar (MUST)

Kullanıcı gereksinimleri ile hizalı zorunlu alanlar:

| Alan | Tip | Açıklama | Örnek |
|------|-----|----------|-------|
| `schema_version` | string | Sabit şema kimliği | `"lumos.audit_event.v1"` |
| `event_type` | string | §2 tablosundan biri | `"approval_granted"` |
| `timestamp` | string | ISO-8601 UTC | `"2026-06-22T14:30:00+00:00"` |
| `requested_by` | string | İsteği başlatan bağlam (model, adapter, kullanıcı oturumu) | `"openai_responses"`, `"pc_remote_bridge"` |
| `target_device` | string | Komutun hedeflendiği cihaz | `"local"`, `"lumos-pc-a1b2"` |
| `command` | string | Bridge komut kimliği | `"pc_open_url"` |
| `command_id` | string | İstek korelasyonu; yoksa `approval_id` ile aynı | `"pc_remote_1735123456789_ab12cd34"` |
| `approval_id` | string | Pending onay kimliği (varsa) | `"pc_remote_1735123456789_ab12cd34"` |
| `approver_device` | string \| null | Onay veren cihaz; pending aşamasında `null` | `"mobile_f3e2d1c0"`, `null` |
| `result_status` | string | Olay anındaki sonuç | `"pending"`, `"approved"`, `"success"`, `"failed"` |
| `source` | string | Tetikleyici yüzey | `"pc_remote"`, `"mobile"`, `"openai"` |

### 3.2 Önerilen ek alanlar (SHOULD)

| Alan | Tip | Açıklama | Örnek |
|------|-----|----------|-------|
| `risk_level` | string | `low` / `medium` / `high` / `meta` | `"medium"` |
| `action_key` | string | CU4 / `confirmation_policy` eşlemesi | `"bridge_medium_dispatch"` |
| `reason_code` | string | Hata veya blok kodu | `"approval_expired"`, `"invalid_approval_token"` |
| `arguments_preview` | object | Redakte önizleme (§5) | `{"url": "https://example.com"}` |
| `approval_token_hash` | string | Ham token yerine SHA-256 hex (§4) | `"a3f5…"` |
| `relay_device_id` | string | LAN relay PC cihaz kimliği | `"c4d5e6f7a8b90123"` |
| `stub_only` | boolean | OSS demo stub bayrağı | `true` |
| `correlation_id` | string | Çok adımlı akış UUID | `"550e8400-e29b-41d4-a716-446655440000"` |

### 3.3 Örnek satırlar

**Onay bekleme:**

```json
{
  "schema_version": "lumos.audit_event.v1",
  "event_type": "approval_pending",
  "timestamp": "2026-06-22T12:00:01+00:00",
  "requested_by": "openai_responses",
  "target_device": "local",
  "command": "pc_type_text",
  "command_id": "pc_remote_1735123456789_ab12cd34",
  "approval_id": "pc_remote_1735123456789_ab12cd34",
  "approver_device": null,
  "result_status": "pending",
  "source": "pc_remote",
  "risk_level": "high",
  "action_key": "cu_act_type",
  "arguments_preview": {"text": "[REDACTED]"},
  "stub_only": true
}
```

**Mobil onay + yürütme:**

```json
{
  "schema_version": "lumos.audit_event.v1",
  "event_type": "command_executed",
  "timestamp": "2026-06-22T12:05:00+00:00",
  "requested_by": "openai_responses",
  "target_device": "local",
  "command": "pc_open_url",
  "command_id": "pc_remote_1735123456789_ab12cd34",
  "approval_id": "pc_remote_1735123456789_ab12cd34",
  "approver_device": "mobile_f3e2d1c0",
  "result_status": "success",
  "source": "pc_remote",
  "risk_level": "medium",
  "reason_code": "",
  "arguments_preview": {"url": "example.com"},
  "stub_only": true
}
```

---

## 4. Yasak alanlar (MUST NOT log)

Aşağıdaki veriler audit satırına **asla** yazılmaz. İhlal, ADR-012 C3 ve public boundary ile çelişir.

| Yasak alan / içerik | Neden | Örnek (yazılmamalı) |
|---------------------|-------|---------------------|
| **`arguments` tam içerik** | Kullanıcı içeriği taşır | `{"text": "banka şifrem 1234"}` |
| **Yazılacak metin (`pc_type_text`)** | Doğrudan kullanıcı içeriği | `"Merhaba, raporu şu adrese gönder…"` |
| **Ham `approval_token`** | Yetki ele geçirme riski | `"a1b2c3d4e5f6789012345678abcdef01"` |
| **URL sorgu parametreleri / token** | Gizli anahtar sızıntısı | `https://api.example.com/cb?token=sk-live-…` |
| **Ekran okuma piksel/ham OCR** | Özel veri | `screen_pixels_base64`, tam OCR metni |
| **Tam dosya yolu (PII riski)** | Kullanıcı dizin yapısı | `/Users/jane/Documents/vergi-2025.pdf` |
| **API anahtarları, passphrase, keystore** | `SECURITY_NEVER_AUTO` / kimlik | `KANDO_BRIDGE_SECRET`, `OPENAI_API_KEY` |
| **Pano içeriği (clipboard)** | Hassas veri | `"kopyalanan kart numarası …"` |
| **Relay oturum token'ı (ham)** | Oturum ele geçirme | `X-Relay-Token` değeri |
| **Onay dışı model prompt / sohbet** | Kullanıcı içeriği | Tam kullanıcı mesajı gövdesi |

**İzinli alternatifler:**

- `approval_token` → yalnızca `approval_token_hash` (SHA-256, salt opsiyonel)
- Dosya yolu → yalnızca `basename` veya `[REDACTED_PATH]`
- URL → §5 domain-only veya şema+host

---

## 5. Redaction kuralları

### 5.1 `arguments_preview` — izinli alanlar

Yalnızca aşağıdaki komut anahtarları ve kurallar geçerlidir (`pc_remote_tools.py` `_safe_preview` ile hizalı, **sıkılaştırılmış**):

| Komut | İzinli preview anahtarları | Redaction |
|-------|---------------------------|-----------|
| `pc_open_url` | `url` (domain-only modda) | Sorgu stringi atılır |
| `pc_open_app` | `app_name` | — |
| `pc_type_text` | — | Her zaman `{"text": "[REDACTED]"}` |
| `pc_suggest_click` | `target_description` (max 80 char, PII yok) | Koordinat/ham selector yok |
| `pc_request_file_picker` | `purpose` (max 80 char) | Dosya yolu yok |
| `pc_read_screen_state` | `mode` (varsa) | Ekran içeriği yok |
| `pc_request_user_approval` | — | `summary` audit'e girmez |

**Uzunluk:** Preview değerleri komut başına **≤ 400 karakter** (mevcut kod); audit için `pc_type_text` istisnası: **0 karakter içerik**.

### 5.2 URL — domain-only seçeneği

`pc_open_url` için audit modu `url_logging: domain_only` (önerilen varsayılan):

```
https://mail.google.com/mail/u/0/#inbox?secret=abc  →  mail.google.com
http://192.168.1.10:8080/admin?key=x                 →  192.168.1.10
```

Şema, path, query ve fragment **audit'e yazılmaz**.

### 5.3 Onay token

- Pending JSON'da ham token kalır (operasyonel gereklilik).
- Audit'te: `approval_token_hash = sha256(token)` veya alan tamamen yok (yalnızca `approval_id`).

### 5.4 Hata mesajları

`reason_code` makine kodu yeterlidir. Ham exception stack veya kullanıcıya özel mesaj gövdesi audit'e **girmez**.

---

## 6. Depolama

### 6.1 Path

| Öğe | Değer |
|-----|-------|
| **Kök** | Workspace `.lumos/` (`CORE_STATE_PATH_NAMES` içinde `logs`) |
| **Dizin** | `.lumos/logs/` |
| **Önerilen dosya** | `.lumos/logs/audit_events.jsonl` |
| **Alternatif (günlük rotasyon)** | `.lumos/logs/audit_events-YYYY-MM-DD.jsonl` |

`workspace_contract.logs_dir_path(base_dir)` ile hizalı: `base_dir` = `.lumos` kökü.

**Not:** Mevcut `lumos_audit.append_audit_log()` günlük dosya adı `YYYY-MM-DD.log` kullanır (`lumos.audit_log.v1` — görev pipeline). PC remote audit **ayrı dosya** veya aynı dizinde **ayrı şema** ile tutulmalı; şema karışımı yapılmamalı.

### 6.2 Format

- **JSONL** (önerilen): append-only, satır başına bir olay, stream-friendly
- Kodlama: UTF-8
- Yazım: `open(path, "a")` — atomik rotate ayrı araçla

### 6.3 Retention ve rotation (öneri)

| Parametre | Öneri |
|-----------|-------|
| **Retention** | 90 gün yerel (ürün kararı ile ayarlanabilir) |
| **Rotation** | Günlük veya 50 MB boyut eşiği |
| **Arşiv** | Sıkıştırılmış `.jsonl.gz`; arşiv state kaynağı değil |
| **Silme** | Otomatik kalıcı silme yok; rotation yalnızca dosya adı/değişimi |

### 6.4 State olmadığı

Audit log:

- Görev durumu, pending onay veya confirmation grant **kaynağı değildir**
- Okuma/yeniden oynatma için **türev özet** üretilebilir; gerçek gate kararı disk state + policy'den gelir
- `trash/` prensibi gibi: audit arşivi operasyonel geri yükleme kaynağı olarak kullanılmaz

---

## 7. Kimler yazar / kimler okur

### 7.1 Yazarlar (append-only)

| Bileşen | Yazdığı olaylar | Not |
|---------|-----------------|-----|
| **kando_bridge** (`pc_remote_tools`, `server.py`) | `command_*`, `approval_*` | Tek choke-point: `handle_tools_execute_body`, `approve_pc_remote_pending` |
| **lan_relay** | `approval_granted`, `approval_rejected` | `approver_device` = paired `mobile_device_id` |
| **Mobil istemci** | Doğrudan yazmaz | Relay üzerinden köprüye iletir |
| **Panel** (opsiyonel) | Panel onay kartı olayları | `source: panel` |
| **Task engine** (Faz 3+) | Görev köprüsü olayları | Mevcut `lumos_audit` ile birleşik veya paralel |

Yazım **best-effort**: audit hatası ana akışı kırmaz (EC2-04 GP10 ilkesi ile uyumlu).

### 7.2 Okuyucular (read-only)

| Tüketici | Erişim | Gösterim |
|----------|--------|----------|
| **Panel** | Özet API (Faz 2) | Son N olay, komut + sonuç + zaman; içerik yok |
| **CLI / teşhis** | Dosya tail veya filtre | Geliştirici modu |
| **Evidence continuity** | Korelasyon (Faz 3) | `correlation_id` ile çapraz referans; şema birleşmez |
| **Mobil** | Okumaz | Yalnızca onay kararı verir |

Panel özeti: `requested_by`, `command`, `result_status`, `timestamp`, `approver_device` — **preview ve hash hariç detay gösterilmez** (ADR-012 şeffaflık ile uyumlu).

---

## 8. Mevcut kod gap analizi

### 8.1 Var olanlar

| Kanal | Konum | Şema | PC remote? |
|-------|-------|------|------------|
| Pending onay state | `.lumos/pending_approvals/*.json` | `lumos.pc_remote_pending_approval.v1` | Evet — **state, audit değil** |
| Görev pipeline audit | `lumos_audit.append_audit_log` | `lumos.audit_log.v1` | Hayır — `/task` pipeline |
| Evidence continuity | `.lumos/logs/evidence_continuity.jsonl` | `lumos.evidence_continuity.v1` | Hayır — guard/policy/panel |
| Policy blocked | `.lumos/logs/log.txt` | logfmt | Hayır |
| Köprü debug | `logs/bridge.log` (repo kökü) | ham byte | Kısmi — sözleşme dışı path |
| CU4 confirmation | `.lumos/pending_confirmations/` | confirmation_policy | Shadow; audit değil |

### 8.2 Eksikler (sözleşmeye göre)

| Gap | Kanıt | Risk |
|-----|-------|------|
| PC remote audit yazımı yok | [pc-remote-pending-approval-contract.md §Sınırlar](pc-remote-pending-approval-contract.md): «Rate limit ve audit log … kapsam dışı» | Onay zinciri diskte izlenir; append-only audit yok |
| `handle_tools_execute_body` audit çağırmıyor | `pc_remote_tools.py` — yalnızca pending/execute | `command_executed` / `failed` kaydı yok |
| `lan_relay` audit yok | `lan_relay.py` — köprüye proxy; log yok | `approver_device` audit'e düşmüyor |
| Pending `arguments` tam içerik | `build_pc_remote_pending_record` → `arguments` dict | State dosyasında kullanıcı içeriği var; audit bunu kopyalamamalı |
| `_safe_preview` yeterince sıkı değil | `pc_type_text` metni preview'da kalır | Pending yanıtında sızıntı; audit redaction §5 ile sıkılaştırılmalı |
| Tekil audit modülü yok | Dağınık: lumos_audit, evidence_continuity, log.txt | Şema ve path tutarsızlığı |

### 8.3 Pending JSON vs audit — karşılaştırma

| Özellik | Pending JSON | Audit event |
|---------|--------------|-------------|
| Amaç | Onay gate state | İzlenebilirlik |
| `approval_token` ham | Evet | Hayır |
| `arguments` tam | Evet | Hayır |
| TTL / `used` | Evet | Hayır (yalnızca olay zamanı) |
| Silinebilir / expire | Dosya güncellenir | Append-only |

---

## 9. Uygulama fazları

| Faz | Kapsam | Çıktı | Bağımlılık |
|-----|--------|-------|------------|
| **Faz 1 — Audit stub** | `append_audit_event()` helper; köprü choke-point'lerde 6 olay tipi | `audit_events.jsonl` satırları; pytest karakterizasyon | PR-RB-10 planı |
| **Faz 2 — Panel özet** | Read-only `GET /audit/summary` veya statik tail | Son 50 olay, içeriksiz kart | Faz 1 |
| **Faz 3 — Relay + mobile** | `approver_device` relay'den; redaction sıkılaştırma | `mobile` source satırları | PR-RB-06+ |
| **Faz 4 — EC korelasyon** | `correlation_id` evidence_continuity ile | Çapraz sorgu; şema ayrık kalır | EC2 backlog |
| **Faz 5 — Rate limit** | `/tools/execute` flood koruması | Audit ile birlikte; ayrı sayaç | PR-RB-10 |

**Faz 1 minimum olay seti:** `approval_pending`, `approval_granted`, `approval_rejected`, `command_executed`, `command_failed`, `approval_expired`.

**Public OSS:** Faz 1–2 demo-safe; gerçek OS executor audit alanları private katmanda genişletilir.

---

## 10. ADR-012 / public boundary hizası

### 10.1 ADR-012 codex eşlemesi

| Codex | Audit karşılığı |
|-------|-----------------|
| **C1 Tek dış kapı** | Tüm etkili komutlar tek audit zincirinde `source` ile etiketlenir |
| **C3 Onay + kanıt** | `approver_device`, `approval_id`, `result_status`; log okunmadan teşhis disiplini |
| **C6 Stop-on-risk** | `command_blocked`, `reason_code`; `SECURITY_NEVER_AUTO` otomatik yürütme audit'te `blocked` |
| **Mock ayrımı** | `stub_only: true` zorunlu (OSS) |

### 10.2 SECURITY_NEVER_AUTO

`profiles.SECURITY_NEVER_AUTO` üyeleri (`permanent_delete`, `external_write`, `irreversible_user_op`, `critical_system_config`) audit'te **yalnızca blok olayı** olarak görünür; başarılı yürütme satırı **üretilmez**.

### 10.3 confirmation_policy

Opt-in (`LUMOS_CONFIRMATION_ENABLED`): audit `action_key` ve `reason_code` (`confirmation_required`, `confirmation_expired`, …) taşır; CU4 grant içeriği kopyalanmaz.

### 10.4 Public GitHub sınırı

| OSS'te | Private'te |
|--------|------------|
| Audit şema sözleşmesi, stub olayları, redaction kuralları | Gerçek executor sonuçları, TLS relay audit genişletmesi |
| Demo panel özeti | Üretim log aggregation |
| `arguments_preview` redaction | Ek PII sınıflandırma |

**Kural:** Audit satırına üretim URL, müşteri verisi veya operasyonel backend kimliği **commitlenmez**.

### 10.5 lumos-karar-sozlesmesi

§3 «Loglama/raporlama biçimi» kontrollü geliştirilebilir alan — bu belge **biçim ve alan sözleşmesini** tanımlar; yol (`.lumos/logs/`) ve yetki (append choke-point) değişmez. Kalıcı silme audit arşivine otomatik uygulanmaz.

---

## Özet referans

**Zorunlu alanlar (MUST):**  
`schema_version`, `event_type`, `timestamp`, `requested_by`, `target_device`, `command`, `command_id`, `approval_id`, `approver_device`, `result_status`, `source`

**En kritik yasaklar (örnekli):**

1. `arguments` tam içerik — örn. `{"text": "gizli not …"}`
2. Ham `approval_token` — örn. `"a1b2c3…ef01"` (yerine hash veya yok)
3. URL token/sorgu — örn. `?api_key=sk-…` (yerine `example.com`)

---

## Kod referansları

| Dosya | Rol |
|-------|-----|
| `packages/kando_bridge/src/kando_bridge/pending_approvals.py` | Pending state; audit kaynağı değil |
| `packages/kando_bridge/src/kando_bridge/pc_remote_tools.py` | Execute/approve choke-point adayları |
| `packages/kando_bridge/src/kando_bridge/lan_relay.py` | Mobil onay proxy |
| `packages/kando_runtime/src/kando_runtime/lumos_audit.py` | Mevcut görev audit (ayrı şema) |
| `src/core/workspace_contract.py` | `.lumos/logs/` path sözleşmesi |
| `src/task_engine/profiles.py` | `SECURITY_NEVER_AUTO` |
| `src/policy/confirmation_policy.py` | CU4 action_key / opt-in gate |

---

## Takip

| Madde | Durum |
|-------|-------|
| Bu belge (sözleşme) | Taslak |
| PR-RB-10 implementasyon | Planlı |
| Panel audit özeti | Faz 2 |
| `_safe_preview` sıkılaştırma | Faz 1 ile birlikte önerilir |
