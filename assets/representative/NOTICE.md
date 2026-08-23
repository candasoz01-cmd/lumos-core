# Representative avatar varlıkları

| Alan | Değer |
|------|-------|
| Dosyalar | `lumos-meet-idle.jpg` · `lumos-meet-speaking.jpg` |
| Boyut | 86 KB · 88 KB (1280×720) |
| Kullanım | Google Meet oturumunda Recall botunun görsel göstergesi |
| Sahiplik | **Lumos / We Lock AI'ye ait** — kurucu beyanı, 2026-08-22 |

## Ne oldukları

İki durumlu **soyut ışık göstergesi**: `idle` (sakin, dikey halkalar) ve
`speaking` (yayılan halkalar). İnsan yüzü, fotoğraf veya kamera görüntüsü
**değildir**; kişi içermez.

Bu bilinçli bir tasarım kararıdır: temsilci kendini yapay zekâ olarak tanıtırken
insan görünümlü bir yüz göstermesi beyanla çelişirdi. Soyut form o çelişkiyi
doğurmaz — bkz. [`ADR-023`](../../docs/decisions/ADR-023-lumos-representative-avatar.md)
§İfşa ilkesi madde 3.

## Teknik sınırlar

Yükleme fail-fast doğrular ve bot oluşturulmadan **önce** koşar:

- JPEG magic byte (`ffd8` … `ffd9`)
- Recall'un **1.3 MB** kare limiti

Sınırlar `src/representative/avatar.py` içinde sabittir.

## Değiştirilirse

Bu dosyalar değişirse beyan metni de gözden geçirilmelidir: beyan görüntünün
**üretilmiş bir gösterge, kamera değil** olduğunu söyler. Gerçekçi bir yüz veya
kamera görüntüsüne geçiş **ayrı kurucu kararı** gerektirir (ADR-023 madde 3).
