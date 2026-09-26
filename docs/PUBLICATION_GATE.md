<!-- markdownlint-disable MD013 -->

# Yayın kapısı — çift katmanlı koruma

> **Kapsam notu (2026-09-17):** Bu belge koruyucu altyapıyı tanımlar; hangi
> içeriğin yayınlanacağına karar vermez. Yayın kararı her zaman kurucunun ayrı,
> açık ve **imzalı** onayıdır. Belge, 2026-07/08 döneminde private karar
> metinlerinin public `.astro` sayfalarına gömülmesi olayından sonra yazıldı;
> gömülü gövdeler PR #857 ile, kaynak taraf Lumos PR #370 ile kapatıldı.

## İlke

**"Özel olduğunu tespit et" değil, "yayınlanabilir olduğunu kanıtla."**
Varsayılan durum her içerik için `PRIVATE_NOT_APPROVED`'dır. "İnceleme
bekliyor" türü ara statü YOKTUR — inceleme beklemek yayın izni değildir.
İki katman birbirinden bağımsızdır: biri hata yapsa da diğeri durdurur.

Public yüzey tanımı: production web (welockai.com), Vercel preview, public repo
branch'i, draft dahil her PR, build artifact, generated static page.

## Katman 1 — Public Release Gate

`ops/publication_gate/gate.py` public yüzeylerde (bkz.
`config/publication/gate_config.json` → `public_surfaces`) kod dosyasına
gömülmüş belge gövdesi arar (kaçışlı `\n` ile tek satıra yazılmış, başlık/tablo
taşıyan büyük string sabitleri; `BODY = "..."` deseni).

Her bulgu için `config/publication/public_release_manifest.json` içinde
**imzalı** kayıt zorunludur. Tek geçerli statü `approved`:
`public_release_approved: true`, `approved_by`, `approved_date`, eşleşen
`content_sha256` ve geçerli `approval_signature`. Kayıtsız, hash'i kaymış,
statüsü farklı veya imzası doğrulanamayan her şey bloklanır.

## Katman 2 — Sensitive Content Boundary

