# Dashboard health sözleşmesi — v1

| Alan | Değer |
| --- | --- |
| Durum | SÖZLEŞME — yalnız sözlük, freshness, türetme ve kabul kriterleri; **ürün kodu yok** |
| Üst sözleşme | [ADR-029](../decisions/ADR-029-dashboard-health-earned-responsibility.md) (izle / düzelt / yükselt). Bu belge merdivenin **state** basamağıdır; alan henüz Lumos’a devredilmez |
| Kapsam | Panel/dashboard kartlarının sağlık **durumu**: beş literal, freshness, backend→durum türetme, semantik UI eşlemesi |
| Kod karşılığı | **Henüz yok.** Uygulama ayrı dilimde açılır; o dilim bu belgeyi kaynak alır |
| Kaynak gerçeği | Sözleşme ile kod ayrışırsa **kod esastır**; ayrışma borç sayılır ([agent-status-v1](agent-status-v1.md) ile aynı kural) |
| Faz | FAZ-1 · Panel. Yeni sayfa / vitrin / TD-13 bağlama / TD-14 yok |
| Aday | `#768` modeli (`not_configured / unknown / healthy / failed / stale`); kurucu kilidi: TTL **provisional**, ölçülmeyen **yeşil olmaz** |

Bu belge, kullanıcının panelde gördüğü sağlık göstergelerinin **ne anlama
geldiğini** sabitler. Amaç yeni bir özellik veya vitrin eklemek değil: panel
bugün sağlık iddiasında bulunuyor ama bu iddianın arkasında ölçüm yok.
Sözleşme, ölçüm ile gösterge arasındaki bağı tanımlar.

**Başarı kriteri (alan devri değil):** “dashboard düzeldi” değil.
Lumos bu alanı gerçekten üstlenebilecek kadar **gözlemleyebiliyor, sınırını
biliyor ve kanıt üretebiliyor.** O kanıt çıkınca sorumluluk kazanılır; bu
belge o kanıtın sözlüğünü kilitler.

## Neden şimdi — bugünkü gerçek (koddan doğrulanmış, 2026-08-20)

| Kaynak | Ürettiği durum | UI'a bağlı mı? |
| --- | --- | --- |
| [`api/bridge/health.js`](../../api/bridge/health.js) | `200 {status:"ok"}` / `503 {status:"unconfigured"}` + `llm`, `mode`, `model` | ❌ **hiçbir UI çağırmıyor** |
| [`api/integrations/meta/connections.js`](../../api/integrations/meta/connections.js) `statusFor()` | `authorized` / `expired` | ✅ tek canlı bağ |
| `ui/src/pages/panel.astro` — **18 nav rozeti** | `--ready` / `--off` / `--active` / `--awaiting` / `--developing` / `--layers` → 🟢 Hazır · ⚪ Kapalı · 🛡️ Aktif | ⚠️ **statik markup**; hiçbir `.ts`/`.js` bunları güncellemiyor |
| `src/integrations/providers/*` (14 sağlayıcı) | `*_not_configured` hata kodları | ❌ UI'a hiç çıkmıyor |
| `src/core/health_check.py` | `ready` / `warning` | ❌ web yüzeyine bağlı değil |

Özet: `not_configured / unknown / healthy / failed / stale` beşlisi kodda
**sıfır** kez geçiyor. Panelde görünen 18 rozetin hiçbiri ölçüm sonucu değil;
elle yazılmış yol haritası etiketleri. Freshness kavramı hiç yok.

**Dürüst sonuç:** bu bir refactor değil, sıfırdan sözleşme + bağlama işi.

## Kapsam dışı (bilinçli, v1)

- **Layer 1-A'ya dokunulmaz.** (Kurucu tarafından konan sınır; bu repoda yazılı
  tanımı yok — burada tanımlanmaya da çalışılmıyor.)
