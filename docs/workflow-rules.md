# Workflow Rules — iş akışı kuralları

**Durum:** Aktif çalışma kuralı  
**Genişletilmiş canonical:** `docs/memory/project-workflow.md`  
**Sınırlar:** Bu belge davranış ve akış kurallarını tanımlar; kod, altyapı veya otomasyon değişikliği yapmaz.

---

## Kaynak önceliği

| Kaynak | Rol |
|--------|-----|
| `docs/lumos-karar-sozlesmesi.md` | Üst sınır |
| `docs/workflow-rules.md` (bu dosya) | Hızlı erişim iş akışı kuralları |
| `docs/memory/project-workflow.md` | Detaylı canonical |
| `.cursor/rules/*` | Cursor oturum kuralları (çift kayıt — birleştirme needs-review OD-008/009) |

---

## Continuous Progress Rule

**Statü:** **aktif kural**

**Kural:**

- Her tamamlanan işten sonra süreç otomatik olarak bir sonraki mantıklı adıma ilerler.
- Asistan «burada duralım», «şimdilik bu kadar», «yarın devam ederiz» gibi kapanış önerileri yapmaz.
- Durma kararını kullanıcı verir.
- Bir iş tamamlandığında asistan kısa durum özeti verir ve hemen sıradaki somut komutu/işi sunar.
- Yeni adıma geçmeden önce yalnızca gerçekten riskli, geri dönüşsüz veya kullanıcı onayı gerektiren işlem varsa açık onay ister.
- Kod, altyapı, ödeme, silme, deploy, database migration gibi riskli işlemler kullanıcı onayı olmadan yapılmaz.
- Güvenli dokümantasyon, not, planlama ve küçük kontrol işleri akış içinde devam ettirilir.

**Amaç:** Kontrollü devamlılık; kullanıcının sürekli «şimdi ne yapıyoruz?» diye sormasına gerek kalmaması.

---

## Agent-First Execution Rule

**Statü:** **aktif kural**

**Kural:**

- Kullanıcıya manuel terminal/tarayıcı adımı yaptırmadan önce, aynı işin Cursor/agent tarafından doğrudan yapılıp yapılamayacağı kontrol edilir; mümkünse önce agent ile yapılır.
- Kullanıcıya verilecek komutlar kısa, tek hedefli ve uygulanabilir olur.
- Gereksiz açıklama, çoklu alternatif ve sonradan çıkan sürpriz manuel adımlardan kaçınılır.

---

## Tek hedef ve dar kapsam

**Statü:** **aktif kural**

| # | Kural |
|---|--------|
| WF-001 | Her görev tek hedefe odaklanır; scope creep yok. |
| WF-002 | Hedef görev başında açık yazılır. |
| WF-003 | Minimum kod değişikliği — sorunu çözen en küçük diff. |
| WF-004 | Atanan iş dışına çıkılmaz; «hazır girmişken» refactor yapılmaz. |
| WF-005 | Test/doğrulama olmadan «bitti» denmez; kullanıcı onayı olmadan görev kapatılmaz. |

---

## Terminal ve komut formatı

**Statü:** **aktif kural**

| # | Kural |
|---|--------|
| WF-010 | **Açıklamalar kod bloğunda verilmez.** Normal metin veya madde listesi kullanılır. |
| WF-011 | **Yalnızca terminalde çalıştırılacak komutlar** terminal kod bloğunda verilir. |
| WF-012 | Terminal komut bloklarında yorum satırı (`#`, `//`) kullanılmaz. |
| WF-013 | Python veya dosya içeriği ile terminal komutu karıştırılmaz (FILE / TERMINAL ayrımı). |
| WF-014 | Komutlar kısa, doğrudan ve mümkünse tek komut olmalıdır. |

---

## Cursor görev metni ve kopyalama düzeni

**Statü:** **aktif kural**

| # | Kural |
|---|--------|
| WF-020 | Cursor'a verilecek **uzun görev metinleri** normal açıklama içinde gömülmez; **ayrı, kolay kopyalanabilir blok/alan** olarak verilir. |
| WF-021 | Terminal kod blokları **yalnızca** terminal komutları içindir; görev talimatı veya açıklama için kullanılmaz. |
| WF-022 | Görev metni bloğu ile komut bloğu birbirinden ayrı tutulur. |

**Örnek düzen (yapı — içerik görevde değişir):**

Görev açıklaması burada düz metin olarak yazılır.

---

KOPYALANACAK GÖREV METNİ:

HEDEF: ...
KURALLAR: ...
KAPSAM: ...

---

```bash
cd /Users/candasoz/work_2026/lumos-core
git status --short
```

---

## CI ve kapsam dışı madde takibi

**Statü:** **aktif kural**

CI geçsin diye çıkarılan kod, test veya doküman **kaybolmaz**. Her madde statülendirilir:

| Statü | Anlam |
|-------|--------|
| **silindi / iptal** | Artık yapılmayacak; gerekçe kayıtlı |
| **public'ten çıkarıldı, private/internal'a taşınacak** | Public repo dışı katmana planlı taşıma |
| **geçici ertelendi** | Bilinçli erteleme; yeniden açılma koşulu not edilir |
| **duplicate kapatıldı** | Başka kayıtla çakışıyor; tek kaynak referans verilir |
| **ileride değerlendirilecek** | Watchlist / OD maddesi; henüz uygulama yok |

Kayıt yeri: `docs/decision-log.md` (özet) ve ilgili `docs/memory/*.md` (detay).

---

## Kanıt ve mock ayrımı

**Statü:** **aktif kural**

| # | Kural |
|---|--------|
| WF-030 | Mock görsel veya üretilmiş ekran gerçek çıktı gibi sunulmaz. |
| WF-031 | Kanıt: gerçek ekran görüntüsü, terminal çıktısı veya dosya içeriği. |
| WF-032 | Analiz seçici ve ekonomik olmalı; gereksiz geniş tarama yapılmaz. |

---

## Araç değerlendirme (Cursor Automations vb.)

**Statü:** **ileride değerlendirilecek**

| Madde | Not |
|-------|-----|
| Cursor Automations | Zamanı gelince proaktif hatırlatılacak; hemen projeye bağlanmayacak. Uygun aşamada güvenli read/report mode gibi düşük riskli kullanım değerlendirilecek. Detay: `docs/tool-watchlist.md` |

---

## CI / workflow needs-review maddeleri

| ID | Konu | Statü | Not |
|----|------|--------|-----|
| WF-D01 | Continuous progress vs tek-adım kuralı | **ileride değerlendirilecek** | OD-008 |
| WF-D02 | Agent-first canonical tek kaynak | **ileride değerlendirilecek** | OD-009 |
| WF-D03 | CI yeşil = bitti hizası | **ileride değerlendirilecek** | OD-010 |

---

## İlişkili belgeler

- `docs/decision-log.md` — erteleme ve iptal günlüğü
- `docs/product-rules.md` — ürün kuralları
- `docs/project-map.md` — proje kökü ve dizinler

---

Son güncelleme: 2026-06-17
