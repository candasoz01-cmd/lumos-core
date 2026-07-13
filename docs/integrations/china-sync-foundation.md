# Çin entegrasyonları — senkron temeli

Durum: **implementation-started / credentials-required**

## İlk katalog

| Sağlayıcı | İlk kapsam |
|---|---|
| WeCom / WeChat Work | Kişiler, mesajlar, takvim |
| DingTalk | Kişiler, mesajlar, takvim, belgeler |
| Feishu | Kişiler, mesajlar, takvim, belgeler |
| Alipay Mini Program | Kimlik onayı, mini program bağlantısı |

## Güven sınırı

- Otomatik senkron kapalıdır.
- `start_sync` açık onay olmadan çalışmaz.
- Uygulama kimliği ve yetki bilgileri tanımlanana kadar durum
  `awaiting_credentials` kalır.
- Token veya uygulama sırrı repo içinde tutulmaz.
- Ödeme başlatma, para transferi ve tahsilat bu fazın dışındadır.

## Sonraki bağlantı adımı

Her sağlayıcı için resmi geliştirici hesabı, uygulama kimliği, dar OAuth/uygulama
yetkileri ve geri çağrı adresi tanımlandıktan sonra ayrı adaptör eklenir. İlk gerçek
senkron salt okunur başlar; yazma kapsamları ayrıca onaylanır.
