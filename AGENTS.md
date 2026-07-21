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
