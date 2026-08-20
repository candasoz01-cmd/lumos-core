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
