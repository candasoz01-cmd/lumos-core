<!-- markdownlint-disable MD013 -->

# ADR-034 — Agent Wall observer: git yürütme bağlamı mimarisi

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-09-21)** — kurucu kararı (chat, birinci el). Eski ADR-033 sandbox kararını ("A — sandbox birincil sınır", 2026-09-05) **supersede eder** |
| Uygulama durumu | Yok. Bu ADR karar + değerlendirme + ölçümdür; **kod izni değildir** — geçiş dilimleri ayrı yetkilendirme ister |
| Tarih | 2026-09-21 (değerlendirme ve karar aynı gün) |
| Kapsam muhasebesi | **KARAR** + **DEĞERLENDİRME** + **ÖLÇÜM**; KOD / SÖZLEŞME DEĞİŞİKLİĞİ / CANLI yok |
| Tetikleyen | lumos-core #832 gövdesi, "An eighth round" bölümü: dört ardışık turda dört ayrı depo-yönlendirme ilkeli, sonra beşincisi; "enumeration yakınsamıyorsa cevap muhtemelen başka bir yama değil mimaridir" |
| İlgili kayıt | #832 (MERGED `f3fffc79`, 2026-09-21, GitHub API) · #838 (MERGED `5dedc056`, 2026-09-06) · eski ADR-033 sandbox kararı ve sandbox v0.1 sözleşmesi — **main'den silinmiş**, bkz. §2 |
| Board claim | `WALL-OBS-ARCH-EVAL` — değerlendirme `9a8de2df`, karar güncellemesi `48b8f1ed`; kapsam yalnız bu dosya |

---

## 0. Karar kaydı (kurucu metni, 2026-09-21)

> Kurucu kararı: eski "A — sandbox birincil sınır" kararını ADR-034 ile
> supersede et. Birincil yön Seçenek 3 olsun: git subprocess kullanımını
> kademeli kaldırıp `.git/index` + doğrudan veri/stat okuma yoluna geç.
> Mevcut jail geçiş boyunca defense-in-depth olarak kalsın; macOS seatbelt
> yalnız defense-in-depth, Linux bwrap ise yeniden ölçülmeden zorunlu ana
> sınır ilan edilmesin. dulwich/pathspec kararını ayrı alt ADR'ye bırak,
> TOCTOU'yu açık risk olarak koru. ADR-034'ü bu kararla güncelle ve
> docs-only commit olarak hazırla; kod yazma.

Maddeler halinde:

| Konu | Karar |
|------|-------|
| Eski ADR-033 "A — sandbox" (2026-09-05) | **Superseded by ADR-034.** Gerekçe ölçümle uyumlu: macOS'ta gerçek allowlist sınırı kurulamıyor (§3.1); index doğrudan okuma gerçek repo üzerinde birebir doğrulandı (§3.2) |
| Birincil yön | **Seçenek 3** — git subprocess bağımlılığı kademeli azaltılır; `.git/index` + doğrudan veri/stat okuma yoluna geçilir |
| Mevcut kod jail'i | **Kaldırılmaz.** Geçiş boyunca ve kalan her git çağrısında defense-in-depth olarak kalır |
| Sandbox | Reddedilmiyor; ama artık mimarinin **ana güvenlik sınırı değil** |
| Linux `bwrap` | İleride uygun hostlarda **ek sınır olabilir**; bu turda yeniden ölçülmediği için "zorunlu mimari temel" ilan edilmez |
| macOS seatbelt | Yalnız defense-in-depth |
| dulwich / pathspec | Bu ADR'ye gömülmez; gerekirse **ayrı alt ADR/karar** |
| TOCTOU | Çözülmüş gibi yazılmaz; **açık risk** olarak kalır (üç seçenekte de açıktı, §5) |

Bu karar kod izni değildir: geçişin her dilimi (index okuma, untracked,
committed diff) ayrı, dar kapsamlı ve ayrıca yetkilendirilecek iştir.

## 1. Sorun

`src/lumos_board/wall_observer.py` ajan worktree'lerini `git` subprocess ile okur.
Worktree yolu claim'den gelir ve **self-asserted**'dır; içindeki depo düşman
varsayılmak zorundadır. #832'nin sekiz inceleme turu boyunca git'in depo
çözümlemesinde **beş ayrı yönlendirme ilkeli** bulundu ve tek tek kapatıldı:

