# Workflow karar hizalaması — OD-008, OD-009, OD-010

> **Durum:** Karar onaylı (`decision-approved`). **Uygulama değildir** — bu belge `.cursor/rules`, `docs/workflow-rules.md` veya diğer workflow dosyalarında değişiklik yapmaz; yalnızca OD-008/009/010 için onaylanan ilkeleri kayıt altına alır. OD-010 için CI sınıflandırması (`doc-only` / `analysis-only`) **implementation-pending** kaldı.

---

## 1. Amaç

`docs/memory/project-workflow.md` içindeki **needs-review** maddeleri (OD-008, OD-009, OD-010) için tek bir karar kaydı oluşturmak:

- Continuous progress ile tek-adım önceliği arasındaki sınırı netleştirmek
- Agent-first kuralının workflow’daki yerini tanımlamak (kapsam genişletmesi olmadan)
- Test / CI doğrulaması ve kullanıcı onayı olmadan “tamamlandı” sayılmama kriterlerini hizalamak

Üst sınır: [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md). Çelişki durumunda çekirdek sözleşme esas alınır.

---

## 2. Canonical hiyerarşi

| Sıra | Kaynak | Rol |
|------|--------|-----|
| 1 | `docs/memory/project-workflow.md` | **Birincil workflow canonical** — karar ve hizalama referansı |
| 2 | `docs/workflow-rules.md` | **Davranış / akış destek belgesi** — `project-workflow` ile uyumlu olmalı |
| 3 | `.cursor/rules/**` | **Operasyonel uygulama katmanı** — Cursor oturumunda uygulanır; bu belge kuralları değiştirmez |

**Not:** Çekirdek sözleşme (`docs/lumos-karar-sozlesmesi.md`) tüm katmanların üst sınırdır (§9).

---

## 3. Kapsam dışı olanlar

| Kapsam dışı | Gerekçe |
|-------------|---------|
| `.cursor/rules/**` değişikliği | Bu adım uygulama değildir |
| `docs/workflow-rules.md` düzenlemesi | Ayrı hizalama adımı gerekir (implementation-pending) |
| Kod, CI pipeline, hook veya otomasyon değişikliği | Davranış belgesi kapsamı dışı |
| Çok ajanlı rol sırası detayı | `kando-lumos-multi-agent.mdc` alanı; bu belge yalnızca workflow tamamlanma sınırına referans verir |
| Ürün onayı / kalıcı silme / vault | Çekirdek sözleşme; workflow OD’leri ile karıştırılmaz |

---

## 4. Netleşen ilkeler

Aşağıdaki maddeler **onaylı** kabul edilir:

1. **Her görev tek hedefli ve dar kapsamlıdır.** Aynı oturumda birden fazla bağımsız problem birleştirilmez.
2. **Tek hedef / tek adım, continuous progress’ten önceliklidir.** Akış devam eder; her turda yalnızca **bir** somut ilerleme adımı sunulur.
3. **Görev, kullanıcı onayı olmadan kapatılmaz.** Ajan “bitti” demekle işi kapatamaz; kabul kullanıcıdadır.
4. **Test / doğrulama olmadan “tamamlandı” denmez.** CI yeşil olmadan (commit/push/merge senaryosunda) iş bitmiş sayılmaz.
5. **Agent-first tercih edilen yürütme yöntemidir** — kullanıcıyı gereksiz manuel adımdan korumak için — **ancak kapsam genişletme izni vermez.** Canonical kaynak: `project-workflow.md`.
6. **Cursor/ajan yalnızca atanan işi yapar;** ek refactor, “hazır girmişken” yan düzeltme veya kapsam dışı dosya değişikliği yoktur.
7. **Bu belge uygulama adımı değildir.** Kuralların ve workflow dosyalarının güncellenmesi ayrı, onaylı bir iş paketidir.

---

## 5. Tek hedef / dar kapsam kararı

