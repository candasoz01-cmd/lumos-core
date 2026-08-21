<!-- markdownlint-disable MD013 -->

# Task Execution Grant — v1

Durum: ADR-031 sözleşmesi. Kod: `src/policy/task_execution_grant.py`.

Kısa ömürlü, tek kullanımlık **görev yürütme anahtarı**. Kullanıcı onayı
(CU4 confirmation / `approval_token`) değildir. Onay varsa ondan *sonra*
üretilir; executor bu anahtarı tüketmeden yürütmez.

## Zincir

```text
Kimlik → Politika → Görev yetkisi → (gerekirse kullanıcı onayı)
    → tek kullanımlık yürütme anahtarı → Executor → Audit
```

## Bağ (zorunlu)

Anahtar şu beş alana bağlıdır; biri uyuşmazsa consume reddeder:

| Alan | Anlam |
| --- | --- |
| `subject_id` | Kim (doğrulanmış özne) |
| `task_id` | Hangi görev örneği |
| `action_key` | Hangi işlem (`file_read`, `mail_send`, `device_control`, …) |
| `resource` | Hangi kaynak |
| `permission` | Hangi yetki (`read` / `send` / `execute`, …) |

`file_read` anahtarıyla `mail_send` yürütülemez. Başka görevden çalınmış
anahtar da çalışmaz.

## Kurallar

1. Token `teg1.<grant_id>.<secret>` biçimindedir. Diskte yalnız `token_hash`
   (SHA-256) durur; ham token mint yanıtında bir kez döner.
2. TTL varsayılan 120 sn, tavan 900 sn.
3. Consume tek kullanımlıktır; Unix'te sidecar `fcntl` kilidi ile replay
   daraltılır (Windows kilitsiz yedek — confirmation/`approval_token` ile aynı
   bilinçli sınır).
4. `SECURITY_NEVER_AUTO` / yüzey bloğu (`permanent_delete`, `external_write`,
   …) için grant **üretilmez** ve consume **açmaz**. Token olsa bile kapalı
   yüzey kapalı kalır.
5. Anahtarsız, bozuk, süresi dolmuş veya bağ uyuşmayan istek **default deny**
   + audit şüphe sinyalidir. Sınıflandırma `unclassified`'dır; "saldırgan"
   denmez (bozuk istemci / dolmuş oturum / yazılım hatası da aynı kapıya
   düşer).
6. Enforcement `LUMOS_TASK_EXECUTION_GRANT_ENABLED=true|1|yes` iken aktiftir.
   Varsayılan kapalı (CU4 confirmation ile aynı opt-in).
7. Audit satırına ham token, tam dosya yolu veya kullanıcı içeriği yazılmaz.

## Reason kodları

| Kod | Anlam | Şüphe |
| --- | --- | --- |
| `task_execution_grant_disabled` | Env kapalı; no-op | none |
| `task_execution_grant_missing` | Token yok | high |
| `task_execution_grant_malformed` | Biçim bozuk | high |
| `task_execution_grant_unknown` | Kayıt yok / hash uyuşmaz | high |
| `task_execution_grant_mismatch` | Kim/görev/işlem/kaynak/yetki uyuşmaz | high |
| `task_execution_grant_used` | Tekrar kullanma | high |
| `task_execution_grant_expired` | TTL doldu | medium |
| `task_execution_grant_binding_incomplete` | Gate bağını kuramadı | high |
| `task_execution_grant_surface_blocked` | Kapalı yüzey; grant açmaz | high |

## Bu dilimin dışı

- Public HTTP uçlarına varsayılan-on bağlama (TD-20)
- ADR-024 `AuthorityGrant` / çok-özne kimlik uygulaması
- CU4 confirmation veya `approval_token` yerine geçme
- Yeni ajan / orkestrasyon katmanı