1. gitfile (`.git` → dışarı işaret eden dosya)
2. `commondir` (bağlı worktree'nin ortak deposu)
3. gitfile **zinciri** (kök içi "bounce" dosyası)
4. object store (`objects` symlink'i + `objects/info/alternates`, iç içe dahil)
5. index (`$GIT_DIR/index` ve `sharedindex.*` symlink'i)

Her tur doğru bir yama üretti ve her tur yeni bir kapı buldu. #832'nin kendi
tespiti: bu, **yakınsamayan bir sayımın** imzasıdır — git'in keşif yüzeyi
dışarıdan tam sayılamaz. Ayrıca `-c` ile kapatılamayan bir yürütme yolu ölçülüp
kayda geçirildi: `filter.<ad>.clean` sürücüsü, adı saldırgan seçtiği için
wildcard'la kapatılamaz (#832 "clean filter ran" tablosu; çıplak git için
§3.1'de bugünkü teyidi). Statükonun buna cevabı sonunda config değil komut
seçimi oldu: observer içerik hash'leten git komutlarını hiç çağırmaz, bu
yüzden bu sürücüler observer sürecinde çalışmaz (`e26d8c13`+; §4 Seçenek 1).

Soru: kalan cevap statüko mu, gerçek sandbox mı, git'i hiç çağırmamak mı?

## 2. Karar tarihçesi — bu değerlendirmenin üzerine oturduğu düğüm

Bu soru daha önce soruldu ve **bir kez karara bağlandı**; kayıt sonra main'den
silindi. Okuyucunun bu zinciri bilmesi gerekir:

| Tarih | Olay | Kanıt |
|-------|------|-------|
| 2026-09-05 | Eski **ADR-033 "Agent Wall observer: sandbox yürütme bağlamı"** Accepted. Kurucu kararı: **"A — sandbox"**; #832'ye yeni git yönlendirme yaması yasak; `d5248e26` sandbox olmadan merge adayı değil. B (trusted repo), C (index/stat), D (residual kabul) fallback olarak kayıtta | `git show 13e581c6:docs/decisions/ADR-033-agent-wall-observer-sandbox.md` |
| 2026-09-05/06 | Sandbox v0 → v0.1 sözleşmesi + yetenek ölçüm betiği; **motor kararı ölçümle kapatıldı** (#838): Linux `bwrap` birincil sınır, macOS `sandbox-exec` yalnız derinlik | #838 MERGED `5dedc056`; `git show 13e581c6:docs/contracts/agent-wall-observer-sandbox-v0.md` |
| 2026-09-11 | **Devpost revert** `73d6f58d`: sözleşme, eski ADR-033, probe betiği ve sözleşme testi main'den silindi (gönderilmiş ağacın restorasyonu). Revert gerekçesi Devpost/OpenAI talebidir; **kararın geri alındığına dair ayrı bir kayıt yoktur** | `git show 73d6f58d --stat` |
| ~2026-09-11 sonrası | ADR-033 numarası **yeniden kullanıldı**: bugünkü `ADR-033-account-activity-correlation.md` farklı bir konudur. Eski sandbox ADR'sine artık yalnız SHA ile erişilir | `docs/decisions/` listesi |
| 2026-09-21 | #832, jail'in son hâliyle (ilkel 4 ve 5 dahil, `d5248e26` sonrası ek turlar) main'e **merge edildi** (`f3fffc79`, 11:45Z) | GitHub API |

İki sonuç: (a) bugünkü main, eski ADR-033'ün "sandbox'sız merge adayı değil"
koşuluyla **gerilim içindedir** — koşulun kaydı silindiği için ihlal denemez,
ama çelişki açıktır ve gizlenmez; (b) bu ADR sıfırdan bir değerlendirme değil,
silinen kararın **yeniden değerlendirilmesidir**. Eski A kararının statüsü
kurucuya açık soru olarak sunuldu ve aynı gün cevaplandı: **Superseded by
ADR-034** (§0). Gerilim böylece kayıtlı biçimde kapanmıştır: bugünkü main'in
jail'li hâli, yeni kararın "geçiş boyunca defense-in-depth" hükmüyle uyumludur.

## 3. Bu ADR için yapılan ölçümler (2026-09-21)

### 3.1 Motor yetenek ölçümü — yeniden koşum (macOS)

Silinen `scripts/wall_sandbox_capability_probe.py` (`13e581c6` sürümü) bu
makinede yeniden çalıştırıldı. Ortam: Darwin 25.6.0, git 2.52.0
(`/opt/homebrew/bin/git`). Fixture: kök içi düşman depo (`filter.evil.clean`),
kök dışı sır, ortamda sahte operatör token'ı.

| Ölçüt | `direct` (sandbox yok) | macOS `seatbelt-strict` (okuma allowlist) | macOS `seatbelt-denylist` |
|-------|------------------------|-------------------------------------------|---------------------------|
| S0 git koşuyor | ✔ | **✘ `rc=-6` (SIGABRT, dyld)** — diğer satırları geçersiz kılar | ✔ |
| S1 düşman `filter.*.clean` kodu | **koştu ve yazdı** | geçersiz | **koştu**, yazamadı |
| S2 kök dışı okuma | okundu | geçersiz | engellendi |
| S3 operatör env sırrı | **sızdı** | geçersiz | **sızdı** (launcher sorumluluğu) |
| S4 ağ | açık (HTTP 301) | geçersiz | kapalı |
| S5 worktree + günce yazımı | yazdı | geçersiz | engellendi |

Sonuç, #838'in v0.1 tablosuyla birebir aynıdır: **macOS'ta okuma sınırı
allowlist olarak kurulamıyor** (git dyld aşamasında ölüyor); geriye kalan
deny-list ise neyin reddedileceğini önceden saymayı gerektirir — yani #832'de
yakınsamayan sayım probleminin kendisi. Linux `bwrap` bu turda **yeniden
ölçülmedi** (bu host macOS); v0.1 kaydı geçerli sayılır ve oradaki zayıf-kanıt
notu aynen taşınır: Linux ağ izolasyonu Ubuntu CI'da koşulmadan "kanıtlandı"
yazılamaz.

`direct` satırı **çıplak git'i** ölçer; statükonun güncel okuma yolunu değil.
Observer bugün çalışma ağacını hash'leten git komutlarını hiç kullanmadığı için
repo-local `filter.*.clean` / `.process` sürücüleri gözlemci sürecinde
çalışmaz (`e26d8c13` ve devamı; otoriter kayıt:
[`agent-wall-observation-v1` §1.1](../contracts/agent-wall-observation-v1.md)).
Satırın buradaki değeri şudur: sayımı garanti edilemeyen yüzeyde bir yürütme
yolu gözden kaçarsa, koşan kodun eli observer yetkisiyle tamamen serbesttir —
kök dışını okur, ağa çıkar, yazar (ölçüldü).

### 3.2 Index'i saf Python ile okuma — fizibilite ölçümü (Seçenek 3)

Stdlib-only, ~90 satırlık bir v2 index parser'ı yazılıp bu reponun gerçek
worktree index'ine karşı koşuldu:

```text
index dosyası : .git/worktrees/heuristic-curie-0753d5/index
format sürümü : v2   (index.version ayarlı değil; git 2.52 varsayılanı)
kayıt sayısı  : 1889
trailer sha1  : doğrulandı
uzantılar     : yok
git ls-files --stage ile (path, mode, oid, stage) küme karşılaştırması: BİREBİR AYNI
```

Yani Seçenek 3'ün en kritik görünen parçası (index okuma) küçüktür ve
doğruluğu ölçülebilmiştir. Kapsam notu: parser v2'de ölçüldü; v3 (extended
flags) kodlandı ama gerçek fixture'la ölçülmedi; v4 (prefix compression),
split-index ve sparse-index **desteklenmedi** — bu formatlar fail-closed
reddedilip skip kaydı düşülmelidir ("desteklenmeyen index" ≠ "temiz worktree").
SHA-256 depoları (32 baytlık trailer) ayrıca ele alınmalıdır; filo bugün SHA-1.

### 3.3 Devralınan ölçümler

- #832 gövdesi, "clean filter ran" tablosu: `-c` overrides + temiz env +
  `--git-dir`/`--work-tree` pinning **birlikte bile** clean filter'ı
  durduramıyor; yalnız `ls-files -o` ve commit-diff güvenli, ikisi de modified
  tracked dosyayı raporlayamıyor.
- #838 / sandbox v0.1 §8: motor tablosunun Linux `bwrap` satırı ve ölçüm
  hataları kaydı (üç kez motor olduğundan güvenli göründü; ölçüm metodolojisi
  dersleri oradadır).

## 4. Seçenekler

### Seçenek 1 — Statüko: kod içi jail + `-c` kapatmaları + ham hash

Bugünkü main. `pin_repository` beş ilkeli onaylı köklere hapseder; env
allowlist'li; worktree içerikleri git filtresinden geçirilmeyip index blob'u
ile ham hash karşılaştırılır (`_raw_worktree_blob` — bu parça zaten saf
Python'dadır).

- **Güvenlik yüzeyi:** Bilinen beş ilkel kapalı ve 86 testle pinli. Bilinen
  yürütme yolları da kapalı: `filter.*.clean` / `.process` yolu `e26d8c13`
  ve devamıyla **kodda kapatıldı** — observer içerik hash'leten git komutu
  kullanmaz, karşılaştırma `_raw_worktree_blob` ile git dışında yapılır; pin
  testleri `test_in_root_filters_never_execute` ve
  `test_filter_from_include_and_info_attributes_never_runs`, otoriter kayıt
  [`agent-wall-observation-v1` §1.1](../contracts/agent-wall-observation-v1.md).
  (#832 gövdesindeki "residual risk stands" kaydı ve eski
  `test_in_root_clean_filter_still_executes_documented_residual_risk` testi
  yedinci tura aittir; sonraki turlar yolu kapattı, eski test silindi.)
  Açık kalanlar: (a) **sayım problemi** — hem yönlendirme hem yürütme
  yüzeyinde "altıncı ilkel yok" ve "yürütme yüzeyi sıfır" iddiaları
  kurulamaz; sekiz turun deneyimi aksi yönde; (b) **TOCTOU** — jail
  kontrolleri ile git koşumu arasında depo mutasyona uğrayabilir;
  kontroller atomik değildir.
- **Bakım maliyeti:** 966 satır modül + 1.226 satır / 86 test; her yeni git
  sürümü yeni keşif/yönlendirme özelliği getirebilir ve bu yüzey dışarıdan
  izlenmek zorundadır. Sekiz turun tarihi, bu bakımın "ara sıra" değil
  sürekli olduğunu gösteriyor.
- **Sinyal kaybı:** Yok — üç sinyal de tam.
- **Mevcut hafifletme:** operasyoneldir, kodda değildir: observer izlediği
  ajanlardan fazla yetkiyle çalıştırılmamalıdır (docstring). Bu bir sandbox
  değil, bir talimattır; bugün onu zorlayan mekanizma yoktur.

### Seçenek 2 — Gerçek sandbox'ta git (eski kurucu kararı A)

Silinen v0.1 sözleşmesinin modeli: güvenlik, düşman kodun **koşmasını
engellemeye değil, koştuğunda elinin boş olmasına** dayanır (yetenek reddi:
kimlik bilgisi yok, kök dışı okuma yok, ağ yok, yazma yok, süreç sınırları
var). Kod içi jail derinlik olarak kalır.

- **Güvenlik yüzeyi:** Linux'ta `bwrap` ile okuma sınırı gerçek bir
  allowlist'tir (`--ro-bind`) — sayım problemine bağlı değildir; #838'de
  ölçüldü. **macOS'ta birincil sınır kurulamıyor** (§3.1, bugün yeniden
  ölçüldü): strict allowlist git'i hiç başlatamıyor, deny-list ise yapısal
  olarak eksik ve env sızdırıyor. v0.1'in kendi hükmü: kök içi düşman depo
  varsayımı gerektiren koşumlar macOS seatbelt'e dayandırılamaz → mikro-VM
  veya izole Linux ortamı zorunlu. Sandbox, kök **içi** verilere erişimi ve
  TOCTOU'yu çözmez; günce bütünlüğü host tarafında kalır.
- **Bakım maliyeti:** Launcher (clearenv + env allowlist — ölçüm: env
  temizliğini hiçbir motor kendiliğinden yapmıyor), süreç sınırları
  (timeout/fork/çıktı/FD), platform başına profil, CI'da kanıt testleri.
  Operasyonel gerçek: filo bugün macOS üzerinde çalışıyor (bu değerlendirme
  dahil; observer henüz hiçbir runtime'a bağlı değil, ilk gerçekçi koşum
  ortamı da macOS'tur). Yani seçenek 2'nin birincil sınırı, tam da
  çalışılan platformda ancak mikro-VM/uzak Linux ile kurulabilir — bu ek bir
  işletme katmanıdır ve gözlemciyi "yerelde ucuz bir tur" olmaktan çıkarır.
- **Sinyal kaybı:** Yok.

### Seçenek 3 — Git'i hiç çağırmamak: index + stat + obje okuma saf Python'da

Subprocess, config-exec anahtarları, filter/hook/textconv yürütmesi ve git
keşif yönlendirmeleri **sınıf olarak** kapanır: düşman depo artık bir yürütme
bağlamı değil, yalnız **parse edilen bayt dizisi**dir. Kalan yüzey: saf-Python
parser'a düşman girdi (bellek-güvenli; DoS boyut/zaman tavanı + fail-closed
ile sınırlanır) ve TOCTOU (kalır — hiçbir seçenek çözmüyor).

Bileşen bileşen maliyet (sinyal → gereken parça):

| Parça | Bugün | Seçenek 3'te | Maliyet ölçüsü |
|-------|-------|--------------|----------------|
| Index okuma (`ls-files --stage` yerine) | git | stdlib parser | **Küçük — ölçüldü** (§3.2: ~90 satır, v2 birebir). v3/v4/split/sparse fail-closed reddedilir |
| Modified tespiti (index oid vs çalışma ağacı) | **zaten saf Python** (`_raw_worktree_blob`) | değişmez | Sıfır — #832 bunu clean-filter kaçınması için zaten yazdı |
| Untracked (`ls-files --others`) | git | dizin yürüyüşü + **ignore motoru** | **Asıl bakım yükü burada.** `.gitignore` semantiği küçümsenemez; yaklaşıklama S1/S2'ye gürültü taşır. Hazır saf-Python: `pathspec` (gitwildmatch) veya dulwich |
| Committed diff (`base..HEAD`) | git | commit/tree walk → loose + **pack** okuma (delta çözümü dahil) | Homegrown pahalı; dulwich'te var. Not: `git fetch <düşman-yol>` ile güvenilir clone'a kaçış **yoktur** — fetch, upload-pack'i düşman depo bağlamında çalıştırır (`uploadpack.packObjectsHook`). Push edilmemiş yerel commit'ler için düşman obje deposu Python'da okunmak zorundadır |

- **Güvenlik yüzeyi:** yukarıda. Ek not: mevcut jail'in yol-hapsi mantığı
  (onaylı kök, symlink çözümü) aynen gerekli kalır — değişen şey, hapsin
  içinde artık kod çalıştırılmamasıdır.
- **Bakım maliyeti:** format sürümü takibi (filo v2 yazıyor, `index.version`
  ayarsız; git varsayılanı değişirse parser skip üretir, sessizce yanlış
  okumaz) + ignore/pack için **bağımlılık kararı**: dulwich olgun, saf Python
  bir git gerçeklemesidir ve "git davranışını yeniden yazmak" itirazını
  büyük ölçüde cevaplar; karşılığı tedarik zinciri yüzeyidir. Bu ayrı bir
  alt karardır (§7).
- **Sinyal kaybı:** dulwich'li tam gerçeklemede yok. Stdlib-only ara adımda
  untracked yaklaşık (gürültü riski) ve committed diff eksik kalır; eksik
  parça skip kaydıyla görünür kılınır, "temiz" diye raporlanmaz.

## 5. Karşılaştırma özeti

| Eksen | 1 — Statüko | 2 — Sandbox | 3 — Git'siz |
|-------|-------------|-------------|-------------|
| Kök içi düşman depo kodu | Bilinen yollar kodda kapalı ve pinli (sözleşme §1.1); sayım garantisi yok — gözden kaçan yol observer yetkisiyle koşar (§3.1 `direct`) | Koşar, eli boş — yalnız Linux'ta ölçülü; **macOS'ta birincil sınır kurulamadı** (ölçüldü §3.1) | **Koşmaz** — subprocess yok |
| Yönlendirme sayım problemi | Açık (5 ilkel / 8 tur, yakınsamadı) | Önemsizleşir (ro-bind allowlist) — macOS hariç | Sınıf olarak kapanır |
| macOS (fiili platform) | Çalışır | Birincil sınır için mikro-VM/Linux şart | Çalışır |
| TOCTOU | Açık | Açık | Açık |
| Bakım | 966 + 1.226 satır; git sürüm yüzeyi sürekli izlenir | Launcher + profil + CI kanıtı + mikro-VM işletmesi | Parser (index parçası ölçüldü: küçük); ignore + pack için dulwich/pathspec bağımlılık kararı |
| Sinyal kaybı | Yok | Yok | dulwich ile yok; stdlib-only ara adımda untracked yaklaşık |
| Ölçüm durumu | #832 tablosu + §3.1 `direct` | #838 v0.1 + §3.1 macOS teyidi; Linux S4 zayıf kanıt | §3.2 index ölçüldü; ignore/pack ölçülmedi |

## 6. Değerlendirme sonucu (teknik öneri — kurucu tarafından §0 ile kabul edildi)

Teknik öneri **Seçenek 3'e yönelmekti**, kademeli ve mevcut jail'i koruyarak:

1. Tehdit modelinin ağırlık merkezi, sekiz turun sonunda "kök dışına kaçış"tan
   "**kök içi düşman depo**"ya kaymıştır. Statüko bilinen yürütme yollarını
   kodda kapatmıştır (sözleşme §1.1) ama bu, dışarıdan sayılamayan bir yüzeyin
   nokta nokta kapatılmasıdır — garanti sayım yoktur; sandbox'ın cevabı ise
   fiili platformda (macOS) kurulamayan bir sınırdır (ölçüldü §3.1).
2. Seçenek 3 açık kalan yüzeyi "düşman bağlamda kod yürütme"den "düşman veriyi
   parse etme"ye indirger; bu, bu kod tabanının zaten iyi yaptığı, fail-closed
   test edilebilir bir iş sınıfıdır (`read_claims`, `_raw_worktree_blob`,
   `last_event_times` aynı desendir).
3. En belirsiz görünen parça (index) ölçüldü ve küçük çıktı (§3.2); büyük
   parçalar (ignore, pack) için olgun saf-Python gerçekleme mevcut, ama bir
   bağımlılık kararı gerektiriyor.

Sandbox reddedilmiş sayılmaz: Linux'ta koşan her observer için `bwrap`
**derinlik katmanı** olarak ucuzdur ve v0.1 sözleşmesindeki launcher
zorunlulukları (env temizliği, süreç sınırları) Seçenek 3'te bile geçerli
kalır — subprocess kalksa da observer sürecinin kendisi düşük yetkiyle
koşmalıdır. Bu öneri, §0'daki kurucu kararıyla aynı gün ve aynı sınırlarla
kabul edilmiştir.

## 7. Karar kapısı — kapanış (2026-09-21)

- Eski "A — sandbox birincil sınır" kararı bu ADR ile **superseded**; birincil
  yön **Seçenek 3**. Bu ADR kod izni değildir; her geçiş dilimi ayrı
  yetkilendirilir.
- #832 kodu, testleri ve mevcut sözleşmeler bu ADR ile değişmez; sekiz turun
  jail'i geçiş boyunca ve kalan git çağrılarında defense-in-depth olarak
  yerinde kalır.
- Bekleyen alt kararlar: dulwich/pathspec bağımlılığı (ayrı alt ADR);
  geçiş dilimlerinin sırası ve kapsamı (ilk aday: index okuma — §3.2'de
  ölçülen parça); Linux `bwrap` derinlik katmanının hangi hostlarda
  kurulacağı (yeniden ölçüm şartıyla).
- Dokunulmayacaklar: `src/lumos_board/wall_observer.py`,
  `tests/test_wall_observer.py`, mevcut sözleşmeler — bu commit docs-only'dir.

## 8. Bilinçli yapılmayan

- Kod, sözleşme değişikliği, bağımlılık ekleme, runtime wiring — yok.
- Linux `bwrap` yeniden ölçümü — bu host macOS; v0.1 kaydına ve oradaki
  zayıf-kanıt notuna atıf yapıldı, "kanıtlandı" denmedi.
- Silinen sözleşme/ADR'nin main'e geri getirilmesi — Devpost revert'inin
  kapsam kararıdır, bu görevin değil.
