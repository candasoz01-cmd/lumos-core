# Lumos for Mac

Lumos’un mevcut web çalışma alanını native bir macOS penceresinde açan minimum uygulama kabuğu.

- Varsayılan giriş: `https://welockai.com/panel?source=desktop`
- Geliştirme URL’si: `LUMOS_APP_URL=http://127.0.0.1:4321/panel?source=desktop`
- Dış bağlantılar Lumos penceresi yerine varsayılan tarayıcıda açılır.
- Sohbet, dosya, görev ve onay davranışı mevcut panel/bridge sözleşmesini kullanır.

Derleme:

```bash
./macos/LumosApp/build-app.sh
```

Çıktı: `macos/LumosApp/dist/Lumos.app`
