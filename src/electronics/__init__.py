"""
Elektronik Uzmanı — pilot veri modeli, pilot erişim kontrolü ve boş sağlayıcı
(Provider) altyapısı.

Kapsam (bu faz): pilot erişim, arıza vakası, manuel ölçüm, bulgu/kanıt/güven
derecesi, yüksek risk uyarısı, ücretli özellik durum akışı (closed/pilot/
validated/paid), boş sağlayıcı registry'si.

Kapsam dışı (bu faz — bkz. docs/analysis/electronics-expert-pilot-design.md §8):
canlı E-Helper entegrasyonu, OCR, kamera ile otomatik teşhis, cihaz kontrolü,
programlayıcıya yazma, otomatik sipariş verme. Bu modül hiçbir dış servise
bağlanmaz, hiçbir cihazı kontrol etmez ve hiçbir ödeme/sipariş eylemi yapmaz.
"""
from __future__ import annotations
