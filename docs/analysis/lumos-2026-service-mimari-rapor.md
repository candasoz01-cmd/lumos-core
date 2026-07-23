# Lumos 2026 Mimari ve İsimlendirme Raporu — Repo Karşılaştırması (v2 — düzeltilmiş)

| Alan | Değer |
|------|-------|
| Durum | **Karar destek — rapor**; kod değişikliği yok, uygulama başlamadı, merge/PR kapatma yapılmadı |
| Tarih | 2026-07-23 |
| Kapsam | İç katman isimlendirmesi (Core/Local/Sentinel) — canonical karar zinciri + `lumos-core` tarafında uygulama durumu |
| Önceki sürüm | v1 (aynı dosya) — yanlış repo temelinde yazılmıştı; bu sürüm onun yerine geçer |
| Doğrulama anı | Bu rapordaki tüm "henüz / şu an / güncel" ifadeleri **2026-07-23 doğrulama turuna** aittir — anlık durum kaydıdır, kalıcı gerçek değildir. Sonraki oturumda GitHub/`git` durumu **yeniden kontrol edilmeden** bu ifadelere güvenilmemelidir. |

## 0. v1'e göre düzeltme

v1, yalnızca `lumos-core` (bu repo) içeriğine bakarak "Kando/Cando/Bando hâlâ canonical, Core/Local/Sentinel repoda yok" sonucuna varmıştı. Bu **yanlıştı** — analiz kapsamı eksikti. Gerçekte iki ayrı repo var:

- **`candasoz01-cmd/Lumos`** (private) — canonical karar deposu. Core/Local/Sentinel kararı burada verildi, ADR ve PR ile kilitlendi.
- **`candasoz01-cmd/lumos-core`** (bu repo, public) — uygulama/kod deposu. Karar buraya bir **doküman patch'i** olarak taşınacak; bu rapor hazırlanırken (2026-07-23) henüz doğrulanmış bir taşıma yoktu.

v1'in üç somut hatası ve düzeltmesi, aşağıda §5'te tablo halinde.

---

## 1. Özet

**Karar zaten verilmiş ve kilitli:** Kando → **Core**, Cando → **Local**, Bando → **Sentinel**; dış yüzey **Lumos** değişmedi. Bu, `Lumos` reposunda ADR taslağıyla (Accepted, 2026-07-23) ve merge edilmiş **PR #179** ile sabitlendi. Teknik tanımlayıcılar (`kando_bridge`, `KANDO_*`, `X-Kando-Token`, `src/kando/`, `packages/kando_*`) bu karara **dahil değil** — bilinçli olarak ayrı bir cutover işine bırakılmış (EXC-WIRE/ENV/PATH istisna kaydı).

**`lumos-core` tarafında durum — bu rapor hazırlanırken (2026-07-23) uygulama henüz doğrulanmamıştı; sebep karar değil, lojistikti:**

1. Karar için `lumos-core`'a uygulanacak bir **doküman patch'i** hazırlandı (35 dosya, tamamı `docs/`+2 test dosyası, sıfır `src/`/`packages/` değişikliği).
2. Bu patch bir cloud ortamında `lumos-core`'un `56e1e8a` taban commit'i üzerine **gerçekten uygulandı ve test edildi** (7 test geçti), sonuç commit `fbc3a03`.
3. Cloud ortamında yapılan push denemeleri **403 ile sonuçlandı**.
4. Kaybolmaması için sonuç, `Lumos` reposunda **PR #183** (OPEN, merge edilmedi) altında bundle+patch+`HANDOFF.md` olarak saklandı — kurtarma artifaktı, kendisi `lumos-core`'a hiçbir şey uygulamıyor.
5. `lumos-core` remote'unda `cursor/core-local-sentinel-naming-fad2` dalı için: **remote branch oluşturuldu ancak head commit taban SHA (`56e1e8a`) üzerinde kaldı; rename commit'i (`fbc3a03`) remote'a ulaşmadı** (doğrulandı: `git ls-remote origin refs/heads/cursor/core-local-sentinel-naming-fad2` → `56e1e8a…`).
6. Bu reponun (`lumos-core`) local/`origin` `main`'i şu an `74b5a17` — taban commit'ten (`56e1e8a`) 8 commit ileride. Repoda Core/Local/Sentinel içeriği **sıfır**.

