# TODO / FIXME / Placeholder Sweep Report

| Alan | Değer |
|------|-------|
| Tarih | 2026-06-26 |
| Dal | `docs/na-sweep-closure-544` |
| Kapsam | Repo taraması (`.git`, `node_modules`, `.venv`, `dist`, lock dosyaları hariç) |

## Özet

| Metrik | Sayı |
|--------|------|
| Toplam eşleşme (grep) | ~120 (çoğu UI `placeholder`, iş `TBD`, bilinçli stub) |
| **SAFE_FIX uygulandı** | **1** |
| **RESOLVED-DOC** | **4** (NA-03, NA-06, NA-07, NA-08) |
| **NEEDS_APPROVAL** | **1** (NA-01 — davranış değişikliği) |
| **NEEDS_OWNER** | **3** (NA-04, NA-05, NA-02 arşiv notu dahil izleme) |
| Terminoloji düzeltmesi (Task 2) | 4 dosya, 7 metin değişikliği |
| Kırık doc linki düzeltmesi (Task 3) | 18 dosya, ~35 link/anchor |

---

## SAFE_FIX — uygulanan

| Dosya | Değişiklik |
|-------|------------|
| `docs/mac-app-link-layer.md` | `TODO (cannot ship…)` → `SHIP BLOCKER (intentional placeholder — Alpha):` — bilinçli Apple Team ID yer tutucusu; davranış değişikliği yok, netleştirme |

---

## NEEDS_APPROVAL — işlenen kayıtlar (NA-01 … NA-08)

| ID | Konum | Sınıflandırma | Durum | Gerekçe / kapanış |
|----|-------|---------------|-------|-------------------|
| NA-01 | `src/core/decision_runner.py:78` | `DEFER` | **NEEDS_APPROVAL** | **core/** — `base_dir` zorunlu kılma otonom apply davranışını değiştirir; yorum `DEFER(autonomous-apply)` ile etiketlendi; mantık değişikliği ayrı onay |
| NA-02 | `archive/packages/kando_core/.../decision_runner.py:78` | Arşiv kopyası | **RESOLVED-DOC** | Arşiv mirror; canonical kaynak `src/core/decision_runner.py` (NA-01); arşivde ayrı patch yapılmaz |
| NA-03 | `docs/mac-app-link-layer.md` | Placeholder `XXXXXXXXXX`, `com.welockai.lumos` | **RESOLVED-DOC** | Bilinçli Alpha stub; SAFE_FIX uygulandı; gerçek Apple kimlik bilgisi → owner (bkz. naming registry §C.2) |
| NA-04 | `src/security/`, `src/engine/online_engine.py`, köprü `KANDO_BRIDGE_SECRET`, OAuth yüzeyleri | Secret / gateway stub | **NEEDS_OWNER** | Güvenlik / köprü sözleşmesi; repoda secret yok; Vercel env + yerel köprü owner checklist |
| NA-05 | İş planı belgelerindeki **TBD** (fiyat, KYC, destek e-postası, SLA) | `TBD` | **NEEDS_OWNER** | Ticari / hukuk kararı — [`bank-readiness-checklist.md`](./bank-readiness-checklist.md), [`pre-commercial-release-plan.md`](./pre-commercial-release-plan.md); sahte değer üretilmez |
| NA-06 | `src/task_engine/observation/state.py` | `known_files` placeholder | **RESOLVED-DOC** | Gözlem v1 bilinçli stub; yorum `intentional stub` ile netleştirildi; davranış değişikliği yok |
| NA-07 | UI / CSS `::placeholder`, `placeholder-block` | HTML/CSS | **RESOLVED-DOC** | Kullanıcı arayüzü yer tutucu metni; ürün stub değil; grep yanlış pozitif — dokunulmaz |
| NA-08 | `DIRECT_WRITE_ATTEMPT` log sabiti | Kod | **RESOLVED-DOC** | Audit terimi; TODO değil, grep yanlış pozitif — [`write_interceptor.py`](../../src/core/write_interceptor.py) |

### NA-01 — onay sonrası öneri (kod değişikliği)

`option_to_proposals()` ve çağıranlarda `base_dir: Optional[Path]` → zorunlu `Path`; `base_dir is None` iken `protected_target=False` yerine erken hata veya explicit non-protected audit. **Güvenlik / otonom apply** kapsamı — ayrı PR + güvenlik sahibi.

### NA-04 — owner adımları (özet)

1. Yerel: `KANDO_BRIDGE_SECRET` yalnızca `.env` / shell export — repoya yazma.
2. Vercel Production: `BRIDGE_UPSTREAM_URL` + `KANDO_BRIDGE_SECRET` — bkz. [`vercel-bridge-proxy-setup.md`](../vercel-bridge-proxy-setup.md).
3. OAuth / gateway stub: private layer; public repoda implementasyon yok.

### NA-05 — owner adımları (özet)

1. Destek e-postası: `support-channel-alpha.md` doldur → naming registry §C.2.
2. Fiyat / KYC / SLA: `bank-readiness-checklist.md` + ticari onay.
3. Repoda `TBD` kalması bilinçli — sahte değer commit edilmez.

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

*Bu rapor NA sweep closure (`docs/na-sweep-closure-544`) çıktısıdır. Konsolide kapanış: [`backlog-closure-report.md`](./backlog-closure-report.md).*
