# SECURITY_NEVER_AUTO — branch scan (2026-06-21)

| Alan | Değer |
|------|-------|
| Durum | **Aktif takip** — dar enforcement PR'ları |
| Referans | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), `task_engine/profiles.py` |

## Özet

`SECURITY_NEVER_AUTO` (`permanent_delete`, `external_write`, `irreversible_user_op`, `critical_system_config`) sözleşme tanımı `profiles.py` ve `core/inviolable.py` içinde sabit; runtime enforce **parçalı**.

## P0 / P1 gap listesi (öncelik sırası)

| Öncelik | Gap | Konum | Durum |
|---------|-----|-------|-------|
| **P0** | Panel `PUT /tasks.json` tam doküman yazımı `check_policy` dışı | `panel/scripts/panel_tasks_server.py` `do_PUT` | **Kapandı** — `fix/security-never-auto-narrow` (#444) |
| **P1** | Panel `POST /tasks/delete-permanent` `may_perform_permanent_delete` yok | `panel_tasks_server.py` `_post_delete_permanent` | **Kapandı** — #445 |
| **P1** | Panel `POST /tasks/restore` policy gate yok | `panel_tasks_server.py` `_post_restore` | **Kapandı** — #446 |
| **P2** | TaskEngine `run_task` içinde `SECURITY_NEVER_AUTO` ayrı branch yok | `task_engine/engine.py` | Bilinçli takip — [P2 analiz](security-never-auto-p2-and-helper-proposal.md) |
| **P2** | CLI vs panel `consent` / `general_approval` ayrımı | `cli_tasks_mutation.py` | **Kapandı** — #450+#451 |

## Hizalı yollar (kontrol edildi)

- `POST /tasks`, `/tasks/complete`, `/tasks/delete`, `/tasks/restore` → `_task_action_gate` + policy + profil (#449) + confirmation opt-in (#456)
- `TaskStore.delete()` → `may_perform_permanent_delete(user_initiated)`
- `may_execute_step_at_runtime` → `external` / `critical` red

## Sonraki dar PR adayı

**P2 (onay gerekir):** TaskEngine `SECURITY_NEVER_AUTO` branch veya `is_security_never_auto()` — yalnızca [P2 analiz](security-never-auto-p2-and-helper-proposal.md) onayı sonrası; bu turda uygulanmadı.