Yani: **karar geçersiz veya tartışmalı değil; uygulama adımı (push → PR → CI → ayrı merge kararı) bu rapor hazırlanırken (2026-07-23) henüz tamamlanmamıştı.** Bu durum ilerleyen bir tarihte değişmiş olabilir — okuyan kişi güncel durumu yukarıdaki "Doğrulama anı" notuna göre yeniden kontrol etmelidir.

---

## 2. Canonical karar zinciri (`candasoz01-cmd/Lumos`, doğrulanmış)

| Kanıt | Durum | Not |
|-------|-------|-----|
| ADR taslağı — `docs/ops/karar-taslagi/2026-07-23-core-local-sentinel-adlandirma.md` | Durum: **Accepted** (2026-07-23) | Kando→Core, Cando→Local, Bando→Sentinel; "tek ADR", ikinci karar dosyası yok |
| **PR #179** — "docs: Kando/Cando/Bando → Core/Local/Sentinel adlandırma" | **MERGED** | Eşleme tablosu PR body'sinde birebir; "wire/env/paket toplu rename bu PR'de yapılmadı" notu var |
| `docs/ops/legacy-naming.md` | Salt tarihçe + guard EXC kaynağı | Kilitli eşleme tablosu; `X-Kando-Token`, `KANDO_*`, `packages/kando*`, `src/kando/`, `cando_local` → **EXC** (uyumluluk artığı, katman adı değil, ayrı cutover) |
| `docs/product/katmanlar.md` | v0 adlandırma sözleşmesi | Hedef ağaç: `Lumos → Core / Local / Sentinel`; **ileride** eklenecek ayrı seviye: Memory · Vision · Voice · Cloud · Studio |
| `config/naming/legacy_exceptions.json` | Makine-okunur EXC kaydı | Guard testlerinin allowlist kaynağı |

**Önemli düzeltme (kullanıcı tarafından işaret edildi, doğrulandı):** Core/Local/Sentinel = güncel iç omurga (kilitli, eşit seviye). Identity/Memory/Voice/Vision/Connect = **ayrı bir soru** — `katmanlar.md`'de "büyüme" bölümünde gelecekte eklenebilecek **yetenek/servis alanları** olarak listeleniyor, Core/Local/Sentinel ile aynı tablo satırında değil. Bunları sekiz eşit katman gibi ele almak yanlış okumaydı.

---

## 3. `lumos-core` tarafı — 2026-07-23 doğrulama turunda tespit edilen durum

### 3.1 Hazırlanan patch (uygulanmayı bekliyor)

`Lumos` reposu → `docs/ops/patches/2026-07-23-lumos-core-layer-rename/`:

| Dosya | İçerik |
|-------|--------|
| `lumos-core-layer-rename.patch` | 35 dosyalık docs-only diff — bugünkü `lumos-core main` (`74b5a17`) üzerinde `git apply --check` **temiz geçiyor** (dosya çakışması yok; doğrulandı bu oturumda) |
| `apply.sh` | Fail-fast apply script — repo kontrolü, temiz worktree, **tam taban SHA eşleşmesi** (`56e1e8a`), idempotent "already applied" kontrolü |
| `README.md` | Kullanım talimatı |

Yeni eklenecek dosyalar: `docs/decisions/ADR-018-internal-layers-core-local-sentinel.md`, `docs/memory/legacy-naming.md`, `docs/memory/od-061-legacy-layer-naming-retirement.md`, `tests/test_legacy_layer_names_retired.py`. Hiçbiri `src/` veya `packages/` dokunmuyor; `ADR-018` madde 5 teknik tanımlayıcıların bu kararla yeniden adlandırılmadığını açıkça yazıyor.

**Not — `apply.sh`'ın kendi kısıtı:** Script `HEAD == 56e1e8a` tam eşleşmesini şart koşuyor; bugünkü `main` (`74b5a17`) bu şartı karşılamıyor (8 commit ileride, ama dosya çakışması yok). Yani script doğrudan bugünkü `main` üzerinde çalıştırılamaz — ya `EXPECTED_BASE_SHA` override edilir ya da HANDOFF.md'deki worktree/bundle akışı izlenir.

