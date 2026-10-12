<!-- markdownlint-disable MD013 -->

# Lumos Write Authorization v1

| Alan | Değer |
| --- | --- |
| Durum | KA-003 yazma dilimi — 2026-10-12 kurucu kararı (TD-10 kapısı) |
| Üst | [task-claim-v1](task-claim-v1.md) (KA-002 kilit) · [single-reader-gateway-v1](single-reader-gateway-v1.md) (KA-003 okuma) |
| Kapı | `python -m lumos_board.claim_cli` — ikinci claim CLI yok |
| Kod | `src/lumos_board/write_gate.py` |

KA-002 kilidi ayırır. Bu dilim kilide uymayı **yazma kontrolünde** zorunlu kılar:
HMAC ile bağlanmış yazma kimliği + ACTIVE claim + kapsam. Sahte `owner`
dizesi yetmez.

## Akış

1. ACTIVE claim kabul edilince, `LUMOS_WRITE_GATE_SECRET` varsa kapı tek
   kullanımlık gösterilen bir yazma jetonu basar. Diskte yalnız SHA-256 özeti durur.
2. Yazma öncesi `claim_cli write-check --token --owner --path` jetonu doğrular,
   claim'in ACTIVE ve sahip eşleşmesini arar, yolların kapsam içinde olduğunu
   kontrol eder.
3. Jeton yok, imza bozuk, sahip uyuşmaz, claim yok/EXPIRED veya kapsam dışı
   ise yazma **red** (`accepted: false`, çıkış 2).
4. Secret yokken `write-check` fail-closed (`WRITE_GATE_UNCONFIGURED`). Claim
   alma (KA-002) secret olmadan çalışmaya devam eder.

## Kimlik

Jeton `claim_id` + `owner` bağlar; HMAC-SHA256 `LUMOS_WRITE_GATE_SECRET` ile
imzalanır (en az 32 byte). Kontrol, çağıranın söylediği `owner` ile jetondaki
kimliğin aynı olmasını ister. Bu, self-asserted `owner` alanının yerini tutmaz;
yazma kontrolü jetona sahip olmayı ister.

## Bilinçli sınır

Dosya sistemine doğrudan yazabilen ayrıcalıklı süreç bu yerel kapıyı atlayabilir
(single-reader sözleşmesiyle aynı). Git/OS kimliği ve zorunlu pre-commit bağlama
ayrı dilimdir. Bu dilim merkezi görev kontrolcüsünü tamamlanmış saymaz; yalnız
yazma API'sinde TD-10 boşluğunu kapatır.

İkinci `TaskClaimStore` veya ikinci claim CLI açılmaz.
