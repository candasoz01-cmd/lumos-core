# Kando v0 kapanış özeti ve v1 ertelenenler

Şu ana kadar yapılan işin net kapatılması ve sonraki faz sınırının çizilmesi. Repo gerçek durumuna göre.

---

## tamam

**Komut yüzeyi:** Interaktif CLI resmî komutları: kilit, kamera, alias, durum, help, exit. HELP_TEXT sabit; bilinmeyen komut tek mesaj: "Desteklenmeyen komut. help yazın." (UNKNOWN_CMD_MSG). Normalize: exit eş anlamlıları (q, çık, cik, quit), alias uygulanıyor.

**Smoke akışı:** docs/SMOKE_KANDO_V0.md ile uyumlu tek senaryo: başlatma → help → durum → kamera (alt menü: durum, cik) → exit. CLI dışında ask/chat/env subcommand’ları çalışıyor; smoke sadece interaktif CLI.

**Smoke scripti:** scripts/smoke_kando_v0.sh. help/durum/kamera/durum/cik/exit pipe ile cli çalıştırır; "Kando v0", "kilit | kamera", "LOCKED | Presence:", "Mode:", "Kamera: durum | ac | kapat", "enabled=", "OK" kontrolü. Repo kökünden; .venv veya PYTHONPATH=src.

**Release checklist:** docs/RELEASE_CHECKLIST_KANDO_V0.md. Git, test, smoke, komut yüzeyi, izin satırı, ask akışı, presence aşama-1 maddeleri; ertelenenler bölümü mevcut.

**Guardrail testleri:** tests/test_interactive_cli.py — HELP_TEXT resmî satırla uyumlu, bilinmeyen komut "unknown" + UNKNOWN_CMD_MSG. tests/test_pre_route.py — izin sorusu destination "tool" (lokal readiness). tests/test_memory.py — run_ask("erişilebilirlik iznim var mı") provider’ı çağırmıyor.

**Permission / env:** Consent yoksa onboarding önizlemesi; macOS’ta başlangıçta print_permission_readiness() (macOS izinleri: Hazır. / Eksik — …). Diğer OS: "macOS izinleri bu sistemde uygulanmıyor (macOS only)." env subcommand: device scan + capabilities (JSON + özet).

**Ask akışı:** pre_route → izin sorusu (erişilebilirlik / ekran kaydı / tam disk / terminal / kamera) lokal cevap (format_permission_readiness_reply); provider’a gitmez. "Adım ne?", "bunu hatırla", dosya/proje/readonly tool pre_route’ta; geri kalan provider. run_ask/router test ile korunuyor.

**Presence aşama-1:** kamera menüsü (kamera → durum | ac | kapat | sure | cik). Yüz yoksa timeout sonrası lock_cb: do_lock + device_lock_cli; macOS’ta lock_mode mac/lumos+mac ise trigger_macos_screen_lock() (SACLockScreenImmediate veya pmset displaysleepnow). Config base_dir’de; start/stop presence_lock thread.

**Kilit (Lumos tarafı):** do_lock (lock_state.lock, passphrase temizleme, root_key None); unlock_with_passphrase (keystore + lumos.lock_state.unlock). Kilit menüsü: durum, kapat, ac (şifre ile).

---

## sınırda bırakılanlar

**"Adım ne" CLI’da yok:** Interaktif "Sen: " prompt’una yazılırsa bilinmeyen komut; isim/hatırlama sadece ask/chat tarafında (lumos ask / lumos chat). Bilinçli: smoke CLI ile sınırlı.

**Consent kalıcılığı yok:** has_user_consent() şu an hep False. Onboarding önizlemesi gösterilir; consent kaydedilmez. v0’da doğrulanmaz.

**Manuel "kilit kapat" fiziksel kilit değil:** "kilit kapat" sadece Lumos lock state + device_lock_cli(). device_lock_cli, lumos.note_memory.device_lock() çağırıyor (memory.py’de no-op). macOS ekran kilidi yalnızca presence timeout path’inde tetikleniyor (trigger_macos_screen_lock). Yani manuel kapatma ekranı kilitlemiyor; bilinçli sınır.

---

## ertelendi (v1 / ürün aşaması)

**Web v1:** Read-only HTTP sunucusu; durum okuma. Kando v0 checklist/scope dışı; doğrulanmaz.

**tg (Telegram):** lumos_core __main__’da tg subcommand var; lumos_social.telegram.cli’ye yönlendiriyor. v0 scope dışı.

**Consent kalıcılığı:** ~/.lumos/consent.json veya benzeri; has_user_consent() gerçek persist. v1/ürün.

**"Adım ne" CLI komutu:** İnteraktif döngüde resmî komut olarak eklenmesi v1 kararı.

**Policy/identity ask-chat’a bağlama:** PolicyRules.evaluate, lumos_id, unlocked şu an sadece Lumos.respond() path’inde; ask/chat AIRouter’a doğrudan pre_route ile gidiyor. Identity gate ask/chat’ta yok; v1 activation plan’da.

**Fiziksel kilit "kilit kapat" ile:** Manuel kapatmada da macOS ekran kilidi tetiklemek (veya ortak device_lock implementasyonu) v1/ürün.

---

## risk / notlar

**Smoke script:** Pipe ile giriş; consent yoksa önce onboarding çıktısı gelir. Script anahtar kelimeleri (Kando v0, LOCKED, Kamera:, OK) çıktıda arıyor; PASS için bu satırların hepsi bulunmalı. Ortamda kamera/izin yoksa presence başlamayabilir; script sadece "enabled=" gibi çıktıyı kontrol ediyor.

**Guardrail:** HELP_TEXT veya UNKNOWN_CMD_MSG değişirse test_interactive_cli testleri kırılır; kasıtlı — davranış korunur. pre_route izin kalıbı (looks_like_perm_query) genişlerse yeni cümleler de lokal kalır; daralırsa provider’a kaçma riski.

**Presence:** opencv (cv2) ve kamera gerekir; yoksa status ERR:opencv_yok / ERR:kamera_acilamadi. make smoke (presence aç/kapat) ortam bağımlı.

**Ask "erişilebilirlik iznim var mı":** API/network yoksa zaten provider’a düşmez (pre_route tool). Test: router.route.assert_not_called() + lokal çıktı boş değil.

---

## Dosya referansları

- Komut yüzeyi / help / unknown: src/lumos_core/interactive_cli.py (HELP_TEXT, UNKNOWN_CMD_MSG, normalize_command).
- Smoke: docs/SMOKE_KANDO_V0.md, scripts/smoke_kando_v0.sh.
- Checklist: docs/RELEASE_CHECKLIST_KANDO_V0.md.
- Guardrail: tests/test_interactive_cli.py, tests/test_pre_route.py (test_perm_question_local_readiness_not_provider), tests/test_memory.py (test_run_ask_perm_query_stays_local_does_not_call_provider).
- İzin / readiness: src/lumos_core/system/env_scan.py (looks_like_perm_query, format_permission_readiness_reply, print_permission_readiness).
- Ask: src/lumos_core/cli.py (run_ask), src/lumos_core/policy/pre_route.py.
- Presence / macOS lock: src/lumos_core/security/presence_lock.py (trigger_macos_screen_lock), interactive_cli lock_cb/device_lock_cli.
