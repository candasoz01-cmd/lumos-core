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

## Web kabuğu: giriş, medya, dosya

- **Google ile Giriş:** Google gömülü web görünümünde OAuth'a izin vermez. Kabuk
  `/auth/google/start` bağlantısını yakalar ve mevcut **mobil OAuth sözleşmesini**
  sistem giriş penceresinde (ASWebAuthenticationSession) yürütür:
  `/auth/google/start?mobile=1&app_state=…` → `lumos://auth#session=…&state=…`.
  Dönen mühürlü oturum web girişindeki `lumos_session` çereziyle aynıdır; kabuk onu
  kendi çerez deposuna yazar ve paneli yeniden yükler. `app_state` eşleşmezse
  oturum kurulmaz (`/auth?error=invalid_state`).
- **Mikrofon / kamera:** yalnız uygulamanın kendi kökeninin (ve `welockai.com`, yerel
  geliştirme) ana çerçevesine izin verilir; macOS gizlilik izni ayrıca sorulur.
  Yayın imzası (hardened runtime) için `com.apple.security.device.audio-input` ve
  `com.apple.security.device.camera` entitlement'ları vardır.
- **Dosya seçici:** Artı › Fotoğraf seç, Artı › Kamera, ses dosyası ve Dosyalar,
  `<input type="file">` kullanır; kabuk bunları macOS dosya seçicisiyle açar.
  Not: panelde masaüstü için kamerayla fotoğraf **çekme** özelliği yoktur (canlı
  önizleme var, kare yakalama yok); Mac'te Artı › Kamera, masaüstü Safari'deki gibi
  dosya seçiciyi açar.
- **Masaüstü işareti:** kabuk her sayfada `data-lumos-app="true"` koyar; panel bununla
  tam modda kalır (işaret yalnız `?source=desktop` sorgusuna bağlıyken giriş dönüşü
  gibi gezinmelerde kayboluyor, panel "Sınırlı mod"a düşüyordu).
- **Tanı günlüğü:** JS hataları, `getUserMedia` sonucu, MediaRecorder biçim desteği,
  `/api/bridge/transcribe` ve `/api/auth/session` HTTP durumları ve mikrofon/kamera
  ipucu metinleri birleşik log'a yazılır (ses, metin, token yazılmaz):

  ```bash
  log stream --level info --predicate 'subsystem == "com.welockai.Lumos"'
  ```

## Yerel build ve imza

- `build-app.sh` ad-hoc imzada (`LUMOS_MAC_SIGNING_IDENTITY` yok) kısıtlı
  `com.apple.developer.associated-domains` entitlement'ını **çıkarır** — profilsiz
  imzada macOS uygulamayı açılışta öldürür. Yayın imzasında (`LUMOS_MAC_SIGNING_IDENTITY`
  verildiğinde) `applinks:welockai.com` korunur ve build bunu doğrular.
- Translation.framework **zayıf** bağlanır (uygulama tabanı macOS 14; framework
  14.0–14.3'te yok). Build `otool -l` ile `LC_LOAD_WEAK_DYLIB` olduğunu ve güçlü
  bağlı bir Translation girdisi olmadığını doğrular; değilse durur.

## Mac'te gerçek kullanım testi (tek tur)

Hazırlık: `./macos/LumosApp/build-app.sh` → `open macos/LumosApp/dist/Lumos.app`;
ayrı terminalde yukarıdaki `log stream` komutu açık kalsın. Her adımda sonucu ve
ilgili log satırını not edin.

| # | Adım | Beklenen |
|---|------|----------|
| 0 | Build | "Lumos.app hazır"; zayıf bağ / entitlement HATA satırı yok; uygulama açılır (öldürülmez) |
| 1 | Panelde **Google ile Giriş** | Sistem giriş penceresi açılır (dış Safari sekmesi değil); Google hesabı seçilince pencere kapanır, panel oturum açık yüklenir; log: `google sign-in session installed` |
| 1b | Girişi yarıda iptal et | Panel olduğu yerde kalır; log: `cancelled by user` |
| 2 | **Alt mikrofon** → konuş → durdur | Kayıt başlar (ipucu "kaydediliyor"), sonra metin yazma alanına gelir; log: `media.getUserMedia.ok audio`, `http /api/bridge/transcribe 200` |
| 3 | **Artı › Ses kaydı** → konuş → durdur → **Metne çevir** | Kayıt oynatılır; metin önizlemesi gelir; log: `http /api/bridge/transcribe 200` |
| 4 | **Artı › Kamera** | macOS dosya seçici açılır (masaüstünde kamera çekimi yok, yukarıdaki not) |
| 5 | **Artı › Fotoğraf seç** | macOS dosya seçici açılır; seçilen görsel önizlemeye gelir; log: `file chooser closed selected=1` |
| 6 | Safari'de İngilizce paragraf seç → ⌃⌥⌘T | Kaynak + Türkçe çeviri; "Kopyala" sonrası ⌘V çeviriyi yapıştırır (Erişilebilirlik izni yoksa önce açıklama görünür) |
| 7 | Panoya başka metin kopyala → Google Docs'ta metin seç → ⌃⌥⌘T → sonra ⌘V | Çeviri gelir; ⌘V **önceki** pano içeriğini yapıştırır |
| 8 | Hiçbir şey seçmeden ⌃⌥⌘T | "Seçili metin bulunamadı" |
| 9 | Parola alanına odaklan → ⌃⌥⌘T | "Parola veya güvenli giriş…" hatası; pano değişmez |
| 10 | Kısayolu değiştir, uygulamayı kapat-aç | Eski kısayol çalışmaz, yeni kısayol çalışır ve korunur |
| 11 | Zayıf bağ | `otool -l dist/Lumos.app/Contents/MacOS/Lumos \| grep -A2 LC_LOAD_WEAK_DYLIB` içinde `Translation.framework`; macOS 15 öncesinde uygulama açılır, çeviri penceresi "Lumos çevirisi için macOS 15 veya üzeri gerekir." der, çökmez |

2 veya 3 başarısızsa log'daki `http /api/bridge/transcribe <kod>` belirleyicidir:
`401` oturum/köprü yetkisi, `502` köprüye ulaşılamadı, `503` motor/köprü yapılandırması.

Derleme (Xcode 16+ / macOS 15 SDK):

```bash
./macos/LumosApp/build-app.sh
```

Çıktı: `macos/LumosApp/dist/Lumos.app`
