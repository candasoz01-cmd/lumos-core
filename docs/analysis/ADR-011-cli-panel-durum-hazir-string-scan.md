# ADR-011 — CLI/Panel `durum` / `hazir` kullanıcı metni taraması

| Alan | Değer |
|------|-------|
| Tarih | 2026-06-21 |
| Kapsam | Salt okuma; kullanıcıya görünen metinlerde `keystore_ready` vs `session_unlocked` karışıklık riski |
| İlgili | [ADR-011](../decisions/ADR-011-lock-semantics-decision.md), Phase 1 rename PR |

## Özet

Phase 1 rename sonrası CLI `durum` çıktısı **Keystore** ve **Oturum** satırlarına ayrıldı. Kalan karışıklık riskleri panel consent vekili, `hazir` tek satır özeti ve yardımcı CLI metinlerinde.

## CLI — düzeltilen alanlar (Phase 1)

| Giriş | Sinyal | Kullanıcı metni | Durum |
|-------|--------|-----------------|-------|
| `durum` → `format_durum` | keystore_ready + session_unlocked | `Keystore: hazır/eksik`, `Oturum: açık/kilitli` | **Hizalı** |
| `hazir` → `get_startup_summary(..., session_unlocked=...)` | session_unlocked | `Oturum açık` / `Oturum kilitli` | **Hizalı** |
| `_get_guvenli_cevap`, `_get_en_onemli_eksik` | keystore_ready | "Keystore hazır değil" | **Hizalı** |

## CLI — kalan drift / düşük risk

| Konum | Metin | Sinyal | Risk |
|-------|-------|--------|------|
| `cli_parse.py` öneri | "Önce keystore kurulumunu kontrol et: **kilit**" | keystore_ready | Orta — komut adı `kilit` hâlâ geçiyor |
| `lumos_runtime.py` | `Kilit: durum \| ac \| kapat \| cik` | session (passphrase) | Düşük — ayrı alt REPL; `durum`/`hazir` değil |
| `model_client.py` prompt | `Lock: {lock}` | runtime lock_status | Düşük — LLM bağlamı; kullanıcı CLI değil |
| `panel_bridge_state.py` general_note | "Consent kayıtlı. **Lock/presence** bu hatta doğrulanmaz." | bilinçli vekili | Bilinçli — demo dürüstlük |

## Panel — consent vekili (değişmedi)

| Alan | Kaynak | Gerçek sinyal | Kullanıcı görür |
|------|--------|---------------|-----------------|
| `keystore_ready` | `consent_ok` | consent vekili | Hazır mı: Evet/Hayır |
| `keystore_state` | consent | consent vekili | Hazır / Kilitli |
| `guidance.lock` | consent | consent vekili | UNLOCKED / LOCKED |

**Risk (ADR-011 Faz 3):** Panel "Kilitli" etiketi `session_unlocked` veya `keystore_ready` yansıtmaz; kullanıcı runtime oturum durumunu yanlış okuyabilir.

## Öncelikli takip (Phase 1 sonrası)

1. **Faz 2:** `cli_parse` öneride `: kilit` → `: keystore` veya net yönlendirme.
2. **Faz 3:** Panel keystore kartında "consent vekili" etiketi (onaylı).
3. **ADR-007:** Trust sinyal tablosuna iki lock alanı referansı.

## Sonuç

Phase 1 rename CLI `durum`/`hazir` ana karışıklığını giderdi. Panel ve birkaç yardımcı metin bilinçli vekili veya ayrı REPL bağlamında kalır; otomatik merge veya davranış değişikliği bu taramanın kapsamı dışındadır.
