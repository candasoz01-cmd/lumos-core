# Karar ≠ Kayıt — Onay ve Kayıt Mekanizmalarının Ayrımı

| Alan | Değer |
|------|-------|
| Durum | **Mimari ilke** — karar destek belgesi; kod değişikliği yok |
| Tarih | 2026-06-26 |
| Kapsam | Onay (gelecek yönetimi) ile kayıt (geçmiş koruma) sorumluluklarının karıştırılmaması |
| İlgili | [`welockai-trust-model-draft.md`](./welockai-trust-model-draft.md), [`lumos-character-prompt-draft.md`](./lumos-character-prompt-draft.md), [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md), [`lumos-audit-log-contract.md`](./lumos-audit-log-contract.md) |

**Sınır notu:** Bu belge public `lumos-core` deposunda foundation ilkesi olarak tutulur. Üretim kimlik, faturalama ve kurumsal arşiv politikası WeLockAI private katmanında yaşar; burada yalnızca sözleşme ve repo eşlemesi tanımlanır.

---

## 1. İlke özeti

**Karar ≠ Kayıt.** Lumos'ta iki mekanizma birbirinin yerine geçmez:

| Mekanizma | Zaman ekseni | Soru |
|-----------|--------------|------|
| **Onay** | Gelecek | «Bu işlem şimdi yapılsın mı?» |
| **Kayıt** | Geçmiş | «Ne oldu, kim onayladı, hangi gerekçeyle?» |

- **Onay mekanizması** → geleceği yönetir: riskli veya dış etkili adım yürütülmeden önce kullanıcı veya politika mercii «evet/hayır» der.
- **Kayıt mekanizması** → geçmişi korur: karar verildikten ve (varsa) uygulandıktan sonra append-only, içerik-güvenli iz bırakır.
- **Karıştırmak** → ya **bürokrasi** (her gözlem için onay ister, sistem tıkanır) ya da **kontrol kaybı** (onay olmadan sessiz yazma veya kayıt olmadan gizli kural değişimi) üretir.

### Kültür cümlesi

> **Kural değişebilir. Ama gizlice değişemez.**

Teknoloji ve ihtiyaçlar evrilir; **dürüstlük sabiti** (root = honesty constant) değişmez. Politika güncellemesi onay + gerekçe + kalıcı kayıt zinciriyle görünür olmalıdır; sessiz prompt veya config kayması bu ilkenin ihlalidir.

---

## 2. Sorumluluk ayrımı — Onay vs Kayıt

| Boyut | Onay | Kayıt |
|-------|------|-------|
| **Amaç** | Yürütme öncesi yetki ve niyet doğrulama | Yürütme sonrası hesap verebilirlik ve teşhis |
| **Zaman** | «Şimdi» — TTL, pending, token tüketimi | «Sonra» — append-only, silinmez özet |
| **Kim karar verir** | Kullanıcı, confirmation policy, kurumsal politika (private) | Sistem (olay yazıcı); insan yalnızca kaydı okur |
| **Veri doğası** | Operasyonel state — güncellenebilir, süresi dolabilir | Audit / ADR / git — değişmez veya versiyonlu |
| **Typical store** | `.lumos/pending_approvals/`, confirmation token | `.lumos/logs/`, `resource_usage.jsonl`, ADR, commit |
| **Başarısızlık sinyali** | Onay gelmedi → işlem **yapılmaz** | Kayıt yok → «ne oldu?» **cevapsız** kalır |
| **Prompt'ta mı?** | Hayır — kod + policy | Hayır — kod + audit sözleşmesi |
| **SECURITY_NEVER_AUTO** | Asla otomatik onay yok; açık komut/onay şart | Blok ve red kararları da kayda girer |

---

## 3. Akış — beş aşama (değişmez çekirdek evrimi)

Çekirdek sınırlar (güvenlik, yetki, kalıcı silme) **sessizce** değişmez. Evrim veya yüksek etkili karar şu zinciri izler:

```
👀 Önerildi → ✍🏻 Gerekçe → 👥 Onaylandı → 📝 Kayıt → 🔍 (yıllar sonra) iz
```

