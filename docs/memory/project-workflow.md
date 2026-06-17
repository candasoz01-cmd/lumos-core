# Proje geliştirme iş akışı — canonical kayıt

> **Politika:** ChatGPT Saved Memories **canonical değildir.** Bağlayıcı kayıt repo’daki `docs/memory/**` dosyalarıdır. Çelişki varsa repo metni esas alınır. Taşıma süreci: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## 1. Amaç

ChatGPT Saved Memories ve oturum bağlamından taşınan **geliştirme iş akışı** kurallarının tek kaynak kaydı. Ajanlar, Cursor oturumları ve geliştirici yönlendirmesi bu belgeyi referans alır.

Bu dosya otomatik senkronize edilmez; içerik manuel güncellenir.

---

## 2. İş akışı ilkeleri

| # | İlke | Açıklama |
|---|------|----------|
| 1 | **Tek hedef, dar kapsam** | Her görev tek hedefe odaklanır; kontrollü, dar kapsamlı ilerlenir. |
| 2 | **Hedef önce yazılır** | Her görevde amaç net ve açık biçimde önce tanımlanır. |
| 3 | **Minimum kod değişikliği** | Sorunu çözen en küçük diff tercih edilir; gereksiz genişletme yok. |
| 4 | **Test olmadan “bitti” yok** | Doğrulama yapılmadan tamamlandı denmez. |
| 5 | **Kullanıcı onayı olmadan kapanmaz** | Görev, kullanıcı onayı olmadan kapatılmaz. |
| 6 | **Kapsam genişletme yok** | Aynı anda birden fazla problem ele alınmaz; scope creep yapılmaz. |
| 7 | **Atanan iş dışına çıkma** | Cursor/ajan yalnızca atanan işi yapar; ek refactor veya yan düzeltme yapılmaz. |

### Ertelenen / kaldırılan iş takibi

Erteleme, iptal veya kapsam dışı bırakma durumları açık statü ile işaretlenir:

| Statü | Anlam |
|-------|--------|
| **silindi / iptal** | İş artık yapılmayacak; gerekçe kayıtlı. |
| **public'ten çıkarıldı, private'a taşınacak** | Public repo kapsamından çıkarıldı; private katmana taşınması planlanıyor. |
| **geçici ertelendi** | Bilinçli erteleme; yeniden açılma koşulu veya tarih not edilir. |
| **duplicate kapatıldı** | Başka bir görev/karar ile çakışıyor; tek kaynak referans verilir. |

---

## 3. Terminal ve komut kuralları

| # | Kural |
|---|--------|
| 1 | Komutlar **kısa, doğrudan** ve mümkünse **tek komut** olmalıdır. |
| 2 | Terminal komutlarında **yorum satırı kullanılmaz** (`#`, `//` vb.). |
| 3 | Açıklamalar normal metinde yazılır; **yalnızca çalıştırılabilir komutlar** kod bloğunda verilir. |
| 4 | **Python kodu terminal komutlarına karıştırılmaz.** FILE (dosya içeriği) ile TERMINAL (shell) ayrımı korunur. |

---

## 4. Cursor/ajan çalışma sınırları

| # | Sınır |
|---|--------|
| 1 | Yalnızca **atanan görev** yapılır; ek refactor, “hazır girmişken” düzeltme veya kapsam dışı dosya değişikliği yok. |
| 2 | Birden fazla bağımsız problem **aynı oturumda birleştirilmez**. |
| 3 | Ara raporlar kaybolmamalı; önemli kararlar **Kayıt/rapor disiplini** (§6) ile belgelenir. |
| 4 | Çekirdek sözleşme (`docs/lumos-karar-sozlesmesi.md`) ve workspace kuralları bu belgeyi gevşetemez. |

---

## 5. Test ve kabul

| # | Kural |
|---|--------|
| 1 | **Test etmeden tamamlandı denmez** — ilgili test, lint veya doğrulanabilir çıktı gerekir. |
| 2 | **Kullanıcı onayı olmadan iş kapatılmaz** — kabul kullanıcı tarafından verilir. |
| 3 | CI yeşil değilse “bitti” sayılmaz (needs-review: CI zinciri `.cursor/rules` ile hizalı mı — bkz. migration tablosu). |

---

## 6. Kayıt/rapor disiplini

Cursor oturumlarındaki **ara raporlar kaybolmamalıdır.** Önemli adımlar şu alanları içerecek şekilde belgelenir:

| Alan | İçerik |
|------|--------|
| **Karar gerekçesi** | Neden bu yol seçildi |
| **Denenen alternatifler** | Ne denendi, neden elendi |
| **Problem** | Somut semptom veya ihtiyaç |
| **Çözüm** | Uygulanan dar düzeltme veya karar |
| **Risk** | Bilinen yan etki veya belirsizlik |
| **Sonraki adım** | Tek net ilerleme adımı |
| **Proje bağlamı** | İlgili dosya, görev veya karar referansı |

