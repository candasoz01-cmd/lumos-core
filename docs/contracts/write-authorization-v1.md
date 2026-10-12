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

## Claim-guard (commit kanıtı)

PR aralığındaki her non-merge commit, o commit'in mesajında
`Lumos-Claim-Attestation` trailer'ı taşımalıdır. Trailer HMAC'i
`LUMOS_WRITE_GATE_SECRET` ile imzalanır; payload o commit'in `parent_sha`,
dosya listesi, `claim_id`, `owner`, `scopes` ve `issued_at` değerini bağlar.

- `issued_at` committer zamanından sonra ise red.
- Trailer'daki yollar o commit'in `--no-renames` diff'i ile birebir uyuşmazsa red.
- Sonradan açılan claim eski commiti meşrulaştırmaz: kanıt o commit nesnesinin
  içinde olmalıdır.
- CheckRun adı: `claim-guard`. Secret yoksa fail-closed.

CI tek başına insan merge'ini kilitlemez. `claim-guard` GitHub
`required_status_checks` listesine admin tarafından eklenene kadar fiziksel
kilit yoktur. Bu ortam Settings API için HTTP 403 verir; ajan koruma
ayarını değiştiremez.

## Bilinçli sınır

Dosya sistemine doğrudan yazabilen ayrıcalıklı süreç bu yerel kapıyı atlayabilir
(single-reader sözleşmesiyle aynı). `pull_request` bootstrap'inde workflow
PR ağacından koşar; `main`'e indikten sonra `pull_request_target` + base SHA
doğrulayıcısı ayrı dilimdir. Merkezi görev kontrolcüsü, required check +
commit-bound kanıt birlikte doğrulanmadan tamamlanmış sayılmaz.

İkinci `TaskClaimStore` veya ikinci claim CLI açılmaz.
