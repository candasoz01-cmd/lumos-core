# ADR-032 — Lumos Duvar v1 görev ve ajan sözleşmesi

| Alan | Değer |
| --- | --- |
| Karar durumu | **Accepted (2026-09-19)** — sekiz maddelik çerçeve 2026-09-18 kurucu kararı; metin 2026-09-19 kurucu onayıyla yürürlükte (chat: önce hukuk, sonra ekran) |
| Uygulama durumu | Sözleşme yürürlükte. Görsel yok. Yazma kapısı mevcut claim |
| Ad | Duvar = Lumos Board'un iç operasyon yüzü; katmanın resmi adı Lumos Board ([ADR-008](ADR-008-agent-network-boundary.md)) |
| Sözleşme | [`lumos-wall-v1.md`](../contracts/lumos-wall-v1.md) |
| Üst sınır | [CONSTITUTION.md](../CONSTITUTION.md), [ADR-019](ADR-019-product-surface-separation-modelregistry.md), [ADR-008](ADR-008-agent-network-boundary.md), [task-claim-v1.md](../contracts/task-claim-v1.md) |
| STOP LIST | Yeni sayfa / yeni agent-orchestration katmanı **yok** |

## Karar

Lumos Duvar, yeni bir koordinasyon yığını değildir. Mevcut Board
(`src/lumos_board/`), KA-002 claim (`claim_cli.py` / `task_claim.py`) ve
anayasa üzerinde **iç operasyon merkezidir**.

Kilit: sekiz madde + ana yasa + teknik kilit, sözleşmede. Anayasa kopyalanmaz,
referans verilir. `claim_cli` tek yetkili yazma/claim kapısıdır; Duvar claim
durumunu tüketir ve gösterir, ayrı claim üretmez. Duvar yalnız
görev durumu, sahiplik, kanıt, çakışma ve kurucu kapısını görünür hale getirir.

Görsel yüz ayrı onaylı sonraki dilimdir ve yalnız sözleşmenin görüntüsüdür;
iş mantığı UI'ya dağılmaz.

## Sonuçlar

- Yazmadan önce `claim_cli` zorunlu kalır.
- Duvar durum makinesi claim `ClaimStatus` üzerine projeksiyondur; enum'u
  genişletmek bu ADR'nin izni değildir. Eşleme kilidi (2026-09-18 kurucu
  kararı): `READY` = `ACTIVE`, `PARKED` = `RELEASED`, `BLOCKED` = `ACTIVE`.
- Kurucuya giden kanal anayasa §10 süzgecidir.
- Onay şeması v1 (`approval_id`, `task`, `gate`, `action`, `head_sha`,
  `approved_by`) **sözleşme gereksinimidir**, uygulanmış sistem değildir.
  Aynı geçerli onay tekrar sorulmaz; ajan `approved_by` üretemez. Anayasa
  farkı ve yayın güvenlik uygulaması bu ADR'nin izni değildir.
- `#859` / `#860` / `#861` bu dilimin kapsamı değildir.

## Bilinçli yapılmaz

UI, yeni endpoint, yeni lease deposu, onay-şeması store/CLI, anayasa yazımı,
ajanlar arası komut, auto-merge.
