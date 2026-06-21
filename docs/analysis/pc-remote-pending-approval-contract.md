# PC Remote Pending Approval Contract

| Alan | Değer |
|------|-------|
| Durum | **Uygulama** — PR-RB-04 |
| Şema | `lumos.pc_remote_pending_approval.v1` |
| Dizin | `.lumos/pending_approvals/` (legacy `/task` ile paylaşımlı) |
| Kaynak | `source: "pc_remote"` |

## Amaç

Onay gerektiren PC remote komutları bellek içi token üretmek yerine diskte bekletilir; Lumos Mobile / panel `GET /pending_approvals` ile listeleyebilir; `POST /approve` onaylar; yürütme yalnızca eşleşen `approval_token` + `status=approved` ile stub çalışır.

## Onay gerektiren komutlar (5)

| Komut | `risk_level` | `action_key` (CU4 shadow) |
|-------|--------------|---------------------------|
| `pc_open_app` | high | `bridge_high_risk_execute` |
| `pc_open_url` | medium | `bridge_medium_dispatch` |
| `pc_type_text` | high | `cu_act_type` |
| `pc_suggest_click` | medium | `cu_act_click` |
| `pc_request_file_picker` | medium | `cu_act_file_send` |

Onay **gerektirmeyen:** `pc_read_screen_state`, `pc_request_user_approval` (meta).

## Zorunlu alanlar

| Alan | Açıklama |
|------|----------|
| `approval_id` | Dosya adı kökü (`pc_remote_<ms>`) |
| `command` | Bridge komut kimliği |
| `requested_by` | İstek bağlamı; yoksa `pc_remote_bridge` |
| `target_device` | `local` veya Lumos cihaz kimliği |
| `created_at` | ISO-8601 UTC |
| `risk_level` | `low` / `medium` / `high` / `meta` |
| `required_user_action` | TR/EN insan okunur onay metni |
| `expires_at` | ISO-8601 UTC (varsayılan TTL 900s) |
| `status` | `pending` \| `approved` \| `rejected` \| `expired` |

Ek uyumluluk alanları: `approval_file`, `approval_token`, `schema_version`, `source`, `arguments`, `arguments_preview`, `used`, `stub_only`, `title`, `pending_summary`.

## Token / imza doğrulama

1. **Oluşturma:** `approval_token = secrets.token_hex(16)` — yalnızca pending JSON ve ilk yanıtta; tahmin edilemez.
2. **Onay (`POST /approve`):** `approval_file` veya `task_id` + `approval_token` zorunlu; token kayıtla birebir eşleşmeli; `used` false; süre dolmamış.
3. **Yürütme (`POST /tools/execute`):** `approval_token` + isteğe bağlı `approval_id`; disk kaydı `status=approved`, token eşleşmesi, `used=false`, `expires_at` geçmemiş — **`approval_granted` bayrağı tek başına yetmez**.
4. **CU4 (opt-in):** `LUMOS_CONFIRMATION_ENABLED=true` ise `attach_bridge_pending_confirmation` shadow grant + `validate_bridge_confirmation` onay adımında çalışır.
5. **Tüketim:** Başarılı stub yürütmeden sonra `used=true`, `consumed_at` yazılır.

## Akış

```
POST /tools/execute {command, arguments}
  → pending JSON (status=pending)
  → yanıt: approval_id, approval_token, approval_file

POST /approve {approval_file, approval_token, approved:true}
  → status=approved (dosya kalır)

POST /tools/execute {command, arguments, approval_token, approval_id}
  → validate_approval_token → stub execute → used=true
```

## Örnek pending JSON

```json
{
  "schema_version": "lumos.pc_remote_pending_approval.v1",
  "source": "pc_remote",
  "approval_id": "pc_remote_1735123456789",
  "approval_file": ".lumos/pending_approvals/pc_remote_1735123456789.json",
  "approval_token": "a1b2c3d4e5f6789012345678abcdef01",
  "command": "pc_open_url",
  "arguments": { "url": "https://example.com" },
  "arguments_preview": { "url": "https://example.com" },
  "requested_by": "pc_remote_bridge",
  "target_device": "local",
  "created_at": "2026-06-21T12:00:00+00:00",
  "expires_at": "2026-06-21T12:15:00+00:00",
  "risk_level": "medium",
  "required_user_action": "URL açmayı onaylayın / Approve opening the URL",
  "status": "pending",
  "action_key": "bridge_medium_dispatch",
  "used": false,
  "stub_only": true,
  "title": "pc_open_url: URL açmayı onaylayın / Approve opening the URL",
  "pending_summary": "URL açmayı onaylayın / Approve opening the URL"
}
```

## Kod referansları

- `kando_bridge/pending_approvals.py` — yazma, doğrulama, durum geçişleri
- `kando_bridge/pc_remote_tools.py` — pending oluşturma, stub gate
- `kando_bridge/server.py` — `POST /approve` PC remote dalı, `GET /pending_approvals`

## Sınırlar

- Gerçek OS otomasyonu yok (`stub_only`).
- Lumos Mobile wire bu repoda tasarım only; poll/approve HTTP uçları mevcut köprüde hazır.
- Rate limit ve audit log PC remote yolunda bu PR kapsamı dışı.
