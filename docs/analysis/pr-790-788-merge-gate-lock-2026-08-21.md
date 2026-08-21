# #790 / #788 merge-kapısı kilidi

| Alan | Değer |
|------|-------|
| Durum | **KARAR kaydı** — Anayasa §2; tarihli çalışma notu. ROADMAP / MODULES / CONSTITUTION değişmez |
| Tarih | 2026-08-21 |
| Faz | FAZ-2 Altyapı (merge-kapısı kaydı; ürün özelliği yok) |
| Merdiven | KARAR (kod yok; bu dosya yalnız kilit + canlı doğrulama) |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md) §2 §10 §11, [`CONTRIBUTING.md`](../../CONTRIBUTING.md) üçlü kapı, [ADR-028](../decisions/ADR-028-standing-low-risk-merge-approval.md), [`AGENTS.md`](../../AGENTS.md) |
| Bu ajan | Kontrollü çekirdek yazıcısı **değildir**. Politika gevşetilmez. |

2026-08-21 kullanıcı kararı (Constitution §2 — en yeni açık karar otoritedir):

> Sınırlar doğru kurulmuş.
> **#790:** karar vermek erken; kapıları bekleyelim. Head `9f91cfa` üzerinde 5 CI + Security Reviewer + Bugbot + unresolved thread 0 + mergeable temiz gelirse, o zaman kullanıcı **explicit merge onayı** verecek.
> **#788:** standing sınıfında (ADR-028). Kendi head’i değişmeden beş koşul temizlenirse kullanıcıdan ayrıca onay beklemeden merge edilebilir.
> **Arşiv/yan kalem tablosu artık kapanmış sayılır.**

---

## Kilit (bağlayıcı)

| PR | Kilit | SHA bağı |
|----|-------|----------|
| `#790` | **Bekle.** Merge yok. Merge-ready denmez. Bu turda merge onayı **istenmez**. Kapılar `9f91cfa` üzerinde SUCCESS olmadan explicit onay da yok. Head değişirse sayaç sıfırlanır. | `9f91cfa3d32c4614fee02edcd78781deb261b4b1` |
| `#788` | **Standing** (ADR-028). Beş koşul + **değişmeyen** head. Head değişirse standing taşınmaz. | `f2e6296dedcd720bf43f165b684d56ac58cd952d` |

`#790` yeni operatör giriş noktasıdır (`./lumos-meet`); PR gövdesi standing hattını **kullanmayacağını** yazar. Standing bu PR’a uygulanmaz.

Ajan `main`’e yazmaz. `gh` salt okunur. Bu ortamda `ManagePullRequest` merge eylemi **yok**; merge yeteneği uydurulmaz.

---

## Canlı doğrulama

Kaynak: `gh` + GitHub Checks API + GraphQL reviewThreads. Repo: `candasoz01-cmd/lumos-core`.

### #790 — wait lock vs live merge

`candasoz01-cmd/lumos-core#790` · MERGED · `9f91cfa3d32c4614fee02edcd78781deb261b4b1` · GitHub API (`gh pr view` + Checks API) · 2026-08-21T15:19Z

- Head beklenen SHA ile **eşleşir** (`9f91cfa` = `9f91cfa3d32c4614fee02edcd78781deb261b4b1`). Sayaç sıfırlanmadı.
- Merge: `2026-08-21T15:15:29Z` · `candasoz01-cmd` (insan; bot değil) · merge commit `b39af65c4e4ff4df1c9e74e6e1f68996340b0fbc`
- Bu ajan **merge etmedi**. Chat kilidi «kapıları bekle, sonra explicit onay» idi. Aynı kullanıcının GitHub merge tıklaması sonraki açık insan eylemidir; ajan merge-ready ilan etmez.

Head `9f91cfa` CheckRun (Checks API · 2026-08-21T15:19Z):

| Kapı | CheckRun | App | Sonuç |
|------|----------|-----|-------|
| CI | `test` | `github-actions` | SUCCESS |
| CI | `rust` | `github-actions` | SUCCESS |
| CI | `macos-app-build` | `github-actions` | SUCCESS |
| CI | `ui-smoke` | `github-actions` | SUCCESS |
| CI | `ui-e2e` | `github-actions` | SUCCESS |
| Güvenlik | `Cursor Security Agent: Security Reviewer` | `cursor` | SUCCESS |
| Bugbot | `Cursor Bugbot` | `cursor` | SUCCESS |

