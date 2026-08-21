# ADR-031 — Görev yürütme anahtarı (task execution grant)

> 2026-08-21 kurucu kararı (chat): tek bir “anahtar biliyor musun?” kontrolü
> değil; her görev için üretilen kısa ömürlü, tek kullanımlık yürütme yetkisi.
> Mevcut politika–onay–kontrollü yürütme zincirinin **ortasına** ikinci bir
> kriptografik kapı konur. **Yeni ajan / orkestrasyon katmanı değildir.**
> STOP LIST ihlali yok: mevcut execute zincirinin güvenlik sertleştirmesi.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-21)** — kurucu, chat kararı |
| Uygulama durumu | Kernel + opt-in `lumos_gate_execute` kapısı bu PR; varsayılan kapalı; diğer yüzeyler TD-20 |
| Tarih | 2026-08-21 |
| Üst ilişki | [ADR-012](ADR-012-lumos-security-codex.md) C1 tek dış kapı; [ADR-010](ADR-010-guard-policy-trust-terminology.md) consent ≠ onay ≠ confirmation; [CU4](ADR-012-lumos-security-codex.md) confirmation; `approval_token`; [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) K4 AuthorityGrant **uygulanmaz** |
| Sözleşme | [`task-execution-grant-v1.md`](../contracts/task-execution-grant-v1.md) |
| Merge kapısı | Security / permissions. ADR-028 standing hattı **yok**. İnsan onayı şart |

## Karar

Açık bir endpoint tek başına ciddi bir şey kazandırmaz. Yürütme katmanına
geçmek için saldırganın (veya meşru istemcinin) **kimliğini, politikasını,
doğru görev bağlamını ve o anda geçerli tek kullanımlık anahtarı** birlikte
sağlaması gerekir.

```text
Kimlik → Politika → Görev yetkisi → (gerekirse kullanıcı onayı)
    → tek kullanımlık yürütme anahtarı → Executor → Audit
```

Bu anahtar **görev örneğine özeldir**. Global “sistem anahtarı” veya oturum
token’ının yeniden etiketlenmesi değildir.

### Ne değildir

| Mevcut kapı | Rolü | Bu ADR |
| --- | --- | --- |
| Kimlik / oturum | Kim olduğunu söyler | Yerine geçmez; önkoşuldur |
| Politika / profil | Bu özne bu işlem sınıfını yapabilir mi | Yerine geçmez |
| CU4 confirmation | İşlem bazlı **kullanıcı onayı** | Yerine geçmez; onay gerekiyorsa önce onay |
| `approval_token` | Köprü yüksek risk **kullanıcı onayı** + consume | Yerine geçmez; onaydan sonra ayrı yürütme anahtarı |
| `surface_blocked` / `SECURITY_NEVER_AUTO` | Token/onaydan bağımsız tam kapı | Grant **açmaz**; mint reddeder |

ADR-024 `AuthorityGrant` (özne çifti, Lumos ID otoritesi) bu dilimde
**uygulanmaz**; TD-16 bilinçli durur. Execution grant, o modele giden
kısa ömürlü *yürütme* kabiliyetidir; kimlik otoritesi değildir.

### Anahtarsız istek = saldırgan değil

Default deny + yüksek şüphe audit sinyali yapılır. Sınıflandırma
`unclassified` kalır. Bozuk istemci, süresi dolmuş oturum veya yazılım
hatası da anahtarsız / uyuşmayan istek üretebilir. “Kesin saldırgan”
denmez; teşhis audit’ten okunur.

### Opt-in

`LUMOS_TASK_EXECUTION_GRANT_ENABLED` — CU4 confirmation (DL-C18) ile aynı
varsayılan-kapalı. Varsayılan-on ayrı ürün kararıdır (TD-20). Kernel mint/
consume env’den bağımsız test edilir; **executor’a geçiş** env açıkken
zorunludur.

## Sonuçlar

- İç API’ler ve ajanlar arasında ikinci kriptografik kapı: çalınmış başka
  görev anahtarı yürütmez.
- Public OSS’te gerçek cihaz kontrolü açılmaz; kapalı yüzey grant ile
  gevşetilmez.
- Ham token audit/disk’te yok; yalnız SHA-256 hash.

## Kabul ölçütü (bu dilim)

1. Mint bağlar: kim + görev + işlem + kaynak + yetki + TTL.
2. Consume tek kullanımlık; yanlış `action_key` (ör. `file_read` → `mail_send`) red.
3. Anahtarsız istek deny + `unclassified` (saldırgan etiketi yok).
4. `SECURITY_NEVER_AUTO` için grant yok.
5. `lumos_gate_execute` env açıkken consume olmadan `execute_plan` çağırmaz.
6. Env kapalıyken mevcut gate testleri değişmez.
