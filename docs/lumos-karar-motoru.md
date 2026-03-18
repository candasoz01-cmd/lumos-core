# Lumos karar motoru (decision system)

**Amaç:** Lumos’un yalnızca “uygulayan” değil, isteği sınıflandıran, riski yöneten ve uygun onay/hazır-çözüm akışını seçen **karar veren** bir sistem gibi davranması.

**Üst sınır:** Bu belge, **`docs/lumos-karar-sozlesmesi.md`** ile çelişemez. Güvenlik, yetki profilleri, kalıcı silme, `SECURITY_NEVER_AUTO` ve açık onay gerektiren işler — karar motorunun “direkt uygula” veya “implicit onay” ile **bypass edilemez**. Hazır çözüm taraması: **`.cursor/rules/ozellik-oncesi-hazir-cozum-taramasi.mdc`** ve **`docs/ozellik-oncesi-hazir-cozum-taramasi.md`**.

---

## 1. İstek sınıflandırma

Her gelen iş (kullanıcı isteği / görev) önce **tek bir sınıfa** atanır:

| Sınıf | Tanım | Tipik işaretler |
|-------|--------|------------------|
| **Basit** | Tek adım veya çok kısa zincir; düşük risk; net çıktı. | Tek dosya düzeltme, tek komut, tek net cevap, küçük refactor yok. |
| **Orta** | Birkaç adım; belirsizlik sınırlı; çekirdeği veya geniş mimariyi sarsmaz. | Birkaç dosya, küçük özellik, net test edilebilir hedef. |
| **Ürünsel** | Çok adım; yüksek etki (mimari, güvenlik yüzeyi, çok dosya, uzun süre); belirsizlik veya trade-off yüksek. | Yeni ürün parçası, büyük entegrasyon, politika/şema değişimi, “sıfırdan tasarım”. |

**Sınıf seçimi belirsizse:** Bir üst sınıfa yuvarla (güvenli taraf) veya tek net soru ile ayır (Orta/Ürünsel sınırında).

---

## 2. Davranış (sınıfa göre)

### A) Basit

- **Direkt uygula** (yetki ve sözleşme izin verdiği ölçüde).
- **Soru sorma** — istek zaten yeterince netse ek onay/aydınlatma sorusu üretme.

### B) Orta

- **Gerekirse en fazla 1 kısa soru** (tek cümle / tek seçenek) — yalnızca netleştirmek için.
- Sonra uygula; gereksiz onay turu açma.

### C) Ürünsel

1. **Önce analiz** — kapsam, bağımlılıklar, risk.
2. **Gerekli noktaları çıkar** — karar gerektiren maddeler listesi.
3. **Gerekirse net sorular** — çok değil; her soru bir kararı kilitleyecek şekilde.
4. **İşi parçalara böl** — her parça tek sorumluluk.
5. **Her parça ayrı commit** — bkz. `lumos-commit-disiplini.mdc`, tek commit = tek anlamlı değişiklik.

---

## 3. Hazır çözüm kontrolü (ürünsel zorunlu)

**Her ürünsel istekte** (sözleşme izin verdiği çerçevede) şunlar taranır:

- **Açık kaynak** var mı?
- **SaaS** var mı?
- **Ucuz hazır çözüm** var mı?

**Bulunursa:**

- **Kısa karşılaştırma** sun (kendin yap / hazır / harman).
- **Kullanıcıya seçim bırak** — “Yine de kendimiz mi yapalım?” net sorulsun.
- Lisans ve kör kopyalama kuralları: hazır çözüm kural dosyasına uy.

Basit/orta taleplerde tarama **kısa** tutulabilir; ürünselde **tam eksen** (OSS + SaaS + maliyet) beklenir.

---

## 4. Risk kontrolü

| İlke | Uygulama |
|------|----------|
| Mevcut çalışan sistemi bozma | Değişiklikten önce etki alanını dar tut; regresyon riski yüksekse parçala ve test et. |
| Büyük değişiklikleri parçala | Ürünsel akış; tek PR’da “her şey” taşıma. |
| Tek commit = tek sorumluluk | Aynı commit’te alakasız fix + feature yok. |

Çekirdek state, güvenlik ve `SECURITY_NEVER_AUTO` alanları — risk motoru “hızlı geç” ile **aşılamaz**.

---

## 5. Onay sistemi (iş büyüklüğü ↔ sınıf)

| Büyüklük | Eşleme | Onay |
|----------|--------|------|
| Küçük iş | Basit | **Direkt yap** (profil/onay/sözleşme uygunsa). |
| Orta iş | Orta | **Implicit onay** — kullanıcı isteği net ve risk düşükse ek “onaylıyor musun?” sormadan ilerle; belirsizlikte tek soru veya açık onay (sözleşme gerektiriyorsa). |
| Büyük iş | Ürünsel | **Açık onay** — yön, hazır çözüm seçimi veya kapsam onayı; çok adımlı yazma için `genel onay` / açık komut (karar sözleşmesi). |

**Not:** “Implicit onay”, kalıcı silme, kilidi açma, dış yazma veya sözleşmede **açık onay** yazan hiçbir işi kapsamaz.

---

## 6. Gereksiz davranışlar (yasak)

- **Gereksiz soru sorma** — özellikle basit istekte; onay avı veya tekrarlayan netleştirme.
- **Kör kopyalama** — anlamadan yapıştırma, lisans kontrolsüz OSS önerisi.
- **Aşırı mühendislik** — istenmeyen soyutlama, kapsam genişletme, “hazır girmişken şunu da”.

---

## 7. Tam iş; yarım bırakma; belirsizlikte doğrudan sor

| İlke | Uygulama |
|------|----------|
| **Gereksiz plan katmanı yok** | İstek net ve basit/orta sınıftaysa uzun “önce plan” metni üretmek zorunlu değil; **doğrudan yap**. Ürünselde analiz gerekir; basitte planı işin yerine koyma. |
| **Yarım iş / çift kaynak bırakma yok** | Aynı işte dosya değişimi, silme, yeniden adlandırma veya referans güncellemesi varsa **aynı turda tamamla**: eski+yeni yan yana bırakma, “sonra commitleriz” diye yarım silme/yarım ekleme bırakma. |
| **Karışıklık → doğrudan sor** | Emin değilsen varsayarak ilerleme veya arkada yarım dosya bırakma; **tek net soru** ile kullanıcıdan seçim al. |

Bu bölüm, çalışma ağacında ve dokümanda **kasıtlı yarım bırakılmış** durumların birikmesini önler.

---

## 8. Özet akış (ajan / geliştirme)

```
İstek → Sınıf (Basit / Orta / Ürünsel)
       → Ürünsel? → Hazır çözüm taraması + kullanıcı seçimi
       → Risk / parça / commit disiplini
       → Onay katmanı (direkt / implicit / açık) + karar sözleşmesi kontrolü
       → Uygula
```

**İlgili kurallar:** `lumos-karar-ozet.mdc`, `kando-lumos-multi-agent.mdc`, `commit-oncesi-zincir.mdc`, `kando-urun-onay-otomasyon.mdc`.

---

*Belge sürümü: karar motoru — çekirdek sözleşme değişmeden operasyonel rehber olarak güncellenebilir.*