**Karar (onaylı):** Tüm geliştirme ve ajan oturumları **tek hedef, dar kapsam** ilkesine tabidir.

| Kaynak | İfade |
|--------|--------|
| `docs/memory/project-workflow.md` §2 | “Tek hedef, dar kapsam”; “Kapsam genişletme yok” |
| `docs/memory/project-workflow.md` §4 | Yalnızca atanan görev; birden fazla bağımsız problem birleştirilmez |
| `.cursor/rules/kando-lumos-multi-agent.mdc` | İstenmeyen refactor/özellik yok; cerrah dar kapsam |
| `.cursor/rules/cursor-run-verify-akisi.mdc` | PATCH: tek dosya, tek neden, en küçük değişiklik |

**Yorum:** “Continuous progress” veya “sonraki adım öner” ifadeleri **yeni hedef eklemek** anlamına gelmez; mevcut görevin doğrulanmış kapanışından sonra **sıradaki tek mantıklı adımı** önermek içindir.

---

## 6. Continuous progress sınırı (OD-008)

**OD-008:** `decision-approved`

**Karar:** **Tek hedef / tek adım, continuous progress’ten önceliklidir.**

| Katman | Kural | Öncelik |
|--------|-------|---------|
| **Görev kapsamı** | Tek hedef, dar kapsam | En üst — continuous progress bunu gevşetemez |
| **Yanıt formatı (tur başına)** | Yalnızca **bir** aksiyon / bir sonraki adım | `tek-adim-ilerleme.mdc` + `sonraki-adim-sorumluluk.mdc` |
| **Akış devamlılığı** | İş bitince durma önermeme; kısa özet + **tek** somut sonraki adım | `docs/workflow-rules.md` Continuous Progress |

### Çözüm özeti

- **Continuous progress ≠ aynı yanıtta çoklu iş.** Otomatik ilerleme, kullanıcının “şimdi ne yapıyoruz?” sorusunu azaltır; **her turda tek adım** kuralını iptal etmez.
- **Continuous progress ≠ kapsam genişletme.** Sıradaki adım, açık görev tanımı veya kullanıcı yönlendirmesiyle uyumlu olmalı; ajan kendi kafasına yeni hedef eklemez.
- **Durma kararı kullanıcıdadır** (`workflow-rules.md`); ajan “burada duralım” demez — ancak **riskli / geri dönüşsüz** işlerde açık onay ister (çekirdek sözleşme ile uyumlu).

**Canonical referans:** `docs/memory/project-workflow.md` birincil; `docs/workflow-rules.md` davranış desteği (§2).

---

## 7. Agent-first kuralının yeri (OD-009)

**OD-009:** `decision-approved`

**Karar:** Agent-first **tercih edilen yürütme yöntemidir**; **kapsam genişletme izni vermez.** **Canonical kaynak:** `docs/memory/project-workflow.md`.

| İlke | Durum |
|------|--------|
| Mümkünse önce agent ile yap (manuel adımı kullanıcıya yıkmadan önce) | Onaylı — davranış hedefi |
| Agent-first **kapsam genişletme izni vermez** | Onaylı |
| Komutlar kısa, tek hedefli, uygulanabilir | Onaylı — `workflow-rules.md` ile örtüşür |
| Atanan iş dışına çıkma yasağı geçerlidir | Onaylı — `project-workflow.md` §4 |

### Kaynak katmanları (çift kayıt — uygulama bekliyor)

Aynı veya yakın içerik operasyonel katmanda da bulunur; **canonical tanım** `project-workflow.md`’dedir:

| Konum | Rol |
|-------|-----|
| `docs/memory/project-workflow.md` §4, migration tablosu | **Canonical** — agent-first + atanan iş sınırı |
| `docs/workflow-rules.md` | Davranış desteği — Agent-First Execution Rule |
| `.cursor/rules/agent-calisma-kurallari.mdc` | Operasyonel uygulama — değiştirilmez (bu adım) |

