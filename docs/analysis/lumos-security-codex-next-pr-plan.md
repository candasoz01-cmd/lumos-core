# Lumos Security Codex — Next Minimal PR Plan

| Alan | Değer |
|------|-------|
| Durum | **Öneri** — ADR-012 paketi sonrası |
| Tarih | 2026-06-21 |
| Önkoşul | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [enforcement map](lumos-runtime-enforcement-map.md), [permission matrix](lumos-action-permission-matrix.md) |

## Karar (tek öneri)

**İlk PR: panel yüzeyinde codex görünürlüğü + gate stub düzeltmesi (minimal kod) — veya salt docs ikinci PR.**

Öncelikli **en küçük güvenli** adım:

### Önerilen PR #1: **Docs cross-link + panel gate warning (minimal)**

| Bileşen | Kapsam | Risk |
|---------|--------|------|
| **Docs** | ADR-012'yi `docs/decisions/` indeksine / ADR-010 chain summary'ye tek satır link | Sıfır |
| **Panel UI metni** | Görev sil/oluştur butonları yakınında codex uyarısı: *"Demo panel — tam policy zinciri CLI ile aynı değil; riskli işlemde dur."* (`panel/index.html` veya mevcut guidance bloğu) | Düşük |
| **Panel server stub** | `_task_actions_gate()` içinde `LUMOS_PROFILE` / offline env okuyup **yalnızca uyarı reason** döndür; `enabled` davranışını **henüz değiştirme** (davranış değişikliği ikinci PR) | Düşük |

**Neden bu PR?**

1. Enforcement map'in en büyük kullanıcı görünür gap'i: panel gate her zaman açık.
2. Davranışı hemen kilitlemek panel demo akışını kırabilir; önce **şeffaflık** (C4, C6) codex ile uyumlu.
3. Tek dosya panel metni + isteğe bağlı gate reason = dar diff.

**Bu PR'da yapılmayacaklar:**

- `profiles.py` / `TaskEngine` refactor
- Panel'den `check_policy` tam entegrasyonu (PR #2)
- Trust motor (ADR-007)
- `SECURITY_NEVER_AUTO` yeni branch'leri

---

## Alternatif (daha da küçük): Docs-only follow-up

Eğer **hiç kod dokunulmayacaksa** ilk merge edilen paket yalnızca bu 4 belge olur; sonraki PR:

- `docs/analysis/ADR-006-010-011-chain-summary.md` içine ADR-012 satırı
- Panel README veya `panel/scripts/panel_tasks_server.py` docstring'te codex referansı

**Artı:** Sıfır regresyon.  
**Eksi:** C6 panel gap kullanıcıya görünmez kalır.

**Karar:** Codex paketi **docs-only merge** kabul edilir; **PR #2 zorunlu** olarak panel warning + gate reason planlanır.

---

## Önerilen PR #2 (davranış — onay sonrası)

| Değişiklik | Dosya | Test |
|------------|-------|------|
| Panel DELETE/POST öncesi `check_policy` çağrısı | `panel/scripts/panel_tasks_server.py` | `tests/test_panel_gorev_delete_phase1.py` genişletme |
| `general_approval` vs `consent` ayrımı netleştirme | `cli_tasks_mutation.py` policy context | `tests/test_action_policy.py` |
| Gate `enabled: False` when offline veya koruma+delete | `panel_tasks_server.py` | Yeni panel policy test |

---

## Test ihtiyacı

| PR | Test |
|----|------|
| Docs-only (bu paket) | Yok — CI docs workflow yeterli |
| Panel warning | Opsiyonel snapshot/CSS test yoksa manuel panel smoke |
| Panel policy entegrasyonu (PR #2) | **Zorunlu:** `test_action_policy.py`, mevcut panel görev testleri |

---

## Başarı ölçütü

- [ ] ADR-012 Taslak merge edildi
- [ ] Enforcement map gap'leri PR planına bağlandı
- [ ] Panel kullanıcısı codex uyarısını görüyor (PR #2) veya docs'ta gap açık yazılı (PR #1 docs-only)
- [ ] CI yeşil

---

## Tek cümle sonraki iş

**Docs paketi merge sonrası:** Panel'de `_task_actions_gate` reason metni + kullanıcıya görünür codex uyarısı için dar PR aç (davranış kilidi değil, şeffaflık önce).
