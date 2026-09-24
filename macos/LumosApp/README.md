# Lumos for Mac

Lumos’un mevcut web çalışma alanını native bir macOS penceresinde açan minimum uygulama kabuğu.

- Varsayılan giriş: `https://welockai.com/panel?source=desktop`
- Geliştirme URL’si: `LUMOS_APP_URL=http://127.0.0.1:4321/panel?source=desktop`
- Dış bağlantılar Lumos penceresi yerine varsayılan tarayıcıda açılır.
- Sohbet, dosya, görev ve onay davranışı mevcut panel/bridge sözleşmesini kullanır.

## Seçili metni çevir

Safari, Google Docs veya başka bir uygulamada metni seçip **⌃⌥⌘T** kısayoluna
basın; küçük **Lumos Çeviri** penceresinde kaynak metin ve Türkçe çeviri görünür,
**Kopyala** çeviriyi panoya alır.

- Kısayol, pencerenin altındaki “Kısayol: …” bağlantısıyla değiştirilir
  (en az ⌘, ⌥ veya ⌃ içermeli; Esc vazgeçer). Lumos açıkken çalışır.
- Seçim yalnız kısayola basıldığı anda okunur. Lumos klavyeyi, ekranı veya panoyu
  sürekli izlemez; kısayol Carbon hot key olarak yalnız bu tuş birleşimini alır.
- Önce macOS Erişilebilirlik ile seçili metin okunur. Google Docs gibi metni
  Erişilebilirlik’e vermeyen editörlerde Lumos o anda bir kez ⌘C gönderir, metni
  okur ve **önceki pano içeriğini geri yükler**. Pano geçmişi tutan araçlar bu
  ara kopyayı görebilir.
- Parola / güvenli giriş alanı odaktayken (güvenli giriş açıkken) metin alınmaz.
- Çeviri Apple Translation ile **cihaz üzerinde** yapılır (macOS 15+); seçilen
  metin Lumos sunucusuna gönderilmez ve kaydedilmez. Dil paketi eksikse macOS
  indirme onayı ister: Sistem Ayarları › Genel › Dil ve Bölge › Çeviri Dilleri.
  En fazla 5000 karakter çevrilir.

### Gerekli izin

**Erişilebilirlik** (Sistem Ayarları › Gizlilik ve Güvenlik › Erişilebilirlik ›
Lumos). Seçili metni okumak ve gerektiğinde tek seferlik ⌘C göndermek için
gerekir. Lumos bu izni kendisi istemez veya açmaz; izin yoksa pencerede açıklama
ve “Erişilebilirlik Ayarlarını Aç” düğmesi görünür. Ad-hoc imzalı her yeni
derlemede macOS izni geçersiz sayabilir; listede Lumos’u kapatıp yeniden açın.

### Mac’te doğrulama

1. `./macos/LumosApp/build-app.sh` ve `open macos/LumosApp/dist/Lumos.app`.
2. İzin vermeden Safari’de metin seçip ⌃⌥⌘T → izin açıklaması görünmeli.
3. Erişilebilirlik’te Lumos’u açın; Safari’de İngilizce paragraf seçip ⌃⌥⌘T →
   kaynak + Türkçe çeviri, “Kopyala” sonrası ⌘V ile çeviri yapıştırılmalı.
4. Panoya önce başka bir şey kopyalayın; Google Docs’ta metin seçip ⌃⌥⌘T →
   çeviri gelmeli, ardından ⌘V önceki pano içeriğini yapıştırmalı.
5. Hiçbir şey seçmeden ⌃⌥⌘T → “Seçili metin bulunamadı”.
6. Bir parola alanına odaklanıp ⌃⌥⌘T → “Parola veya güvenli giriş…” hatası;
   pano değişmemeli.
7. Kısayolu değiştirip eskisinin çalışmadığını, yenisinin çalıştığını ve uygulama
   yeniden açıldığında korunduğunu doğrulayın.

Derleme (Xcode 16+ / macOS 15 SDK):

```bash
./macos/LumosApp/build-app.sh
```

Çıktı: `macos/LumosApp/dist/Lumos.app`
