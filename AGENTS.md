<!-- markdownlint-disable MD013 -->

# Lumos çalışma düzeni

**Her ajanın (Claude, Cursor, Codex, ...) ilk adımı:** önce
[`docs/CONSTITUTION.md`](docs/CONSTITUTION.md)'yi oku. Roadmap ve çekirdek
belgeler (`docs/ROADMAP.md`, `docs/MODULES.md`, `docs/TECHNICAL_DEBT.md`)
canonical kaynaktır; başka repoda kopyaları oluşturulmaz. Sana atanan kapsamın
dışına çıkma. Bir dosyanın aynı anda yalnızca bir sahibi vardır — görev
tamamlanana veya devredilene kadar başka ajan o dosyaya yazmaz.

Bu repoda yazma işi başlamadan önce Lumos Board üzerinde görev claim'i alınır.

1. Aynı görev kimliği ve çakışan dosya kapsamları kontrol edilir.
2. Claim kaydında görev, repo, branch, worktree, sahip, kapsam ve TTL bulunur.
3. Claim kabul edilmeden dosya değiştirilmez. Çakışma reddedilir; iş kuyruğa alınır
   veya mevcut sahibin açıkça devrettiği alt görev olur.
4. Uzun işlerde heartbeat gönderilir. Sahiplik bırakılmadan başka ajan işi alamaz.
5. PR açılınca claim kaydına bağlanır. İş bitince claim serbest bırakılır.
6. Manual override yalnız açık onaylayan kişi ve gerekçe ile yapılır; audit kaydı zorunludur.

Ortak depo Git common directory üzerinden otomatik bulunur. Temel komut:

```text
python -m lumos_board.claim_cli claim --task KA-000 --repo lumos-core --branch codex/example --worktree /path/to/worktree --owner agent-name --scope path/to/file
```

Claim aracı henüz hedef dalda yoksa bootstrap rezervasyonu olarak aynı görev kimliğini
taşıyan uzak branch açılır; kod değişikliğinden önce açık PR, branch ve worktree çakışması
elle kontrol edilir.

## Bulgu düzeltme ve otomasyon sınırları (cloud ajanları)

- **Merge edilmemiş dala ait bulgular:** Bir PR'ın dalında olup henüz `main`'e
  inmemiş kodda tespit edilen bulgular (ör. Bugbot), o kod `main`'e inene kadar
  "güncel `main` tabanlı ayrı PR" ile düzeltilemez — düzeltilecek dosya `main`'de
  yoktur. Bu bulgular ilgili PR'da **pre-merge review notu** olarak tutulur;
  STOP-LIST / dondurulmuş PR'lara düzeltme **yığılmaz**. Kod `main`'e indikten
  sonra her bulgu ayrı, dar, güncel-`main` tabanlı PR ile ele alınır.
- **`gh` CLI salt-okunur:** Bu ortamda `gh` yalnız okuma içindir; PR/issue
  yorumunu **düzenleyemez/silemez** (`PATCH .../issues/comments/{id}` → HTTP 403
  "Resource not accessible by integration"). Yazma işleri ManagePullRequest ile
  yapılır, ancak o da yorum düzenleme/silme sunmaz. Yanlış yayımlanan bir yorum
  geri düzeltilemez; gerekirse tekrar yayımlamak yerine tek bir
  **düzeltme/indeks yorumu** eklenip canonical kayıt orada belirtilir.

## Üçlü merge kapısı (tüm ajanlar)

Normatif metin: [`CONTRIBUTING.md`](CONTRIBUTING.md) § Merge gate.

Hiçbir ajan bu üç kapıdan biri **pending** veya **fail** iken `main`'e
merge etmez, merge'i hazır saymaz veya merge önerisini uygulamaz:

1. **Zorunlu CI yeşil.** `.github/workflows/ci.yml` CheckRun'ları: `test`,
   `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`.
2. **Güvenlik incelemesi tamamlanmış ve temiz.** CheckRun adı:
   `Cursor Security Agent: Security Reviewer` (GitHub app: `cursor`; canlı
   doğrulama: `candasoz01-cmd/lumos-core#755` / `#762` · Checks API ·
   2026-08-19T17:31Z). Check henüz yoksa, queued/in_progress ise veya
   conclusion SUCCESS değilse **pending** sayılır. "Security reviewer henüz
   çalışıyor" merge yasağıdır.
3. **Açık insan onayı.** Ajan, bot veya GitHub App review'ı insan onayı
   yerine geçmez. GitHub required-review sayacı bunu ayırt etmez; kural
   yazılı normdur.

`layer1a.yml` ve `prod-smoke.yml` PR merge kapısı değildir. Branch protection
`main`'de açıktır ama `required_status_checks` listesi boştur; fiziksel kilit
Settings'te required check eklenene kadar yoktur. Ajan yine de bu üçlü
sözleşmeyi uygular. Durum bildirimi bir sonraki bölümün formatını kullanır.

## PR / CI / Deploy doğrulama (tüm ajanlar)

- PR, CI, merge veya deploy durumu bildirirken canlı doğrulama yapılır.
  Kullanılan doğrulama yöntemi (GitHub API, `gh`, `git` veya eşdeğer canlı
  kaynak) açıkça belirtilir.

- Durum bildirimi aşağıdaki bilgileri içerir:
  - owner/repo
  - PR numarası
  - durum
  - commit SHA (varsa)
  - doğrulama kaynağı
  - doğrulama zamanı

  Örnek:
  `candasoz01-cmd/lumos-core#277 · MERGED · d6d1eb7 · GitHub API · 2026-07-27T19:28Z`

- Yalnızca "#277 merged" gibi repo kimliği içermeyen ifadeler kullanılmaz.

- Canlı doğrulama yapılamıyorsa bu açıkça belirtilir. Tahmin veya eski bağlam
  kesin bilgi olarak sunulmaz.

- Kaynaklar çelişiyorsa çelişki gizlenmez. Yeniden doğrulama yapılır ve canlı
  doğrulama sonucu esas alınır.
