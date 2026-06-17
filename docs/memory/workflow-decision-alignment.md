# Workflow karar hizalaması — OD-008, OD-009, OD-010

> **Durum:** Karar taslağı (needs-review). **Uygulama değildir.** Bu belge `.cursor/rules`, `docs/workflow-rules.md` veya diğer workflow dosyalarında değişiklik yapmaz; yalnızca OD-008/009/010 için netleşen ve hâlâ açık kalan ilkeleri kayıt altına alır.

---

## 1. Amaç

`docs/memory/project-workflow.md` içindeki **needs-review** maddeleri (OD-008, OD-009, OD-010) için tek bir karar taslağı oluşturmak:

- Continuous progress ile tek-adım önceliği arasındaki sınırı netleştirmek
- Agent-first kuralının workflow’daki yerini tanımlamak (kapsam genişletmesi olmadan)
- Test / CI doğrulaması ve kullanıcı onayı olmadan “tamamlandı” sayılmama kriterlerini hizalamak

Üst sınır: [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md). Çelişki durumunda çekirdek sözleşme esas alınır.

---

## 2. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| `.cursor/rules/**` değişikliği | Bu adım uygulama değildir |
| `docs/workflow-rules.md` düzenlemesi | Ayrı hizalama adımı gerekir |
| Kod, CI pipeline, hook veya otomasyon değişikliği | Davranış belgesi kapsamı dışı |
| Çok ajanlı rol sırası detayı | `kando-lumos-multi-agent.mdc` alanı; bu belge yalnızca workflow tamamlanma sınırına referans verir |
| Ürün onayı / kalıcı silme / vault | Çekirdek sözleşme; workflow OD’leri ile karıştırılmaz |

---

## 3. Netleşen ilkeler

Aşağıdaki maddeler **bu karar taslağında firm** kabul edilir; kaynaklar arasında örtüşen çekirdek ilkelerdir:

1. **Her görev tek hedefli ve dar kapsamlıdır.** Aynı oturumda birden fazla bağımsız problem birleştirilmez.
2. **Continuous progress, tek hedefi kırmaz.** Akış devam eder; her turda yalnızca **bir** somut ilerleme adımı sunulur.
3. **Görev, kullanıcı onayı olmadan kapatılmaz.** Ajan “bitti” demekle işi kapatamaz; kabul kullanıcıdadır.
4. **Test / doğrulama olmadan “tamamlandı” denmez.** Local doğrulama yetersizse CI zinciri tamamlanana kadar iş bitmiş sayılmaz (commit/push senaryolarında).
5. **Agent-first tercih edilebilir iş akışıdır** — kullanıcıyı gereksiz manuel adımdan korumak için — **ancak kapsam genişletme izni vermez.**
6. **Cursor/ajan yalnızca atanan işi yapar;** ek refactor, “hazır girmişken” yan düzeltme veya kapsam dışı dosya değişikliği yoktur.
7. **Bu belge uygulama adımı değildir.** Kuralların ve workflow dosyalarının güncellenmesi ayrı, onaylı bir iş paketidir.

---

## 4. Tek hedef / dar kapsam kararı

**Karar (firm):** Tüm geliştirme ve ajan oturumları **tek hedef, dar kapsam** ilkesine tabidir.

| Kaynak | İfade |
|--------|--------|
| `docs/memory/project-workflow.md` §2 | “Tek hedef, dar kapsam”; “Kapsam genişletme yok” |
| `docs/memory/project-workflow.md` §4 | Yalnızca atanan görev; birden fazla bağımsız problem birleştirilmez |
| `.cursor/rules/kando-lumos-multi-agent.mdc` | İstenmeyen refactor/özellik yok; cerrah dar kapsam |
| `.cursor/rules/cursor-run-verify-akisi.mdc` | PATCH: tek dosya, tek neden, en küçük değişiklik |

**Yorum:** “Continuous progress” veya “sonraki adım öner” ifadeleri **yeni hedef eklemek** anlamına gelmez; mevcut görevin doğrulanmış kapanışından sonra **sıradaki tek mantıklı adımı** önermek içindir.

---

## 5. Continuous progress sınırı

**OD-008 bağlamı:** `docs/workflow-rules.md` (Continuous Progress Rule) ile `.cursor/rules/tek-adim-ilerleme.mdc` arasında öncelik sorusu.

### Firm hizalama

| Katman | Kural | Öncelik |
|--------|-------|---------|
| **Görev kapsamı** | Tek hedef, dar kapsam | En üst — continuous progress bunu gevşetemez |
| **Yanıt formatı (tur başına)** | Yalnızca **bir** aksiyon / bir sonraki adım | `tek-adim-ilerleme.mdc` + `sonraki-adim-sorumluluk.mdc` |
| **Akış devamlılığı** | İş bitince durma önermeme; kısa özet + **tek** somut sonraki adım | `docs/workflow-rules.md` Continuous Progress |

