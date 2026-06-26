# TODO / FIXME / Placeholder Sweep Report

| Alan | Değer |
|------|-------|
| Tarih | 2026-06-26 |
| Dal | `chore/hygiene-sweep-20260626` |
| Kapsam | Repo taraması (`.git`, `node_modules`, `.venv`, `dist`, lock dosyaları hariç) |

## Özet

| Metrik | Sayı |
|--------|------|
| Toplam eşleşme (grep) | ~120 (çoğu UI `placeholder`, iş `TBD`, bilinçli stub) |
| **SAFE_FIX uygulandı** | **1** |
| **NEEDS_APPROVAL** | **8** kayıt (NA-01 … NA-08; aşağıdaki tablo) |
| Terminoloji düzeltmesi (Task 2) | 4 dosya, 7 metin değişikliği |
| Kırık doc linki düzeltmesi (Task 3) | 18 dosya, ~35 link/anchor |

---

## SAFE_FIX — uygulanan

| Dosya | Değişiklik |
|-------|------------|
| `docs/mac-app-link-layer.md` | `TODO (cannot ship…)` → `SHIP BLOCKER (intentional placeholder — Alpha):` — bilinçli Apple Team ID yer tutucusu; davranış değişikliği yok, netleştirme |

---

## NEEDS_APPROVAL — dokunulmadı

| ID | Konum | Sınıflandırma | Gerekçe |
|----|-------|---------------|---------|
| NA-01 | `src/core/decision_runner.py:78` | `TODO` | **core/** — `base_dir` zorunlu kılma; otonom apply davranışı |
| NA-02 | `archive/packages/kando_core/.../decision_runner.py:78` | `TODO` | Arşiv kopyası; core ile aynı not |
| NA-03 | `docs/mac-app-link-layer.md` | Placeholder `XXXXXXXXXX`, `com.welockai.lumos` | Bilinçli Alpha stub; gerçek Apple kimlik bilgisi ship öncesi dış kaynak |
| NA-04 | `src/security/`, `src/engine/online_engine.py`, köprü `KANDO_BRIDGE_SECRET`, OAuth yüzeyleri | Secret / gateway stub | Güvenlik / köprü sözleşmesi; persona gap belgelerinde kayıtlı |
| NA-05 | İş planı belgelerindeki **TBD** (fiyat, KYC, destek e-postası, SLA) | `TBD` | Ticari / hukuk kararı bekliyor — [`bank-readiness-checklist.md`](./bank-readiness-checklist.md), [`pre-commercial-release-plan.md`](./pre-commercial-release-plan.md) |
| NA-06 | `src/task_engine/observation/state.py` | `known_files` placeholder | **task_engine/** — gelecek gözlem alanı |
| NA-07 | UI / CSS `::placeholder`, `placeholder-block` | HTML/CSS | Kullanıcı arayüzü yer tutucu metni; ürün stub değil |
| NA-08 | `DIRECT_WRITE_ATTEMPT` log sabiti | Kod | Audit terimi; TODO değil, grep yanlış pozitif |

---

## Bilinçli açık notlar (değişiklik gerekmez)

- `docs/analysis/session-closure-report.md` — Mac AASA Team ID TODO durumu **kayıtlı bilinçli açık**
- `lumos-quantum/` placeholder — ADR-001 ile takip; silinmez
- `PUBLIC_KANDO_TOKEN` / panel token — persona gap; üretim çözümü sonraki faz

---

## Task 2 — Terminoloji (Panel vs Dashboard)

| Dosya | Değişiklik |
|-------|------------|
| `docs/analysis/lumos-consent-and-panel-profile-matrix-draft.md` | Dashboard okuma → Panel okuma |
| `docs/analysis/lumos-cu4-confirmation-skeleton-draft.md` | Dashboard / listeleme → Panel / listeleme |
| `docs/memory/evidence-continuity-ec2-07-decision.md` | Kayıtlar/Dashboard → Kayıtlar/Panel (3 yer) |
| `docs/memory/domain-monitoring-design-decision.md` | Dashboard → Panel izleme özeti |

**Dokunulmadı:** Legacy kod adları (`getDashboardData()`, `readBackendDashboardState()`) — kod sembolü; yalnızca kullanıcıya dönük metin hedeflendi. Mimari «Gateway» terimi ADR/trust model bağlamında bilinçli.

---

## Task 3 — Doc link düzeltmeleri (özet)

- RB-XX ve aşama anchor'ları: çift tire (`--`) → GitHub slug uyumu
- `docs/integrations-overview.md` → `analysis/lumos-audit-log-contract.md`
- `docs/decisions/ADR-012-lumos-security-codex.md` → `../analysis/ADR-012-enforcement-decision-matrix.md`
- `docs/analysis/release-blockers.md` → `../GITHUB_RELEASE_CHECKLIST.md`
- `docs/memory/audit-hook-term-decision.md` → `../../.github/workflows/ci.yml`
- `.cursor/rules/*.mdc` → `docs/ozellik-oncesi-hazir-cozum-taramasi.md` (repo içi)
- `docs/lumos-persona-bypass-entry-inventory.md` — persona checkpoint/gap anchor'ları
- `docs/analysis/lumos-pc-remote-bridge-skeleton-verification.md` — satır numarası linkleri → başlık anchor'ları

**Kalan (düşük öncelik):** `technical-debt-*` belgelerinde `td-XX` kısa anchor'ları; tam başlık slug'ına güncelleme ayrı PR'da yapılabilir — dosya yolu doğru, yalnızca alt başlık eşleşmesi kısmi.

---

*Bu rapor `chore/hygiene-sweep-20260626` hijyen dalının çıktısıdır.*
