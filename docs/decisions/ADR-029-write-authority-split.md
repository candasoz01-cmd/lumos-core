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
`collaborators`, PR reviews. Aynı sorgular 2026-10-16T17:20Z tekrarlandı;
id/slug/bot type değişmedi. Settings yazılmadı. Sır okunmadı.

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

## Aşama A ve B — yetki haritası (açılmadı)

Kurucu 2026-10-16: Aşama 0 kanıtı kabul; Aşama A/B **henüz yok**. Bu
bölüm envanterdir. `stage_authority_map()` her çağrıda
`grants_stage_a=false` ve `grants_stage_b=false` döner. Ajan bu
listeyi okuyarak A veya B'yi başlatamaz.

A ve B **ayrı kurucu kararlarıdır**. Biri diğerini içermez. İkisini
birden onaylamak bu belgede yoktur.

### Aşama A — imzalayıcı kodunu `main`'e indirmek

Üretim imzası basmaz. Üretim sırrını ajana açmaz.

| Açar | Açmaz |
| --- | --- |
| Yalnız kurucunun, imzalayıcı iş dosyasını taşıyan PR'ı `main`'e merge etmesi | Ajan/bot merge |
| Merge sonrası `origin/main:.github/workflows/write-sign-trusted.yml` varlığı | `workflow_dispatch` |
| `gh workflow list`'te `Write sign trusted` işinin `active` görünmesi | `lumos-write-gate` ortam onayı |
| | Üretim HMAC / `LUMOS_WRITE_GATE_SECRET` kullanımı |
| | `trusted-sign/pr-*` yazımı |
| | `grants_merge` |
| | `#945` / `#946` kilidinin kalkması |
| | sonraki PR'ların merge'i |

Aşama A kanıtı (yalnız A açılırsa): `git cat-file -e origin/main:.github/workflows/write-sign-trusted.yml` ve iş listesinde `active`. Bu kanıt üretim imzasının çalıştığını göstermez.

### Aşama B — ilk üretim kullanımı

Aşama A kanıtı olmadan B açılmaz. B, A'nın merge yetkisini tekrar etmez.

| Açar | Açmaz |
| --- | --- |
| Kurucunun `refs/heads/main` üzerinden `Write sign trusted` `workflow_dispatch` | Ajan dispatch |
| Kurucunun `lumos-write-gate` ortamında compare URL onaylaması (merge değil) | Ajan ortam onayı |
| Yalnız `service.write-gate` + `main` + `workflow_dispatch` bağlamında üretim sırrı | Ajanın üretim sırrı |
| Aralığın `trusted-sign/pr-<n>` kopyası (kaynak dal ve `main` değişmez; force yok) | `main`'e doğrudan yazma |
| İmzalı kopyanın taslak PR'ı | O taslağın veya kaynak PR'ın merge'i |
| Kopya SHA'da `write-attestation-trusted` SUCCESS (ilk üretim kanıtı) | Prova HMAC'nin üretim sayılması |
| | doğrulayıcı gevşetme |
| | branch protection Settings yazımı |
| | imza kökü / `allowed_signers` |

Aynı kopyada prova `write-attestation` üretim imzasıyla eşleşmez; bu beklenen ayrımdır.

### Ajan

Claude, Codex ve Cursor kendi App kimlikleriyle çalışır. Hiçbir A/B maddesi
ajanın kurucu merge, dispatch, ortam onayı veya üretim sırrını devralmasını
açmaz. `LUMOS_AGENT` dolu bir oturum kurucu sayılmaz.

## Bu ADR'nin vermediği yetkiler

- Aşama A ve Aşama B (yukarıdaki harita; karar ayrı ve henüz yok)
- `#945` / `#946` kilidinin kaldırılması
- ajan merge, dispatch, ortam onayı
- branch protection listesinin doldurulması
