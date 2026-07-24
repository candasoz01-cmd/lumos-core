# Lumos Persona — Uygulama Boşlukları (Gap Kaydı)

| Alan | Değer |
|------|-------|
| Durum | **Gap kaydı** — kod değişikliği yok; persona ilkesi ↔ mevcut kod farkı |
| Tarih | 2026-06-07 |
| Persona referansı | [lumos-persona-layers.md](lumos-persona-layers.md) |
| Test / denetim planı | [lumos-persona-security-checkpoint.md](lumos-persona-security-checkpoint.md) |

## Giriş

Bu belge, [lumos-persona-layers.md](lumos-persona-layers.md) güven sınırları ile **bugünkü kod gerçekliği** arasındaki **6 bilinen boşluğu** kayıt altına alır. Checkpoint belgesi *nasıl test edileceğini* planlar; bu belge *nerede uyumsuzluk olduğunu* özetler. Protokol, anahtar, algoritma veya wire-format detayı içermez.

---

## 1. Lumos dışından Core'ya komut — CLI / TaskEngine bypass

- **Hedef davranış:** Core işi yalnızca doğrulanmış Lumos kanalından kabul eder; dış dünyadan (CLI, panel köprüsü dışı, subprocess) doğrudan komut reddedilir veya bilinçli yerel-only olarak etiketlenir.
- **Mevcut kod durumu:** Köprü hattında (`packages/kando_bridge/server.py` → `kando_runtime/lumos_gate.py`) kısmi gate/policy var. Buna karşılık CLI görev mutasyonu (`src/cli/cli_tasks_mutation.py`) `policy.action_policy.check_policy` kullanır; `run_lumos_gate` çağrısı yok. `src/` altında TaskEngine/CLI yollarında `lumos_gate` referansı bulunmuyor. Yerel `python -m` / `src/main.py` ile görev oluşturma ve mutasyon, köprü kapısından bağımsız çalışabilir.
- **Risk:** Persona “tek giriş: Lumos” ilkesi köprüde kısmen, CLI/TaskEngine’de fiilen bypass. Aynı repo üzerinde onaysız veya gate’siz görev yürütme yolu açık kalır.
- **İlk uygulanabilir test/assertion:** Salt okuma envanter testi — tüm dış etkili giriş noktaları listelenir; köprü `POST /task` için `lumos_gate` geçişi doğrulanır, CLI `gorev_olustur` yolunda `lumos_gate` çağrısı olmadığı assert edilir.
- **Faz:** şimdi (envanter + manuel trace) → sonraki faz (tek kapı invariant test paketi)

---

## 2. Local doğrudan dosya / komut — yabancı giriş ve Lumos kanalı

- **Hedef davranış:** Local read-only recipe/runbook katmanı; dış komut, iş, dosya veya veri yalnızca doğrulanmış Lumos kanalından gelir. Doğrudan shell veya üçüncü taraf çağrısı “yabancı giriş” sayılır, reddedilir veya loglanır.
- **Mevcut kod durumu:** `scripts/cando_local.py` recipe’leri doğrudan çalıştırır (`src/cando/branch_cleanup_review`, `pr_ready_check`); `--dry-run` salt okuma sınırı var ancak `lumos_gate`, kanal doğrulama veya yabancı giriş reddi yok. Recipe hedefi sabit `REPO_ROOT`; kullanıcı path argümanı sınırlı olsa da giriş tamamen CLI/subprocess.
- **Risk:** Persona “Core / Local doğrudan dış kabul etmez” kuralı Local yolunda uygulanmıyor. Operasyonel rutinler Lumos onayı veya gate olmadan tetiklenebilir.
- **İlk uygulanabilir test/assertion:** `cando_local.py recipe … --dry-run` çalıştırıldığında gate veya kanal kontrolü olmadığı dokümante edilir; sonraki fazda “Lumos kanalı dışı Local çağrısı → reddedildi / security_event” davranış testi tasarlanır.
- **Faz:** şimdi (manuel dry-run + gap kaydı) → sonraki faz (yabancı giriş reddi davranış testi)

---

## 3. Offline kuyruk — internet gelince otomatik dış aksiyon yok

- **Hedef davranış:** Offline bekleyen işler reconnect’te otomatik push, sync, PR, mail, bulut veya API işlemine dönüşmez. Her dış etki Lumos doğrulaması ve kullanıcı onayı ister.
- **Mevcut kod durumu:** Persona offline prensibi docs’ta net. `src/kando/agent_runner.py` pipeline’ında commit sonrası otomatik `git push` fazı **kaldırıldı**; dış gönderim ayrı, Lumos/kullanıcı onaylı akışa ertelendi (bu PR kapsamı dışı). Panel tarafında `policy-engine.js` offline reddi var; kalıcı “offline kuyruk + reconnect auto-flush” modülü ve bunu engelleyen merkezi invariant kodda tanımlı değil.
- **Risk:** Gelecekte kuyruk eklendiğinde otomatik dış gönderim persona ile çelişebilir; onaylı push akışının ayrıca tanımlanması gerekir.
- **İlk uygulanabilir test/assertion:** `agent_runner` tamamlandığında otomatik push tetiklenmediği trace; simüle offline→online senaryosunda otomatik push/PR/API tetiklenmediği davranış testi (sonraki faz).
- **Faz:** şimdi (auto-push kaldırıldı — kısmi) → sonraki faz (onaylı push akışı + auto-flush yok invariant testi)

---

## 4. Lumos secret ana deposu değil — sonuç odaklı iletişim

