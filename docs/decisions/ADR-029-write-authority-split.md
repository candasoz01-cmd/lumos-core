# ADR-029 — Yazma yetkisinde kurucu / ajan / sır ayrımı (Aşama 0)

| Alan | Değer |
| --- | --- |
| Durum | **Accepted (önkoşul, 2026-10-16)** — kurucu: Aşama A/B yok; #945 ve #946 kilitli |
| Uygulama | `src/lumos_board/write_authority_split.py` — fail-closed sınıflandırma + sır kullanımı + zorunlu kontrol *simülasyonu* |
| Üst | [CONSTITUTION §11](../CONSTITUTION.md), [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) N8, [ADR-027](ADR-027-controlled-core-writer.md), [write-authorization-v1](../contracts/write-authorization-v1.md), TD-10 |
| Yasak | Merge, `workflow_dispatch`, ortam onayı, Settings yazımı, imza kökü kaydı, doğrulayıcı gevşetme |

## Karar

İnsan neyi onayladıysa sistem yalnız onu yapar. Bunun için üç özne
**ayrı**dır ve birbirinin yerine geçmez:

| Özne | Kimlik kanıtı | Üretim sırrı | Merge / Aşama A-B |
| --- | --- | --- | --- |
| `human.founder` | Fail-closed onaycı allowlist; `LUMOS_AGENT` yok | Kullanamaz | Yalnız kurucu kararı; bu ADR açmaz |
| `agent` | `LUMOS_AGENT`, `Lumos-Agent`, bot/App, ajan `owner` | Kullanamaz | Yetki yok |
| `service.write-gate` | `owner=lumos-write-gate` **ve** `refs/heads/main` **ve** `workflow_dispatch` | Yalnız bu bağlam | Merge üretmez |

Kurucu GitHub oturumu ajan trailer'ı taşıyorsa özne `agent` olur. Ajan
kendini kurucu yazamaz. Prova HMAC (`write-attestation`) üretim sırrı
değildir.

## Zorunlu kontrol etkisi (yazmadan)

Simülasyon Settings API'ye yazmaz. Mevcut fiziksel required liste
(`test`, `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`,
`publication-gate`) üzerine `write-attestation-trusted` eklenirse, o
CheckRun SUCCESS olmayan her PR merge kilidine girer.

Canlı kayıt (GitHub API, tanıtan PR kilitli kalır):
`candasoz01-cmd/lumos-core#945` · OPEN · prova `write-attestation`
SUCCESS · üretim `write-attestation-trusted` FAILURE ·
`CLAIM_GUARD_UNAUTHORIZED`. Bu kırmızı beklenen bootstrap kilitlenmesidir;
yeşile zorlanmaz. `write-attestation-trusted`'ı required yapmak #945'i
(ve prova imzalı her tanıtıcı PR'ı) fiziksel olarak kilitler. Bu etki
doğrulandı; ayar uygulanmadı.

## Bu ADR'nin vermediği yetkiler

- Aşama A (imzalayıcıyı `main`'e indirmek)
- Aşama B (ilk üretim imzası / dispatch)
- `#945` / `#946` kilidinin kaldırılması
- ajan merge, dispatch, ortam onayı
- branch protection listesinin doldurulması
