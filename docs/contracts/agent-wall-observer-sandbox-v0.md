<!-- markdownlint-disable MD013 -->

# Agent Wall Observer — Sandbox yürütme bağlamı v0

Durum: **sözleşme** (docs-only). Uygulama ayrı dilim.  
Üst karar: [ADR-033](../decisions/ADR-033-agent-wall-observer-sandbox.md).  
Gözlem sinyalleri: [agent-wall-observation-v1](agent-wall-observation-v1.md).  
İlgili uygulama adayı (henüz merge değil): lumos-core **#832** head `d5248e26`.

## 0. Tek cümle

Observer’ın Git çağrıları, operatör yetkisinde değil; **gerçek bir düşük-yetkili sandbox** içinde çalışır. Kod içi “jail/yamalar” sandbox’ın yerine geçmez.

## 1. Kurucu karar (özet)

> **Founder decision: A — sandbox.**  
> #832’ye yeni Git yönlendirme yamaları eklenmeyecek. Observer’ın Git çağrıları gerçek bir düşük-yetkili sandbox içinde çalıştırılacak. Sandbox; operatör kimlik bilgilerine, yazma yetkilerine ve gereksiz ağ erişimine sahip olmayacak. Observer hiçbir durumda izlediği ajanlardan daha fazla yetkiyle çalışmayacak. Mevcut `d5248e26` bu mimari karar uygulanana kadar merge adayı değildir. B/C/D reddedilmedi; fallback seçenekleri olarak kayıtta kalır.

| Seçenek | Durum |
| --- | --- |
| **A — sandbox** | **Kabul** — bu sözleşme |
| B — trusted repo | Fallback (Wall’ı daraltır) |
| C — index/stat | Fallback (Git davranışını yeniden yazmak) |
| D — residual kabul | Fallback (şimdilik erken) |

## 2. Neden sandbox (kısa gerekçe)

#832 üzerinde Git yönlendirme yüzeyleri peş peşe çıktı (gitfile zinciri, `commondir`, object store, nested `alternates`, …). Enumerate yaklaşımı yakınsamadı. Ayrıca `filter.*.clean` kod içi `-c` listesiyle kapanmıyor. Observation-only olsa bile **execution-context** riski kalır; çözüm yeni yama değil, **yürütme bağlamı**.

## 3. En küçük uygulanabilir sınır (MVP)

MVP, ileride seçilecek somut motoru (bubblewrap / seatbelt / Landlock+seccomp / mikro-VM) kilitlemez. Kilitleyen şey **yetenek tablosu**dır: hangi motor kullanılırsa kullanılsın aşağıdaki sınırlar bozulmaz.

### 3.1 Zorunlu yetenek tablosu

| Yetenek | MVP kuralı |
| --- | --- |
| Kimlik / UID | Observer süreci, izlediği ajanlardan **daha yüksek** yetkili olamaz. Operatör hesabı / admin / CI secret principal **yok**. |
| Kimlik bilgisi | Operatör token’ları, SSH agent, cloud credential, macOS Keychain erişimi sandbox’a **girmez**. |
| Ağ | Varsayılan **kapalı** (deny-all). Observer Git’i uzak fetch/push yapmaz. |
| Yazma | Ajan worktree’lerine, claim store’a, operatör home’una, secret store’a yazma **yok**. |
| Okuma | Yalnız operatörün verdiği `allowed_roots` (ve sabitlenmiş gitdir/object paths) okunabilir. |
| Çalıştırma | Sandbox içinde izinli ikili: `git` (+ zorunlu dinamik yükleyiciler). Genel shell / paket yöneticisi / interpreter spawn **yok** (git’in tetiklediği filter/helper’lar da bu sınırda boğulur veya süreç öldürülür). |
| Günce yazımı | Tek yan etki: gözlem güncesi — **sandbox dışında**, operatör kontrollü path’e, observer host tarafında append. Sandbox içinden günce path’ine yazma yok. |

### 3.2 MUST / MUST NOT