**Implementation-pending:** `docs/workflow-rules.md` ve `project-workflow.md` migration tablosunun bu kararla senkron edilmesi ayrı onaylı adımdır.

---

## 8. CI ve tamamlanma kriteri (OD-010)

**OD-010:** `decision-approved` / `implementation-pending`

**Karar:** **CI yeşil olmadan “tamamlandı” denmez** (commit/push/merge senaryosunda).

### Firm tamamlanma kriterleri

Bir iş **tamamlandı** sayılmaz:

| Koşul | Kaynak |
|-------|--------|
| İlgili test / lint / doğrulanabilir çıktı yok | `project-workflow.md` §5 |
| Kullanıcı onayı / kabul yok | `project-workflow.md` §5; `lumos-karar-sozlesmesi.md` §6 |
| CI kırmızı (commit/push/merge sonrası senaryoda) | `kando-lumos-multi-agent.mdc`; `lumos-karar-ozet.mdc`; **OD-010 onaylı** |
| “Çalışıyor gibi” — kanıtsız iddia | Çok ajanlı disiplin; `project-workflow.md` §7 |

### Doğrulama zinciri (geliştirme)

Commit/push önerildiğinde esas alınan sıra (özet):

**RUN → VERIFY → LINT → GIT → CI RISK → COMMIT → PUSH** (`commit-oncesi-zincir.mdc`)

- Local test geçse bile **push sonrası en güncel CI run** yeşil değilse iş bitmiş sayılmaz.
- CI kırmızıysa teşhis önce **log** (`ci-diagnosis.mdc`); repo state tek başına teşhis kaynağı değildir.

### Doc-only / analysis-only istisna sınırı (implementation-pending)

**Onaylı ilke:** Yalnızca doküman veya analiz görevlerinde, yerel pre-commit / test yeterliyse **CI sınıflandırması uygulama detayı** olarak kalır — kararın kendisi “CI yeşil = tamamlandı” kuralını gevşetmez; kod/commit/push senaryosunda CI zorunludur.

**Implementation-pending:** Bu sınıflandırmanın `project-workflow.md` §5 ve ilgili indekslerde nasıl yazılacağı henüz uygulanmadı.

---

## 9. Kullanıcı onayı ve kapanış kuralı

**Onaylı:**

1. Görev **kullanıcı onayı olmadan kapatılmaz** (`project-workflow.md` §2, §5).
2. Ajan işi bitirdiğini düşünse bile **kabul kullanıcıdadır**; “tamamlandı” raporu öneri niteliğindedir.
3. Riskli işlemler (silme, deploy, kalıcı değişiklik, dış yazma) **açık onay** gerektirir — `docs/workflow-rules.md` ve `lumos-karar-sozlesmesi.md` ile uyumlu.
4. Continuous progress, **onaysız riskli iş** yapma izni vermez.

**Geliştirme commit’i:** Kullanıcı açıkça “commit at” demeden commit yapılmaz (user/agent kuralları); bu, görev kapanışından ayrı bir onay kapısıdır.

---

## 10. Çelişki çözüm sırası

Kaynaklar çeliştiğinde aşağıdaki sıra uygulanır (onaylı):

| Sıra | Kaynak | Gerekçe |
|------|--------|---------|
| 1 | `docs/lumos-karar-sozlesmesi.md` | Çekirdek sözleşme; üst sınır |
| 2 | `docs/memory/project-workflow.md` | **Birincil workflow canonical** |
| 3 | `docs/workflow-rules.md` | Davranış/akış desteği; `project-workflow` ile hizalanmalı |
| 4 | `.cursor/rules/*` (workspace) | Operasyonel uygulama katmanı |
| 5 | Bu belge (`workflow-decision-alignment.md`) | OD karar kaydı; uygulama değil — yönlendirme |