- Ürün kodu bu PR'da değişmez: `panel.astro`, `api/*`, sağlayıcılar aynen kalır.
- Push/WebSocket/SSE ile gerçek zamanlı sağlık yok; v1 poll tabanlı.
- Geçmişe dönük sağlık grafiği, uptime yüzdesi, alarm/bildirim yok.
- Yeni sağlık ucu **tasarlanmaz**; v1 yalnız var olan uçlardan türetir.
- TD-13 CSS/hero bağlanmaz. TD-14 (first-audio / port) bu işe karışmaz.
- UI makyajı yok; §5 yalnız semantik eşlemedir, tasarım turu değildir.

## 1. Durum sözlüğü — beş literal

Bu beş değer **kapalı bir sözlüktür**. Kart durumu başka bir değer alamaz.

### `not_configured`
Lumos bu yeteneği çalıştıracak yapılandırmaya **sahip değil**. Eksik olan
yapılandırmadır; kırık olan bir şey yoktur. **Hata değildir.**
Kullanıcı/operatör eylemi gerektirir. Bu durumu söylemek için bir çağrı
denemeye gerek yoktur — yapılandırmanın yokluğu tek başına kanıttır.

### `unknown`
Lumos **henüz bakmadı**, ya da baktı fakat sonucu öğrenemedi. Yapılandırmanın
var olup olmadığı da bilinmiyor olabilir. Bu bir **bilgi yokluğudur**, olumsuz
bir sonuç değildir. İlk yükleme, süren probe, sonuçsuz kalan kontrol, yetkisiz
oturum — hepsi buraya düşer.

### `healthy`
En son yapılan **gerçek kontrol** olumlu sonuçlandı ve sonuç hâlâ **taze**
(freshness bütçesi içinde).

### `failed`
En son yapılan **gerçek kontrol** yapıldı ve **olumsuz** sonuçlandı.
Yapılandırma var, ama çalışmıyor. (Süresi dolmuş token, 5xx, reddedilen probe.)

### `stale`
Geçmişte gerçek bir sonuç alındı, fakat **freshness bütçesi aşıldı**. O sonucun
hâlâ geçerli olduğu garanti edilemez. `stale`, en son bilinen sonucu
**yok etmez** — `last_known` alanında taşır.

### Ayırt edici tablo (uygulama testi bunun üzerinden yazılır)

| Soru | `not_configured` | `unknown` | `healthy` | `failed` | `stale` |
| --- | --- | --- | --- | --- | --- |
| Yapılandırma var mı? | Hayır | **Bilinmiyor** | Evet | Evet | Evet |
| Gerçek kontrol yapıldı mı? | Gerekmez | Hayır / sonuçsuz | Evet | Evet | Evet (geçmişte) |
| Sonuç | — | — | Olumlu | Olumsuz | Olumlu/olumsuz, **bayat** |
| `checked_at` | `null` | `null` | dolu | dolu | dolu (geçmiş) |
| Kullanıcı eylemi | Kur | Kontrol et | — | Onar | Kontrol et |

`unknown ≠ failed ≠ not_configured` — üçü de "yeşil değil" diye tek kovaya
konamaz. Bunlar kullanıcıya **üç farklı şey** söyler: *bilmiyoruz* /
*kurulmamış* / *kırık*.

## 2. Kart yükü (payload)

```json
{
  "id": "bridge.llm",
  "state": "healthy",
  "checked_at": "2026-08-20T08:31:04Z",
  "ttl_seconds": 120,
  "last_known": null,
  "reason_code": null,
  "evidence": "GET /api/bridge/health → 200"
}
```

| Alan | Tip | Zorunlu | Anlam |
| --- | --- | --- | --- |
| `id` | str | Evet | Kart kimliği; kararlı, çeviriye tabi değil |
| `state` | str | Evet | Beş literalden biri |
| `checked_at` | ISO 8601 \| `null` | Evet | Gerçek probe'un **tamamlandığı** an. Bilinmiyorsa `null`; **uydurulmaz** |
| `ttl_seconds` | int | Evet | Bu kartın freshness bütçesi |
| `last_known` | `"healthy"` \| `"failed"` \| `null` | Evet | Yalnız `state="stale"` iken anlamlı; diğer durumlarda `null` |
| `reason_code` | str \| `null` | Evet | Makine okunur sebep; çeviri anahtarı değil, log/teşhis için |
| `evidence` | str | Evet | Bu durumu hangi kontrol üretti (uç + sonuç) |