### Çözüm özeti

- **Continuous progress ≠ aynı yanıtta çoklu iş.** Otomatik ilerleme, kullanıcının “şimdi ne yapıyoruz?” sorusunu azaltır; **her turda tek adım** kuralını iptal etmez.
- **Continuous progress ≠ kapsam genişletme.** Sıradaki adım, açık görev tanımı veya kullanıcı yönlendirmesiyle uyumlu olmalı; ajan kendi kafasına yeni hedef eklemez.
- **Durma kararı kullanıcıdadır** (`workflow-rules.md`); ajan “burada duralım” demez — ancak **riskli / geri dönüşsüz** işlerde açık onay ister (çekirdek sözleşme ile uyumlu).

### Needs-review (OD-008 kısmi)

- `docs/workflow-rules.md` ile `docs/memory/project-workflow.md` arasında **hangi belge birincil workflow canonical** olduğu henüz kapatılmadı.
- Continuous progress’in **güvenli dokümantasyon / planlama** ile **kod değişikliği** sınırı metin olarak örtüşüyor; tek cümlelik öncelik sırası indekste hâlâ `needs-review`.

---

## 6. Agent-first kuralının yeri

**OD-009 bağlamı:** Agent-first kuralının tek canonical kaynağı nerede tutulacak?

### Firm hizalama

| İlke | Durum |
|------|--------|
| Mümkünse önce agent ile yap (manuel adımı kullanıcıya yıkmadan önce) | Firm — davranış hedefi |
| Agent-first **kapsam genişletme izni vermez** | Firm |
| Komutlar kısa, tek hedefli, uygulanabilir | Firm — `workflow-rules.md` ile örtüşür |
| Atanan iş dışına çıkma yasağı geçerlidir | Firm — `project-workflow.md` §4 |

### Çift kayıt (needs-review — OD-009 açık)

Aynı veya çok yakın içerik şu an **birden fazla yerde** bulunuyor:

| Konum | İçerik |
|-------|--------|
| `docs/workflow-rules.md` | Agent-First Execution Rule |
| `.cursor/rules/agent-calisma-kurallari.mdc` | Agent-First Çalıştırma Kuralı (+ genel ajan disiplini) |
| `docs/memory/project-workflow.md` §4, migration tablosu | Atanan iş sınırı; agent-first `needs-review` |

**Karar taslağı:** Agent-first **tercih edilen iş akışı** olarak kalır; **canonical tek kaynak** seçimi bu belgede kapatılmadı — OD-009 `needs-review` devam eder.

**Önerilen yön (uygulama değil):** Uzun vadede `docs/memory/project-workflow.md` özet + `docs/workflow-rules.md` veya tek seçilmiş kural dosyası; çift kayıt birleştirmesi ayrı onaylı adım.

---

## 7. CI ve tamamlanma kriteri

**OD-010 bağlamı:** CI yeşil olmadan tamamlandı sayma kuralı workflow belgeleriyle tam hizalı mı?

### Firm tamamlanma kriterleri

Bir iş **tamamlandı** sayılmaz:

| Koşul | Kaynak |
|-------|--------|
| İlgili test / lint / doğrulanabilir çıktı yok | `project-workflow.md` §5 |
| Kullanıcı onayı / kabul yok | `project-workflow.md` §5; `lumos-karar-sozlesmesi.md` §6 |
| CI kırmızı (commit/push/merge sonrası senaryoda) | `kando-lumos-multi-agent.mdc`; `lumos-karar-ozet.mdc` |
| “Çalışıyor gibi” — kanıtsız iddia | Çok ajanlı disiplin; `project-workflow.md` §7 |

### Doğrulama zinciri (geliştirme)

Commit/push önerildiğinde esas alınan sıra (özet):

**RUN → VERIFY → LINT → GIT → CI RISK → COMMIT → PUSH** (`commit-oncesi-zincir.mdc`)

- Local test geçse bile **push sonrası en güncel CI run** yeşil değilse iş bitmiş sayılmaz.
- CI kırmızıysa teşhis önce **log** (`ci-diagnosis.mdc`); repo state tek başına teşhis kaynağı değildir.

### Needs-review (OD-010 kısmi)

- `project-workflow.md` §5 madde 3’te CI hizası açıkça `needs-review` işaretli; bu taslak firm kriterleri yazar ancak **tüm workflow dosyalarının senkron olduğunu iddia etmez**.
- **Sadece analiz/plan** görevlerinde CI’nin nasıl uygulanacağı (ör. yalnızca doküman değişikliği) ayrı netleştirme gerektirebilir — `needs-review`.

---

