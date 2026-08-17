# ADR-025 — Lumos Agent Wall görünürlük dilimi

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-17)** — kurucu: yatay AI→AI komut yok; dikey kontrol; önce göz, sonra el |
| Uygulama durumu | İlk dilim: Board CLI salt-okunur duvar özeti |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md), [`ROADMAP.md`](../ROADMAP.md) STOP LIST, [ADR-008](ADR-008-agent-network-boundary.md), [ADR-019](ADR-019-product-surface-separation-modelregistry.md) |
| Kapsam | Operatörün dört soruyu tek bakışta görmesi |
| Kapsam dışı | Komut kapısı (durdur / devam / yön / onay / başka ajana ver), yeni kullanıcı sayfası, ModelRegistry, Router, yeni provider |

## Bağlam

Lumos Agent Wall (eski Command Wall) ADR-019 ile iç operatör yüzeyi olarak
kilitlendi; uygulama yoktu. Board kaydı (claim + agent status) vardı, ekran
yoktu. Operatör akışı borsa ticker gibi izliyor, karar veremiyordu.

Kurucu (2026-08-17): **Duvar = göz. Board = kayıt. Komut kapısı = el.**
Yatay ajan komutu yok; kontrol dikeydir: operatör → Lumos → tek ajan.

## Karar

### 1. STOP LIST istisnası dardır

FAZ-1 "yeni agent / orchestration katmanı" yasağı kalkmaz. Bu ADR yalnız
**mevcut Board kayıtlarını** operatörün karar verebileceği bir özet olarak
okumaya izin verir. Yeni orkestrasyon motoru, ajan ağı veya kullanıcı ürünü
değildir.

### 2. İlk dilim yalnız gözdür

Duvar özeti şu dört soruyu cevaplar:

1. Hangi ajan ne işte?
2. Ne bekliyor?
3. Nerede kilitlendi?
4. Operatörden hangi karar duruyor?

Sunum durumları: `WORKING` · `WAITING` · `BLOCKED` · `NEEDS_DECISION`.
Bunlar Board görünürlük sözlüğüdür; agent-status v1 şemasını değiştirmez.

### 3. El bu dilimde yoktur

`durdur`, `devam et`, `yön değiştir`, `onayla`, `işi başka ajana ver`
yazılmaz, CLI bayrağı olarak eklenmez, API olarak açılmaz. JSON sözleşmesi
`read_only: true` ve `command_surface: false` taşır.

### 4. Yüzey sınırı

- Operatör yüzeyi **mevcut** Board CLI'dir: `python -m lumos_board.claim_cli list`.
  Varsayılan çıktı duvar özetidir. `wall` aynı projeksiyonun takma adıdır;
  ikinci bir panel veya komut ailesi değildir.
- Yeni public sayfa, panel widget veya kullanıcı API'si **yok** (STOP LIST:
  yeni sayfa; ADR-019 sızıntı yasağı).
- Kullanıcı yüzüne ajan adı, worktree, heartbeat, PR/merge kapısı sızmaz.

### 5. Sonraki dilim ayrı karardır

Kumanda (el) ancak bu görünürlük canlı ve dürüst olduktan sonra ayrı kullanıcı
kararıyla bağlanır. El bağlansa bile komut dikey kalır; ajanlar birbirine
emir atmaz.

## Kabul

- Açık claim ve kuyruk satırları `WORKING` / `WAITING` olarak ayrılır.
- Sessiz/stale heartbeat ve başarısız ajan işi `BLOCKED` olur.
- Sahiplik çakışması `NEEDS_DECISION` olur; uydurma onay yazılmaz.
- Komut fiili veya yazma uçları bu PR'da yoktur.