### 3.2 Patch fiilen uygulandı ve test edildi — ama `lumos-core`'a değil, geçici bir ortamda

`Lumos` **PR #183** (OPEN, "docs(ops): lumos-core fbc3a03 handoff bundle (push 403)"):

- Kanıt zinciri (`HANDOFF.md`): taban `56e1e8a` → sonuç commit `fbc3a03`, doğrudan parent ilişkisi, `tests/test_legacy_layer_names_retired.py` + naming registry testleri **7 passed**, orijinal kirli worktree'ye dokunulmadı.
- **Açıkça yapılmadı:** `lumos-core` remote push (cloud **403**), `lumos-core` PR açma, `Lumos` **#180**'i kapatma, merge.
- PR açıklaması kendisi şunu belirtiyor: *"#183 ≠ lumos-core migration PR"* — bu PR yalnız kurtarma artifaktı, `lumos-core`'a hiçbir şey uygulamıyor, merge edilse bile.

### 3.3 Bu oturumda doğrulanan somut kanıtlar (`lumos-core` tarafında, salt okuma)

| Kontrol | Sonuç |
|---------|-------|
| `git ls-remote origin refs/heads/cursor/core-local-sentinel-naming-fad2` | `56e1e8a…` — remote branch oluşturuldu ancak head commit taban SHA (`56e1e8a`) üzerinde kaldı; rename commit'i (`fbc3a03`) remote'a ulaşmadı (HANDOFF.md'nin uyardığı tuzak doğrulandı) |
| `main` HEAD | `74b5a17` (taban `56e1e8a`'dan 8 commit ileride) |
| Repoda "Core/Local/Sentinel" / "Sentinel" içeriği | **Sıfır eşleşme** |
| Patch'in dokunduğu 35 dosyayla `56e1e8a..74b5a17` arası değişen dosyalar kesişimi | **Boş** — çakışma riski yok |
| `git apply --check` (bugünkü `main` üzerinde) | **Temiz geçiyor** |

### 3.4 `Lumos` reposunun kendi ilişkili PR'ı

| PR | Repo | Durum | Not |
|----|------|-------|-----|
| #179 | Lumos | **MERGED** | Kando/Cando/Bando → Core/Local/Sentinel kararı |
| #180 | Lumos | **OPEN** (kapatılmadı, merge edilmedi) | Eski/süperseded `lumos-core` migration PR'ı; HANDOFF.md sırasına göre yalnızca #179'un `lumos-core` push+PR+CI adımları tamamlandıktan **sonra** "superseded by #179" notuyla kapatılması planlanıyor — **kesinlikle merge edilmeyecek** şekilde işaretli |
| #183 | Lumos | **OPEN**, merge edilmedi | Kurtarma artifaktı (bundle+patch+HANDOFF.md) |

---

## 4. Paralel, isimlendirmeyle ilgisiz PR zinciri (#186/#187/#188)

Bu üç PR `candasoz01-cmd/Lumos` reposunda — Core/Local/Sentinel kararıyla **ilgisiz**, eski/stale PR'lardan (#149, #151, #148) içerik "carry" (taşıma) işlemi. **Durum güncellemesi (bu oturum içinde değişti, yeniden doğrulandı):** #186/#187/#188 önce DRAFT'tı, şimdi **MERGED**; taşıdıkları eski PR'lar (#149, #151, #148) da **CLOSED** (merge değil, "superseded" gerekçesiyle kapatma — kendi planlarıyla tutarlı).

| PR | Durum | Taşıdığı içerik | Not |
|----|-------|------------------|-----|
| #186 | **MERGED** | #149 — "Karar Güveni" kuralı + durum şablonu | Test: 5 passed; #149 → **CLOSED** (doğrulandı, merge değil) |
| #187 | **MERGED** | #151 — Üç Kapı + kanıt dokümanı | Test: 6 passed; #151 → **CLOSED** (doğrulandı, merge değil) |
| #188 | **MERGED** | #148 — faz1-136 kapsam brief (tarihli arşiv) | Test: 1 passed; #148 → **CLOSED** (doğrulandı, merge değil) |

Bu rapora yalnızca **mevcut durum** olarak, karıştırılmaması için ayrı bölümde not edildi — isimlendirme kararının bir parçası değil, aynı repoda eşzamanlı yürüyen başka bir iş akışı. Bu PR'ların merge edilmiş olması Core/Local/Sentinel kararının uygulama durumunu (§1, §3) **değiştirmez** — ayrı dosyalar, ayrı dallar, ayrı konu.

---

## 5. v1 hata düzeltme tablosu (referans)

| # | v1'in iddiası | Düzeltilmiş gerçek |
|---|---|---|
| 1 | Sentinel repoda hiç tanımlı değil | `Lumos` reposunda ADR ile kilitli; `lumos-core`'a taşınması bekleniyor |
| 2 | Kando/Cando/Bando hâlâ canonical | Emekli; canonical karar Core/Local/Sentinel'e geçti (ADR-018 hazır, henüz `lumos-core`'a uygulanmadı) |
| 3 | OD-027 "keep" kararı rename'i veto ediyor | Hayır — ADR-018 madde 5 açıkça ayırıyor: mimari ad değişir, teknik paket adı ayrı cutover |
| 4 | 8 katman eşit seviye | Yanlış — Core/Local/Sentinel = omurga; Identity/Memory/Voice/Vision/Connect = ayrı, ileride eklenecek yetenek alanları |
| 5 | Bu iş açık karar gerektiriyor | Karar kilitli; açık olan yalnızca **uygulama** (push/PR/CI/merge adımları) |
| 6 | persona-layers.md / product-rules.md güncel canonical | Hayır, tarihsel; patch bunları güncelleyecek ama henüz uygulanmadı |

---

## 6. Kando/Cando/Bando — artık tarihsel çerçeve (özet)

Önceki rapordaki tam kanıt listesi (dosya+satır, ~90 referans) hâlâ **doğru envanterdir** — ama bu isimler artık "aktif kural" değil, **emekliye ayrılmış, canonical karardan önceki durumu belgeleyen tarihsel kayıt**. Patch uygulandığında bu dosyaların çoğu (`docs/lumos-persona-layers.md`, `docs/product-rules.md`, `docs/project-map.md`, `docs/memory/internal-agent-layers.md`, IP sınıflandırma dosyaları) otomatik olarak güncellenecek. Canlı kod tarafı (`src/kando/`, `packages/kando_runtime`, `packages/kando_bridge`, `tests/kando/`, `tests/cando/`) bu patch'in **kapsamı dışında** — ADR-018 madde 5 ile bilinçli olarak ayrılmış, ayrı bir cutover kararı gerektiriyor.

---

## 7. Gerçekten açık olan adımlar (karar değil, lojistik)

1. **`lumos-core`'a push** — kurucu, `HANDOFF.md`'deki worktree+bundle akışıyla (`56e1e8a` tabanlı, `ff-only merge`, sonuç `fbc3a03`) veya `apply.sh`'ı `EXPECTED_BASE_SHA` override ile bugünkü `main` üzerinde çalıştırarak.
2. **`lumos-core` PR açma** — push sonrası, `base: main`.
3. **CI** — `tests/test_legacy_layer_names_retired.py` dahil.
4. **Merge kararı** — HANDOFF.md'de açıkça "ayrı" olarak işaretli; bu rapor merge varsaymıyor, önermiyor.
5. **Sonra** `Lumos` **#180**'i "superseded by #179" notuyla kapatma — **merge değil**, yalnızca kapatma, ve yalnızca 1-4 tamamlandıktan sonra.
6. Ayrı, bu ADR'nin kapsamı dışı: teknik tanımlayıcı cutover (`kando_bridge`→?, `KANDO_*`→?, `X-Kando-Token`→?, `src/kando/`→?) — kendi OD'sini gerektirir.
7. Ayrı: Identity/Memory/Voice/Vision/Connect'in `lumos-core` karşılığı — henüz hiçbir ADR'de tanımlanmadı.

**Bu rapor hiçbir adımı gerçekleştirmedi** — kod değiştirilmedi, commit/push/PR/merge yapılmadı.
