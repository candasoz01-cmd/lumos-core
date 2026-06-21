# Lumos Gizlilik Manifestosu (Taslak)

*Bu metin bir taslaktır; hukuki tavsiye değildir.*

---

## Lumos'a söz

Lumos, kullanıcının verisini bir ürün malzemesi olarak görmez. Güvenlik, onay ve şeffaflık çekirdek sözleşmenin parçasıdır — `docs/lumos-karar-sozlesmesi.md` ve ADR-012 Security Codex bu omurgayı tanımlar. Bu manifesto, o ilkelerin insan dilinde özeti ve taahhüdüdür: verin sende kalır, amacın dışına çıkmayız, hesap verebilirliği gizlilikle dengelemeyi reddetmeyiz.

## Satmayız

Kullanıcı verisi **satılmaz**. Profil, görev, not, kimlik veya cihaz bağlamı üçüncü taraflara ticari amaçla aktarılmaz; reklam ağlarına, veri broker'larına veya “anonimleştirilmiş” paket satışına girdi olmaz. Lumos’un iş modeli, verini başkalarına kiralamak üzerine kurulmaz. Ticari katmanlar ayrı olsa bile bu ilke ürün ailesi için sabittir.

## Reklam yok

Kullanıcı içeriği **reklam için kullanılmaz**. Yazdığın metinler, görevler, sohbet veya dosya özetleri hedefli reklam profili üretmek, davranışsal pazarlama yapmak veya “ilgi alanı çıkarımı” satmak için işlenmez. Lumos seni izlemek için değil, senin işini yapmak için vardır. İçerik yalnızca senin talebin ve onayın çerçevesinde, belirlenen amaç için işlenir.

## Audit: ne kaydederiz, ne kaydetmeyiz

Güven ve hesap verebilirlik için sınırlı bir audit izi tutulur; tam metin şema ayrı sözleşmelerde kalır (`guard_audit`, evidence continuity ruhu). **Kaydederiz:** riskli veya reddedilen işlemler (guard deny, policy blok), görev mutasyonlarının özeti, onay ve consent eksikliği gibi güvenlik sinyalleri — çoğunlukla *ne oldu*, *hangi kapıda durdu*, *hangi amaçla* düzeyinde. **Kaydetmeyiz:** parolalar, anahtarlar, ham kullanıcı metninin tamamı, üretim URL’leri veya kişisel tanımlayıcıların gereksiz kopyaları; journal ve loglar *demo-safe* özet taşır, içeriği reklam veya profil çıkarımına açmaz. Audit, seni gözetlemek için değil; sistemin söz verdiği gibi durduğunu kanıtlamak içindir. Bu denge bilinçlidir: şeffaflık ile mahremiyet arasında minimum gerekli kayıt.

## Kontrol sende

Karar katmanları nettir: okuma ve analiz onay gerektirmez; yazma, silme ve dış etki **açık onay** ister. Kilit, keystore, consent ve presence (ADR-012) online modda işlem öncesi kontrol sağlar; consent ile confirmation ayrı sinyallerdir — genel onay kapalıyken riskli adımlar öneri düzeyinde kalır. Kalıcı silme otomatik yapılmaz; çöp alanı sözleşmelidir, geri dönüş için tasarlanır. Offline modda dış ağ yoktur. Kontrol sende: Lumos, senin yerine “sessizce karar veren” bir aracı değil, onayını isteyen bir yardımcıdır.

## Şeffaflık ve sınırlar

Açık kaynak Lumos çekirdeği (`lumos-core`) demo-güvenli bir temeldir; üretim sırları, ticari orkestrasyon ve operasyonel backend detayları public sınırın dışındadır. Bu manifesto o foundation için güvenli ve tutarlıdır. Bölgesel entegrasyonlar ve üçüncü taraf araçlar (ör. Çin menşeli hizmetler) ayrı değerlendirilir; veri sınırı netleşmeden devreye alınmaz. Şeffaflık, her şeyi herkese açmak değil; *neyin nerede işlendiğini* anlamanı sağlamaktır.

## Kapanış

Lumos, güven verir ama manipüle etmez. Verini satmayız, içeriğini reklama çevirmeyiz, audit’i gizliliğe kurban etmeyiz. Bu taahhüt ürün evrimiyle birlikte güncellenir; değişiklikler açık ve geriye dönük izlenebilir kalır. Soruların için bu taslak başlangıç noktasıdır — son söz her zaman sende.
