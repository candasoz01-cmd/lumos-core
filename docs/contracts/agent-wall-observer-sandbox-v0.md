<!-- markdownlint-disable MD013 -->

# Agent Wall Observer — Sandbox yürütme bağlamı v0

Durum: **sözleşme v0.1** (docs + ölçüm betiği). Uygulama ayrı dilim; wire/control yok.  
v0.1 farkı: motor kararı ölçümle kapatıldı (§3.4, §8), yürütme modeli yeniden yazıldı (§4.1),
host zorunlulukları eklendi (`clearenv` + env allowlist, süreç sınırları).  
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
| Çalıştırma | Depo denetimi sırasında **depo denetimli kod çalışabilir** (v0.1 ölçümü: `filter.*.clean` her iki motorda da koştu). Güvenlik bunun engellenmesine dayanmaz; §4.1'e bakınız. Yetenek reddi esastır: kod koşsa bile kimlik bilgisi, kök dışı dosya, ağ ve yazılabilir durum eline geçmez. |
| Ortam (host sorumluluğu) | Sandbox süreci **`clearenv` + açık env allowlist** ile başlatılır. Ölçüm: hiçbir motor ortamı kendiliğinden temizlemiyor; sahte operatör token'ı `sandbox-exec` ve `bwrap` altında sızdı. Bu motorun değil **launcher'ın** görevidir. |
| Süreç sınırları | Zaman aşımı, süreç/fork tavanı, `stdout`/`stderr` boyut tavanı ve devralınan FD temizliği zorunludur. Dosya sistemi ve ağ izolasyonu tek başına yetmez: koşan kod hâlâ zaman ve kaynak tüketebilir, açık FD üzerinden veri taşıyabilir. |
| Günce yazımı | Tek yan etki: gözlem güncesi — **sandbox dışında**, operatör kontrollü path’e, observer host tarafında append. Sandbox içinden günce path’ine yazma yok. |

### 3.2 MUST / MUST NOT

1. **MUST** — Her `git` çağrısı sandbox içinde yapılır; host process’te “cwd jail + env allowlist” tek başına yeterli sayılmaz.
2. **MUST** — Sandbox, operatör kimlik bilgisi ve gereksiz ağ olmadan ayağa kalkar (fail-closed: kurulamazsa gözlem turu atlanır, boş bulgu uydurulmaz).
3. **MUST NOT** — Observer, izlediği ajanlardan daha fazla yetkiyle çalıştırılamaz.
4. **MUST NOT** — #832 (veya devam PR’ları) yeni Git yönlendirme yaması ekleyerek bu sözleşmeyi ertelemez.
5. **MUST NOT** — Sandbox, ajan worktree’sini “güvenilir” saymaz; kök içi düşman depo varsayılır.
6. **MUST** — Launcher sandbox sürecini `clearenv` + açık env allowlist ile başlatır. Env temizliği motora bırakılamaz (v0.1 ölçümü: ikisi de sızdırdı).
7. **MUST** — Her koşum zaman aşımı, süreç/fork tavanı ve çıktı boyut tavanı ile sınırlanır; devralınan file descriptor'lar kapatılır.
8. **MUST NOT** — macOS seatbelt profili **birincil güvenlik sınırı sayılamaz** (§3.4).

### 3.3 Mevcut kod jail’i ile ilişki

`d5248e26` üzerindeki pin/jail katmanı (gitfile, `commondir`, objects, …) **savunma derinliği** olarak kalabilir; **birincil sınır değildir**. Birincil sınır sandbox’tır. Yeni yönlendirme deliği bulunursa varsayılan cevap yine yama değil: sandbox sınırını sıkılaştırmak veya B/C fallback’e kurucu dönüş.

### 3.4 Somut motor — v0.1'de karara bağlandı

v0'da bilinçli açık bırakılan seçim, §8'deki ölçümden sonra kapatıldı. **İki motor
eşdeğer güvenlik sınırı sayılmaz:**

| Platform | Motor | Statü |
| --- | --- | --- |
| Linux | `bwrap` (user namespace + ro-bind `allowed_roots` + `--unshare-all`) | **Birincil güvenlik sınırı** |
| macOS | `sandbox-exec` deny-list profili | **Yalnız savunma derinliği** — birincil sınır değil |
| Yüksek risk / gerçek düşman depo | mikro-VM veya izole Linux ortamı | Zorunlu geçiş |

Gerekçe ölçülmüştür (§8): macOS'ta okuma sınırı **allowlist olarak kurulamıyor** —
`file-read*` dar bir subpath listesine indirildiğinde süreçler dyld aşamasında
`SIGABRT` ile ölüyor (`/bin/echo` dahil). Geriye kalan deny-list, doğası gereği
eksiktir: neyin reddedileceğini önceden saymayı gerektirir ve bu sayım #832'de
yakınsamayan tam sayımın aynısıdır. `bwrap`'te okuma sınırı gerçek bir
allowlist'tir (`--ro-bind`), yani sayıma bağlı değildir.

Bu yüzden: macOS'ta observer çalıştırılabilir, ama **kök içi düşman depo
varsayımı gerektiren koşumlar macOS seatbelt'e dayandırılamaz**; mikro-VM veya
izole Linux ortamına geçilir.