Hedef belgeler: `docs/changelog/development-log.md`, `docs/journal/`, ilgili ADR veya görev notları.

---

## 7. Mock-gerçek çıktı ayrımı

| # | Kural |
|---|--------|
| 1 | **Mock görsel / üretilmiş ekran** gerçek çıktı gibi sunulmaz. |
| 2 | **Kanıt sayılan çıktılar:** gerçek ekran görüntüsü, terminal çıktısı, dosya içeriği. |
| 3 | Analiz **seçici ve ekonomik** olmalı; gereksiz geniş tarama veya tekrarlı kontrol yapılmaz. |

---

## 8. Migration tablosu

ChatGPT Saved Memories / oturum bağlamından taşınan maddeler.

| Kaynak (ChatGPT / oturum) | Durum | Proje ilgisi | Lumos etkisi | Not |
|---------------------------|-------|--------------|--------------|-----|
| Tek hedef, dar kapsam, kontrollü workflow | migrated | Tüm geliştirme oturumları | Ajan davranışı, görev tanımı | §2 |
| Her görevde hedef önce yazılır | migrated | Görev açılışı | Net kapsam, scope creep önleme | §2 |
| Minimum kod değişikliği | migrated | Cerrah/ajan düzeltmeleri | Çekirdek stabilite | §2; `.cursor/rules` ile uyumlu |
| Test olmadan “bitti” deme | migrated | Doğrulama zinciri | Kalite kapısı | §5 |
| Kullanıcı onayı olmadan görev kapatma | migrated | Görev kapanışı | Onay sözleşmesi | §5; `lumos-karar-sozlesmesi` ile hizalı |
| Scope creep yok; çoklu problem aynı anda yok | migrated | Oturum disiplini | Rol kapma önleme | §2, §4 |
| Cursor: sadece atanan iş; ek refactor/yan fix yok | migrated | Cursor agent | Kapsam disiplini | §4 |
| Ertelenen iş statüleri (silindi, private taşıma, ertelendi, duplicate) | migrated | Görev/backlog yönetimi | Public/private sınır takibi | §2 |
| Ara rapor alanları (karar, alternatif, problem, çözüm, risk, sonraki adım, bağlam) | migrated | Oturum → dokümantasyon | Bilgi kaybı önleme | §6 |
| Komutlar kısa, tek komut tercih | migrated | Terminal yönlendirme | Kullanıcı deneyimi | §3 |
| Terminalde yorum satırı yok | migrated | Komut formatı | Yanlış kopyalama önleme | §3 |
| Açıklama metinde; komut kod bloğunda | migrated | Yanıt formatı | FILE/TERMINAL ayrımı | §3 |
| Python kodu terminal komutuna karışmaz | migrated | Komut/dosya ayrımı | Hata önleme | §3 |
| Mock ≠ gerçek çıktı | migrated | Demo/panel | Yanıltıcı kanıt önleme | §7 |
| Kanıt: gerçek screenshot, terminal, dosya | migrated | Doğrulama | “Çalışıyor gibi” yasağı | §7 |
| Analiz seçici ve ekonomik | migrated | Keşif/tarama | Limit ve odak | §7 |
| Continuous progress / otomatik sonraki adım | needs-review | `docs/workflow-rules.md` ile örtüşme | Tek-adım kuralı ile çelişki riski | Repo’da ayrı belge var; hangisi öncelikli netleştir |
| Agent-first execution (önce agent dene) | needs-review | `.cursor/rules/agent-calisma-kurallari.mdc` | Davranış kuralı çift kayıt | Taşındı sayılabilir; canonical tek yer tercih edilmeli |
| CI yeşil olmadan tamamlandı sayma | needs-review | CI disiplini | `kando-lumos-multi-agent.mdc` ile hizalı | §5’e eklendi; detay CI kuralına referans |

---

## 9. Manuel eklenecek maddeler

ChatGPT Saved Memories’ten henüz taşınmamış veya yeni eklenen maddeler için şablon.

| # | Durum | ChatGPT / oturum metni (yapıştır) | Hedef bölüm | Not |
|---|--------|-----------------------------------|-------------|-----|
| 1 | `[queued]` | | | |
| 2 | `[queued]` | | | |
| 3 | `[queued]` | | | |
| 4 | `[queued]` | | | |
| 5 | `[queued]` | | | |

*(Boş satırlar kasıtlıdır; gerektiğinde yeni satır ekleyin.)*

---

## İlişkili belgeler

- [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md) — taşıma süreci ve durum tanımları
- [`product-rules.md`](./product-rules.md) — ürün ilkeleri
- [`../workflow-rules.md`](../workflow-rules.md) — continuous progress / agent-first (needs-review: hizalama)
- [`../lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — çekirdek sözleşme (üst sınır)

---

*Son güncelleme: 2026-06-17*
