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

## Ajan koordinasyonu ve maliyet sınırı

- Her işin tek bir koordinatörü vardır. Yardımcı ajanlar birbirleriyle uzun diyalog
  kurmaz; bulgularını koordinatöre teslim eder. Son karar, kapsam birleştirme ve kullanıcı
  raporu koordinatörün sorumluluğudur.
- Aynı anda en fazla iki yardımcı ajan kullanılır. Paralel çalışma yalnız birbirinden
  bağımsız dosya kapsamları veya salt-okunur incelemeler için açılır. Tek hedefli ya da
  sıralı işlerde yardımcı ajan kullanılmaz.
- Yazma yetkisi açıkça verilmemiş yardımcı ajan salt-okunur çalışır. Farklı araçlar aynı
  checkout'ta eşzamanlı yazamaz. Dosya sahipliği ve worktree/branch kuralları için
  yukarıdaki claim düzeni geçerlidir; burada tekrarlanmaz.
- Yardımcı ajana tüm konuşma geçmişi yerine aşağıdaki kısa iş paketi verilir. Talimatlar
  ve ürün kuralları tekrarlanmaz; canonical belgelere bağlantı verilir.

```text
HEDEF:
KAPSAM:
DOKUNMA:
KANIT / BAŞARI ÖLÇÜTÜ:
ÇIKTI: En fazla 10 satır; bulgu, dosya, test, risk ve açık engel.
```

- Teslim raporu şu alanlarla sınırlıdır: `DURUM`, `DEĞİŞEN DOSYALAR`, `TEST KOMUTU VE
  SONUCU`, `AÇIK RİSK`, `SONRAKİ ADIM`. Test çalıştırılmadıysa veya bağımlılık eksikse
  bu açıkça yazılır; tahmini sonuç "geçti" olarak raporlanmaz.
- Aynı repo taraması ve aynı test paketi yardımcı ajanlarda tekrarlanmaz. Koordinatör
  ortak ön kontrolü bir kez yapar, görevleri daraltır ve final doğrulamasını bir kez
  çalıştırır.
- Yüksek muhakeme ve çoklu ajan yalnız güvenlik, mimari veya kanıtlanmış zor problemlerde
  kullanılır. Rutin arama, biçimlendirme ve dar test işleri daha düşük maliyetli akışta
  tutulur.
- Commit, push, PR, merge ve deploy görev metninde açıkça verilmedikçe ajan tesliminin
  parçası değildir. `main`'e yazma yetkisinin kendisi aşağıdaki *Kontrollü çekirdek
  yazıcısı ve üçlü kapı* bölümünde tanımlıdır; bu madde yalnız yardımcı ajana devredilen
  görevin varsayılan kapsamını sınırlar.

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

## Kontrollü çekirdek yazıcısı ve üçlü kapı (tüm ajanlar)

Hedef: [CONSTITUTION §11](docs/CONSTITUTION.md),
[ADR-027](docs/decisions/ADR-027-controlled-core-writer.md).
Normatif geçici rejim: [`CONTRIBUTING.md`](CONTRIBUTING.md) § Merge gate.

Dış ajanlar (Claude, Cursor, Codex, …) çekirdeği **sahiplenmez**. Araştırır,
önerir, patch üretir, test eder. `main`'e yazan taraf tek kontrollü Lumos
writer'dır; o writer yokken geçici üç kapı yürür. Ajan kendini writer
saymaz. Lumos (veya ajan) kendi güvenlik politikasını gevşetmez, yazma
yetkisini genişletmez, onay mekanizmasını kaldırmaz.

Hiçbir ajan bu üç kapıdan biri **pending** veya **fail** iken `main`'e
merge etmez, merge'i hazır saymaz veya merge önerisini uygulamaz. Sayaçlar
**o anki head SHA**'ya bağlıdır; head değişince sıfırlanır.

1. **Zorunlu CI yeşil.** `.github/workflows/ci.yml` CheckRun'ları: `test`,
   `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`.
2. **Güvenlik incelemesi tamamlanmış ve temiz.** CheckRun adı:
   `Cursor Security Agent: Security Reviewer` (GitHub app: `cursor`; canlı
   doğrulama: `candasoz01-cmd/lumos-core#755` / `#762` · Checks API ·
   2026-08-19T17:31Z). Check henüz yoksa, queued/in_progress ise veya
   conclusion SUCCESS değilse **pending** sayılır. Cursor automation
   tetikleri (Marketplace: **PR Opened** + **PR Pushed**) draft açılışı
   kapsamaz; CheckRun gökten inmez. "Security reviewer henüz çalışıyor"
   veya "hiç doğmadı" aynı pending'dir.
