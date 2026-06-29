# Internal Alpha — 8 Saat Testi Runbook

| Alan | Değer |
|------|-------|
| **Belge türü** | Operasyonel runbook (docs only) |
| **Amaç** | Lumos'u **tek iş günü** boyunca gerçek kullanım; sürtünme ve blokaj yakalama |
| **Kuzey yıldızı** | *«Lumos'u kendim için bütün gün kullanabilir miyim?»* |
| **Üst sınır** | [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md), [`grounded-phase-roadmap.md`](analysis/grounded-phase-roadmap.md) |

**Bu test canlı OAuth gerektirmez.** GitHub / Slack / Gmail bağlantısı Phase 3 kapısıdır; bugün panel, yerel görevler ve köprü sohbeti odaktır.

---

## Ne zaman çalıştırılır

- P1-02 Hafta 1 kapandıktan sonra (**2026-06-26** itibarıyla uygun).
- Phase 2 kapısı: **en az bir tam 8 saat oturumu** + Hafta 2 checkpoint → [`INTERNAL_ALPHA_OPERATIONS.md`](INTERNAL_ALPHA_OPERATIONS.md) §9.
- Haftada en fazla **bir** tam oturum yeterli; sürtünme günlüğü birikir.

---

## 1. Sabah kurulum checklist (≤30 dk hedef)

### Ortam seçimi

| Seçenek | Ne zaman | Referans |
|---------|----------|----------|
| **Katman B — yerel tam** | Varsayılan; köprü + sohbet test edilecek | [`getting-started.md`](getting-started.md) §Katman B |
| **Prod Sınırlı mod** | Yalnızca statik panel smoke; köprü **503 beklenir** | [`INTERNAL_ALPHA_OPERATIONS.md`](INTERNAL_ALPHA_OPERATIONS.md) §4 |
| **Prod + köprü (owner)** | Owner Vercel env set ettiyse | [`vercel-bridge-proxy-setup.md`](vercel-bridge-proxy-setup.md) §Owner verification checklist |

### Katman B — sabah sırası (işaretle)

- [ ] Repo güncel: `git pull` → `main` CI yeşil ([`GITHUB_RELEASE_CHECKLIST.md`](GITHUB_RELEASE_CHECKLIST.md))
- [ ] `make test` — pass (baseline)
- [ ] `ui/.env.local` — `PUBLIC_*` ve token ([`getting-started.md`](getting-started.md))
- [ ] `export KANDO_BRIDGE_SECRET='…'` → `./scripts/bridge_start.sh` (8765)
- [ ] `python3 panel/scripts/panel_tasks_server.py` (8766)
- [ ] Repo kökü: `BRIDGE_UPSTREAM_URL` + `vercel dev` → `http://127.0.0.1:3000/panel`
- [ ] Panel **Sınırlı mod değil** / köprü bağlı görünüyor
- [ ] (Opsiyonel) `OPENAI_API_KEY` — en az bir sohbet turu için
- [ ] Sürtünme günlüğü dosyası açık (§2 şablon)

**Prod sınırlı smoke (alternatif, ≤10 dk):**

- [ ] `https://welockai.com/panel` → 200, Sınırlı mod badge **beklenen**
- [ ] `curl -sS -o /dev/null -w "%{http_code}" https://welockai.com/api/bridge/task` → **503** (env yoksa normal)

Detaylı köprü adımları: [`local-kando-dev-runbook.md`](local-kando-dev-runbook.md).

---

## 2. Sürtünme günlüğü şablonu

Gün boyunca her sürtünmede **bir satır**. Kopyala-yapıştır veya ekip kanalına yapıştır.

