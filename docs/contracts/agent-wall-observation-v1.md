<!-- markdownlint-disable MD013 -->

# Lumos Agent Wall Observation v1

Durum: sözleşme — Faz-1 uygulandı (`src/lumos_board/wall_observer.py`, PR #832 · MERGED · f3fffc79 · GitHub API · 2026-09-21T11:45Z).

## 0. Kayıt geçmişi ve otorite (2026-09-21)

Bu dosyanın yayın geçmişi düz değildir; hangi kaydın güncel otorite olduğu burada açıkça yazılır:

- Sözleşme #831 ile eklendi (`0bdcc47f`), 2026-09-05'te sandbox notuyla güncellendi (`708d112a`).
- Devpost geri-alma commit'i (`73d6f58d`, 2026-09-11) — Devpost/OpenAI'nin "yalnız #829/#830 kalsın" izni gereği — bu dosyayı, `agent-wall-observer-sandbox-v0.md`'yi ve o günkü `ADR-033-agent-wall-observer-sandbox.md`'yi `main`'den sildi.
- #832 (uygulama) bu silmeden **sonra** merge edildi; `main`'de sözleşmesiz bir uygulama kaldı. Bu restorasyon, #832 gövdesinin söz verdiği "separate docs-only PR"dır.
- 2026-09-05 sandbox notu ("birincil sınır sandbox'tır; #832 sandbox MVP'siz merge adayı değildir") **geri getirilmedi**: fiilen merge edilen sınır aşağıda §1.1'de tanımlanan `allowed_roots` jail'idir ve `ADR-033` numarası bu arada başka bir karara (Account Activity Correlation) verildi. Gözlemcinin yürütme bağlamı mimarisi (sandbox / git'siz okuma / mevcut jail) ayrı bir ADR değerlendirmesinde sürüyor (ADR-034 taslak süreci, board claim `WALL-OBS-ARCH-EVAL`); o karar bu sözleşmeyi değiştirirse buradan güncellenir.
- **PR #832 gövdesi tarihî kayıttır ve yerinde durur.** Gövdenin yedinci tur bölümü, repo-local `filter.<name>.clean` sürücülerinin gözlemci sürecinde çalışmasını "kapatılamaz, kalan risk" diye anlatır; o anlatım `e26d8c13` ve sonrası ile **koddaki gerçekliğin gerisinde kalmıştır** (ayrıntı §1.1). Güncel davranışın otoriter kaydı bu dosyadır.

Agent Wall bugün çakışma önleyicidir: [`task-claim-v1`](task-claim-v1.md) yazma başlamadan sahipliği ayırır, [`agent-status-v2`](agent-status-v2.md) kim ne yapıyor sorusunu gösterir. İkisi de **beyana** dayanır. Bu sözleşme üçüncü bir soruyu tanımlar: *beyan ile fiilen olan aynı mı?*

Gözlem katmanı **salt-okunurdur**. Hiçbir claim'i değiştirmez, hiçbir ajanı durdurmaz, hiçbir yazmayı engellemez.

## 1. Güven modeli — neden türetilmiş sinyal

Bu sözleşmenin tek belirleyici kararı budur.

[`TD-10`](../TECHNICAL_DEBT.md) kayıtlı: claim kimlikleri self-asserted, *"kötü niyetli ajan sahte kimlik beyan edebilir"*. Aynı sınır `agent_status_*.json` için de geçerlidir — sapan bir ajan kendi durum dosyasında da yanlış yazabilir.

Bu yüzden sinyaller ikiye ayrılır:

| Sınıf | Kaynak | Gözlemde kullanımı |
| --- | --- | --- |
| **Beyan** | `agent_status_*.json`, claim'in kendi `status` alanı | Yalnız bağlam. Tespit dayanağı **değildir**. |
| **Türetilmiş** | git geçmişi, çalışma ağacı durumu, `claim_events.jsonl` (append-only + fsync), dosya mtime | Tespit **yalnız** buna dayanır. |

Beyana dayanan bir gözlem katmanı yalnız dürüst ajanları izler; onlar zaten sorun değildir.

**Bu katman ajan kimliğini doğrulamaz.** TD-10 açık kalır. Gözlem, kimliğin doğru olduğunu varsaymaz — yalnız *bir claim ile bir etkinin uyuşup uyuşmadığını* söyler.

### 1.1 Beyan edilen yol güvenilir yürütme bağlamı DEĞİLDİR (ek, 2026-09-21)

§1'in ilk yazımı beyanın *tespit dayanağı* olamayacağını söylüyordu ama bir katman aşağısını açık bırakıyordu: beyan, **nerede kod çalışacağını da seçemez**. #832'nin en ciddi bulgusu tam bu boşlukta büyüdü — `claim.worktree` alanı `git`'e `cwd` olarak verildi ve düşman bir depo `core.fsmonitor`/`diff.external` ile gözlemci sürecinde komut çalıştırabildi (confused deputy; PR kayıtlarında üretilmiş kanıtla). Bu ek, o dersin sözleşme hükmüdür:

1. **Claim verisi yalnız *neyin* inceleneceğini önerebilir; *nerede ve neyle* inceleneceğini asla seçemez.** İnceleme bağlamı (`allowed_roots`) gözlemciyi başlatan operatörden gelir, hiçbir zaman claim'den gelmez. Kök tanımlı değilse hiçbir şey incelenemez — fail-closed.
2. **Jail depoyu da kapsar, dizini değil yalnız.** Worktree symlink'leriyle birlikte strict çözülür; git'in fiilen açacağı depo ayrıca çözülür ve o da köklerin içinde olmak zorundadır: gitfile zinciri (adım sınırıyla, her adım denetimli), bağlı worktree'nin `commondir`'i, nesne deposu ve `objects/info/alternates` girdileri, `$GIT_DIR/index` ve `sharedindex.*` dosyaları. Komutlar `--git-dir`/`--work-tree` sabitlenmiş, `GIT_*` miras almayan allowlist ortamda koşar. Reddedilen claim'de git **hiç çağrılmaz**, claim kendi adını taşıyan gerekçeyle atlanır ve kök dışı hiçbir yol günceye yazılmaz (yazmak başlı başına sızıntı olurdu).
3. **Çalışma ağacını hash'leyen git komutları kullanılmaz.** `status` / `diff-files` / `ls-files -m` ailesi, repo-local `filter.<name>.clean` ve `filter.<name>.process` sürücülerini çalıştırır ve bu sürücüler adı saldırgan seçtiği için wildcard ile kapatılamaz. Bu yüzden commit'lenmemiş etki git'e içerik hash'lettirmeden okunur: `diff --cached --no-ext-diff --no-textconv`, `ls-files --others`, `ls-files --stage` + index blob kimliğinin **git dışında** ham dosya içeriğiyle karşılaştırılması (`_raw_worktree_blob`; symlink/FIFO takip edilmez). Repo-local filtre sürücüleri gözlemci sürecinde hiçbir aşamada çalışmaz.
4. **Bu davranış testle sabitlenmiştir:** `tests/test_wall_observer.py` içinde `test_in_root_filters_never_execute` (clean + process, kök İÇİNDEKİ depo için) ve `test_filter_from_include_and_info_attributes_never_runs` (`include.path` + `info/attributes` yolu). Bu testler gerçek bir sürücü diker ve marker dosyasının **oluşmadığını** doğrular.

**Yerine geçme notu:** PR #832 gövdesinin "Residual risk, documented rather than claimed closed" bölümü ve o günkü pin testi (`test_in_root_clean_filter_still_executes_documented_residual_risk`) bu yolun kapatılamayacağını, operasyonel mitigasyonla yaşanacağını kaydediyordu. `e26d8c13` ve devamı yolu **kodda** kapattı; eski test adı artık yoktur, yerini yukarıdaki iki test aldı. O tarihteki ölçüm o tarih için doğruydu; bugünkü doğru, bu maddedir.

**Kapatmanın kapatMAdıkları** — kalan riskin doğru adları (bunlar filtre bulgusunun devamı değildir, jail'in koruma İDDİASININ sınırlarıdır):

- **Onaylı kök içindeki düşman depo, jail'in koruma iddiası dışındadır.** `allowed_roots` gözlem işe yarasın diye ajan-yazılabilir worktree'leri içermek zorundadır; kök içindeki bir depo kendi git verisini (geçmiş, index, claim güncesine düşecek yol adları) istediği gibi şekillendirebilir (§5 son madde) ve git'in depo keşfindeki yönlendirme ilkellerinin (gitfile → commondir → zincir → nesne deposu → index; dört turda dört ilkel) **tam sayıldığı kanıtlanmamıştır**. "Yeni bulgu yok", "küme kapandı" demek değildir.
- **Eşzamanlı mutasyona karşı izolasyon yoktur (TOCTOU).** Jail denetimi ile okuma ayrı sistem çağrılarıdır; aradaki anda depoyu değiştirebilen bir süreç denetlenen ile okunanı ayrıştırabilir. Gözlemci bir işletim sistemi sandbox'ı değildir ve öyle tanıtılamaz.
- **Bu yüzden yetki kuralı normatiftir, tavsiye değil:** gözlemci, izlediği ajanlardan **fazla yetkiyle çalıştırılmaz** — ayrı, düşük yetkili kimlik; operatör kimlik bilgisi yok, kendi güncesi dışında yazma yetkisi yok, ağ erişimi yok. Modül docstring'i bu kuralı taşır; bu sözleşme onu bağlayıcı kılar.

## 2. Faz-1 kapsamı: üç sinyal

Üçü de bugün main'de var olan veriden türetilir. Yeni emisyon, yeni ajan enstrümantasyonu, koşum yoluna müdahale **yoktur**.

### S1 — Kapsam dışı dokunuş

`claim.scopes` (beyan edilen repo-relative kapsamlar) ile dalın/çalışma ağacının fiilen dokunduğu dosyalar karşılaştırılır. Karşılaştırma aynı `repo` içindeki claim'lerle yapılır; paylaşılan board'da başka reponun kapsamı ihlal sayılmaz.

İki ayrı bulgu üretir; ağırlıkları farklıdır:

- `OUT_OF_SCOPE` — dokunulan yol hiçbir aktif claim kapsamında değil.
- `FOREIGN_SCOPE` — dokunulan yol **başka** bir `ACTIVE` claim'in kapsamında. Anayasa §3 ihlali adayıdır ve daha ağırdır.

Bu, §3'ün (*"bir dosyanın aynı anda yalnızca bir sahibi vardır"*) bugün yazılı norm olan hâlini ölçülebilir yapar.

### S2 — Sessiz sapma

Claim'in `task_id`'si bir işi söylerken dokunulan dosya kümesi başka bir işi anlatıyorsa bulgu üretilir. S1'in üstünde çalışır: kapsam dışı dokunuşların tek bir tutarlı başka işe (tek üst dizine, eşik `DRIFT_MIN_PATHS`) kümelenmesi sapma göstergesidir.

Bunun gerçek bir örneği kayıtlıdır: `claude/console-lock-ast` dalında, claim'in söylediğinden farklı bir iş (retention süpürücüsü) yazıldı ve **10 gün commit edilmeden durdu**; ancak elle tarama ile bulundu (PR #827; o günkü TD-29 kaydı Devpost geri-almasında silindi). Bu sinyal onu ilk gün görünür kılardı.

### S3 — Ritim ve asılı claim

`claim_events.jsonl` zaman damgalarından türetilir:

- `heartbeat_at` ile `expires_at` arasındaki sapma
- TTL aşımı (`EXPIRED` olması gerekirken `ACTIVE` görünen)
- uzun süre `ACTIVE` olup hiç olay üretmeyen claim

"Ajan çalışıyor mu, asılı mı" sorusunu ajanın kendi beyanına sormadan cevaplar.

## 3. Kapsam dışı — Faz-1'de yok

| Konu | Neden Faz-1'de değil |
| --- | --- |
| Anormal çağrı oranı | Ajan başına araç/çağrı sayacı **bugün yok**. `claim_events` claim yaşam döngüsünü sayar, iş hacmini değil. Yeni emisyon kararı gerekir. |
| Ajan başına bütçe / limit | `owner` bazlı bütçe kaydı yok; hacim ölçülmeden anlamsızdır. |
| Beklenmeyen hedefe erişim (egress) | Kısmi bir mekanizma **zaten çalışıyor**: pytest `test provenance` bloğu gerçek egress host'larını raporluyor. Sıfırdan yazılmaz, genişletilir — ayrı dilim. |
| Kontrol / engelleme | Bilinçli. Ölçülmemiş bir sinyalle kapı koymak, yanlış pozitifte çalışan ajanı durdurur. |
| Ajan kimliğinin doğrulanması | TD-10'un konusu. |
| `wall.py` (#807) entegrasyonu | Bağımlılık ters yönde kurulmaz; #807 merge olursa bu okuyucu onun altına girer. |

## 4. Çıktı: ayrı gözlem güncesi

Gözlem çıktısı **`.lumos/logs/wall_observations.jsonl`** dosyasına yazılır.

`evidence_continuity` hattına **bağlanmaz**. Gerekçe: o hattın payload'ı bilinçli olarak dar bir allowlist ile sınırlıdır (`src/core/evidence_continuity.py`), sapma bulgusu için gereken alanları taşıyamaz; ayrıca gözlem kaydının kendi yaşam döngüsü ve saklama kararı ayrı olmalıdır.

Şema: `lumos.agent_wall_observation.v1`

Zorunlu alanlar:

- `schema`, `at` (UTC, ISO-8601)
- `signal` — `OUT_OF_SCOPE` | `FOREIGN_SCOPE` | `SILENT_DRIFT` | `STALE_CLAIM`
- `claim_id`, `task_id`, `repo`, `owner` — gözlenen claim'den
- `evidence` — bulgunun **türetildiği** kanıt: dalda dokunulan yollar, olay zaman damgaları, karşılaştırılan kapsam
- `derived_from` — hangi kaynaklardan türetildiği (`git`, `claim_events`, `claim_store`); beyan kaynağı kullanıldıysa açıkça `agent_status` yazılır

Kurallar:

1. Kayıt **append-only**; gözlemci hiçbir satırı geri dönüp değiştirmez.
2. Dosya yolları repo-relative yazılır; mutlak yol ve makine yolu kaydedilmez. Jail'in reddettiği claim için **hiçbir yol** kaydedilmez; skip kaydı yalnız kendi gerekçesini taşır (§1.1).
3. Serbest metin `mask_secretlike` (`src/lumos_board/agent_status.py`) ile kayıt sınırında maskelenir; sapma raporu sır sızdıramaz.
4. Gözlemci claim store'a, `agent_status_*.json`'a veya çalışma ağaçlarına **yazmaz**. (`TaskClaimStore.list_claims()` bu yüzden kullanılmaz: o çağrı yazar ve kilit tutar; `claims.json` kilitsiz, doğrudan okunur.)
5. Bir bulgu, üretildiği kanıt olmadan kaydedilmez — `evidence` boş olamaz.
6. Başarısız git okuması "temiz" değildir: okunamayan kısım `git_read_failed:<komutlar>` gerekçesiyle kayda düşer, okunabilen kısmi kanıt yine sinyal üretir.

## 5. Bu sözleşmenin vermediği garantiler

- **Tam kapsama değildir.** Commit edilmemiş ve hiç git etkisine düşmemiş etki (ör. repo dışına yazma) görülmez.
- **Gerçek zamanlı değildir.** Gözlem periyodik okumadır; sapma anında değil, sonraki okumada görünür. Okumalar arasında depoyu değiştirebilen süreçlere karşı izolasyon yoktur (§1.1).
- **Yanlış pozitif üretir.** Meşru ama claim'de beyan edilmemiş dokunuşlar `OUT_OF_SCOPE` sayılır. Ayrıca içerik karşılaştırması ham blob üzerinden yapıldığı için filtre/CRLF dönüşümü kullanan dosyalar ihtiyatlı biçimde "değişmiş" sayılabilir — bilinçli tercih: yanlış tarafta hata, güvenilmeyen dönüşümü çalıştırmaktan iyidir. Faz-1'in amacı bu oranı **ölçmektir**; kapı koymak değil.
- **Kötü niyetli ajana karşı tam değildir.** Git geçmişini ve claim güncesini üretebilen bir aktör sinyali de şekillendirebilir. Bu katman gizli düşmana karşı değil, **sessiz sapmaya** karşıdır. Onaylı kök içindeki düşman deponun sınırları §1.1'de adlandırılmıştır.