1. **MUST** — Her `git` çağrısı sandbox içinde yapılır; host process’te “cwd jail + env allowlist” tek başına yeterli sayılmaz.
2. **MUST** — Sandbox, operatör kimlik bilgisi ve gereksiz ağ olmadan ayağa kalkar (fail-closed: kurulamazsa gözlem turu atlanır, boş bulgu uydurulmaz).
3. **MUST NOT** — Observer, izlediği ajanlardan daha fazla yetkiyle çalıştırılamaz.
4. **MUST NOT** — #832 (veya devam PR’ları) yeni Git yönlendirme yaması ekleyerek bu sözleşmeyi ertelemez.
5. **MUST NOT** — Sandbox, ajan worktree’sini “güvenilir” saymaz; kök içi düşman depo varsayılır.

### 3.3 Mevcut kod jail’i ile ilişki

`d5248e26` üzerindeki pin/jail katmanı (gitfile, `commondir`, objects, …) **savunma derinliği** olarak kalabilir; **birincil sınır değildir**. Birincil sınır sandbox’tır. Yeni yönlendirme deliği bulunursa varsayılan cevap yine yama değil: sandbox sınırını sıkılaştırmak veya B/C fallback’e kurucu dönüş.

### 3.4 Somut motor — bilinçli açık

MVP motor seçimini kilitlemez. Uygulama dilimi şunlardan **birini** seçer ve kanıtlar:

- Linux: user namespace + mount (ro `allowed_roots`) + network namespace yok + seccomp/landlock, veya bubblewrap eşdeğeri
- macOS: `sandbox-exec` / App Sandbox profili (yazma yok, ağ yok, credential yok)
- Daha sert: mikro-VM / gVisor — gerekirse sonraki dilim

Seçim kriteri: §3.1 tablosunu **ölçülebilir** sağlayan en küçük motor.

## 4. Kabul ölçütleri (sandbox dilimi yeşil sayılınca)

Aşağıdakiler olmadan #832 **merge adayı olmaz**:

1. Host’ta planted `filter.*.clean` / nested `alternates` senaryosu sandbox içinde **çalıştırılamaz** veya observer sürecini etkilemez (kanıtlı test).
2. Sandbox env’de operatör credential sızıntısı yok (kanıtlı negatif test).
3. Ağ denemesi fail-closed.
4. Worktree’ye yazma denemesi fail-closed.
5. Gözlem güncesi yalnız operatör path’ine host tarafında yazılır.
6. Docs + test bu sözleşmeye bağlanır; wire/control hâlâ yok.

## 5. Bu dilimin dışında (bilinçli)

| Konu | Not |
| --- | --- |
| #832’ye kod / yeni Git yaması | **Yasak** (bu PR ve karar) |
| `worktree` + `gitdir` + `commondir` sözleşme metni | #832 temiz kapanışından **sonra** ayrı docs-only contract PR |
| Control / engelleme / claim yazma | Observation v1 ile aynı — yok |
| Trusted-repo allowlist (B) | Fallback; Wall amacını daraltır |
| Index/stat ile Git’siz gözlem (C) | Fallback |
| Residual risk’i “kabul ettik, merge” (D) | Fallback; sandbox uygulanmadan yok |
| Guard “sandbox mode” hedef dizini (`docs/lumos-sandbox-hedef-dizin-sozlesmesi.md`) | **Farklı konu** (yazım yönlendirme); bu sözleşme observer **yürütme** bağlamıdır |

## 6. Uygulama sırası (öneri)

1. Bu sözleşme + ADR-033 merge (docs-only).
2. Sandbox MVP uygulama PR (motor + §4 testleri) — observation API’sine bağlanır; control yok.
3. #832, sandbox dilimine rebase/adapt; yeni yönlendirme yaması yok.
4. Exact-head CI + güvenlik turu; sonra insan merge.
5. Sonra: `worktree`/`gitdir`/`commondir` + untrusted execution context docs-only contract.

## 7. Kısa sözlük

| Terim | Anlam |
| --- | --- |
| Host observer | Sandbox’ı başlatan, günceyi yazan düşük-yetkili süreç |
| Sandbox git | `git`’in çalıştığı izole bağlam |
| `allowed_roots` | Operatörün okumaya izin verdiği worktree kökleri |
| Jail (kod) | #832 pin/resolve katmanı — derinlemesine savunma, birincil sınır değil |
