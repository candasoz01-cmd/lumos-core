# Agent Status sözleşmesi — v2 (tasarım taslağı)

| Alan | Değer |
|------|-------|
| Durum | **Tasarım taslağı — insan onay kapısında.** Kod yazılmadı; bu belge merge edilse bile tek başına kod izni değildir |
| Karar dayanağı | OD-063 güncellemesi (2026-08-25, kurucu — minimal human-on-exception dilimi yetkilendirildi) · [ADR-008](../decisions/ADR-008-agent-network-boundary.md) § Gözlem (2026-08-24 saha kanıtı) |
| Önceki sürüm | [`agent-status-v1.md`](agent-status-v1.md) — kod karşılığı `src/core/agent_status_contract.py` |
| Kod karşılığı | **Yok** (hedef: aynı modülün v2 genişletmesi; ayrı PR, ayrı onay) |
| Şema sürümü | 2 |

Tek şema hem bu belgede hem (yazıldığında) kodda tanımlı olacaktır; ayrışma
olursa doküman güncellenene kadar kod esas alınır. Kod PR'ı, doküman ↔ kod
eşitliğini **iki yönde** doğrulayan türetme testi olmadan kabul edilmez.

## Amaç

v1 yalnız "ajan koşuyor mu?" sorusuna cevap verir. 2026-08-24 gözlemi eksiği
gösterdi: insan kararında durmuş üç oturumun üçü de v1'e göre `running`
raporlardı. v2, **beklemeyi** ve **bekleme sebebini** tipli hale getirir ki
Decision Queue yalnız gerçekten insan yetkisi gerektiren kayıtları süzebilsin.

## Kavram sınırı: ajan çalışma durumu ≠ Board öğesi yaşam döngüsü

ADR-008 § Kayıt yaşam döngüsü, Board **kayıtları** için
`OPEN / IN_PROGRESS / BLOCKED / WAITING_APPROVAL / COMPLETED / ARCHIVED`
kümesini tanımlar. Bu küme **bilinçli olarak buraya taşınmamıştır**:

- `OPEN`, `ARCHIVED` bir görev/Board öğesinin yaşam döngüsüdür; koşan bir
  ajanın çalışma durumu değildir.
- Agent Status bir **ajanın tek bir iş üzerindeki anlık çalışma durumunu**
  tanımlar. İki kavram ileride ayrışmak zorunda kalmamak için baştan ayrıdır.

## Durum kümesi (v2 — tam liste)

| Durum | Anlam |
|-------|-------|
| `running` | Ajan gerçekten iş yapıyor |
| `blocked` | İlerleme, **insan kararı dışındaki** bir bağımlılığa takıldı |
| `awaiting_decision` | İlerlemek için **açık insan yetkisi/kararı** gerekiyor |
| `completed` | Görev başarıyla bitti |
| `failed` | Görev teknik olarak başarısız |
| `unknown` | Gözlemci güvenilir durum çıkaramıyor |

`blocked` ile `awaiting_decision` ayrımı bu sözleşmenin varlık sebebidir:
duvar/Decision Queue insana yalnız `awaiting_decision` gösterir; `blocked`
makine tarafında çözülür veya çözülemezse sebep kaydıyla görünür kalır.

## Alanlar

v1'in tüm alanları (`version`, `agent_id`, `job_id`, `status`, `owner`,
`started_at`, `updated_at`, `evidence_ref`, `progress`, `message`) anlamları
değişmeden korunur; `version` v2 kayıtlarında `2`'dir. Eklenen alanlar:

| Alan | Tip | Zorunlu | Anlam |
|------|-----|---------|-------|
| `wait_reason` | str | Yalnız `blocked` / `awaiting_decision` için zorunlu | Beklemenin sebebi; aşağıdaki eşleme tablosuna tabidir |
| `decision_ref` | str | Yalnız `awaiting_decision` için zorunlu | Beklenen kararın **somut karar yüzeyi / kanıt hedefi** (örn. PR numarası/URL'i, OD kaydı, soru kaydı, onay kapısı kimliği); diğer tüm durumlarda bulunamaz |

### `wait_reason` eşleme kuralları (normatif)

| `status` | Geçerli `wait_reason` değerleri |
|----------|--------------------------------|
| `blocked` | `dependency`, `agent_result`, `external_event` |
| `awaiting_decision` | yalnız `human_decision` |
| diğer dört durum | `wait_reason` **bulunamaz** (varsa doğrulama hatası) |

- `human_decision` yalnız `awaiting_decision` ile geçerlidir; `blocked` bir
  kayda `human_decision` yazılamaz.
- `blocked` veya `awaiting_decision` kaydında `wait_reason` eksikse kayıt
  geçersizdir — "sebepsiz bekleme" şema düzeyinde yasaktır; aksi halde hangi
  beklemenin insan aksiyonu gerektirdiği yine görünmez kalırdı.

### `decision_ref` kuralları (normatif)

- `awaiting_decision` kaydında `decision_ref` **zorunludur**: boş veya yalnız
  boşluk içeren değer geçersizdir. "İnsan kararı bekliyorum ama neyin kararı
  belli değil" kaydı şema düzeyinde yasaktır — Decision Queue'daki her satır
  eyleme dönüştürülebilir olmalıdır.
- Değer, beklenen kararın **somut yüzeyini veya kanıt hedefini** tanımlamalıdır
  (PR numarası/URL'i, OD kaydı, soru kaydı, onay kapısı kimliği vb.);
  `evidence_ref` disipliniyle aynı: işaretçi verilir, içerik kopyalanmaz.
- Diğer beş durumda `decision_ref` **bulunamaz** (varsa doğrulama hatası).

## v1 geriye uyumluluk (normatif)

1. **Hiçbir v1 kaydı geçersizleşmez:** `version: 1` kayıtları v1 kurallarıyla
   doğrulanmaya devam eder; v2 okuyucu her iki sürümü de kabul eder.
2. **Sessiz yeniden yorumlama yok:** v1 kaydından `blocked` /
   `awaiting_decision` **çıkarımı yapılmaz**. v1 `running` kaydı v1 `running`
   olarak kalır; "bekliyor olabilir" tahmini üretilmez.
3. **Versiyonsuz eski dosyalar** bugünkü gibi v1'e normalize edilir; bu kural
   değişmez.
4. **Rollout tehlikesi (doğrulanmış):** mevcut v1 okuyucu `version != 1` olan
   her kaydı eski format sayıp normalize eder — bir v2 kaydını `agent_id =
   kando.agent_runner`, `status = unknown` biçiminde **bozarak** okur. Bu
   nedenle sıralama zorunludur: **önce okuyucu v2'ye yükseltilir, sonra
   herhangi bir v2 yazıcısı devreye girer.** KA-003 single-reader gateway tek
   yükseltme noktası olduğundan bu sıralamayı uygulanabilir kılar; kod PR'ının
   kabul kriteridir.

## Güvenilir-yazıcı sınırı (öneri — karar değil, ayrı onay kapısı)

Bu sözleşme yazıcı davranışı tanımlamaz; kurucu talimatı gereği yazıcı
uygulanmadan önce sınır önerisi kayda geçirilir.

**Mevcut durum tespiti (2026-08-25):** KA-003 gateway'i birden çok kaynaktan
gönderim kabul eder, ancak bir `source` değerinin yetkili Agent Status
yazıcısı olduğunu **kendisi kurmaz**. Aynı şekilde bir KA-002 claim'ine sahip
olmak veya ona referans vermek, tek başına yazıcı yetkisi **değildir**.

- **Görev sahipliği bağlamı:** gelecekteki yazıcı, KA-002 ile uyumlu
  **aktif/geçerli bir görev sahipliği bağlamını** kanıtlamak zorundadır.
- **Yetki ayrı ve açık karardır:** yazıcı yetkilendirmesi ayrı bir
  allowlist/credential/politika kararıdır; `claim_id`, `owner` veya `source`
  alanlarından hiçbiri tek başına yetki **ima etmez**. İnsan onaylı yazıcı
  listesi kod hakkında kural kodladığından iki yönlü türetme testiyle korunur.
- **KA-003'ün rolü:** gateway, kalıcılık/yönlendirme boğaz noktası olarak
  ancak bu yetki kontrolü var olduktan **sonra** yeniden kullanılabilir;
  bugünkü haliyle bir yetki kapısı değildir.
- **Fail closed:** yetkisiz veya kendi kendini kaydetmiş yazıcılar sessizce
  düşürülmez veya kısmen kabul edilmez — yazım **kapalı biçimde reddedilir**.
- **Ekle-revize et:** ADR-008 kuralı aynen — sessiz üzerine yazma yok; durum
  değişikliği yeni revizyon + gerekçe ister.
- Kesin credential/token mekanizması bu PR'ın kapsamı **dışındadır** ve ayrı
  bir insan onayı gerektirir.

## Kapsam dışı (bilinçli, bu tur)

- Üretim kodu, yazıcı uygulaması, UI/panel, yeni endpoint yok.
- Ajanlar arası doğrudan komut yok; auto-merge / auto-deploy / dış gönderim /
  geri döndürülemez eylem yok — insan kapıları aynen korunur.
- Claude/Cursor oturum bildirimlerinin otomatik yakalanması kapsam dışıdır;
  duvar yalnız Board'a **gönüllü yazılan** durumu görür.

## Kod PR'ı kabul kriterleri

1. v1 test kümesi değişmeden geçer; v1 kayıtları birebir aynı sonucu üretir.
2. Doküman ↔ kod durum/`wait_reason` tabloları iki yönlü türetme testiyle bağlı.
3. Eşleme kuralları ihlalleri (örn. `blocked` + `human_decision`,
   `running` + `wait_reason`, `awaiting_decision` ile eksik/boş `decision_ref`,
   `completed` + `decision_ref`) testte **bozarak** kanıtlanır.
4. Okuyucu-önce rollout sırası (bkz. § v1 geriye uyumluluk madde 4) test veya
   koruma ile güvence altındadır.