## 4. Kabul ölçütleri (sandbox dilimi yeşil sayılınca)

Aşağıdakiler olmadan #832 **merge adayı olmaz**:

1. **Yürütme modeli — v0.1'de yeniden yazıldı.** v0'daki "çalıştırılamaz" şıkkı
   ölçümle düştü: düşman `filter.*.clean` her iki motorda da koştu. Geçerli ifade:

   > **Repository-controlled code may execute as a side effect of Git inspection.
   > Security does not rely on preventing execution; it relies on denying
   > capabilities outside the observer's explicit sandbox. Such code must not
   > access operator credentials, unauthorized host files, the network, writable
   > worktree/journal state, or persistently affect observer state.**

   Bu model ancak §3.1'in tamamı sağlanırsa kabul edilebilir: temizlenmiş ortam,
   kök dışı okuma/yazma reddi, kapalı ağ **ve** süreç düzeyi sınırlar (zaman
   aşımı, fork tavanı, çıktı tavanı, FD temizliği). Bunlardan biri eksikse
   "koşuyor ama etkisiz" iddiası kurulmuş sayılmaz.
2. Sandbox env’de operatör credential sızıntısı yok (kanıtlı negatif test) — env temizliği **launcher** tarafında (`clearenv` + allowlist), motora bırakılmaz.
3. Ağ denemesi fail-closed. **Kanıt Ubuntu CI'da koşmadan "Linux network isolation proven" yazılamaz** (§8 zayıf kanıt notu).
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
| Motor ölçümü | `scripts/wall_sandbox_capability_probe.py` — §8 |

## 8. Ölçüm kaydı (v0.1) — motor kararının dayanağı

Motor seçimi tahminle değil ölçümle kapatıldı. Betik: `scripts/wall_sandbox_capability_probe.py`.
Her senaryo kendi geçici fixture'ında koşar; taban çizgisi (`direct`) her turda birlikte ölçülür.

**Kurulum:** kök içi düşman depo (`.gitattributes` + `filter.evil.clean`, betik deponun
içinde), kök dışında bir sır dosyası, ortamda sahte operatör token'ı, aynı boyutta
kirletilmiş izlenen dosya (boyut değişirse git içeriği hash'lemez ve filter hiç koşmaz).

**Geçerlilik kapısı (S0):** motor `git --version`'ı çalıştıramıyorsa diğer satırlar
**GEÇERSİZ** sayılır. "Kötü şey olmadı" güvenlik değildir; #832'de tam bu hataya
düşülmüştü.

| Ölçüt | `direct` | macOS `seatbelt-denylist` | Linux `bwrap` |
| --- | --- | --- | --- |
| S0 araç koşuyor | ✔ | ✔ | ✔ |
| S1 düşman filter **kodu** | koştu + yazdı | **koştu**, yazamadı | **koştu**, yazamadı |
| S2 kök dışı okuma | okundu | engellendi | engellendi |
| S3 operatör env sırrı | sızdı | **sızdı** | **sızdı** |
| S4 ağ | açık (HTTP 301) | kapalı | kapalı *(zayıf kanıt)* |
| S5 worktree + günce yazımı | yazdı | engellendi | engellendi |

macOS `seatbelt-strict` (okuma allowlist) satırı S0'da düştü: `rc=-6` (`SIGABRT`),
git hiç başlamadı. Bu yüzden §3.4'te macOS için allowlist değil deny-list konuşuluyor.

Ortam: macOS 26.6.2 / git 2.52.0 · Ubuntu 22.04 / git 2.34.1.

### 8.1 Kanıt gücü — açıkça zayıf olanlar

- **Linux S4 (ağ) zayıftır.** Ölçüm CI'da değil, egress'i zaten kapalı bir yerel
  Linux ortamında koştu; orada `direct` bile ağa çıkamadı. Ubuntu CI'da yeniden
  koşulmadan **"Linux network isolation proven" yazılamaz.**
- **S3 her iki motorda da düştü** ve bu bir motor kusuru değildir: ortam mirası
  launcher'ın sorumluluğudur (§3.1 "Ortam" satırı, §3.2 madde 6).
- Ölçüm `nested alternates` senaryosunu **kapsamamaktadır**; §4.1'in o yarısı
  uygulama diliminde ayrıca ölçülecektir.

### 8.2 Yol boyunca düzeltilen iki ölçüm hatası

İkisi de motoru olduğundan **güvenli** gösteriyordu; kayda geçirilmesinin sebebi bu:

1. İlk fixture'da kirli dosya farklı boyuttaydı; git stat ile karar verip içeriği
   hash'lemedi, filter hiç koşmadı ve bu "güvenli" diye okunuyordu.
2. Düşman betik depo **dışına** konmuştu; `bwrap` betiği hiç göremediği için S1'i
   sahte olarak geçti. Betik depo içine alınınca ölçüm tersine döndü.

Ayrıca çalışma sinyali `stderr`'e taşındı: yalnız dosya marker'ına bakmak, yazma
yasağını "kod çalışmadı" sanmaya yol açıyordu.
