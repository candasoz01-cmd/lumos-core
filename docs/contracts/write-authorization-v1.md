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
3. `claim_cli write-attest attest` aynı jetonu `consume=true` ile yakar.
   İkinci attest `WRITE_TOKEN_CONSUMED` ile red edilir. Jeton yok, imza bozuk,
   sahip uyuşmaz, claim yok/EXPIRED veya kapsam dışı ise yazma **red** (çıkış 2).
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
- HMAC CheckRun adı: `write-attestation`. Secret yoksa fail-closed.
- Orkestratör `pull_request_target`; doğrulayıcı `base.sha` extract.
  Secret yalnız güvenilir PYTHONPATH adımındadır.
- Pano CheckRun adı: `claim-guard` (`lumos_board.claim_guard`,
  `Lumos-Claim` / `Lumos-Agent`). HMAC yeşili pano kanıtı değildir; pano
  yeşili HMAC kanıtı değildir. İkisi ayrı işler, biri diğerinin yerine geçmez.
- `#936` MERGED (`d0a1379f` / merge `423025c7`). `#935` DRAFT, merge onayı yok;
  `9a113ced` yeniden yazılmaz.

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

## Yetkili imza

`write-attestation-trusted` yalnız doğrular. İmza,
`.github/workflows/write-sign-trusted.yml` içindedir.

- Tetik yalnız `workflow_dispatch`. `pull_request` bu işi çalıştırmaz. PR
  ağacı veri olarak fetch edilir; signer olarak checkout edilmez.
- Sıra: önce önizleme, sonra ortam onayı, sonra imza, sonra otomatik
  kontroller. Önizleme commitleri, yolları ve sabit `base...head`
  karşılaştırmasını yazar. Ortam kaydının adresi bu karşılaştırmadır.
  İnceleyici onaydan önce o ekranı görür.
- Onaylanan manifest ile canlı başlık aynı değilse imza yazılmaz. Üretim
  sırrı yalnız imza işine gelir; önizleme ve kontrol işinde yoktur.
- Ortam `lumos-write-gate`. Dal politikası yalnız `main`. Zorunlu inceleyici
  ortam kaydındadır. İş ayrıca `github.ref == refs/heads/main` ister.
  Bu onay merge izni değildir. `grants_merge` üretilmez. İş merge çağırmaz.
- Genel prova anahtarı reddedilir. Üretim sırrı workflow metninde durmaz.
- Aralık yeni dala kopyalanır: `trusted-sign/pr-<numara>`. Kaynak dal ve
  `main` güncellenmez. Var olan hedef dalın üstüne yazılmaz; force yoktur.
  İmzadan sonra taslak PR açılır; otomatik kontroller orada koşar.
- `write-attestation-trusted`, `claim-guard` ve zorunlu CI tamamlanmadan
  izleme işi durur. Biri başarısızsa veya askıda kalırsa iş fail olur ve
  merge yoktur. Genel prova anahtarı işi üretim imzasında eşleşmez; bu
  beklenen ayrımıdır, doğrulayıcı gevşetilmez. `standing-class` başarısızlığı
  imza başarısı sayılmaz ve merge açmaz.
- Her commit mevcut kapıyı kullanır: bir ACTIVE claim, bir yazma jetonu,
  `write-attest` tüketimi, sonra claim serbest.
- Bu dosya `main`'de yokken iş seçilemez. Tanıtan PR kendini üretim sırrıyla
  imzalayamaz. Bu bootstrap'tir; doğrulayıcı gevşetilmez.

## Kurucu bootstrap (taslak — onay yok)

| Alan | Değer |
| --- | --- |
| Durum | **TASLAK** — kurucu kararı değil, uygulanmadı, yetki üretmez |
| Amaç | Üretim imzalayıcısını `main`'e güvenilir biçimde indirmek |
| Yasak | Ajan merge / `workflow_dispatch` / ortam onayı / anahtar kaydı yapmaz |

Bu bölüm yürürlükte değildir. Kurucu onu ayrıca onaylamadıkça Aşama A
veya Aşama B başlatılmaz.

### Neden kilitlenme var

`write-sign-trusted.yml` yalnız `workflow_dispatch` ve `refs/heads/main`
üzerinde çalışır. GitHub, varsayılan dalda olmayan bir iş dosyasını
dispatch listesine koymaz. Tanıtan PR bu yüzden kendini üretim sırrıyla
imzalayamaz.

Aynı aralıkta iki HMAC CheckRun ayrı sırlar kullanır:

- `write-attestation` (`claim-guard.yml`) — genel prova anahtarı
- `write-attestation-trusted` — `secrets.LUMOS_WRITE_GATE_SECRET`, doğrulayıcı
  `base.sha`

Prova HMAC üretim sırrını doğrulamaz. Beklenen sonuç
`CLAIM_GUARD_UNAUTHORIZED`'dır. Bu, `CLAIM_GUARD_UNCONFIGURED` değildir:
sır enjekte edilmiş, imza uymamıştır. Tanıtan PR'da trusted SUCCESS
beklemek kilitlenmedir. Doğrulayıcı bu kilitlenme için gevşetilmez.

Bootstrap iki ayrı kurucu eylemidir: önce imzalayıcı kodunu `main`'e
indirmek (üretim yetkisi değil), sonra ayrı bir dispatch ile ilk üretim
imzasını basmak.

### Canlı önkoşul kaydı (doğrulama, uygulama değil)

GitHub API · 2026-10-16T14:20Z. Head değişince bu satırlar bayatlar;
uygulama öncesi yeniden doğrulanır.

1. `origin/main` `write-sign-trusted.yml` **içermez**.
2. `origin/main` `write-attestation-trusted.yml` **içerir**.
3. Ortam `lumos-write-gate` vardır; zorunlu inceleyici `candasoz01-cmd`;
   dal politikası kayıtlıdır.
4. `candasoz01-cmd/lumos-core#945` · OPEN ·
   `31b14443e7003400be4d1c00063c509ad5b38c39` · `write-attestation`
   SUCCESS · `write-attestation-trusted` FAILURE ·
   `CLAIM_GUARD_UNAUTHORIZED` (aralıktaki her commit).

### Aşama A — imzalayıcıyı `main`'e indirmek

Bu aşama üretim imzası basmaz.

1. Kurucu tanıtan PR'ın `main...head` aralığını okur. Bu aralık imzalanacak
   sonraki iş değildir; imzalayıcıyı taşır.
2. Bu PR'daki `write-attestation-trusted` kırmızısı **beklenen** kırmızı
   olarak kayda geçer. Yeşile zorlanmaz. İş dosyası gevşetilmez.
3. Üç kapı (zorunlu CI, güvenlik incelemesi, kurucu onayı) hâlâ **o SHA**
   içindir. `write-attestation-trusted` fiziksel required check değildir
   ve bootstrap'te SUCCESS sayılmaz.
4. Kurucu yazılı olarak o SHA için şunu kaydeder: imzalayıcı bootstrap;
   üretim yetkisi değil. Ajan veya bot onayı yetmez.
5. Yalnız kurucu merge eder. Ajan merge etmez. İş `grants_merge`
   üretmez ve merge çağırmaz.
6. Merge sonrası aynı anda iki kanıt gerekir: `git cat-file -e
   origin/main:.github/workflows/write-sign-trusted.yml` başarılıdır ve
   `gh workflow list` `Write sign trusted` işini `active` gösterir.

Bu merge, üretim imzasının çalıştığını kanıtlamaz.

### Aşama B — ilk üretim kullanımı

Aşama A kanıtlandıktan sonra, iş `main` üzerinden seçilir. Kaynak PR
`validate_pr_request` koşullarını sağlar: açık, `base.ref=main`,
`base.sha` dispatch `GITHUB_SHA` ile aynı. Bu PR `main`'de olmayan
commitler taşır.

1. Kurucu `Write sign trusted` işini `refs/heads/main` üzerinden
   `workflow_dispatch` ile çalıştırır.
2. Önizleme, onayın kapladığı `base...head` compare URL'sini yazar. Ortam
   kaydının adresi bu URL'dir.
3. `lumos-write-gate` inceleyicisi o URL'yi onaylar. Bu onay merge
   değildir.
4. İmza işi aralığı `trusted-sign/pr-<n>` üzerine kopyalar. `main` ve
   kaynak dal değişmez. Force yoktur.
5. **İlk üretim kanıtı:** imzalı kopyanın PR'ında, o SHA için
   `write-attestation-trusted` CheckRun SUCCESS. Aynı SHA'da prova işi
   (`write-attestation`) üretim imzasıyla eşleşmez; bu beklenen ayrımdır.
6. İzleme işi kırmızı veya askıdaysa durur. Merge yoktur.

### Bu taslağın vermediği yetkiler

- sonraki PR'ların merge'i
- prova anahtarının üretim sayılması
- doğrulayıcının gevşetilmesi
- ajanın merge, dispatch veya ortam onayı
- imza kökü / `allowed_signers` kaydı
- branch protection listesini ajanın doldurması