- **Hedef davranış:** Lumos tek dış geçittir; şifre, token ve gizli bilgiler için ana depo değildir. Mümkün olduğunca amaç bazlı sınırlı erişim; gateway yanıtları sonuç odaklı (başarılı/reddedildi), ham secret taşınmaz.
- **Mevcut kod durumu:** `src/security/keystore.py` root key’i passphrase ile diskten yükler; `src/engine/online_engine.py` oturumda `FileKeyStore.load_root_key` ve `RequestSigner` ile bellekte tutar. Köprü süreci `KANDO_BRIDGE_SECRET` ortam değişkenini okur (`kando_bridge/server.py`). `lumos_gate.py` reasoning için `OPENAI_API_KEY`’i süreç belleğinde kullanır. Gateway API’de “secret dönmez, yalnızca sonuç” sözleşmesi kod seviyesinde zorunlu değil. Panel (`ui/src/pages/panel.astro`, PR #110) aynı deseni kullanır.
- **Risk:** Lumos/köprü süreçlerinde secret birikimi; ele geçirme yüzeyi persona ilkesinden geniş. Sonuç odaklı iletişim tasarım hedefi, uygulama sınırında henüz enforce edilmiyor. **Tarayıcı-visible token (`PUBLIC_KANDO_TOKEN`):** Panel (`ui/src/pages/panel.astro`, PR #110) ve UI `define:vars` / `import.meta.env.PUBLIC_*` ile token'ı istemci bundle'ına gömer — DevTools'ta okunur. Yerel loopback geliştirmede placeholder (`test123`) kabul edilebilir; gerçek `KANDO_BRIDGE_SECRET` değerinin `PUBLIC_*` veya kalıcı client bundle'ında taşınması üretim için kabul edilemez. Sonraki faz (public repo'da tam çözüm yok): sunucu tarafı proxy, kısa ömürlü token veya çalışma anı kullanıcı girdisi (`frontend/index.html` deseni).
- **İlk uygulanabilir test/assertion:** Salt okuma — köprü/gate/online_engine modüllerinde env + keystore yükleme noktaları envanter; log/audit çıktılarında ham token pattern taraması. Sonraki faz: gateway yanıt contract testi (secret alanı yok).
- **Faz:** şimdi (envanter + log gözlemi) → sonraki faz (sonuç-only contract testi)

---

## 5. Sahte Lumos imzası / iç mesaj reddi (anti-taklit)

- **Hedef davranış:** Lumos dışından veya Lumos’u taklit eden kaynaktan gelen iç mesaj güvenilir sayılmaz; Core ↔ Lumos (ve gerektiğinde Local) iç iletişimde doğrulama / bütünlük; sahte iç komut reddedilir.
- **Mevcut kod durumu:** Köprü kimlik doğrulaması loopback (`127.0.0.1`) + **zorunlu** paylaşımlı token (`KANDO_BRIDGE_SECRET`; boş veya tanımsızsa korumalı uç noktalar **401**). `GET /health` kimlik doğrulamasız kalır. `src/security/request_signer.py` ve `online_engine` imza altyapısı var; köprü ↔ Core iç mesaj hattına bağlı değil. İç kanalda “Lumos kaynaklı” iddiasını kanıtlayan merkezi anti-taklit katmanı yok.
- **Risk:** Paylaşımlı bearer tek başına tam anti-taklit değildir; iç kanal bütünlüğü ve imza katmanı hâlâ eksik. Yerel süreç secret bilirse iç komut enjekte edebilir.
- **İlk uygulanabilir test/assertion:** Gap #5 anti-taklit köprü auth checkpoint testleri geçer (`tests/test_persona_security_simdi_checkpoint.py`); yetkisiz/sahte kaynak için iç kanal bütünlük testleri sonraki faz.
- **Faz:** şimdi (köprü secret zorunlu — **kısmen kapandı**) → sonraki faz (iç kanal bütünlük invariant testleri)

---

## 6. Sentinel — dış komut güvenlik olayı (runtime yok)

- **Hedef davranış:** Sentinel yalnızca gözlem / anomali katmanı; dış komut, iş, dosya veya veri kabul etmez. Dış girişim güvenlik olayı → koruma modu; rapor yalnız Lumos’a.
- **Mevcut kod durumu:** Sentinel yalnızca [lumos-persona-layers.md](lumos-persona-layers.md) içinde tanımlı. Repo’da `Sentinel`/`bando` runtime modülü, endpoint veya güvenlik olayı işleyicisi yok. Checkpoint belgesi de “runtime’da yok” olarak kayıtlı.
- **Risk:** İleride Sentinel eklendiğinde execution veya dış yüzey olarak yanlış konumlandırma; dış komutun “görev” sanılması persona ihlali.
- **İlk uygulanabilir test/assertion:** Repo grep — runtime `bando` referansı olmadığı assert; Sentinel eklendiğinde checklist: dış komut → `security_event` (görev değil), dış yüzey yok, rapor Lumos’a.
- **Faz:** şimdi (docs-only doğrulama) → sonraki faz (Sentinel tasarım checklist + unit test) → ileride (formal threat model)

---

## İlişki

| Belge | Rol |
|-------|-----|
| [lumos-persona-layers.md](lumos-persona-layers.md) | Persona ve güven sınırı tanımı |
| [lumos-persona-security-checkpoint.md](lumos-persona-security-checkpoint.md) | Denetim soruları, test yöntemi, faz sınıflandırması |
| **Bu belge** | 6 gap’in hedef ↔ kod özeti ve ilk test/assertion ipucu |

`lumos-karar-sozlesmesi` ile uyum: güvenlik, yetki, consent ve kilit alanları bu kayıtla gevşetilmez; yalnızca uygulama farkı belgelenir.