Unresolved review thread: **0** (GraphQL · 2026-08-21T15:16Z). `mergeable` merge sonrası `UNKNOWN` (beklenen). Chat kilidi yine de ajan için «wait / not merge-ready» durur; merge’i insan yaptı.

### #788 — standing, SHA-bound

`candasoz01-cmd/lumos-core#788` · MERGED · `f2e6296dedcd720bf43f165b684d56ac58cd952d` · GitHub API (`gh pr view` + Checks API) · 2026-08-21T15:19Z

- Diff: yalnız `docs/decisions/ADR-023-lumos-representative-avatar.md` · +1/−1 (başlık tablosu **Uygulama durumu** olgusu). Kod yok.
- ADR-028 sınıf **dahil**: docs-only olgu düzeltmesi («ne doğrudur?»). Hariç listesine girmez (security / policy / governance / permissions / secrets / prod / veri sınırı / ödeme / controlled-writer / `docs/contracts/` / anayasa / ADR-027 yok). Kullanıcı 2026-08-21 kararı bu sınıfı açıkça onaylar.
- Merge: `2026-08-21T15:10:24Z` · `candasoz01-cmd` · merge commit `75f0445ef04547b6f79387ec3076f22244b20e7d`
- Head açılıştan beri değişmedi (`f2e6296`). Standing taşınmadı; aynı SHA.

Head `f2e6296` beş koşul (Checks API + GraphQL · 2026-08-21T15:19Z / 15:16Z):

| # | Koşul | Sonuç |
|---|-------|-------|
| 1 | CI `test` `rust` `macos-app-build` `ui-smoke` `ui-e2e` | 5/5 SUCCESS |
| 2 | `Cursor Security Agent: Security Reviewer` (`cursor`) | SUCCESS |
| 3 | `Cursor Bugbot` (`cursor`) | SUCCESS |
| 4 | Unresolved review thread | 0 |
| 5 | Merge conflict yok | Merge anında PR yorumu MERGEABLE/CLEAN; doğrulama anında state MERGED → `mergeable=UNKNOWN` |

Standing yetki **vardı** (sınıf + beş koşul + değişmeyen head). Bu ortam **merge edemez** (`gh` salt okunur; `ManagePullRequest` merge eylemi yok; `gh pr merge` kullanılmadı). Canlı sonuç: insan zaten merge etmiş.

---

## Arşiv / yan kalem tablosu — KAPALI

Açık takip listesi **değildir**. 2026-08-21 kullanıcı kararı tabloyu kapatır.

Repo taraması (`docs/analysis/`, `docs/memory/`, `docs/drafts/`, git, açık PR gövdeleri): «arşiv/yan kalem» adlı **açık** bir takip dosyası yoktu. Küme sohbet kararı + ilgili PR’lar. Snapshot:

| Kalem | Kapanış |
|-------|---------|
| `#788` ADR-023 uygulama-durumu olgusu | KAPALI — MERGED `f2e6296` · standing |
| `#790` `lumos-meet` launcher | KAPALI — chat kilidi wait; canlı MERGED `9f91cfa` (insan) |
| `#780` Meet avatar görsel dilimi | Bu tabloya **yeniden açılmaz** — CLOSED, merge edilmedi (2026-08-20T18:49:39Z) |

`#789` (TD-20 standing-class, draft, governance) ve `#782` (X-Ray FİKİR notu) **bu tablonun parçası değildir**; burada izlenmez.

---

## Ortam sınırı

- `gh` salt okunur: merge / yorum düzenleme yok.
- Bu alt ajanın araç listesinde `ManagePullRequest` **yok**; merge uydurulmaz.
- `#790` için PR içinde merge onayı **istenmedi**.
- Abonelik: `cursor-subscriptions` PR + CI (`#790` `representative-meet-launcher`, `#788` `adr-023-implementation-status`). Polling yok.
