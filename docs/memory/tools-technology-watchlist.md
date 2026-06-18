# Araçlar, teknolojiler ve gelecek entegrasyon takip listesi — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından taşınan araç, teknoloji ve gelecek entegrasyon takip notlarının repo'daki **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir. **Gerçek credential, token, production endpoint veya özel entegrasyon detayı bu dosyaya yazılmaz.**

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |
| **Public repo sınırı** | Takip listesindeki araçlar public `lumos-core` sınırına uygun değerlendirilir; production/özel katman detayı taşınmaz. |

Taşıma süreci: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Değerlendirme ilkesi

1. **Rastgele veya toplu ekleme yok** — Projeye araç/teknoloji sebepsiz veya toplu halde eklenmez.
2. **Tek parça, zamanı gelince** — İhtiyaç doğduğunda **bir araç/teknoloji** değerlendirilir; çekirdek panel / görev / güvenlik akışı korunur.
3. **Önce test, sonra süreç** — Faydalı görünen araçlar önce denenir; uygun olanlar sürece entegre edilir.
4. **Watchlist ≠ entegrasyon** — Bu dosyadaki maddeler otomatik uygulanmaz; yalnızca takip ve değerlendirme adayıdır.

---

## Reverse engineering / firmware araçları

| Araç | Durum | Not |
|------|-------|-----|
| **Ghidra** | `[needs-review]` | Kando/Lumos güncellemeleri için takipte. Potansiyel kullanım: reverse engineering, firmware analizi, decompile/disassemble, cihaz yazılım mantığı inceleme. |

**Kapsam uyarısı:** Ghidra entegrasyon kapsamı ve public repo sınırı netleştirilmeden uygulama yapılmaz. `[needs-review]`

---

## Vibe coding ve prototip araçları

| Kategori | Durum | Not |
|----------|-------|-----|
| **Çin menşeli AI uygulama / prototip üretim araçları** | `[needs-review]` | Vibe coding çözümleri — güvenlik ve veri sınırı değerlendirmesi gerekir. |
| **Google AI Studio + Cursor + Android Studio akışı** | `[migrated]` | Mobil / prototip geliştirme için birincil izlenen akış. |
| **Çin menşeli alternatifler** | `[needs-review]` | Aynı ihtiyaç için alternatifler; önce test, uygun olanlar benimsenir. |

**İlke:** Çalışan araçlar test edilir; sürece uygun olanlar benimsenir.

---

## OpenAI ajan ve computer-use araçları

| Araç / yetenek | Durum | Değerlendirme odağı |
|----------------|-------|---------------------|
| **OpenAI Agents SDK** | `[migrated]` | Kontrollü kullanıcı-ajan aksiyonları |
| **Realtime / voice agent modelleri** | `[migrated]` | Doğal sesli ajan deneyimi |
| **Computer Use** | `[migrated]` | Çok adımlı bilgisayar görevleri |
| **Codex Plugins** | `[migrated]` | Güvenli sistem bağlantıları |

Tüm maddeler watchlist'te; otomatik entegrasyon yok. Değerlendirme: kontrollü aksiyon, onay modeli ve public repo sınırı ile hizalı mı?

---

## Connector ve dış sistem araçları

| Sistem | Durum | Not |
|--------|-------|-----|
| **Takvim / Kişiler** | `[migrated]` | TW-D02 — OD-032 ilke onaylı; uygulama bekliyor — [`calendar-contacts-decision.md`](./calendar-contacts-decision.md) |
| **GitHub** | `[migrated]` | Bağlantı / plugin yaklaşımları takipte; OD-033 katman 1 |
| **Slack** | `[migrated]` | Bağlantı / plugin yaklaşımları takipte |
| **Google Drive** | `[migrated]` | Bağlantı / plugin yaklaşımları takipte |
| **Linear** | `[migrated]` | Bağlantı / plugin yaklaşımları takipte |
| **Notion** | `[migrated]` | Sayfa/görev bağlamı — OD-033 katman 4 |
| **Asana** | `[migrated]` | Görev/proje bağlamı — OD-033 katman 4 |

**Çapraz referans:** Onaylı karar [`work-tools-connectors-decision.md`](./work-tools-connectors-decision.md) (OD-033); izin omurgası [`external-integrations-permissions.md`](./external-integrations-permissions.md) — değerlendirme listesi; rastgele connector eklenmez.

