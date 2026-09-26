<!-- markdownlint-disable MD013 -->

# İkinci Manifesto

> **Konum.** Kurucu kitabın iskeleti [`docs/lumos-book-outline.md`](../lumos-book-outline.md) içinde durur ve lumos-book-v0.1 olarak dondurulmuştur; yeni düşünce o dosyaya yazılmaz. Belge §8 Kurucu Manifestosu pusulayı taşır. Bu kitap o pusulayı yeniden kurmaz. İkinci Manifesto, kurucu metinde henüz yeri olmayan düşünce kayıtlarının evidir.
>
> **Gerekçe.** Repoda «İkinci Manifesto» adında bir bölüm veya dosya yoktur. Companion (Belge §13) uzun vadeli ürün vizyonudur; ADR-005 bellek katmanının mimari hedefidir. İkisi de bu düşüncenin evi değildir. Ürün mimarisi ve kod bu kayıtla değişmez.
>
> **Durum.** Yaşayan düşünce kaydı. İlk kayıt 2026-09-26. Vaat değildir. Kurucu kitabın Belge §11 kapısından geçmeden okuma sürümü veya kitap yayını sayılmaz.

## Kayıt 1 — Bilinç Uzantısında Ortak Hafıza

*2026-09-26*

İnsan hafızası eksiksiz bir arşiv değildir. Onun uzantısı da olmak zorunda değildir.

Lumos'un amacı, insanın yerine hatırlayan bir veritabanı olmak değil; insan ile yapay zekânın birlikte hatırladığı bir bilinç uzantısı oluşturmaktır. İnsan eksik hatırlar. Uzantı da eksik hatırlayabilir. Birlikte hatırlamanın işi, küçük bir izden doğru bağlama ulaşmaktır.

### Bağ

Aşağıdaki cümleler bu kayıtta yeniden keşfedilmiş gibi durmaz. Yalnız hafızaya düşen devamları ve henüz yazılmamış ayrımlar eklenir.

| Süregelen düşünce | Nerede durur | Bu kayıttaki yeri |
| --- | --- | --- |
| Lumos insanın yerine karar veren otorite değildir. | Kurucu kitap, Kitap §3. Gizlilik manifestosu, «Kontrol sende». Eğitim manifestosu: öğretmenin veya profesyonelin yerine geçmez. | Amaç cümlesi bunun hafıza halidir. Veritabanı, insanın yerine hatırlamaz. İlke burada yeniden yazılmaz. |
| Emin değilken kesin konuşulmaz. Veri yoksa boşluk doldurulmaz. | Kitap §4. [`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md), «Ne yapmaz». Karar sözleşmesi §6: belirsizlikte «anlamadım» ve örnek. | Ortak hatırlamada yeni biçim, yakın bağlam tutamağıdır. «Anlamadım» ve komut örneği, komut belirsizliğine aittir; burada tekrarlanmaz. |
| Belirsizlik hata değildir. Gizlenen belirsizlik hatadır. Hakem susmaz ve kesin de konuşmaz; ikilemi açık tutar. | [`BACKLOG.md`](BACKLOG.md), LUMOS-0005. | Karar ikilemi, güven düzeyi ve «son söz kullanıcıda» burada yeniden kurulmaz. Yeni olan, birlikte ulaşılamayan anının kendiliğinden sistem hatası sayılmaması ve tanınamama durumunun korunmasıdır. |
| «Her şeyi sakla» modeli yoktur. Geçmiş bağlam korunur; hafıza gereksiz şişmez. Hafıza düz not listesi değil, ilişki kurabilen bir katman olmayı hedefler. | [ADR-005](../decisions/ADR-005-memory-graph.md). | Mimari karar değiştirilmez. Yeni ölçü şudur: değer, deponun genişliği değil, küçük bir kayıttan doğru bağlama ulaşmaktır. |
| Kaynak uydurulmaz. Boş alan olabilir; yanlış alan olmaz. Araç verisi provenance taşır. | LUMOS-0003. [`welockai-charter-draft.md`](../analysis/welockai-charter-draft.md), hafıza ve provenance. | Aday ile özgün anı karışmaz. Yeni olan bu karışmama ayrımıdır; kaynak etiketi disiplininin kendisi değil. |
| Hatırlama, ürün kimliğini veya güvenlik çizgisini kullanıcı fark etmeden yeniden tanımlamaz. | [`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md), «Hatırlama». | Yaşanmış olayın yeniden yazılmaması ayrı konudur. Sonraki beyan bir zaman katmanıdır. Karar kaydındaki *supersedes* burada uygulanmaz. |
| Companion, bağlamı zamanla anlamayı hedefleyen uzun vadeli yol arkadaşlığıdır. | Kurucu kitap, Belge §13. | Ürün vizyonu olarak yerinde durur. Bu kayıt bir Companion özelliği ilan etmez. |

### Küçük kayıttan bağlama

Hafızanın değeri, çok geniş bir bağlamı saklamakta değildir. Küçük bir kayıttan doğru bağlama ulaşabilmektedir.

