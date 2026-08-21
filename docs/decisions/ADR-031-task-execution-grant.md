# ADR-031 — Görev yürütme anahtarı (task execution grant)

> 2026-08-21 kurucu kararı (chat, iki tur): tek “anahtar biliyor musun?”
> kontrolü değil; görev kabulünde merkezi Task Authority’nin ürettiği kısa
> ömürlü yetki. Üç parça: **Task Registry**, **Capability Token**,
> **Immutable Audit Ledger**. Ledger kapı değildir; kapı registry + token +
> policy’dir. Ajan anahtar üretmez; kullanıcıdan da istenmez. **Yeni ajan /
> orkestrasyon katmanı değildir.** STOP LIST ihlali yok.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-21)** — kurucu, chat kararı |
| Uygulama durumu | Kernel (üç parça) + opt-in `lumos_gate_execute`; varsayılan kapalı; diğer yüzeyler TD-20 |
| Tarih | 2026-08-21 |
| Üst ilişki | [ADR-012](ADR-012-lumos-security-codex.md) C1; [ADR-010](ADR-010-guard-policy-trust-terminology.md); CU4 confirmation; `approval_token`; [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) K4 **uygulanmaz** |
| Sözleşme | [`task-execution-grant-v1.md`](../contracts/task-execution-grant-v1.md) |
| Merge kapısı | Security / permissions. ADR-028 standing hattı **yok**. İnsan onayı şart |

## Karar

```text
Kimlik → oturum → görev ID → verilen yetki → istenen işlem
    → policy kararı → (yalnız riskli işlemde kullanıcı onayı)
    → Capability Token consume → Executor → Ledger
```

Açık endpoint serbest dolaşma vermez. Kayıtlı bir görev zincirine
bağlanamayan işlem yürümez.

### Üç parça

| Parça | Rol | Kapı mı? |
| --- | --- | --- |
| **Task Registry** | Kabul edilmiş görevin resmi kaydı (`G-12841` var mı, hangi bağ?) | Evet (yoksa red) |
| **Capability Token** | Göreve özel, kullanıcı+ajan+işlem+kaynak bağlı, tek kullanımlık | Evet (yok/uyuşmaz/replay → red) |
| **Immutable Audit Ledger** | Hash-zincirli işlem defteri: kim, ne zaman, ne denedi | Hayır — sonradan kanıt |

v1 ledger: append-only JSONL + `prev_hash`/`entry_hash`. Dağıtık WORM
değildir; bütünlük `verify_ledger_chain` ile denetlenir.

### Anahtar kaynağı

Görev sisteme **kabul edilince** (`accept_execution_task`) merkezi gate
üretir. Bundle’daki token iç elden teslimdir; kullanıcıya sorulmaz, ajan
kendi `teg1…` uyduramaz (uydurursa `key_not_registered`).

### Red tablosu (sınıf: `unclassified`)

| Gelen | Sonuç | `event_kind` |
| --- | --- | --- |
| Kimlik yok | Executor’a inmeden red | `missing_identity` |
| Görev registry’de yok | Red | `unknown_task` |
| Görev var, anahtar o göreve kayıtlı değil | Red + yüksek şüphe | `unregistered_key` |
| Anahtar var, `fileA` yerine `mail_send` | Red + yetki sapması | `capability_deviation` |
| Anahtar daha önce kullanılmış | Red | `replay` |
| TTL dolmuş | Red | `expired` |

“Kesin saldırgan” denmez. Bozuk istemci / dolmuş oturum aynı kapıya düşer.

### Gecikme

Kontroller yerel SHA-256 + bir dosya okuma / kilit / append’tir; milisaniye
seviyesi. Asıl gecikme model, ağ, dış API, cihazdır. Kullanıcı onayı **her
adımda değil**, yalnız mevcut riskli işlem kapılarında (CU4 / `approval_token`).

### Ne değildir

| Mevcut kapı | Bu ADR |
| --- | --- |
| Kimlik / oturum | Önkoşul |
| Politika / profil | Önkoşul |
| CU4 / `approval_token` | Kullanıcı onayı; yerine geçmez |
| `surface_blocked` / `SECURITY_NEVER_AUTO` | Grant açmaz |
| ADR-024 `AuthorityGrant` | Bu dilimde uygulanmaz (TD-16) |

### Opt-in

`LUMOS_TASK_EXECUTION_GRANT_ENABLED` — varsayılan kapalı (CU4 DL-C18).
Mint/registry/ledger env’den bağımsız çalışır; **executor’a geçiş** env
açıkken zorunludur. Varsayılan-on TD-20.

## Kabul ölçütü (bu dilim)

1. Kabul = registry + merkezi mint; ajan/kullanıcı mint etmez.
2. `file_read` anahtarı `mail_send` yapamaz (`capability_deviation`).
3. Olmayan görev, kayıtlı olmayan anahtar, replay, kimlik yok → red + ledger.
4. Ledger silinse bile consume kararı registry+token’dan gelir.
5. `SECURITY_NEVER_AUTO` için grant yok.
6. `lumos_gate_execute` env açıkken consume olmadan `execute_plan` çağırmaz.
7. Env kapalıyken mevcut gate testleri değişmez.