---

## Kabul kriterleri

Bir madde watchlist'ten aşağıdaki aşamalara **yalnızca** bu kriterlerle geçer.

### Watchlist → değerlendirme (evaluation)

| Kriter | Açıklama |
|--------|----------|
| **Somut ihtiyaç** | Panel, görev motoru veya güvenlik akışında net bir boşluk / kullanım senaryosu var |
| **Tek aday** | Aynı anda yalnızca bir araç değerlendirilir |
| **Sınır uyumu** | Public repo, onay modeli ve çekirdek sözleşme ile çelişmiyor |
| **Risk notu** | `[needs-review]` maddeler için güvenlik / kapsam notu güncellenmiş |

### Değerlendirme → entegrasyon (integration)

| Kriter | Açıklama |
|--------|----------|
| **Test kanıtı** | Dar kapsamda denendi; sonuç dokümante |
| **Süreç uyumu** | Mevcut panel / görev / güvenlik akışını bozmuyor |
| **Onay modeli** | Dış etki veya credential gerekiyorsa kullanıcı onayı tanımlı |
| **Tek sorumluluk** | Entegrasyon tek commit / tek PR mantığında parçalanabilir |
| **İptal yolu** | Geri alınabilir veya feature-flag / opsiyonel bağlantı |

Watchlist'te kalan maddeler **entegrasyon adayı sayılmaz**.

---

## Riskler

| Risk | Etki | Azaltma |
|------|------|---------|
| **Toplu araç ekleme** | Bakım yükü, güvenlik yüzeyi | Değerlendirme ilkesi: tek parça, zamanı gelince |
| **Çin menşeli AI / vibe coding araçları** `[needs-review]` | Veri sızıntısı, belirsiz lisans / güvenlik | Önce izole test; public repo'ya taşınmadan sınır kontrolü |
| **Ghidra kapsamı** `[needs-review]` | Public OSS sınırı, firmware/RE iş yükü | Kapsam netleşmeden repo'ya kod veya otomasyon eklenmez |
| **OpenAI computer-use / ajanlar** | Kontrolsüz dış aksiyon | Onay modeli + güvenli geçit; otomatik bağlantı yok |
| **Connector credential'ları** | Sızıntı, yetkisiz erişim | `external-integrations-permissions.md` ruhu; credential bu dosyada tutulmaz |
| **ChatGPT kaynağı eskir** | Yanlış öncelik | Canonical kaynak `docs/memory/`; periyodik gözden geçirme |

---

## Migration tablosu

ChatGPT / oturum bağlamından bu dosyaya taşınan ana maddeler.

| Kaynak özeti | Hedef bölüm | Durum |
|--------------|-------------|-------|
| Değerlendirme ilkesi (rastgele ekleme yok, tek parça, test sonra süreç) | Değerlendirme ilkesi | `[migrated]` |
| Ghidra — RE / firmware takibi | Reverse engineering / firmware | `[needs-review]` |
| Çin menşeli vibe coding / prototip araçları | Vibe coding ve prototip | `[needs-review]` |
| Google AI Studio + Cursor + Android Studio | Vibe coding ve prototip | `[migrated]` |
| OpenAI Agents SDK, Realtime/voice, Computer Use, Codex Plugins | OpenAI ajan ve computer-use | `[migrated]` |
| GitHub, Slack, Google Drive, Linear connector yaklaşımları | Connector ve dış sistem | `[migrated]` |
| external-integrations-permissions ruhu | Connector ve dış sistem | `[migrated]` |
| Kabul kriterleri (watchlist → evaluation → integration) | Kabul kriterleri | `[migrated]` |

---

## Manuel eklenecek maddeler

Aşağıdaki şablon satırları boş bırakılmıştır; yeni takip maddeleri buraya eklenir.

| Araç / teknoloji | Kategori | Durum | Not | Eklenme tarihi |
|------------------|----------|-------|-----|----------------|
| | | `[queued]` | | |
| | | `[queued]` | | |
| | | `[queued]` | | |

**Durum kodları:** `[migrated]` · `[queued]` · `[needs-review]` · `[superseded]` — tanım: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

*Son güncelleme: 2026-06-17*