`checked_at`/`last_known` için `null` disiplini [agent-status-v1](agent-status-v1.md)
precedent'ini izler: *"bilinmiyorsa `null`, uydurulmaz"*.

## 3. Freshness kuralları

1. `age = now − checked_at`. `age > ttl_seconds` → durum **`stale`** olur,
   `last_known` o ana kadarki `healthy`/`failed` değerini taşır.
2. **`checked_at = null` gerçek bir durumdur.** "Hiç kontrol edilmedi"
   demektir. Yalnız `not_configured` veya `unknown` ile birleşebilir.
   `healthy`/`failed`/`stale` **asla** `null` `checked_at` ile görünmez.
3. **Sahte timestamp yasak.** `checked_at` yalnız probe'un tamamlandığı andır.
   Sayfa yüklenme anı, render anı, cache yazma anı, `now()` varsayılanı —
   hiçbiri `checked_at` değildir. Boşsa `null` kalır.
4. `null` `checked_at` **hiçbir koşulda** göreli zaman metnine çevrilmez.
   "0 dakika önce", "az önce", "şimdi" yazılmaz.
5. TTL tek kaynaktan gelir, kart tarafında sabit yazılmaz.

### v1 TTL — **provisional defaults**, kesin gerçek değil

`60 / 120 / 300` ölçülmüş SLO değildir. Canlı kanıt yokken seçilmiş **geçici
varsayılanlardır.** Değişmeleri sözleşme ihlali sayılmaz; tek kaynaktan
gelmeleri ve aşağıdakini ihlal etmemeleri gerekir.

| Kart sınıfı | `ttl_seconds` (provisional) | Neden bu mertebe (kanıt değil, gerekçe) |
| --- | --- | --- |
| Oturum/kimlik | 60 | Kullanıcı en hızlı burada etkilenir |
| LLM köprüsü | 120 | Board projeksiyonundaki `stale_after_seconds=120.0` ile hizalı |
| Dış entegrasyon bağlantıları | 300 | Dış servis kotasını yakmamak için |

TTL’yi “doğru” kılmak v1 kabul kriteri **değildir.** Freshness kuralı
(`age > ttl` → `stale`, `last_known` korunur) bağlayıcıdır; sayıların
kendisi değil.

## 4. Backend → durum türetme

Sözleşmenin çekirdeği. Solda bugün gerçekten var olan gözlem, sağda tek geçerli
karşılık.

| Kaynak | Gözlem | `state` | `reason_code` |
| --- | --- | --- | --- |
| `api/bridge/health.js` | `200 {status:"ok"}` | `healthy` | — |
| | `503 {status:"unconfigured"}` | `not_configured` | `unconfigured` |
| | `401` | *(kart durumu değil — bkz. §6)* | `unauthorized` |
| | ağ hatası / zaman aşımı | `unknown` | `probe_unreachable` |
| | hiç çağrılmadı | `unknown`, `checked_at=null` | `not_checked` |
| `api/integrations/meta/connections.js` | `status:"authorized"` | `healthy` | — |
| | `status:"expired"` | `failed` | `token_expired` |
| | bağlantı kaydı yok | `not_configured` | `no_connection` |
| | `401` | *(kart durumu değil — bkz. §6)* | `unauthorized` |
| `src/integrations/providers/*` | `*_not_configured` | `not_configured` | ilgili hata kodu |
| **her kart** | `age > ttl_seconds` | `stale` (+ `last_known`) | `freshness_expired` |
| **her kart** | sözlük dışı/çözümlenemeyen değer | `unknown` | `unmapped_value` |

Son satır [agent-status-v1](agent-status-v1.md) kuralını izler: *"sözlük dışıysa
`unknown`"*. Beklenmeyen bir değer **asla** `healthy` sayılmaz.

