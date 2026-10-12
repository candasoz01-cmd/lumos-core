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

1. ACTIVE claim kabul edilince, `LUMOS_WRITE_GATE_SECRET` varsa kapı bir
   yazma jetonu basar (`credential_id` + HMAC). Diskte yalnız SHA-256 özeti
   ve `issued`/`consumed` durumu durur.
2. Yazma öncesi `claim_cli write-check --token --owner --path` jetonu doğrular
   (`consume=false`). Claim ACTIVE, sahip eşleşmeli, yollar kapsam içinde.
3. `claim-guard attest` aynı jetonu `consume=true` ile yakar. İkinci attest
   `WRITE_TOKEN_CONSUMED` ile red edilir. Jeton yok, imza bozuk, sahip
   uyuşmaz, claim yok/EXPIRED veya kapsam dışı ise yazma **red** (çıkış 2).
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
`LUMOS_WRITE_GATE_SECRET` ile imzalanır; payload `attestation_id`,
`credential_id`, `parent_sha`, dosya listesi, `claim_id`, `owner` ve
`scopes` bağlar.

- `issued_at` commit mesajındaki zaman **kanıt değildir**. Kanıt, attest
  anında yakılan tek-kullanımlık jeton + HMAC (sır PR koduna verilmez) +
  `attestation_id` tekilliğidir. Aynı trailer'ın kopyası
  `CLAIM_GUARD_ATTESTATION_REUSED` ile red edilir.
- Trailer'daki yollar o commit'in `--no-renames` diff'i ile birebir uyuşmazsa red.
- Sonradan açılan claim eski commiti meşrulaştırmaz: kanıt o commit nesnesinin
  içinde olmalıdır. `9a113ced` bilinçli olarak trailersızdır; tarih yeniden
  yazılmaz.
- CheckRun adı: `claim-guard`. Secret yoksa fail-closed.
- Orkestratör `pull_request_target`; doğrulayıcı `base.sha` üzerinden
  `src/lumos_board` extract. PR ağacı checkout edilmez, çalıştırılmaz.
  Secret yalnız güvenilir PYTHONPATH adımındadır. Bu workflow henüz
  `main`'de yoksa CheckRun doğmaz veya fail-closed kalır (bootstrap).

CI tek başına insan merge'ini kilitlemez. `claim-guard` GitHub
`required_status_checks` listesine admin tarafından eklenene kadar fiziksel
kilit yoktur. Bu ortam Settings API için HTTP 403 verir; ajan koruma
ayarını değiştiremez.

## Bilinçli sınır

Dosya sistemine doğrudan yazabilen ayrıcalıklı süreç bu yerel kapıyı atlayabilir
(single-reader sözleşmesiyle aynı). Merkezi görev kontrolcüsü, required
check + güvenilir taban + tek-kullanımlık jeton birlikte doğrulanmadan
tamamlanmış sayılmaz. #935 taslak kalır; merge ve deploy yoktur.

İkinci `TaskClaimStore` veya ikinci claim CLI açılmaz.
