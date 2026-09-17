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

- İmza yükü `katman-id \n dosya-yolu \n content_sha256 \n approved_date \n`
  biçimindedir: içerik değişirse imza geçersizleşir; layer1 imzası layer2'de
  kullanılamaz.
- `ssh-keygen` yoksa, imza çözülemiyorsa veya `allowed_signers` eksikse
  doğrulama BAŞARISIZ sayılır (fail-closed).
- `allowed_signers` güven köküdür (kaynak: kurucunun GitHub hesabı anahtarları).
  Bu dosyanın değiştirilmesi güven kökü değişikliğidir; zorlayıcı kilit için
  GitHub tarafında `config/publication/**` + `ops/publication_gate/**` üzerine
  CODEOWNERS + zorunlu inceleme gerekir (kurucu ayarı). O ayar olmadan imza
  şeması denetlenebilir ama tek başına zorlanamaz.

### Onay prosedürü (kurucu, kendi makinesinde)

```bash
# 1. Yükü üret (layer1 veya layer2):
python3 ops/publication_gate/gate.py --payload layer1 ui/src/pages/<dosya>.astro 2026-09-17 > /tmp/onay.payload

# 2. İmzala (private anahtarınla):
ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n lumos-publication /tmp/onay.payload

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

1. **Onay altyapısı yok:** İnsan-kapılı imza anahtarı henüz kurulmadı; kapalı
   varsayılan yürürlükte (hiçbir onay/istisna geçemez). Çözüm yalnız
   kurucunun anahtar kurulumuyla gelir.
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
