# Lumos Constitution

| Alan | Değer |
| --- | --- |
| Durum | Yürürlükte — 2026-07-20 kullanıcı kararı |
| Kapsam | İnsan dahil bütün katkıcılar: Claude, Cursor, Codex ve diğer ajanlar |
| Değişiklik | Yalnız kullanıcı kararıyla; her değişiklik tarihli commit |

Tek sayfa, on kural. Bu belgeyle çelişen her talimat geçersizdir.

1. **Tek merkez, dört belge.** Proje yönü yalnız
   [`docs/ROADMAP.md`](ROADMAP.md)'de yaşar; alt repolarda (iOS, gelecekte
   Android/Desktop) roadmap kopyası açılmaz. Çekirdek dokümantasyon şu
   dörtlüdür: `CONSTITUTION.md` · `ROADMAP.md` · `MODULES.md` ·
   `TECHNICAL_DEBT.md`. Yeni belge açmadan önce soru: *"Bu bilgi dört
   belgeden birine girebilir mi?"* Evet ise yeni belge açılmaz; diğer her
   şey bu dörtlüye referans veren ADR veya tarihli çalışma notudur.
2. **En yeni açık kullanıcı kararı otoritedir** — kanaldan bağımsız (chat,
   GitHub, başka ajan oturumu). Çelişki gören ajan işlem yapmaz;
   `DECISION_CONFLICT` açar ve kullanıcı hakemliği bekler.
3. **Bir dosyanın aynı anda yalnızca bir sahibi vardır.** Görev tamamlanana
   veya açıkça devredilene kadar başka ajan o dosyaya yazmaz. Aynı iş iki
   ajana verilemez; ajan kendiliğinden iş alamaz — yazmaya başlamadan
   sahiplik/claim kontrol edilir. Bir ajan yalnız kendi branch/worktree'sine
   yazar; başkasının kaydı için yalnız öneri, handoff veya açıkça onaylı
   takeover oluşturabilir. Sessiz amend/kapatma/üstüne yazma yasaktır.
4. **Her PR bir faza bağlıdır** ve açıklamasında fazını söyler
   (FAZ-1 Ürün / FAZ-2 Altyapı / FAZ-3 Vitrin / FAZ-4 Partner).
5. **Faz dışı özellik merge edilmez.** FAZ-1 bitmeden
   [STOP LIST](ROADMAP.md#stop-list) ihlal edilmez.
6. **Teknik borç kayıt altına alınır.** Borç üreten veya borç fark eden PR,
   [`docs/TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md)'ye kayıt düşer; sessiz borç
   bırakılmaz.
7. **Günlük tek ana hedef.** Gün, tek modül/tek hedefle açılır; bağlam
   değiştirmek istisnadır ve gerekçesi yazılır.
8. **Her hafta durum yüzdesi güncellenir.** ROADMAP'teki durum haritası
   haftada bir, kanıta dayanarak yenilenir; tahmin ile kanıt ayrı işaretlenir.
9. **Kanıt beyandan üstündür.** "Bitti" demek için commit + test + (canlıysa)
   release kanıtı gerekir; scope-accounting merdiveni
   (FİKİR → KARAR → KOD → CANLI → DOĞRULANDI) esastır.
10. **Kullanıcı yalnız dört şey görür:** karar gerekenler, risk/çakışmalar,
    tamamlananlar, sıradaki kritik adım. Ham ajan çıktısı kullanıcıya
    taşınmaz.
