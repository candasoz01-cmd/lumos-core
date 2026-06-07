# Lumos Persona / Güvenlik — Uygulama Checkpoint ve Test Planı

| Alan | Değer |
|------|-------|
| Durum | **Checkpoint / test planı** — kod değişikliği yok; doğrulama yol haritası |
| Tarih | 2026-06-07 |
| İlgili | [lumos-persona-layers.md](lumos-persona-layers.md), [ADR-008](decisions/ADR-008-agent-network-boundary.md), `lumos-karar-sozlesmesi` |

## Amaç ve kapsam

[PR #100](https://github.com/candasoz01-cmd/lumos-core/pull/100) ile eklenen `lumos-persona-layers.md` ilkelerinin **uygulamada nasıl doğrulanacağını** planlar. Bu belge test kodu veya implementasyon taşımaz; salt okuma audit, manuel senaryo ve sonraki faz test tasarımı içindir.

**Mevcut durum (kısa):** Persona ilkeleri büyük ölçüde **docs-only**. Köprü hattında kısmi gate/policy var; CLI, TaskEngine ve Cando recipe yolları tam kapı modelini henüz yansıtmıyor. Bando runtime’da yok.

---

## Sınıflandırma

| Etiket | Anlam |
|--------|--------|
| **Şimdi yapılacak** | Salt okuma envanter, manuel trace, mevcut davranış gözlemi — kod yazmadan |
| **Sonraki faz** | Hedef davranış için odaklı test veya ince instrumentation |
| **İleride güvenlik sertifikası için** | Formal audit, penetrasyon, sürekli regresyon, sertifikasyon kanıtı |

---

## 1. Lumos tek dış geçit

**Checkpoint soruları**

- Dış dünyadan sisteme giren tüm HTTP/CLI/panel yolları listelenmiş mi?
- Her yol `lumos_gate` / policy / onay zincirinden geçiyor mu, yoksa bypass var mı?
- İç katmanlara (Kando görev motoru, Cando recipe) doğrudan erişim kapısı var mı?

**Audit hedefleri (salt okuma)**

- `packages/kando_bridge/src/kando_bridge/server.py` — `POST /task`, `/chat`, `/agent-run`
- `packages/kando_runtime/src/kando_runtime/lumos_gate.py` — `policy_ok`, `run_lumos_gate`
- `src/main.py`, `src/cli/cli_tasks_mutation.py` — CLI / TaskEngine girişleri
- `scripts/cando_local.py`, `src/cando/*` — Cando doğrudan çağrı

**Nasıl test / denetlenir**

| Adım | Yöntem | Sınıf |
|------|--------|-------|
| Giriş envanteri tablosu (endpoint → gate evet/hayır) | Repo taraması + manuel akış | **Şimdi** |
| Köprü: policy-blocked istek → 403 | Manuel veya mevcut integration testleri | **Şimdi** |
| CLI/TaskEngine gate bypass var mı? | Trace: `main.py` → TaskEngine gate çağrısı yok mu? | **Şimdi** |
| Tek kapı invariant testi (tüm dış girişler gate’e zorlanır) | Yeni odaklı test paketi | **Sonraki faz** |
| Formal dış yüzey haritası + değişiklik kontrolü | CI drift / security review | **İleride güvenlik sertifikası** |

**Beklenen sonuç:** Persona ilkesine göre tüm dış etkili giriş Lumos (gate + onay) üzerinden; bypass’lar ya kapatılır ya da “bilinçli yerel-only” olarak etiketlenir.

---

## 2. Kando / Cando — doğrudan dış komut, iş, dosya, veri

**Checkpoint soruları**

- Lumos dışından Kando’ya komut ulaşabiliyor mu? (CLI, subprocess, panel → köprü dışı)
- Cando recipe’ye dosya/path doğrudan verildiğinde “yabancı giriş” veya kanal reddi var mı?
- Kando/Cando HTTP veya socket yüzeyi dışarıya açık mı?

**Nasıl test / denetlenir**

| Senaryo | Yöntem | Sınıf |
|---------|--------|-------|
| `POST /task` gate öncesi/sonrası reddi | Mevcut köprü + policy blocked body | **Şimdi** |
| CLI: `main.py` / task mutation gate’siz mi? | Salt okuma + manuel CLI trace | **Şimdi** |
| `cando_local.py --dry-run` gate’siz repo erişimi | Manuel çalıştırma; dokümante gap | **Şimdi** |
| Cando’ya doğrudan dosya = reddedilir / loglanır | Davranış testi (henüz yok → tasarla) | **Sonraki faz** |
| Kando dış komut invariant (tüm girişler doğrulanmış kanal) | Entegrasyon testi seti | **Sonraki faz** |
| Dış ağdan Kando/Cando port taraması / yüzey yok | Pen-test / deployment audit | **İleride güvenlik sertifikası** |

**Beklenen sonuç:** Dış komut/iş/dosya/veri yalnızca doğrulanmış Lumos kanalından; doğrudan Cando/Kando yolu ya yok ya reddedilir.

---

## 3. Offline — kuyruk otomatik push / sync / PR / mail / API

**Checkpoint soruları**

- “Offline kuyruk” diye kalıcı bir yapı var mı? Reconnect’te otomatik flush var mı?
- `agent_runner` veya benzeri pipeline commit sonrası otomatik `git push` yapıyor mu?
- Panel offline cache reconnect’te dış gönderim tetikliyor mu?

**Audit hedefleri**

- `src/kando/agent_runner.py` — push fazı
- `panel/js/app.js` — offline-cache / sync
- `src/policy/action_policy.py`, `src/policy/offline_engine.py` — offline reddi

**Nasıl test / denetlenir**

| Senaryo | Yöntem | Sınıf |
|---------|--------|-------|
| Offline panel: reconnect → otomatik push yok | Manuel UI + network trace | **Şimdi** |
| Agent job: onay olmadan push denemesi | Trace `agent_runner` push fazı | **Şimdi** |
| Simüle offline → online: kuyruk auto-flush yok | Test ortamı senaryosu (kuyruk yoksa gap kaydı) | **Şimdi** |
| Push/PR/mail/API = Lumos doğrulama + kullanıcı onayı zorunlu | Davranış testi + gate hook | **Sonraki faz** |
| Regresyon: reconnect storm’da otomatik dış aksiyon yok | Otomasyon + CI | **İleride güvenlik sertifikası** |

**Beklenen sonuç:** Internet gelince otomatik dış gönderim yok; her dış etki açık onay + Lumos doğrulaması.

---

## 4. Lumos secret ana deposu değil

**Checkpoint soruları**

- Gateway süreci şifre/token/root key’i kalıcı veya geniş bellekte tutuyor mu?
- Hassas değer `.lumos/` veya log’a yazılıyor mu?
- “Sonuç odaklı iletişim” (bağlantı OK/red) mümkün mü, yoksa ham secret taşınıyor mu?

**Audit hedefleri**

- `src/security/keystore.py`, `src/engine/online_engine.py`, `RequestSigner` kullanımı
- `KANDO_BRIDGE_SECRET` env / köprü bellek ömrü
- Log ve audit çıktıları — secret sızıntısı

**Nasıl test / denetlenir**

| Adım | Yöntem | Sınıf |
|------|--------|-------|
| Keystore/signer bellek ve persist envanteri | Salt okuma + grep (secret pattern) | **Şimdi** |
| Log/audit dosyalarında token/key dump var mı? | Manuel log inceleme | **Şimdi** |
| Gateway API: sonuç-only contract (secret dönmez) | Tasarım review + contract test | **Sonraki faz** |
| Bellek dump / runtime secret minimizasyonu | Güvenlik audit | **İleride güvenlik sertifikası** |

**Beklenen sonuç:** Lumos geçit kalır; ana secret deposu olmaz; mümkün olduğunca amaç bazlı sınırlı erişim ve sonuç odaklı yanıt.

---

## 5. Bando (varsa) — yalnızca gözlem / anomali

**Checkpoint soruları**

- Runtime’da Bando modülü veya endpoint var mı? (Bugün: **yok**, yalnızca persona doc)
- Varsa: komut çalıştırma, dış iş/veri kabul, dış yüzey var mı?
- Dış girişim güvenlik olayı olarak raporlanıyor mu?

**Nasıl test / denetlenir**

| Adım | Yöntem | Sınıf |
|------|--------|-------|
| Repo’da `Bando` runtime referansı yok | Grep / modül envanteri | **Şimdi** |
| Bando eklendiğinde: dış komut → güvenlik olayı, görev değil | Tasarım checklist + unit test | **Sonraki faz** |
| İzole gözlem; rapor yalnız Lumos’a | Entegrasyon + audit | **Sonraki faz** |
| Anomali katmanı formal threat model | Güvenlik sertifikasyon paketi | **İleride güvenlik sertifikası** |

**Beklenen sonuç:** Bando execution/ajan değil; dış komut kabul etmez; doğrudan giriş güvenlik olayı.

---

## 6. Anti-Lumos taklit (yüksek seviye)

**Checkpoint soruları (protokol detayı yok)**

- Lumos dışından veya Lumos’u taklit eden kaynaktan gelen iç mesaj “güvenilir” sayılıyor mu?
- İç kanalda doğrulama / bütünlük kontrolü tanımlı mı, yoksa yalnızca loopback + shared secret mi?
- Sahte veya yetkisiz iç komut reddediliyor mu?

**Nasıl test / denetlenir**

| Adım | Yöntem | Sınıf |
|------|--------|-------|
| İç mesaj güven modeli: hangi yollar imza/doğrulama kullanıyor? | Salt okuma envanter (detay doc’a girilmez) | **Şimdi** |
| Köprü: yetkisiz token / sahte kaynak reddi | Mevcut `KANDO_BRIDGE_SECRET` manuel test | **Şimdi** |
| Kando ↔ Lumos kanal bütünlüğü invariant testleri | Sonraki implementasyon checkpoint | **Sonraki faz** |
| Formal impersonation / replay test suite | Güvenlik sertifikasyon | **İleride güvenlik sertifikası** |

**Not:** `lumos-persona-layers.md` uygulamayı ayrı checkpoint olarak işaretler; bu bölüm wire-format, algoritma veya anahtar detayı içermez.

---

## Öncelikli sonraki adımlar

1. **Şimdi:** Giriş envanteri tablosu (köprü / CLI / Cando / panel) — gate bypass listesi.
2. **Şimdi:** Offline + push trace (`agent_runner`, panel) — persona ile çelişki var mı kaydı.
3. **Sonraki faz:** “Tek kapı” ve “offline auto-push yok” için odaklı davranış testleri (test dosyası ayrı PR).
4. **Sonraki faz:** Secret taşıma ve Anti-Lumos — implementasyon checkpoint (ADR veya ayrı ADR taslağı).

---

## Ne yapılmaz (bu belge kapsamında)

- Kod, recipe veya test dosyası değişikliği
- Protokol, anahtar, algoritma veya wire-format spesifikasyonu
- Bando veya yeni güvenlik modülü implementasyonu

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent ve kilit alanları bu planla gevşetilmez.