Bir olay kaydı kısa tutulabilir. Kısa kayıt, izsiz kayıt demek değildir. Olayın giriş, gelişme ve sonuç izleri durur. Bu izleri birbirine bağlayan çağrışımlar da durur. Böylece aynı olay başından, ortasından veya sonucundan yakalanabilir. Tutamak değişir; olay değişmez.

İnsan bir olayı tarih damgasıyla, sohbet kimliğiyle veya mesaj numarasıyla aramaz. Bunlar makinenin indeksidir. İnsana yaşanmış bağlam verilir: ne yapılıyordu, ne olmuştu, kim veya ne oradaydı, hangi fikirle ilişkiliydi, öncesinde veya sonrasında ne konuşulmuştu.

### Ortak hatırlama

Kesin eşleşme yoksa Lumos susmaz. Tek bir cevabı da zorlamaz. Hatırlayabildiği yakın bağlamları kısa tutamaklar halinde sunar.

> Bunları hatırlıyorum; hangisini kastettiğini tam yakalayamadım.

Bu cümle, kullanıcının kendi hafızasını tetikleyen ortak hatırlama sürecidir. Kurucu cevap disiplini boşluk doldurmayı ve sahte kesinliği zaten yasaklar. Hakem modeli, belirsizlikte susmayı da kesin konuşmayı da reddeder. Ortak hafızada bu yasağın biçimi karar ikilemi değildir. Yaşanmış tutamaktır.

İnsan da her şeyi hatırlayamaz. İnsan ve Lumos birlikte doğru kaynağa ulaşamıyorsa, bu kendiliğinden sistem hatası değildir. Belirsizlik, ortak hafızanın doğal durumlarından biridir. Gizlenen belirsizlik hâlâ hatadır. Burada eklenen ayrım şudur: ulaşılamayan anı, bir arıza kaydına zorla çevrilmez.

### Zaman katmanı

Kullanıcı baştan olayı hatırlamadığını söylüyorsa, «kesinlikle bu değildi» demesi geçmiş kaydı silmek veya değiştirmek için tek başına yeterli kanıt değildir. Sonraki hatırlama ve sonraki beyan, geçmiş kaydın üzerine ayrı bir zaman katmanı olarak eklenir. Geçmiş yeniden yazılmaz.

Lumos'un getirdiği doğru kayıt, kullanıcı tarafından o anda tanınmayabilir. Bu yüzden «doğrulandı» ve «reddedildi» ikilisinin yanında üçüncü bir durum durur: tanınamadı, ya da belirsiz kaldı.

Lumos'un önerdiği aday, kullanıcının özgün anısıyla karıştırılmaz. Kaynağın kimden geldiği korunur. Ne kadar kesin olduğu da korunur. Biri Lumos'un tuttuğu adaydır. Öteki, insanın o andaki beyanıdır. İkisi aynı cümlede eritilmez.

### Başarı

Başarı yalnız «yapay zekâ doğru cevabı tek seferde buldu mu» sorusuyla ölçülmez. İki soru birlikte sorulur. Doğru anı, farklı çağrışım noktalarından erişilebilir kılınabiliyor mu. İnsan ile Lumos, birlikte hatırlama döngüsünü sürdürebilir mi.

### Yüzük

Bir yüzük dün kaybolur. Düşme sesi duyulur. Koltuk civarında aranır. Ertesi gün bulunur.

Kayıt bu izleri ve aralarındaki çağrışımı taşıyorsa, aynı olay dört uçtan yakalanır.

- «Dün ne kaybettim?» girişten girer.
- «Sesini duyduğum neydi?» duyulan sesten girer.
- «Koltukları çekince ne çıktı?» aranan yerden girer.
- «Bugün neyi buldum?» sonuçtan girer.

Dört soru aynı kısa kayda çıkar. Giriş, gelişme ve sonuç birbirine bağlı kaldığı için, hangi uçtan tutulursa tutulsun aynı bağlama varılır.

### Katılacak proje

«Bütün yapay zekâların katılacağı proje» diye bir iz duruyor olabilir. İnsan bu izi sonra tanımayabilir. Tanımamak, izi yanlış kılmaz. Doğru kayıt o anda tanınmayabilir; insanın kendi hafızası da eksiktir. Lumos, tanınmayan doğruya uydurmak için geçmişi yeniden yazmaz.

İnsan baştan olayı hatırlamadığını söylüyorsa, o andaki «kesinlikle bu değildi» sonraki bir zaman katmanı olarak eklenir. Kayıt silinmez ve yerine yeni bir hikâye konmaz. Lumos'un getirdiği aday ile insanın beyanı ayrı kaynak olarak durur. Hangisinin kesin olduğu da yerinde kalır. Tanınamadı veya belirsiz kaldı durumu kapanmaya zorlanmaz. İnsan aynı olayı başka bir uçtan hatırlarsa, katmanlar hâlâ duruyordur. Birlikte hatırlama döngüsü sürmüş olur.