| Adım | Ad (TR) | Sorumluluk | Repo örneği |
|------|---------|------------|-------------|
| 1 | **Önerildi** | Sistem gözlemler, önerir; **uygulamaz** | ORAA `recommend_mode` / `propose_mode_change` |
| 2 | **Gerekçe** | Neden bu adım — eşik, risk, politika referansı | ORAA öneri JSON; ADR «Context / Decision» |
| 3 | **Onaylandı** | Kullanıcı veya yetkili mercii açık «evet» | `apply_mode_change(..., user_approved=True)`; `POST /approve`; confirmation consume |
| 4 | **Kayıt** | Uygulanan karar append-only veya versiyonlu kalıcı iz | `resource_modes.json` güncellemesi **sonrası** audit; git commit + ADR |
| 5 | **İz** | Yıllar sonra «kim, ne zaman, hangi gerekçeyle» sorulabilir | Audit JSONL, ADR dizini, `resource_usage.jsonl` istatistik geçmişi |

**Kritik:** Adım 3 tamamlanmadan adım 4'teki «uygulama kaydı» tek başına onay sayılmaz. Adım 4'teki audit, adım 3'ün **kanıtıdır**, yerine geçmez.

---

## 4. Başarısızlık modları

### 4.1 Yalnızca onay — kayıt yok

| Belirti | Sonuç |
|---------|--------|
| Pending onay silindi, audit yazılmadı | «Onayladım mı?» tartışması; teşhis imkansız |
| Mod değişti, `resource_usage.jsonl` / audit yok | Davranış değişti ama **iz yok** — güven kaybı |
| Kural prompt'ta «sessizce» güncellendi | Gizli politika değişimi; «kural değişebilir ama gizlice değişemez» ihlali |

**Önlem:** Onay tüketildikten sonra ilgili `event_type` audit satırı veya ADR/git kaydı zorunlu tutulur ([`lumos-audit-log-contract.md`](./lumos-audit-log-contract.md)).

### 4.2 Yalnızca kayıt — onay yok

| Belirti | Sonuç |
|---------|--------|
| Her telemetry satırı için kullanıcıdan onay istenir | Bürokrasi; sistem kullanılamaz |
| `resource_usage.jsonl` yazımı onay gerektirir | Gözlem katmanı tıkanır — **kayıt ≠ karar** |
| Log yazmak için confirmation | Yanlış sınıflandırma; kontrol kaybı değil **kontrol felci** |