**Özel çelişki notları:**

- **Tek-adım vs continuous progress (OD-008):** Tek hedef / tek adım üstün; tur başına tek aksiyon; akış devamı ayrı katman.
- **Local test vs CI (OD-010):** CI kırmızıysa “tamamlandı” yok; öncelik CI > test çıktısı > git state (`kando-lumos-multi-agent.mdc`).
- **Agent-first vs dar kapsam (OD-009):** Agent-first yalnızca **yürütme yöntemi**; kapsamı genişletmez; canonical: `project-workflow.md`.

---

## 11. Karar durumu özeti

| ID | Konu | Durum |
|----|------|--------|
| OD-008 | Continuous progress vs tek-adım önceliği | **decision-approved** — tek hedef / tek adım öncelikli (§6) |
| OD-009 | Agent-first canonical kaynak | **decision-approved** — tercih edilen yöntem; kapsam genişletmez; canonical: `project-workflow.md` (§7) |
| OD-010 | CI tamamlanma kriteri | **decision-approved** / **implementation-pending** — CI yeşil zorunlu; doc-only CI sınıflandırması uygulama bekliyor (§8) |

---

## 12. Açık kalan maddeler

| Konu | Kategori | Not |
|------|----------|-----|
| `project-workflow.md` migration tablosu + OD indeks senkronu | implementation-pending | Karar onaylı; metin güncellemesi ayrı adım |
| `docs/workflow-rules.md` hizalama | implementation-pending | Canonical hiyerarşi onaylı; dosya düzenlemesi bu adımda yapılmadı |
| Doc-only / analysis-only CI sınıflandırması metni | implementation-pending | OD-010 kararı net; uygulama detayı bekliyor |
| `.cursor/rules/**` | kapsam dışı | Operasyonel katman; bu belge değiştirmez |

**Kapatılan sorular (OD-008/009/010):**

1. ~~Birincil workflow canonical?~~ → `docs/memory/project-workflow.md`
2. ~~Agent-first canonical kaynak?~~ → `docs/memory/project-workflow.md`
3. ~~Continuous progress vs tek-adım?~~ → Tek hedef / tek adım öncelikli
4. ~~CI yeşil olmadan tamamlandı?~~ → Hayır (commit/push/merge senaryosunda)

---

## 13. OD eşleme tablosu

| OD | Kaynak | Karar sorusu | Bu belgedeki karşılık | Durum |
|----|--------|--------------|------------------------|--------|
| OD-008 | `project-workflow.md` | Continuous progress ile tek-adım hangisi öncelikli? | §6 — **tek hedef / tek adım öncelikli**; continuous progress durma önermeme + tek sonraki adım | **decision-approved** |
| OD-009 | `project-workflow.md` | Agent-first tek canonical yerde mi? | §7 — tercih edilen yöntem; kapsam genişletmez; **canonical: `project-workflow.md`** | **decision-approved** |
| OD-010 | `project-workflow.md` | CI yeşil olmadan tamamlandı sayma tam hizalı mı? | §8 — **CI yeşil zorunlu**; doc-only sınıflandırma implementation-pending | **decision-approved** / **implementation-pending** |

---

## 14. Sonraki adım

**Tek önerilen adım (uygulama — ayrı onay):** OD-010 `implementation-pending` kapsamında `docs/memory/project-workflow.md` migration tablosu ve `open-decisions-needs-review.md` indeksinde OD-008/009/010 durumlarını bu belgeye referansla güncellemek — **bu adımda yapılmaz.**

---

## İlişkili belgeler

- [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) — OD indeksi (senkron implementation-pending)
- [`project-workflow.md`](./project-workflow.md) — **birincil workflow canonical**
- [`../workflow-rules.md`](../workflow-rules.md) — davranış/akış desteği
- [`../lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — üst sınır

---

*Son güncelleme: 2026-06-17 — OD-008/009/010 decision-approved*