Katman 1'den bağımsız; manifest onayı olsa bile koşar. Kapsam uzantı
allowlist'i kullanmaz: medya (görüntü/font/ses-video) dışında `public_surfaces`
altındaki **her** dosya taranır (`.log`, `.csv`, `.pem`, uzantısız dahil);
metne çözülemeyen dosya atlanmaz, `unscannable-file` bulgusudur ve ancak
kurucu imzalı baseline kaydıyla geçer. Çözüm sırası UTF-8, sonra yalnız
BOM'lu UTF-16 (`FF FE` / `FE FF`); UTF-8 başarısızken BOM'suz `utf-16`
denenmez (native-endian mojibake fail-open'ı, 2026-09-17 Bugbot). Aradıkları:

- **private-source-reference:** private repo yolları/URL'leri
  (`candasoz01-cmd/Lumos` her harf biçiminde; public `lumos-core` hariç).
  GitHub owner/repo eşlemesi büyük/küçük harfe duyarsızdır.
- **classification-marker:** "İÇ KULLANIM", "YAYINLANMAZ", "public değil" gibi işaretler.
- **secret-material:** token/anahtar desenleri.

private-source-reference ve classification-marker bulguları yalnız
`config/publication/sensitive_boundary_baseline.json` içinde hash'i eşleşen ve
**kurucu imzalı** bir kayıtla geçer (ayrı ikinci insan onayı). **Secret bulgusu
hiçbir kayıtla geçirilemez**; tek çözüm kaldırma + rotasyondur.

## İnsan onayı = imza (anahtar yönetimi şartıyla)

Manifest/baseline'daki düz metin alanlar tek başına onay sayılmaz — bir ajan da
yazabilir. Onayın kanıtı, kurucunun private SSH anahtarıyla üretilmiş imzadır;
kapı bunu `config/publication/allowed_signers` içindeki public anahtarlarla
(`ssh-keygen -Y verify`, namespace `lumos-publication`) doğrular.

> **KAPALI VARSAYILAN (2026-09-18):** İmza, onayı yalnız *anahtara* bağlar;
> ajan erişebilen bir anahtar insan onayı kanıtlayamaz. Kurucunun genel amaçlı
> GitHub anahtarı geliştirme ortamında ajan erişimine açık bulunduğundan
> güven kökünden ÇIKARILDI ve parmak izi `gate.py`
> `REVOKED_SIGNER_FINGERPRINTS` listesine alındı — yeniden kaydı kapı
> bulgusudur. Şu an **hiçbir imza kökü kayıtlı değildir**: geçerli onay
> altyapısı kurulana kadar tüm yayın onayı ve istisna (baseline) talepleri
> reddedilir. Kök kaydı, yalnız insan etkileşimiyle kullanılabilen bir
> anahtarla (donanım anahtarı, Secure Enclave — ör. Secretive, biyometrik
> onaylı 1Password SSH agent) ve kurucu eliyle yapılır; genel amaçlı veya
> ajan-erişilebilir anahtar kabul edilmez.

### Kurucu kararı — biyometrik insan kapısı (2026-09-26)

#858 için kurucu kararıdır. Tasarım burada netleşir. Bu kayıt anahtar
üretmez, `config/publication/allowed_signers` içine satır eklemez ve kapıyı
açmaz. Tek seferlik kurulum sonraki ayrı kurucu eylemidir. Çalışan kod veya
kayıtlı imza kökü değildir; kapalı varsayılan yürürlükte kalır.

İki katman birbirinin alternatifi değildir. Yüzeydeki adım insan varlığını
doğrular (Face ID, Touch ID veya eşdeğeri). Alttaki yetki ayrı bir yayın
anahtarının SSH imzasıdır. Publication gate yalnız bu imzayı doğrular.

Akış:

1. Yayın isteği gelir.
2. Lumos, istenen görev, SHA ve eylemin doğru olduğunu doğrular.
3. Onay, kurucunun güvenilir cihazına gelir.
4. Cihazın yerel biyometrisi (Face ID veya Touch ID) kullanıcı varlığını
   doğrular.
5. Secure Enclave içindeki yayın anahtarı imzayı üretir.
6. Publication gate imzayı doğrular.

Lumos yüz görüntüsünü görmez, kameradan yüz tanıma yapmaz ve biyometrik veri
tutmaz. Apple cihazında Face ID bunu donanım ve işletim sistemi seviyesinde
yapar. Lumos yalnız şu sonucu alır: korunan anahtar, kullanıcı
doğrulamasından sonra kullanılabildi.

Kamera veya Face ID olmayan cihazda yetki aynı kalır. Değişen yalnız insanı
doğrulayan yöntemdir: Touch ID, donanım güvenlik anahtarı veya ayrı bir
güvenilir cihazdan onay. 2026-09-18 notundaki Secretive, donanım anahtarı ve
biyometrik 1Password örnekleri yalnız bu varlık yöntemleridir; private yarı
donanım sınırından çıkıyorsa veya anahtar günlük GitHub anahtarıysa kabul
edilmezler.

Anahtar kuralları:

1. Anahtar, ajanların göremediği kurucu makinesinde oluşur. Private yarı
   repoya, bulut ajana veya bu çalışma ortamına girmez.
2. Kullanım insan varlığı ister. Anahtar günlük GitHub anahtarı değildir.
   `~/.ssh/id_ed25519` ve "kurucunun GitHub hesabı anahtarları" güven kökü
   değildir; bu kalıp iptal edilmiştir. Ayrı publication key kullanılır.
   Private yarı Secure Enclave veya donanım sınırından çıkmaz. Cihaz
   destekliyorsa kullanım, yerel biyometrik kullanıcı doğrulamasına bağlanır.
3. Repoya sonra yalnız public satır girer: principal, namespace
   `lumos-publication`, `ssh-ed25519`. Yük ve namespace değişmez. Parmak izi
   `REVOKED_SIGNER_FINGERPRINTS` içindeki anahtar olamaz.
4. O public satır sonraki ayrı kurucu PR'ıdır. O PR gelene kadar
   `allowed_signers` boş kalır ve kapı kapalı kalır.

- İmza yükü `katman-id \n dosya-yolu \n content_sha256 \n approved_date \n`
  biçimindedir: içerik değişirse imza geçersizleşir; layer1 imzası layer2'de
  kullanılamaz.
- `ssh-keygen` yoksa, imza çözülemiyorsa veya `allowed_signers` eksikse
  doğrulama BAŞARISIZ sayılır (fail-closed).
- `allowed_signers` güven kökünün public yarısıdır: ayrı publication key.
  Kaynak günlük GitHub anahtarı değildir. Bugün dosyada kayıtlı imzacı satırı
  yoktur; boşluk kapalı varsayılandır. Bu dosyanın değiştirilmesi güven kökü
  değişikliğidir; zorlayıcı kilit için
  GitHub tarafında `config/publication/**` + `ops/publication_gate/**` üzerine
  CODEOWNERS + zorunlu inceleme gerekir (kurucu ayarı). O ayar olmadan imza
  şeması denetlenebilir ama tek başına zorlanamaz.

### Onay prosedürü (kurucu, kendi makinesinde)

```bash
# 1. Yükü üret (layer1 veya layer2):
python3 ops/publication_gate/gate.py --payload layer1 ui/src/pages/<dosya>.astro 2026-09-17 > /tmp/onay.payload

# 2. İmzala. Private yarı Secure Enclave / donanım sınırında kalır.
#    Günlük GitHub anahtarı (~/.ssh/id_ed25519) kullanılmaz.
#    İmza, yerel kullanıcı doğrulamasından sonra üretilir
#    (Face ID, Touch ID, donanım güvenlik anahtarı veya ayrı güvenilir cihaz).
#    Anahtar yolu repoda yoktur. Kurulum yapılana kadar bu adım çalıştırılmaz:
ssh-keygen -Y sign -f <yayin-anahtari> -n lumos-publication /tmp/onay.payload

# 3. /tmp/onay.payload.sig içeriğini manifest kaydına approval_signature olarak,
#    hash'i content_sha256 olarak yaz; normal PR akışıyla merge et.
```

## Nerede koşar (dört nokta)

1. **pre-push kancası** (`.githooks/pre-push`, kurulum `make setup-commit-guard`):
   public remote'a push'tan ÖNCE son yerel bariyer.
2. **CI:** `.github/workflows/ci.yml` → `publication-gate` job'ı; `if:` yok,
   `continue-on-error` yok, draft dahil her `pull_request`'te koşar.
3. **Pytest:** `tests/test_publication_gate.py` gerçek repo taramasını içerir;
   zorunlu `test` check'i içinde. (#857'nin `test_public_pages_no_private_embed.py`
   testi bağımsız ikinci ağdır.)