**Önlem:** Gözlem ve telemetry (`record_event`) onaysız; **dış etkili uygulama** (`apply`, `execute`, `write_local` dış yüzey) onaylı. Sınır: [`lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md) § «Gözlemler → Önerir → Onay alır → Uygular».

### 4.3 Karışım — pending = audit sanmak

| Belirti | Sonuç |
|---------|--------|
| `.lumos/pending_approvals/*.json` arşiv audit gibi kullanılır | TTL dolunca kayıt kaybolur; compliance boşluğu |
| Audit satırına tam `arguments` kopyalanır | Gizlilik ihlali; pending state audit'e karışır |

**Önlem:** [`lumos-audit-log-contract.md`](./lumos-audit-log-contract.md) §1.4 — **pending ≠ audit**.

---

## 5. Repo eşlemesi

| Kavram | Rol | Onay mı / Kayıt mı | Referans |
|--------|-----|---------------------|----------|
| **ORAA** (Operational Risk & Assurance Agent) | Kaynak modu danışmanı — gözle → öner → onay → uygula | **Her ikisi** — öneri/onay ayrı, telemetry/audit ayrı | [`lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md), `src/integrations/resource_mode_advisor.py`, panel ORAA kartı |
| **Bridge audit** | Köprü komut/onay yaşam döngüsü olayları | **Kayıt** (onay sonrası özet) | [`lumos-audit-log-contract.md`](./lumos-audit-log-contract.md), `pc_remote_tools.py`, `lan_relay.py` |
| **`resource_usage.jsonl`** | Katman bazlı kullanım olayları (append-only JSONL) | **Kayıt / gözlem** — onay gerektirmez | `.lumos/resource_usage.jsonl`, `record_event()` |
| **ADR / git** | Mimari ve politika kararlarının kalıcı, versiyonlu izi | **Kayıt + gerekçe** (onay = merge/review süreci) | `docs/decisions/ADR-*.md`, PR review |
| **`SECURITY_NEVER_AUTO`** | Otomatik yürütme yasağı — onay mekanizmasının tabanı | **Onay katmanı** — profil/onaydan bağımsız blok | `task_engine/profiles.py`, [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) §2 |
| **`pending_approvals`** | Onay bekleyen operasyonel state | **Onay** — audit değil | `.lumos/pending_approvals/`, `packages/kando_bridge/.../pending_approvals.py`, [`pc-remote-pending-approval-contract.md`](./pc-remote-pending-approval-contract.md) |

### ORAA akışında ayrım (somut)

1. **Kayıt:** `record_event` → `resource_usage.jsonl` (onaysız gözlem).
2. **Onay öncesi:** `propose_mode_change` → kullanıcıya öneri; state değişmez.
3. **Onay:** Panel «Geç» / «Hayır, aktif kalsın» → `user_approved` bayrağı.
4. **Uygulama + kayıt:** `apply_mode_change` → `resource_modes.json`; audit/telemetry devam eder.

Mod değişimi **asla** yalnızca jsonl istatistiğine bakılarak otomatik uygulanmaz — bu, «yalnızca kayıt» ile «onay»ın birleştirilmesi hatasıdır.

---

## 6. Karar sözleşmesi ile hizalama

[`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) katmanları bu ilkeye şöyle oturur:

| Karar katmanı | Onay / Kayıt |
|---------------|--------------|
| Sadece cevap ver | İkisi de minimal — state değişmez |
| Analiz et, uygulama yapma | Kayıt (okuma logu) olabilir; onay gerekmez |
| Öner ama bekle | **Onay beklenir**; kayıt yalnızca öneri/ simülasyon düzeyinde |
| Açık onayla uygula | **Onay zorunlu** → uygulama → **kayıt zorunlu** |
| Asla dokunma | Onay bile otomatik tüketilmez; red/blok **kayda** girer |

---

## 7. Çapraz bağlantılar

| Belge | İlişki |
|-------|--------|
| [`welockai-trust-model-draft.md`](./welockai-trust-model-draft.md) | Onay zinciri (§6), pending vs audit, SECURITY_NEVER_AUTO |
| [`lumos-character-prompt-draft.md`](./lumos-character-prompt-draft.md) | Onay/kayıt ayrımı prompt'ta değil; kod + audit'te |
| [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) | Karar katmanları ve dokunulmaz çekirdek |
| [`lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md) | ORAA — gözlem/kayıt vs onay/uygulama referans uygulaması |
| [`lumos-audit-log-contract.md`](./lumos-audit-log-contract.md) | Bridge audit, pending ≠ audit, olay tipleri |
| [`pc-remote-pending-approval-contract.md`](./pc-remote-pending-approval-contract.md) | Köprü pending onay state sözleşmesi |
| [`lumos-security-never-auto-branch-scan.md`](./lumos-security-never-auto-branch-scan.md) | NEVER_AUTO enforcement haritası |
| [ADR-012](../decisions/ADR-012-lumos-security-codex.md) | Tek dış kapı, onay + kanıt |
| [`docs/templates/support-report-oraa.md`](../templates/support-report-oraa.md) | ORAA destek raporu şablonu |

---

## Özet

- **Onay** geleceği yönetir; **kayıt** geçmişi korur — birbirinin yerine geçmez.
- Karışım → bürokrasi veya kontrol kaybı.
- Çekirdek evrim: öner → gerekçe → onay → uygula → kalıcı iz.
- Kültür: kural değişebilir; gizlice değişemez — dürüstlük sabit, teknoloji evrilir.
- Repo: ORAA, bridge audit, `resource_usage.jsonl`, ADR/git, `SECURITY_NEVER_AUTO`, `pending_approvals` — her biri doğru sütunda kalır.
