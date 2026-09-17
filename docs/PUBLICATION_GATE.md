<!-- markdownlint-disable MD013 -->

# Yayın kapısı — çift katmanlı koruma

> **Kapsam notu (2026-09-17):** Bu belge koruyucu altyapıyı tanımlar; hangi
> içeriğin yayınlanacağına karar vermez. Yayın kararı her zaman kurucunun ayrı
> ve açık onayıdır. Belge, 2026-07/08 döneminde private karar metinlerinin
> public `.astro` sayfalarına gömülmesi olayından sonra yazılmıştır.

## İlke

**"Özel olduğunu tespit et" değil, "yayınlanabilir olduğunu kanıtla."**
Varsayılan durum her içerik için `PRIVATE_NOT_APPROVED`'dır. İki katman
birbirinden bağımsızdır: biri hata yapsa da diğeri durdurur.

Public yüzey tanımı: production web (welockai.com), Vercel preview, public repo
branch'i, draft dahil her PR, build artifact, generated static page.

## Katman 1 — Public Release Gate

`ops/publication_gate/gate.py` public yüzeylerde (bkz.
`config/publication/gate_config.json` → `public_surfaces`) kod dosyasına
gömülmüş belge gövdesi arar (kaçışlı `\n` ile tek satıra yazılmış, başlık/tablo
taşıyan büyük string sabitleri; `BODY = "..."` deseni).

Her bulgu için `config/publication/public_release_manifest.json` içinde kayıt
zorunludur:

| status | Anlamı | Geçer mi? |
|--------|--------|-----------|
| (kayıt yok) | `PRIVATE_NOT_APPROVED` — varsayılan | ❌ Bloklanır |
| `approved` | Kurucunun ayrı yayın onayı; `public_release_approved: true`, `approved_by`, `approved_date` ve eşleşen `content_sha256` zorunlu | ✅ |
| `legacy_baseline_review_required` | Hash pin izleme kaydı; kurucu incelemesi bekliyor. **Onay değildir.** Eşleşen hash yayın izni üretmez. | ❌ Bloklanır |
| başka her değer | Tanınmaz | ❌ Bloklanır |

İçerik bir bayt bile değişirse hash eşleşmez ve kapı durdurur; değişiklik ancak
kurucunun yeni onayı + manifest güncellemesiyle geçer. Hash üretimi:
`python3 ops/publication_gate/gate.py --hash <dosya>`.

## Katman 2 — Sensitive Content Boundary

Katman 1'den bağımsız; manifest onayı olsa bile koşar. Aradıkları:

- **private-source-reference:** private repo yolları/URL'leri
  (`candasoz01-cmd/Lumos`, private raw URL'ler, `publish/welockai`,
  `docs/canonical/`).
- **classification-marker:** "İÇ KULLANIM", "YAYINLANMAZ", "public değil",
  "TEK KAYNAK" gibi sınıflandırma işaretleri.
- **secret-material:** token/anahtar desenleri (`ghp_…`, `github_pat_…`,
  `sk-…`, `xox…`, `AKIA…`, private key blokları, `x-access-token:`).

private-source-reference ve classification-marker bulguları yalnız
`config/publication/sensitive_boundary_baseline.json` içinde **hash'i eşleşen
ve ikinci insan onayı metadata'sı tamamlanmış** bir kayıtla geçer
(`boundary_review_approved: true`, `approved_by`, `approved_date`). Salt hash
eşleşmesi yetmez. **Secret bulgusu hiçbir kayıtla geçirilemez**; tek çözüm
kaldırma + rotasyondur.

## Nerede koşar (üç bağımsız zorlama noktası)

1. **CI:** `.github/workflows/ci.yml` → `publication-gate` job'ı. `if:` koşulu,
   `continue-on-error` veya atlama bayrağı yoktur; draft dahil her
   `pull_request` ve `main` push'unda koşar.
2. **Pytest:** `tests/test_publication_gate.py` gerçek repo taramasını da
   içerir; kapı bulgusu varsa zorunlu `test` check'i kırmızıya döner.
3. **Vercel build:** `vercel.json` → `buildCommand` önce kapıyı çalıştırır.
   PAT'la push edilmiş bir branch'in preview'u bile, kapı geçilmeden **derlenmez**
   — preview yüzeyi fail-closed'dır.

## Bypass edilemezlik

- `gate.py` ortam değişkeni okumaz; `--force`/`--skip` benzeri bayrak yoktur.
- PAT veya bot token'ı sahibi olmak kapıyı geçme yetkisi vermez: push
  yapılabilir, ama CI + Vercel build kapıyı her koşulda çalıştırır.
- Rapor içerik alıntılamaz; yalnız dosya, satır, kural ve gereken onay yazılır.
- Kapı, manifest, baseline veya testlerde her gevşetme kurucu onayı ister
  (bkz. `AGENTS.md` § "Yayın ayrı bir kullanıcı eylemidir").

Bilinen kalıntı sınırlar: `publication-gate` job'ının branch protection'da
required check yapılması ve `config/publication/**` + `ops/publication_gate/**`
için CODEOWNERS zorunlu incelemesi GitHub ayarıdır; kurucu eliyle açılır.

## Onay prosedürü (kurucu)

1. Yayınlanacak dosyayı incele.
2. `python3 ops/publication_gate/gate.py --hash <dosya>` ile hash al.
3. Manifest'e `status: "approved"`, `public_release_approved: true`,
   `approved_by`, `approved_date`, `content_sha256` yaz.
4. Katman 2 bulgusu da varsa baseline'a ayrı kayıt ekle: eşleşen
   `content_sha256` **ve** `boundary_review_approved: true`, `approved_by`,
   `approved_date` (ikinci onay). Hash tek başına yetmez.
5. Değişikliği normal PR akışıyla merge et.