3. **Açık insan onayı** — bugün kontrollü writer + yüksek-risk otoritenin
   vekili. Kapı 1–2 aynı SHA'da SUCCESS olduktan sonra, **o SHA için**
   istenir. Ajan/bot/App review yerine geçmez; "sanırım merge edilir"
   nihai onay değildir.

**Standing istisnası ([ADR-028](docs/decisions/ADR-028-standing-low-risk-merge-approval.md))
sınıftan önce gelir.** CheckRun `standing-class` classifier'ı **PR
checkout'tan çalıştırmaz**; `github.event.pull_request.base.sha`
üzerindeki `src/standing_merge` ayrı dizine çıkarılır. Base'de yoksa
fallback yoktur — fail-closed FAILURE. Yollar `git diff -z` ile
NUL-delimited gider, çağrı `--` kullanır; `-` ile başlayan path excluded'dır.
`python3 -m standing_merge.classify` değişen dosyalara bakılır. Üç durum: `excluded` (yasak) ·
`semantic_review` (yol karar vermeye yetmez; olgu/norm insanca ve head SHA'ya
bağlı değerlendirilir) · `eligible` (dar makine-güvenli sınıf). Yalnız
`eligible` standing açar. `semantic_review` **yasak değil, karar verilmemiş**
demektir: olgu/norm değerlendirilip sonuç `--attest factual|normative
--attest-sha <head>` ile taşınır. `factual` → eligible, `normative` →
excluded, yok/bayat → semantic_review kalır. Attestation hard-exclusion'ı
terfi ettiremez ve sonraki head SHA'ya taşınmaz. Hariç veya belirsiz →
standing merge yok, kapı 3 durur. CheckRun `standing-class` hariçte fail olur: bu
standing yasağıdır, insan merge yasağı değil. Bu CheckRun GitHub required
check **yapılmaz**; o, insan onaylı hariç PR’ı da fiziksel kilitler.
Fiziksel kilit ayrı `merge-authority` modeli ister. PR gövdesindeki
“standing hattı yok” cümlesi tek başına otorite değildir. Listelenmeyen
yol `eligible` değildir; `docs/` altındaki genel bir belge de değildir
(semantic_review'a düşer). `docs/` altında security/privacy/permission adlı
dosya da hariçtir. Canlı ihlal: `#777` / [TD-20](docs/TECHNICAL_DEBT.md).

`layer1a.yml` ve `prod-smoke.yml` PR merge kapısı değildir. Branch protection
`main`'de açıktır ama `required_status_checks` listesi boştur; fiziksel kilit
Settings'te required check eklenene kadar yoktur. Ajan yine de bu sözleşmeyi
uygular. Durum bildirimi bir sonraki bölümün formatını kullanır.

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

## Cursor Cloud specific instructions

Standard commands live in the [Makefile](Makefile),
[CI workflow](.github/workflows/ci.yml), and
[docs/getting-started.md](docs/getting-started.md). The notes below are
Cloud Agent gotchas that those docs do not cover (or contradict on purpose).

- **`python` / `pytest` may be missing from PATH.** This image often has only
  `python3`. `pip install` (no venv) puts `ruff`, `pytest`, and `lumos` in
  `~/.local/bin`, which login shells get via `~/.bashrc`. Prefer
  `python3 -m ruff` / `python3 -m pytest`, or add `~/.local/bin` to `PATH`.
- **pytest needs PYTHONPATH + `KANDO_MOCK=1`.** `make test` sets both (CI
  parity). Bare `pytest` fails. `Makefile` uses `PYTEST := pytest`; if that
  binary is absent, export the same env and run `python3 -m pytest -q`.
- **Rust needs current stable, not the image's pinned 1.83.** Workspace
  edition is 2021, but a crates.io dep (`clap_lex` 1.1.0, checked
  2026-08-20T08:08Z) requires Cargo `edition2024`. `cargo 1.83` fails to parse
  that manifest. The environment start script runs `rustup default stable`
  (>= 1.85). Then `make test-rust`.
- **Astro `npm run dev` in this Linux cloud binds IPv6 localhost.** Use
  `http://localhost:4321`. `http://127.0.0.1:4321` refuses. This is the
  opposite of [getting-started](docs/getting-started.md) (macOS: prefer
  `127.0.0.1` to avoid IPv6 drift).
- **UI e2e serves `ui/dist`, not `astro dev`.** Build first (`npm run build`
  in `ui/`). `*-api` / tasks flows spawn `panel_tasks_server.py`. Task flows
  need panel user mode `full`; the harness calls `patchPolicyAllowTasks`
  (`ui/e2e/lib/panel-helpers.mjs`). The browser default is Limited mode.