```markdown
## 8 Saat Sürtünme — YYYY-MM-DD

**Katılımcı:** @owner
**Ortam:** Katman B yerel / prod sınırlı / prod+köprü
**Başlangıç:** HH:MM — **Bitiş:** HH:MM (aktif ≥6 saat)

| # | Saat | Tür | Komut / ekran / akış | Ne oldu | Beklenen miydi? | Durum |
|---|------|-----|----------------------|---------|-----------------|-------|
| 1 | | komut | | | evet/hayır | çözüldü / ertelendi / açık |
| 2 | | kafa karışıklığı | | | | |
| 3 | | gereksiz konuşma | | | | |
| 4 | | blokaj | | | | |
| 5 | | komut | | | | |

**Türler:** `komut` · `kafa karışıklığı` · `gereksiz konuşma` · `blokaj` · `güvenlik/onay` · `diğer`

**Minimum:** 5 satır. Blokaj satırlarında «sonraki tek adım» yaz.
```

### Örnek satırlar (kalibrasyon)

| Tür | Örnek |
|-----|-------|
| komut | `vercel dev` kökte değil `ui/` içinde — 503 |
| kafa karışıklığı | Panel görevleri `localStorage` vs köprü — hangisi kaynak? |
| gereksiz konuşma | Ajan OAuth önerdi; scope'ta yok |
| blokaj | `OPENAI_API_KEY` yok — sohbet atlandı |
| güvenlik/onay | Silme onayı net değil — kullanıcı durdu |

---

## 3. Gün içi minimum aktivite

| # | Aktivite | Başarı |
|---|----------|--------|
| 1 | Panel açık kaldı (sekme veya yerel dev) | ≥6 saat toplam aktif |
| 2 | Yerel görev: ekle → düzenle → tamamla | ≥3 görev |
| 3 | Köprü sohbet | ≥1 soru-yanıt (key varsa) |
| 4 | Sürtünme günlüğü | ≥5 satır |
| 5 | `make test` veya gün sonu regresyon | pass |

**Bilinçli dışı:** Canlı GitHub issue, Slack mesajı, Gmail okuma — henüz yok.

---

## 4. Gün sonu inceleme soruları

Her oturum sonunda **üç soru** yanıtlanır (kısa cümle):

1. **Tekrar kullanır mıyım yarın?** (evet / hayır — tek cümle gerekçe)
2. **En büyük tek blokaj neydi?** (komut, ürün, güvenlik, eksik env)
3. **Bir şeyi yarın kaldırmak için neyi değiştirirdim?** (docs / UX / kod / owner action — taahhüt değil, not)

Şablon:

```markdown
### Gün sonu — YYYY-MM-DD

1. Yarın tekrar: evet/hayır — …
2. En büyük blokaj: …
3. Kaldırılacak sürtünme: …
4. P0-05 / regresyon: pass / fail
5. Phase 2 kapısına katkı: evet (tam oturum) / hayır (eksik)
```

Tam oturum kriterleri: [`grounded-phase-roadmap.md`](analysis/grounded-phase-roadmap.md) Katman 4.

---

## 5. İlgili belgeler

| Belge | Amaç |
|-------|------|
| [`getting-started.md`](getting-started.md) | Katman A/B, port tablosu |
| [`local-kando-dev-runbook.md`](local-kando-dev-runbook.md) | Köprü smoke, tanılama |
| [`vercel-bridge-proxy-setup.md`](vercel-bridge-proxy-setup.md) | Prod köprü owner checklist |
| [`INTERNAL_ALPHA_OPERATIONS.md`](INTERNAL_ALPHA_OPERATIONS.md) | P1-02 checkpoint, Phase 2 kapısı |
| [`grounded-phase-roadmap.md`](analysis/grounded-phase-roadmap.md) | 5 katman + OAuth blokajları |
| [`integrations-overview.md`](integrations-overview.md) | Demo vs canlı entegrasyon |
| [`GITHUB_RELEASE_CHECKLIST.md`](GITHUB_RELEASE_CHECKLIST.md) | Merge / CI operatör |

---

*Son güncelleme: 2026-06-26 — Internal Alpha 8 saat testi runbook; kod/OAuth yok.*
