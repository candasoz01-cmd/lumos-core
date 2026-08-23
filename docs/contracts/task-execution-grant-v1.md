<!-- markdownlint-disable MD013 -->

# Task Execution Grant — v1

Durum: ADR-031 sözleşmesi. Kod: `src/policy/task_execution_grant.py`.

Üç parça, tek yürütme kapısı. Ledger **güvenlik mekanizması değildir**.

## Parçalar

| Parça | Disk | Görev |
| --- | --- | --- |
| Task Registry | `.lumos/task_registry/<task_id>.json` | Kabul edilmiş görev + kayıtlı `token_hash` |
| Capability Token | `.lumos/task_execution_grants/<grant_id>.json` | Kısa ömürlü tek kullanımlık anahtar (diskte hash) |
| Immutable Ledger | `.lumos/ledgers/execution_ledger.jsonl` | Hash-zincirli deneme defteri |

## Zincir

```text
Kimlik → oturum → görev ID → verilen yetki → istenen işlem
    → policy → (gerekirse onay) → token consume → executor → ledger
```

Mint yalnız `accept_execution_task` (Task Authority). Ajan üretmez;
kullanıcıdan sorulmaz.

## Bağ

| Alan | Anlam |
| --- | --- |
| `subject_id` | Kullanıcı / özne |
| `agent_id` | Ajan (ör. `agent:kando`) |
| `session_id` | Oturum |
| `task_id` | Görev örneği (`G-12841`) |
| `action_key` | İşlem (`file_read`, `mail_send`, …) |
| `resource` | Kaynak |
| `permission` | Yetki (`read` / `send` / `execute`) |

## Kurallar

1. Token `teg1.<grant_id>.<secret>`. Disk ve defterde yalnız SHA-256 hash.
2. TTL varsayılan 120 sn, tavan 900 sn. Kontroller yerel; ekstra kullanıcı
   turu yok (onay yalnız mevcut riskli kapılarda).
3. Consume tek kullanımlık; Unix `fcntl` sidecar kilidi.
4. Registry’de olmayan görev → `unknown_task`. Kayıtlı olmayan anahtar →
   `unregistered_key`. İşlem sapması → `mismatch` / `capability_deviation`.
5. `SECURITY_NEVER_AUTO` grant alamaz.
6. Enforcement `LUMOS_TASK_EXECUTION_GRANT_ENABLED=true|1|yes`. Varsayılan kapalı.
7. Defter allow/deny vermez; `verify_ledger_chain` bütünlük içindir.
8. Ham token, tam yol, kullanıcı içeriği deftere yazılmaz.

## Reason / event_kind

| Reason | event_kind | Şüphe |
| --- | --- | --- |
| `task_execution_grant_disabled` | — | none |
| `task_execution_grant_identity_missing` | `missing_identity` | high |
| `task_execution_grant_unknown_task` | `unknown_task` | high |
| `task_execution_grant_key_not_registered` | `unregistered_key` | high |
| `task_execution_grant_missing` / `malformed` | `unregistered_key` | high |
| `task_execution_grant_mismatch` | `capability_deviation` | high |
| `task_execution_grant_used` | `replay` | high |
| `task_execution_grant_expired` | `expired` | medium |
| `task_execution_grant_surface_blocked` | `surface_blocked` | high |

Sınıflandırma deny’de `unclassified`; "saldırgan" yazılmaz.

## Bu dilimin dışı

- Varsayılan-on ve kalan execute yüzeyleri (TD-20)
- ADR-024 AuthorityGrant
- CU4 / `approval_token` yerine geçme
- Dağıtık/WORM ledger
- Yeni ajan katmanı
