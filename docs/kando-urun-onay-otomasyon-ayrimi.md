# Core / ürün: otomasyon ve kullanıcı onayı

Bu belge **ürün ve Core davranış modeli** içindir. **Git pre-commit / ruff / pytest** gibi geliştirme otomasyonu ile **karıştırılmamalıdır**.

| Katman | Otomasyon | Onay |
|--------|-----------|------|
| **Geliştirme** (commit guard) | Commit öncesi lint/test zorunlu olabilir | Geliştirici makinesi; `--no-verify` istisnası |
| **Ürün / Lumos çalışma anı** | Etkili işlem **kullanıcı onaysız yapılmaz** | Açık onay veya açık kullanıcı komutu |

## Ürün tarafı — temel kural

**Otomatik veya sessizce yapılmaz** (açık kullanıcı onayı / açık komut olmadan):

- Kalıcı **silme**
- Geri alınması zor **değiştirme** (canlı state / dosya)
- **Dışa gönderme** (network, harici servis yazımı)
- **Dış etkili** işlem
- **Kalıcı karar** (geri dönüşsüz sonuç)

## Serbest (onay gerektirmez)

- **Öneri** sunmak
- **Taslak** hazırlamak
- **Simülasyon / önizleme** (canlı state’e yazmadan)
- Okuma, analiz, plan metni (yetki profiline uygun şekilde)

## Uygulama

Canlı uygulama, yazma, silme, dış etki için **kullanıcı onayı veya açık komut** gerekir. Ayrıntılı karar katmanları: `docs/lumos-karar-sozlesmesi.md`.

---

*Geliştirme commit zinciri: `docs/dev-commit-guard.md`*