## 8. Kullanıcı onayı ve kapanış kuralı

**Firm:**

1. Görev **kullanıcı onayı olmadan kapatılmaz** (`project-workflow.md` §2, §5).
2. Ajan işi bitirdiğini düşünse bile **kabul kullanıcıdadır**; “tamamlandı” raporu öneri niteliğindedir.
3. Riskli işlemler (silme, deploy, kalıcı değişiklik, dış yazma) **açık onay** gerektirir — `docs/workflow-rules.md` ve `lumos-karar-sozlesmesi.md` ile uyumlu.
4. Continuous progress, **onaysız riskli iş** yapma izni vermez.

**Geliştirme commit’i:** Kullanıcı açıkça “commit at” demeden commit yapılmaz (user/agent kuralları); bu, görev kapanışından ayrı bir onay kapısıdır.

---

## 9. Çelişki çözüm sırası

Kaynaklar çeliştiğinde aşağıdaki sıra uygulanır (bu taslakta firm):

| Sıra | Kaynak | Gerekçe |
|------|--------|---------|
| 1 | `docs/lumos-karar-sozlesmesi.md` | Çekirdek sözleşme; üst sınır |
| 2 | `docs/memory/project-workflow.md` | Repo canonical workflow kaydı (`open-decisions-needs-review.md` indeks kuralı) |
| 3 | `.cursor/rules/*` (workspace) | Cursor oturumunda uygulanan operasyonel kurallar |
| 4 | `docs/workflow-rules.md` | Davranış/akış kuralı; `project-workflow` ile hizalanması devam eden alan |
| 5 | Bu belge (`workflow-decision-alignment.md`) | OD karar taslağı; uygulama değil — canonical değil, yönlendirme |

**Özel çelişki notları:**

- **Tek-adım vs continuous progress:** §5 — tek hedef üstün; tur başına tek aksiyon; akış devamı ayrı katman.
- **Local test vs CI:** CI kırmızıysa “tamamlandı” yok; öncelik CI > test çıktısı > git state (`kando-lumos-multi-agent.mdc`).
- **Agent-first vs dar kapsam:** Agent-first yalnızca **yürütme yöntemi**; kapsamı genişletmez.

---

## 10. Açık kararlar

| ID | Konu | Bu taslaktaki durum |
|----|------|---------------------|
| OD-008 | Continuous progress vs tek-adım önceliği | **Kısmi netleşti** — §5 firm sınır; canonical öncelik belgesi ve indeks durumu `needs-review` |
| OD-009 | Agent-first canonical kaynak | **Açık** — çift kayıt; tek canonical yer seçilmedi |
| OD-010 | CI tamamlanma kriteri hizası | **Kısmi netleşti** — firm “bitti” kriterleri §7; tüm workflow dosyaları senkron değil (`needs-review`) |

**Kapatılmayan sorular:**

1. `docs/workflow-rules.md` mi `docs/memory/project-workflow.md` mi birincil workflow canonical?
2. Agent-first metni hangi tek dosyada toplanacak?
3. Doküman-only / analiz-only görevlerde CI zorunluluğu nasıl sınıflandırılacak?
4. OD indeksinde OD-008/009/010 durumu `needs-review` → `aligned-draft` geçişi kim onaylar?

---

## 11. OD eşleme tablosu

| OD | Kaynak | Karar sorusu | Bu belgedeki karşılık | Durum |
|----|--------|--------------|------------------------|--------|
| OD-008 | `project-workflow.md` | Continuous progress ile tek-adım hangisi öncelikli? | §5 — tek hedef üstün; tur başına tek aksiyon; continuous progress durma önermeme + tek sonraki adım | Kısmi netleşti / needs-review |
| OD-009 | `project-workflow.md` | Agent-first tek canonical yerde mi? | §6 — davranış firm; kaynak birleştirme açık | needs-review |
| OD-010 | `project-workflow.md` | CI yeşil olmadan tamamlandı sayma tam hizalı mı? | §7 — firm kriterler; dosya senkronu açık | Kısmi netleşti / needs-review |

---

## 12. Sonraki adım

**Tek önerilen adım (uygulama değil):** Kullanıcı onayıyla OD-008/009/010 için ya (a) `docs/memory/project-workflow.md` migration tablosunda bu taslağa referans + durum güncellemesi, ya da (b) `docs/workflow-rules.md` ile `.cursor/rules` hizalama paketi planlanır — **bu adımda hiçbiri yapılmaz.**

---

## İlişkili belgeler

- [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) — OD indeksi
- [`project-workflow.md`](./project-workflow.md) — canonical workflow kaydı
- [`../workflow-rules.md`](../workflow-rules.md) — continuous progress / agent-first
- [`../lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — üst sınır

---

*Son güncelleme: 2026-06-17*
