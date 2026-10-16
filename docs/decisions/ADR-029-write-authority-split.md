# ADR-029 — Yazma yetkisinde kurucu / ajan / sır ayrımı (Aşama 0)

| Alan | Değer |
| --- | --- |
| Durum | **Accepted (önkoşul, 2026-10-16)** — kurucu: Aşama A/B yok; #945 ve #946 kilitli |
| Uygulama | `src/lumos_board/write_authority_split.py` — fail-closed sınıflandırma + sır kullanımı + zorunlu kontrol *simülasyonu* + canlı App/kurucu kimlik kaydı |
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

## Canlı kimlik ayrımı (2026-10-16T17:19Z, GitHub API)

Kaynak: `gh api apps/<slug>`, `gh api users/<login>`,
`repos/candasoz01-cmd/lumos-core/environments/lumos-write-gate`,
`collaborators`, PR reviews. Settings yazılmadı. Sır okunmadı.

| Özne | Kanıt | Sınıf |
| --- | --- | --- |
| Kurucu `candasoz01-cmd` | User id `260758816`, repo `admin`, tek collaborator | `human.founder` (ajan env yokken) |
| Claude App | slug `claude` id `1236702`, owner `anthropics`, bot `claude[bot]` id `209825114` type Bot | `agent` |
| Claude commit yazarı | User `claude` id `81847` — App bot'u değil; `lumos-core` commit yazarı | yine `agent` |
| Codex App | slug `chatgpt-codex-connector` id `1144995`, owner `openai`, bot `chatgpt-codex-connector[bot]` id `199175422` type Bot | `agent` |
| Codex işletim | commit yazarı olarak 0; PR review `#930` ve `#932` | `agent` |
| Cursor App | slug `cursor` id `1210556`, bot `cursor[bot]` id `206951365`; `#947` yazarı `app/cursor` | `agent` |
| `lumos-write-gate` | zorunlu inceleyici yalnız `candasoz01-cmd`; dal politikası yalnız `main` | hizmet ortamı; merge değil |
| Bu ajan süreci | `LUMOS_WRITE_GATE_SECRET` / `GITHUB_TOKEN` / `GH_TOKEN` yok; `~/.ssh` yok; `gh auth` hesabı `cursor` (`ghs_`, kurucu User değil) | kurucu kimliği yok |

Kurucu allowlist'e yazılmış olsa bile `LUMOS_AGENT` doluysa özne `agent`
kalır. Claude'un commit'leri App bot'u yerine User `claude` ile gelmiş
olması App kaydını kurucu yapmaz; her iki login ajan olarak kilitlenir.

`evaluate_identity_evidence` bu tabloyu fail-closed doğrular. Aşama A/B
açılmaz. `#945` / `#946` kilitli kalır.

## Bu ADR'nin vermediği yetkiler

- Aşama A (imzalayıcıyı `main`'e indirmek)
- Aşama B (ilk üretim imzası / dispatch)
- `#945` / `#946` kilidinin kaldırılması
- ajan merge, dispatch, ortam onayı
- branch protection listesinin doldurulması