4. **Vercel build:** `vercel.json` → `buildCommand` önce kapıyı çalıştırır;
   preview dahi kapı geçilmeden derlenmez.

## Çözülmemiş sınırlar (dokümante edilmiş ≠ çözülmüş)

1. **Kurulum bekliyor (tasarım kararlaştı, 2026-09-26):** Biyometrik insan
   kapısı yukarıda kurucu kararı olarak kayıtlıdır. Yayın anahtarı henüz
   kurulmadı; `allowed_signers` boştur; kapalı varsayılan yürürlüktedir
   (hiçbir onay/istisna geçemez). Bu kayıt anahtar üretmez. Çözüm, sonraki
   tek seferlik kurucu kurulumuyla gelir. Geliştirme bekleyen iş değildir.
2. **İnsan incelemesi zorlanmıyor:** `require_code_owner_reviews=false`,
   `required_approving_review_count=0`. Tek insan hesabı kendi PR'ını
   onaylayamayacağı için bu ayar ikinci inceleyici hesap olmadan AÇILMAMALIDIR
   (kilitlenme); ikinci hesap kurulana kadar bu sınır açık kalır.
3. **Kapı kodu repo içinde:** `gate.py`, iptal listesi, manifestler ve testler
   push erişimli bir aktörce aynı commit'te değiştirilebilir; CODEOWNERS
   yalnız bilgilendiricidir. Sunucu tarafı zorlamayı yalnız GitHub ayarları
   (aşağıda) sağlar.

## Dürüst sınırlar

- **Push anı = yayın.** Public GitHub'a push edilen içerik, CI verdikten önce
  görünür olur; CI ilk ifşayı geri alamaz. Pre-push kancası bunu azaltır ama
  `--no-verify`, kancasız klon veya doğrudan API push'u ile atlanabilir;
  GitHub.com'da sunucu tarafı pre-receive yoktur. Atlatılamaz tek önlem kaynak
  taraftadır: private içerik, public remote'a push yetkisi olan bir çalışma
  ağacına hiç girmemelidir (Lumos PR #370'in kapattığı yol) — ajan kuralı da
  push'u ayrı yetki sayar (`AGENTS.md`).
- **Zorlama için gereken GitHub ayarları** (2026-09-18'de doğrulanan mevcut
  durum: `require_code_owner_reviews=false`, `required_approving_review_count=0`,
  required checks yalnız test/rust/macos-app-build/ui-smoke/ui-e2e). Kurucunun
  `main` branch protection'da yapması gerekenler:
  1. Required status checks listesine `publication-gate` ekle.
  2. "Require a pull request before merging" altında
     `required_approving_review_count: 1` ve
     "Require review from Code Owners" (`require_code_owner_reviews: true`) aç.
  3. `enforce_admins` açık kalsın (bugün açık).
  4. `.github/CODEOWNERS` bu PR ile geliyor; dosya, 2. madde açılmadan yalnız
     bilgilendiricidir.
  **Bilinen kilitlenme:** repoda tek insan hesabı var; PR yazarı kendi PR'ını
  onaylayamaz. 2. madde açılırsa kurucunun kendi açtığı, CODEOWNERS kapsamına
  giren PR'lar ikinci bir inceleyici hesap (veya inceleme botu) olmadan merge
  edilemez; `enforce_admins` açıkken admin bypass da yoktur. Bu bilinçli bir
  bedeldir — açmadan önce ikinci inceleyici hesabı planla.
- Kapı, manifest, baseline, `allowed_signers` veya testlerdeki her gevşetme
  kurucu onayı ister.