**Ölçülmeyen → `healthy` yok.** Statik markup, hiç çağrılmamış uç,
`checked_at=null`, `unmapped_value`, `401`/`unknown` yolları yeşil
üretemez. Bu, TTL sayılarından bağımsız **tartışmasız invariant**tır.

## 5. UI karşılığı

Her durumun **kendi** görsel kimliği vardır. İki durum aynı rozeti, aynı rengi
veya aynı erişilebilir etiketi paylaşamaz.

| `state` | Rozet | Renk rolü | Kullanıcı metni (TR) | Eylem |
| --- | --- | --- | --- | --- |
| `not_configured` | ⚪ Kurulmadı | nötr | "Henüz kurulmadı" | **Kur** |
| `unknown` | ◌ Bilinmiyor | nötr-ikincil (⚪'dan **farklı**) | "Durum bilinmiyor" | **Kontrol et** |
| `healthy` | 🟢 Çalışıyor | olumlu | "Çalışıyor · *n* dk önce kontrol edildi" | — |
| `failed` | 🔴 Çalışmıyor | olumsuz | "Çalışmıyor — *sebep*" | **Yeniden dene** |
| `stale` | 🟡 Doğrulanmadı | uyarı | "*n* dakikadır doğrulanmadı (son bilinen: *çalışıyor/çalışmıyor*)" | **Kontrol et** |

**En olası ihlal:** `not_configured` ile `unknown` ikisi de "gri/boş" hissi
verdiği için aynı rozete indirgenir. Bu yasaktır — kullanıcıya *"kurmadın"* ile
*"bilmiyoruz"* aynı şey değildir. Farklı glif **ve** farklı erişilebilir etiket
zorunludur; yalnız renk tonu farkı yeterli değildir.

`checked_at = null` iken metin daima "hiç kontrol edilmedi"dir; göreli zaman
ifadesi kurulmaz.

## 6. Başlık / oturum durumu — kartlardan türetilmez

- Global başlık (oturum, hosted/yerel kip, bağlantı) **kendi kaynağından**
  beslenir: `api/auth/session` ve barındırma kipi. Kart sağlıkları bu hesaba
  **girmez**.
- Bir kart `failed` diye başlıkta "Lumos çevrimdışı" **denmez**.
- Başlık sağlıklı diye kartlar `healthy` **varsayılmaz**.
- Kartların hiçbir toplamı (sayı, oran, "3/5 sağlıklı") global bir sağlık
  hükmüne dönüştürülmez.
- **Türetilen kural:** oturum yoksa/`401` ise bütün kartlar `unknown` olur —
  `failed` **olmaz**. Yetkisiz oturum, entegrasyonun kırık olduğunu değil,
  Lumos'un bakamadığını gösterir.

## 7. Ad alanı ayrımı — `agent-status-v1` ile karışmaz

[agent-status-v1](agent-status-v1.md) `failed` ve `unknown` kelimelerini zaten
kullanıyor. **Aynı kelimeler, farklı özne:**

| | agent-status-v1 | dashboard-health-v1 |
| --- | --- | --- |
| Özne | Bir **iş** (job) | Bir **yeteneğin erişilebilirliği** |
| Sözlük | `running` / `completed` / `failed` / `unknown` | `not_configured` / `unknown` / `healthy` / `failed` / `stale` |
| `stale` | Projeksiyonda **ayrı boolean** (`stale_after_seconds=120.0`) | Görüntülenen **durumun kendisi** (+ `last_known`) |

İki sözlük **1:1 eşlenmez**. Bir ajan işinin `failed` olması bir kartı `failed`
yapmaz. `stale` tasarımındaki fark bilinçlidir: board projeksiyonu makine
tüketicisi için durum+bayraq taşır, dashboard ise kullanıcıya tek bir okunur
durum göstermek zorundadır — bilgi kaybını `last_known` önler.

## 8. Invariantlar (ihlali bug'dır)

1. **Ölçülmeyen şey yeşil gösterilmez.** `healthy` yalnız şu dördü birden
   varken üretilir: yapılandırma var + gerçek kontrol yapıldı + sonuç olumlu +
   freshness bütçesi içinde. Statik rozet, varsayılan yeşil, “henüz bakmadık
   ama çalışıyordur”, `checked_at=null`, sözlük dışı değer — hiçbiri `healthy`
   olamaz. **Tartışmasız.** Panel bunun sonucunda daha az yeşil görünürse bu
   hata değil, **doğruluk kazanımıdır.**
2. **Aynı backend state → aynı UI semantiği.** Aynı `state` iki farklı kartta
   aynı rozeti, aynı renk rolünü ve aynı metin şablonunu üretir.
3. **Farklı state'ler görsel olarak ezilmez.** Beş durumun beş ayrı görsel
   kimliği vardır; hiçbir ikisi tek göstergeye indirgenmez.
4. **`unknown ≠ failed ≠ not_configured`.** Üçü tek "sorunlu" kovasına
   toplanmaz.
5. **`null` freshness gerçek bir durumdur.** Gizlenmez, `now()` ile
   doldurulmaz, göreli zamana çevrilmez.
6. **Global oturum/bulut durumu kartlardan hesaplanmaz.** Tek yön: başlık kendi
   kaynağından; kartlar kendi kaynaklarından.

## 9. Kabul kriterleri

Uygulama dilimi bu maddelerin **hepsi** kanıtlanmadan kapanmaz.

1. Her kartın `state`'i beş literalden biridir; sözlük dışı değer render
   edilmez, `unknown` + `unmapped_value` olur.
2. `checked_at = null` olan hiçbir kart göreli zaman metni göstermez.
3. `not_configured` ve `unknown` farklı glif **ve** farklı erişilebilir etiket
   üretir (erişilebilirlik testi).
4. Aynı `state`, farklı kartlarda aynı rozet/metin şablonunu üretir (snapshot).
5. Bir kart `failed` iken global başlık **değişmez** (test).
6. `401` altında bütün kartlar `unknown`; hiçbiri `failed` değil (test).
7. `age > ttl_seconds` → `stale`, `last_known` korunur (test).
8. Hiçbir kod yolu `checked_at`'i `now()`/render anıyla doldurmaz — kaynak
   taramasıyla kanıtlanır.
9. Sözleşme uygulanmadan hiçbir rozet "canlı" / `healthy` iddiasında bulunmaz;
   bugünkü 18 statik rozet ya gerçek kaynağa bağlanır ya
   `unknown`/`not_configured`'a düşer.
10. Hiçbir kod yolu ölçülmemiş bir kartı `healthy` yapmaz (invariant 1);
    kaynak taraması + test. "Daha az yeşil panel" gerileme sayılmaz.

## 10. v1 sınırları (dürüst)

- **Bu belge sözleşmedir; kod yoktur.** Uygulama ayrı dilimde açılır.
- Bugün gerçek sağlık üreten **yalnız iki** kaynak var: `api/bridge/health.js`
  ve `api/integrations/meta/connections.js`. Kalan kartların arkasında ölçüm
  yok.
- **Beklenen görünür sonuç:** sözleşme uygulandığında panel bugünkünden **daha
  az yeşil** görünecek. 18 rozetin çoğu `unknown`/`not_configured`'a düşecek.
  Bu bir gerileme değil — bugünkü yeşil zaten ölçüme dayanmıyor. Kurucu
  (2026-08-20): daha az yeşil **doğruluk kazanımıdır.** Amaç paneli iyi
  göstermek değil, **doğru** göstermek; alan devri kriteri “dashboard
  düzeldi” değildir.
- Sağlık probe'larının maliyeti (dış API kotası) v1'de TTL ile sınırlanır;
  ayrı bir bütçe mekanizması yoktur.
- Kart kimlikleri (`id`) bu belgede sabitlenmedi; uygulama diliminde envanterle
  birlikte kararlaştırılır.
