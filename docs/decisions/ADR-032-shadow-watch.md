<!-- markdownlint-disable MD013 -->

# ADR-032 — Gözcü Katmanı / Shadow Watch

> 2026-09-02 kurucu tasarım isteği: scope dışına çıkan veya kötü niyet
> **şüphesi** alan ajanları, yalnız Lumos’un yetki sınırları içinde gözlemek.
> Sistemi terk ettikten sonra yetkisiz dış takip yok.
>
> **Kabul (2026-09-02):** kurucu `Accepted` + tek düzeltme — re-entry
> korelasyonu yalnız `subject_id` + `agent_id` ile kurulmaz. Kernel dilimi
> (şema, hash zinciri, doğrulanabilir oturum/lease/job bağı) yetkilendirildi.
> Gate / panel / TEG consume / varsayılan-on **yok**.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-09-02)** — kurucu; re-entry düzeltmesi dahil |
| Uygulama durumu | Kernel (şema + zincir + korelasyon) — `src/security/shadow_watch.py`; gate wiring yok; production yolları çağırmaz |
| Tarih | 2026-09-02 |
| Kapsam muhasebesi | **KARAR** + **KOD** (kernel, bu dal); CANLI / DOĞRULANDI yok |
| Üst ilişki | [CONSTITUTION](../CONSTITUTION.md) §9 / §11; [ADR-006](ADR-006-ai-firewall-guard-layer.md); [ADR-007](ADR-007-trust-engine-layer.md); [ADR-008](ADR-008-agent-network-boundary.md); [ADR-010](ADR-010-guard-policy-trust-terminology.md); [ADR-012](ADR-012-lumos-security-codex.md); [ADR-018](ADR-018-internal-layers-core-local-sentinel.md); [ADR-024](ADR-024-lumos-identity-multi-subject-model.md); [ADR-027](ADR-027-controlled-core-writer.md); [ADR-028](ADR-028-standing-low-risk-merge-approval.md); [ADR-031](ADR-031-task-execution-grant.md) |
| Merge kapısı | Security / privacy / permissions / governance. ADR-028 standing hattı **yok**. İnsan onayı şart |
| STOP LIST | [ROADMAP](../ROADMAP.md) «yeni agent / orchestration katmanı» **delinmez**. Bu belge Sentinel **kipi** tarif eder; dördüncü iç katman veya Agent Network açmaz |

---

## 1. Karar

Shadow Watch, Lumos’ta **gözlem-yalnız güvenlik kipi**dir. Hedef ajan
scope dışına çıkınca veya davranış zinciri yüksek risk skoru üretince:

1. **Olay kaydı** açılır (append-only, hash’li artefakt).
2. Lumos Orkestratör **geri çağırma / uyarı** gönderir.
3. Ajan dönmezse **salt-okuma yetkili gözcü** (Sentinel Shadow Watch kipi)
   yalnız Lumos’un kontrol ettiği yüzeylerde telemetri ve kanıt toplar.
4. Ajan Lumos yüzeyini terk ederse gözcü **durur**. Başka sistemde, başka
   üründe veya gerçek dünyada takip **yoktur**.
5. Lumos yüzeyinde yeniden görünürse önceki olay **yalnız doğrulanabilir
   iş yükü kimliği** ile ilişkilendirilir (oturum, Board lease soyu veya
   job). Yalnız `subject_id` + `agent_id` yetmez. Belirsiz kimlik önceki
   incident’ı **miras almaz**. Etiket sonraki erişimde karantina, dar
   scope, salt-okuma, ek onay veya otomatik engelleme tetikleyebilir.
6. «Kasıtlı / kasıtsız» ve «suçlu» **kesin hüküm değildir**. Çıktı davranış
   zincirinden **risk skoru + işlem etiketi**dir.
7. «Kötü maksatlı» etiketi sınırsız takip yetkisi **vermez**.
8. Belirsizlik, eksik kanıt, bozuk grant veya kapalı telemetri **fail-closed**
   kapanır: gözlemlenemeyen yürütme sürmez.

**Tek cümle:** Shadow Watch ajanı kovalamaz; Lumos evinin içinde izler,
kapıdan çıkınca durur, tekrar girince önceki dosyayı açar.

---

## 2. Ne değildir

| Bu ADR | Değil |
|--------|--------|
| Sentinel’in **olay kipi** (kernel: `src/security/shadow_watch.py`) | Dördüncü iç katman (Core / Local / Sentinel sabittir, ADR-018) |
| Gözlem + kanıt | Yürütme, patch, merge, görev tamamlama |
| Lumos-yüzeyi telemetrisi | OS-geneli, tarayıcı-dışı, fiziksel dünya, üçüncü taraf hesap takibi |
| Risk skoru + işlem etiketi | Niyet mahkemesi, «saldırgan» hükmü (ADR-031 ile aynı disiplin) |
| Opt-in kernel; production çağırmaz | Gate wiring, varsayılan-on, STOP LIST istisnası |
| Guard’ın yerine geçiş | `lumos_gate` / policy / TEG / confirmation **önce** durur; Watch onların **arka planı**dır |

Yatay kontrol yasağı (ADR-008, iç katmanlar) bozulmaz: gözcü hedef ajana
komut vermez, yetkisini artırmaz, onayını vermez. Geri çağırma yalnız
**Lumos Orkestratör** kaynaklıdır.

---

## 3. Konum — mevcut omurgada

Öncelik sırası değişmez (ADR-001 / ADR-006 / ADR-007 / ADR-008):

```text
AI Firewall (guard) → Trust → Router → Memory → Agent Network
                              ↑
                    Shadow Watch burada DEĞİL
```

Shadow Watch **Agent Network değildir** ve Router’ın yerine geçmez.

```text
Dış dünya / ajan yüzeyi
        │
        ▼
Lumos geçidi (ADR-012 tek dış kapı)
        │
        ├─ guard / policy / confirmation / TEG     ← yürütme kapısı
        ├─ Trust (lock, consent, presence)         ← kim / hangi rıza
        └─ Sentinel                                 ← gözlem (OD-006)
              └─ Shadow Watch kipi                  ← bu ADR
                    (yalnız olay sonrası, salt okuma)
```

**Rol ayrılığı (ADR-030 ile hizalı):** icra eden ≠ doğrulayan ≠ kayıt üreten.
Hedef ajan icra adayıdır; gözcü doğrulayan değildir (yalnız kanıt toplar);
nihai durum kaydını **olay defteri + insan / Orkestratör** üretir.

**Kimlik (ADR-024):** gözcü ayrı bir **agent öznesi**dir (`agent:shadow-watch`).
Lumos ID grant kaydeder; gözcü kendi lehine yetki üretemez (N8). İnsan
özneden gelen `observe_only` grant’ı olmadan kip **açılmaz** — uygulama
diliminde TEG `action_key` önerisi: `shadow_watch_observe` (yazma yok).

---

## 4. Mimari akış

```text
[1] Oturum bağlanır
    Scope Manifest (M) üretilir → checksum S = H(M)
    M ⊂ {tools, paths, network class, task_id, action_keys, profile}
    S, CU4 scope_hash ve TEG (task, action, resource) bağlarıyla
    YAN YANA durur; onları ezmez (bkz. §12)

[2] Her araç / kaynak / dosya / ağ / süreç / görev / metadata adımı
    gözlemlenen bağ O üretir → o_hash = H(O)
    o_hash ∈ S  → IN_SCOPE (sessiz, örneklemeli audit yeter)
    o_hash ∉ S  → SCOPE_VIOLATION_DETECTED
                    veya risk skoru eşik aşımı → SUSPICION_DETECTED

[3] Incident I açılır (append-only). Fail-closed: I yazılamazsa
    hedef yürütme durur (gözlemlenemeyen sapma sürdürülmez).

[4] RECALL — Orkestratör hedefe uyarı + son izinli scope’a dönüş
    ister. Gözcü henüz spawn olmaz.
        dönmüş + IN_SCOPE  → RETURNED (I kapanır veya residual)
        timeout / devam    → WATCH_ARMED

[5] WATCH_ARMED — TEG observe_only mint. Yazma grant’ı yok.
    Mint başarısız veya yüzey okunamıyorsa → FAIL_CLOSED_BLOCK
    (fail-open «izlemeden devam» yok).

[6] WATCHING — salt okuma telemetri (bkz. §9). Hedefin grant’ı
    genişlemez. Gözcü Local yürütme kipine düşemez.

[7a] Hedef Lumos yüzeyinde kalır
       skor / etiket etkileri: daralt, salt-okuma, ek onay, karantina, blok

[7b] Hedef Lumos yüzeyini terk eder
       WATCH_CLOSED_SURFACE_EXIT
       kovalama yok; doğrulanabilir kimlik kaydı kalır (§4.1)

[8] Yeniden görünürlük (yalnız Lumos kontrolündeki yüzey)
       doğrulanabilir oturum / lease soyu / job eşleşirse
           I ile CORRELATED_REENTRY
       yalnız subject+agent, placeholder veya çelişen oturum
           no_inherit — önceki incident miras değil
       etiket yalnız korelasyon varsa sonraki kapılara uygulanır
```

### 4.1 Re-entry korelasyonu (2026-09-02 düzeltmesi)

Korelasyon anahtarı **`subject_id` + `agent_id` değildir.** Bunlar gerekli
önkoşuldur; miras için ek olarak **doğrulanabilir** iş yükü kimliği gerekir:

| Bağ | Ne zaman geçerli |
|-----|------------------|
| `session_id` | Boş / `session:unspecified` / `unknown` değil |
| Board lease soyu | `claim_id` veya `parent_claim_id` zinciri kesişir |
| `job_id` | Agent-status / iş yükü kimliği, placeholder değil |

Kurallar:

1. Her iki tarafta da doğrulanabilir bağ yoksa → `no_inherit`.
2. Aynı `session_id` → korelasyon.
3. Lease soyu kesişiyorsa (çocuk claim parent’ı taşır) → korelasyon; oturum
   değişmiş olsa bile.
4. Aynı doğrulanabilir `job_id` → korelasyon.
5. İki doğrulanabilir `session_id` farklı ve lease kesişmiyorsa →
   `session_conflict_without_lease` → `no_inherit`.
6. Belirsiz veya doğrulanamayan kimlik **önceki incident’ı miras almaz**.

### Lumos-kontrollü yüzey (gözlemin **tek** yasal alanı)

Gözcü yalnız şu sınıfta okuyabilir (uygulama allowlist’i ayrı PR’da kilitlenir):

- `lumos_gate` / `task_dispatch` / `task_engine` adım izi
- `write_interceptor` / `workspace_contract` path kararları
- `guard_audit` + evidence journal
- TEG registry / ledger (hash’ler; ham token yok)
- confirmation grant metadata (`confirmation_id`, `scope_hash`, action_key)
- panel / köprü / WebMCP tool çağrıları (panel-kontrollü)
- Board claim (görev, scope, owner) — yazmadan

**Dışında (yasak):** başka tarayıcı profili, OS süreç ağacı (Lumos executor
dışı), ağdaki üçüncü taraf hesap, e-posta sağlayıcısı, fiziksel konum,
başka ürün, başka cihaz, «gerçek dünya» kişi takibi.

---

## 5. Durum makinesi

Durumlar **tek incident** içindir. Yeni sapma yeni incident açabilir;
eskiyi sessizce genişletmez.

```text
                  ┌─────────────┐
                  │  IN_SCOPE   │
                  └──────┬──────┘
           scope dışı / skor eşik
                         ▼
              ┌──────────────────────┐
              │ INCIDENT_OPEN        │
              │ (kayıt zorunlu)      │
              └──────────┬───────────┘
                         ▼
              ┌──────────────────────┐
              │ RECALL_ISSUED        │
              └─────┬──────────┬─────┘
           döndü    │          │  timeout / devam
                    ▼          ▼
         RETURNED_TO_SCOPE   WATCH_ARMED
                    │          │
                    │          ├─ mint fail → FAIL_CLOSED_BLOCK
                    │          ▼
                    │        WATCHING
                    │          │
                    │          ├─ yüzey terk → SURFACE_EXIT (dur)
                    │          ├─ skor↑ → QUARANTINED / BLOCKED
                    │          └─ insan kapat → CLOSED
                    ▼
                 CLOSED
```

| Durum | Gözcü | Hedef yürütme | Çıkış |
|-------|-------|---------------|--------|
| `IN_SCOPE` | yok | mevcut kapılar | sapma |
| `INCIDENT_OPEN` | yok | duraklatılabilir | kayıt yazılamazsa blok |
| `RECALL_ISSUED` | yok | daraltılmış / durdurulmuş | dönüş veya timeout |
| `WATCH_ARMED` | mint | yok (bekler) | mint fail → blok |
| `WATCHING` | salt okuma | mevcut + etiket etkileri | terk / kapat / yükselt |
| `SURFACE_EXIT` | **yok** | Lumos dışı = yetki dışı | yalnız reentry |
| `QUARANTINED` | isteğe bağlı | sandbox / salt-okuma | insan |
| `BLOCKED` | yok | deny | insan |
| `FAIL_CLOSED_BLOCK` | yok | deny | insan |
| `CLOSED` | yok | normal kapılar | — |

**Zorunlu geçiş kuralı:** `WATCHING` ancak `RECALL_ISSUED` sonrası ve
dönüş yoksa. Gözcü, geri çağırma atlanarak «sessiz takip» için spawn
**edilemez** (gizli polis kipi yok).

---

## 6. Tehdit modeli

Kapsam: **ajan sapması ve gözcü suistimali**. Kullanıcı tehdidi, klasik
ağ saldırısı ve fiziksel güvenlik bu ADR’nin uygulama paketi değildir.

| ID | Tehdit | Aktör | Etki | Karşı ölçü |
|----|--------|-------|------|------------|
| T1 | Scope creep (izinli tool, izinsiz hedef) | hedef ajan | yetki sapması | Manifest checksum; TEG `capability_deviation` |
| T2 | Görev / metadata ile kalıcılık | hedef ajan | iz bırakmadan devam | görev oluşturma/değiştirme kanalı zorunlu kayıt |
| T3 | Dışarı veri (network, clipboard, dosya) | hedef ajan | sızıntı | network class + boyut hash; içerik kopyalanmaz |
| T4 | Gözcüyü executor’a çevirme | hedef / prompt | yatay kontrol | observe_only; Local rol yasağı; NEVER_AUTO |
| T5 | «Kötü maksatlı» etiketini takip emri sanma | operatör / ajan | yetki genişlemesi | §8 etiket tavanı |
| T6 | Lumos dışı kovalama | gözcü / insan talimatı | yasal ve sözleşme ihlali | SURFACE_EXIT = dur; dış konektör yok |
| T7 | Consent / confirmation bypass «güvenlik istisnası» | gözcü | mahremiyet delinmesi | §12; keystore/lock açılmaz |
| T8 | Telemetriye secret / PII yazma | log hattı | ikinci sızıntı | §9 minimizasyon; ham token yasak |
| T9 | Fail-open (sink kapalıyken yürütme) | hata | kör sapma | telemetri yoksa blok |
| T10 | Yanlış korelasyon (başka ajanı / yeni işi lekeleme) | yalnız subject+agent veya placeholder session | haksız karantina | doğrulanabilir oturum/lease/job yoksa `no_inherit` |
| T11 | Watcher impersonation | sahte özne | sahte kanıt | ADR-024 kimlik + TEG mint yalnız Task Authority |
| T12 | Bu ADR’yi docs-only sayıp standing merge | süreç | kapı atlama | §12 ADR-028; normative excluded |
| T13 | Prompt injection ile recall atlama | girdi | sessiz watch | recall atlanamaz (durum makinesi) |
| T14 | Label ile SECURITY_NEVER_AUTO / merge / writer açma | etiket | anayasa ihlali | etiket bu kapıları **açamaz** |

Kabul edilen residual risk: Lumos yüzeyine hiç uğramayan bir aktör
gözlenemez. Bu bir açık değil; **yetki sınırıdır**.

---

## 7. Risk skoru — niyet değil zincir

Skor, **gözlenen adımların** ağırlıklı bileşimidir. Çıktı alanında
`intent: intentional | accidental` **yoktur**. ADR-031’deki gibi sınıf
`unclassified` kalabilir; «kesin saldırgan» yazılmaz.

### Sinyaller (v1 sözleşme — ağırlık uygulama PR’ında kilitlenir)

| Sinyal | Ölçülen | Yön |
|--------|---------|-----|
| `scope_distance` | Manifest dışı adım sayısı / çeşit | ↑ |
| `persistence_after_recall` | Recall sonrası devam | ↑↑ |
| `grant_deviation` | TEG mismatch / replay / unregistered_key | ↑↑ |
| `privilege_seeking` | Yeni tool, geniş path, NEVER_AUTO adayı | ↑↑ |
| `exfil_signal` | Network / dış yazma / büyük okuma | ↑ |
| `concealment` | Audit kapatma, log silme, claim sahteciliği | ↑↑ |
| `task_mutation_burst` | Görev/metadata ani yazımı | ↑ |
| `return_after_recall` | Scope’a dönüş | ↓ |

Bantlar (eşik sayıları kilitlenmez; sıra kilitlenir):

| Bant | Anlam | Otomatik etki |
|------|-------|----------------|
| 0 | IN_SCOPE | yok |
| 1 | sapma adayı | incident + recall |
| 2 | kalıcı sapma | WATCH_ARMED |
| 3 | yüksek | karantina / salt-okuma / ek CU4 |
| 4 | tavan | auto-block; insan |

Skor **tek başına** «kötü maksatlı» etiketi basmaz. Etiket için: bant ≥ 3
**ve** `persistence_after_recall` **ve** insan veya ayrı kural kümesi
(uygulama PR’ı). Otomatik etiket varsa bile niyet cümlesi yok; işlem adı
`handling_tag=malicious_behavior_suspected`.

---

## 8. «Kötü maksatlı» etiketi — tavan

Etiket bir **işlem etiketidir**, suç hükmü değildir.

### Tetikleyebilir (yalnız sonraki Lumos erişiminde)

- karantina (`sandbox_only` / izole oturum)
- daha dar Scope Manifest (yeniden checksum)
- profil zorlaması: `rapor` / salt-okuma
- ek confirmation (CU4) — `safe_local` dahil
- otomatik engelleme (deny until human)
- Board claim reddi veya TTL kısaltma

### Tetikleyemez

- Lumos dışı takip, OS/kullanıcı avı, üçüncü taraf sorgu
- Watcher’a yazma, network, NEVER_AUTO, merge, controlled-writer
- Consent / lock / keystore açma
- Standing merge, ADR-028 sınıf terfisi
- Orijinal ajan grant’ını genişletme
- «Kanıt var, ömür boyu izle» yetkisi

Süre: etiket TTL + insan gözden geçirme olmadan **yenilenmez**. Bayat etiket
fail-closed **kalkmaz**; süresi dolunca `needs_human_review` olur, sessiz
temizlenmez.

---

## 9. Kayıt sözleşmesi, minimizasyon, privacy

### Zorunlu olay alanları (içerik değil bağ)

Her incident append kaydı en az şunları taşır (değerler hash veya enum):

| Alan | Ne | Saklama biçimi |
|------|----|----------------|
| Kullanılan araçlar | tool adı, sayı | allowlist adı; argüman gövdesi yok |
| Erişilen kaynaklar | kaynak sınıfı + id hash | ham URL/token yok |
| Okunan / yazılan dosyalar | workspace-relative path + SHA-256 | içerik yok; home/username strip |
| Network istekleri | yön + host sınıfı + boyut | full URL, header, body yok |
| Süreçler | Lumos executor pid/role | yabancı süreç yok |
| Görev oluşturma/değiştirme | task_id, op enum | başlık/gövde isteğe bağlı redakte |
| Metadata değişiklikleri | alan adı, old/new **hash** | PII değer yok |
| Dışarı gönderilen veri | kanal + byte + dest class | payload yok |
| Son bilinen işlem | action_key + timestamp + surface | serbest metin yok |

Her artefakt için `artifact_hash = SHA-256(canonical_bytes)`. Kayıt
`prev_hash` / `entry_hash` zinciri taşır (ADR-031 ledger ile **aynı fikir**,
aynı dosya olmak zorunda değil). Ledger kapı değildir; kapı hâlâ
registry + token + policy’dir.

### Minimizasyon kuralları

1. Amaç bağlama: kayıt yalnız incident soruşturması ve sonraki Lumos kapısı
   içindir. Ürün analitiği, model eğitimi, pazarlama yok.
2. Kullanıcı içeriği (görev başlığı, dosya metni, chat) **varsayılan yazılmaz**.
   Yazılacaksa kırmızı çizgi: hash veya sabit uzunlukta redakte özet.
3. Secret, passphrase, TEG ham token, vault ref çözümü **yasak**.
4. Gözcü, `effective_consent` olmadan identity/keystore **okumaz**.
5. WebMCP okuma izni (`read_consent_required`, `#821`) gözcüye «tahtayı
   oku» hakkı **vermez**. Gözcü tool **çağırmaz**; panel/köprü denetim
   izini okur.
6. Public repo: canlı telemetri şeması, operasyonel endpoint, PII örneği
   yazılmaz. Bu ADR demo-safe ilkedir.

### Privacy sınırı (tek tablo)

| Soru | Cevap |
|------|--------|
| Gözcü kullanıcıyı mı izler? | Hayır — ajan davranışını, Lumos yüzeyinde |
| Ajan çıktıktan sonra? | Hayır |
| Başka üründe aynı kişi? | Hayır; korelasyon yalnız Lumos handle |
| Consent yokken dosya içeriği? | Hayır |
| Güvenlik istisnası lock açar mı? | Hayır |
| Retention | Incident TTL + yasal asgari; trash aktif kaynak değil |

---

## 10. Fail-closed

Aşağıdakilerin **her biri** hedef yürütmeyi durdurur veya hiç başlatmaz.
«Biraz izleyelim» diye gevşeme yok.

| Koşul | Sonuç |
|-------|--------|
| Scope Manifest / checksum yok | yürütme yok |
| Incident kaydı yazılamıyor | yürütme yok |
| Recall atlanmış spawn isteği | reddedilir |
| `shadow_watch_observe` mint yok/uyuşmaz/replay | `FAIL_CLOSED_BLOCK` |
| Telemetri sink yok / zincir bozulmuş | blok |
| Yüzey allowlist dışı okuma talebi | gözcü deny; hedef blok |
| Kimlik belirsiz reentry | önceki incident miras değil; ek onay veya deny |
| Etiket TTL dolmuş, insan yok | `needs_human_review` (sessiz silme yok) |
| Gözcü yazma / dış network / NEVER_AUTO ister | deny + yeni incident (T4) |

ADR-010 ayrımı korunur: `locked ≠ denied`. Kilitli oturumda gözcü lock’u
açmaz; kilitliyse hassas yüzey okunamaz ve fail-closed uygulanır.

---

## 11. Önerilen entegrasyon noktaları

**Kod yok.** Uygulama ayrı, dar, env-kapalı dilim ister. Aşağısı harita.

| Nokta | Bugünkü parça | Shadow Watch rolü |
|-------|---------------|-------------------|
| Gate | `lumos_gate.py` | adım `o_hash` vs Manifest; sapmada incident+recall |
| Dispatch | `task_dispatch.py` | pending_approval ≠ watch spawn |
| Policy | `action_policy.py` | consent/offline kırmızı çizgi; gözcü istisna değil |
| Confirmation | `confirmation_policy.py` `_scope_hash` | CU4 hash Manifest’e **girdi**; watch grant ayrı |
| TEG | `task_execution_grant.py` | gözcü `observe_only`; hedef grant genişlemez |
| Guard audit | `guard_audit.py` | bugün log-ağırlıklı; Watch append-only disk ister (yeni) |
| Evidence | `evidence_continuity.py` | incident mirror adayı; PII kuralları aynı |
| Profiles | `profiles.py` | gözcü ≡ `rapor` + read; `write_local` yok |
| Workspace | `write_interceptor` / `workspace_contract` | path telemetrisi; yazma yok |
| Board claim | `lumos_board` | sapma claim ihlali de sinyal |
| WebMCP | `PanelRuntime.astro` consent gate `#821` | tool çağrısı izi; gözcü tool register etmez |
| Panel lock | `LockState` | trust sinyali; Watch tüketir, üretmez |
| Standing class | `standing_merge` | Watch etiketi merge açmaz |
| Sentinel | OD-006 / ADR-018 | kip burada yaşar; yeni katman yok |

Önerilen uygulama sırası (ayrı onay, FAZ-1 STOP LIST sonrası veya açık
istisna): (1) olay şeması + hash zinciri testleri, (2) Manifest checksum
yalnız log_only, (3) recall sinyali, (4) observe_only TEG, (5) etiket →
kapı. Varsayılan-on yok (CU4 / ADR-031 disiplini).

---

## 12. Çakışma kaydı — consent gate, checksum/scope, ADR-028

Bu bölüm «yok say» demez; çakışmayı **normatif sıraya** bağlar.

### 12.1 Consent gate

Üç ayrı kapı vardır; Watch dördüncüyü «güvenlik için hepsini ez» diye
açamaz.

| Kapı | Ne | Watch |
|------|----|--------|
| **Trust consent** | `effective_consent` — identity/keystore rızası (ADR-010; `#450/#451`) | Gözcü keystore/lock **açmaz**. Consent yokken kimlik alanı okunmaz. |
| **Confirmation** | CU4 tek-adım onay; `consent ≠ confirmation` | Recall ve karantina confirmation **yerine geçmez**. Riskli hedef işlem hâlâ CU4 ister. |
| **WebMCP okuma izni** | `#821` `lumos_panel_webmcp_read_consent_v1` — görev tahtası paylaşımı; `read_consent_required`; oturum + fail-closed | Watch, izinsiz tahta içeriğini **alır diye tool çağırmaz**. Denetim izi (tool adı, ret reason, consent.scope enum) içerik değildir. İzin yokken üyelik oracle’ı (`task_not_found` vs `already_completed`) zaten kapatıldı; Watch bu kapağı geri açamaz. |

**Çakışma:** «ajan kötü, o halde tahtayı / dosyayı oku» — **red**. Mahremiyet
kapısı güvenlik etiketinden üstündür. Gözcü ihtiyaç duyduğu şey bağ ve
hash’tir, içerik değil.

**Çakışma:** Watch spawn’ı kullanıcıya «yeni rıza» gibi sunulmaz (Sentinel
kullanıcıya görünmez, ADR-018). Operatör/Agent Wall görünürlüğü ayrı
yüzeydir (ADR-019); son kullanıcı Chat’ine «seni izliyoruz» sızması
ürün kuralı ihlalidir. İnsan onayı, etiket ve karantina **iç operatör /
kullanıcının kendi onay kapıları** üzerindedir.

### 12.2 Checksum / scope fikri

Bugün canlı olan bağlar:

| Bağ | Kod | Ne işe yarar |
|-----|-----|----------------|
| CU4 `scope_hash` | `confirmation_policy._scope_hash` — canonical JSON SHA-256[:16] | Onay **şu** what/where/effect için; sapınca `confirmation_scope_mismatch` |
| TEG bağ | `subject × agent × session × task × action × resource` | `capability_deviation` / replay |
| WebMCP consent.scope | `"session"` enum | Tahta paylaşımının **ömrü**; içerik checksum’u değil |

**Shadow Watch Scope Manifest checksum `S`** bunları **ikame etmez**.
`S`, oturumun izinli araç+kaynak kümesinin kanonik hash’idir; CU4 ve TEG
onun **alt bağlarıdır**.

| Yanlış birleştirme | Doğru |
|--------------------|--------|
| Gözcü, hedef ajanın `confirmation_id`’sini consume eder | Ayrı `shadow_watch_observe` grant |
| `scope_hash` eşleşmedi = kötü niyet | = sapma sinyali; niyet yok |
| Watch, Manifest’i genişleterek «izlemek için yetki verir» | Hedef grant aynı kalır veya daralır; Watch ayrı dar grant |
| WebMCP session consent = Manifest | Consent ömürdür; Manifest araç kümesidir |

**Çakışma:** CU4 hash 16 hex karakter (kırpılmış). Incident artefakt hash’i
tam SHA-256 olmalıdır. İki hash **karıştırılmaz**; kayıtta alan adları ayrı
(`cu4_scope_hash`, `manifest_sha256`, `artifact_sha256`).

### 12.3 ADR-028 standing merge

Bu ADR **hariç sınıftadır**: security, privacy, permissions, governance,
çekirdek sözleşme. Kapılar yeşil olsa bile standing merge **yok**.

Yol sınıfı (classifier, `origin/main` `src/standing_merge`):

- Dosya adı `docs/decisions/ADR-032-shadow-watch.md` — `docs/decisions/`
  `semantic_review` (hard-exclusion listesinde ADR-032 henüz yok).
- İçerik yeni norm tanımlar («bundan sonra neye izin verilir?») →
  attestation **`normative` → `excluded`**. `factual` attestation **hatalı**
  olur (TD-20 sınıfı: kâğıtta hariç, süreçte eligible).
- Uygulama kodu `src/security/`, `src/policy/`, `.github/` → hard-exclusion.
- Etiket / Watch kararı standing-class CheckRun’ını **yeşile boyayamaz**.

**Kabul sonrası öneri (ayrı PR, insan onayı):** `excluded_paths.json`
`exclude_prefixes` içine `docs/decisions/ADR-032` eklenmesi. Bu PR
`src/standing_merge/` değiştirdiği için kendisi de standing-hariçtir.

**Çakışma:** «docs-only = standing uygun» — ADR-028 ikinci filtresi bunu
keser. Bu belge olgu düzeltmesi değil, yetki sınırıdır.

---

## 13. Test matrisi

Kernel: `tests/test_shadow_watch.py`. Gate / panel / TEG consume satırları
hâlâ uygulama adayıdır.

| ID | Senaryo | Beklenen |
|----|---------|----------|
| W1 | Manifest’siz araç çağrısı | deny; incident; yürütme yok |
| W2 | IN_SCOPE adım | watch spawn yok; skor 0 |
| W3 | İlk scope dışı | incident + RECALL; watch yok |
| W4 | Recall sonrası dönüş | RETURNED; watch yok |
| W5 | Recall timeout | WATCH_ARMED → observe_only |
| W6 | Recall atlayıp watch isteği | reddedilir |
| W7 | observe_only mint fail | FAIL_CLOSED_BLOCK |
| W8 | Gözcü `write_local` / `mail_send` | deny + T4 incident |
| W9 | Telemetriye dosya içeriği / token | yazılmaz (assert yok) |
| W10 | SURFACE_EXIT sonrası dış host | hiçbir istek yok |
| W11 | Yalnız `agent_id`+`subject_id` reentry | `no_inherit` — önceki incident miras değil |
| W11b | Aynı doğrulanabilir `session_id` | `correlated_reentry` |
| W11c | Board lease soyu kesişimi | `correlated_reentry` (oturum değişse bile) |
| W11d | Aynı doğrulanabilir `job_id` | `correlated_reentry` |
| W12 | Placeholder session / çelişen oturum, lease yok | `no_inherit` |
| W13 | Etiket + NEVER_AUTO adayı | hâlâ deny; etiket açmaz |
| W14 | Etiket + standing merge | standing_merge false |
| W15 | WebMCP `read_consent_required` iken Watch list-tasks | çağrı yok; içerik yok |
| W16 | `effective_consent=false` iken keystore okuma | deny |
| W17 | CU4 `scope_hash` mismatch | sapma sinyali; consume yok |
| W18 | TEG replay gözcü grant | `replay` + blok |
| W19 | Sink down | blok, fail-open yok |
| W20 | «kasıtlı» alanı şemada | şema reddi |
| W21 | Kullanıcı yüzüne Sentinel/Watch adı | sızıntı testi fail |
| W22 | Env kapalı (varsayılan) | mevcut testler değişmez |

---

## 14. Public sınır ve STOP LIST

| Public `lumos-core` | Private / sonraya |
|--------------------|-------------------|
| Bu ADR’nin ilkeleri, durumlar, tavanlar | Operasyonel hunt runbook’u |
| Test isimleri ve fail-closed tablosu | Canlı incident store, imza anahtarı |
| Sentinel kip adı (iç doküman) | Dağıtım, edge, imzalama (OD-007) |

FAZ-1 STOP LIST: yeni agent/orchestration katmanı **yok**. Bu belge o yasağı
delmez; kipin **kodu** ayrı kullanıcı kararı + Board claim ister. OD-006
(Sentinel implementation-pending) ve OD-026 (iç mesaj olay kaydı) ana
ebeveyn kararlardır; bu ADR onların olay-kipi tasarımıdır.

Kapsam merdiveni: bugün **KARAR adayı (Proposed)**. Kullanıcı kabul etmeden
`Accepted` sayılmaz. KOD basamağı bu ADR’den doğmaz.

---

## 15. Kabul ölçütü (tasarım — uygulama değil)

1. Gözcü dördüncü katman olarak adlandırılmaz; Sentinel kipidir.
2. Watch, recall’sız spawn edilemez.
3. Gözcü yazamaz; observe_only dışında grant yok.
4. SURFACE_EXIT’te kovalama yok; reentry yalnız doğrulanabilir oturum / lease soyu / job ile.
5. Niyet alanı şemada yok; skor davranış zincirinden gelir.
6. «Kötü maksatlı» etiket tavanı §8’i aşamaz.
7. Consent, CU4, TEG, lock, NEVER_AUTO, standing, writer **gevşemez**.
8. Fail-closed tablosundaki her satır «devam et» diye yorumlanamaz.
9. Varsayılan production yolları bu kernel’i çağırmaz (gate wiring ayrı dilim).

---

## 16. Bilinçli yapılmaz (bu tur)

- `lumos_gate` / panel / WebMCP / TEG consume wiring
- `excluded_paths.json` güncellemesi (öneri §12.3; ayrı insan PR)
- Yeni env varsayılan-on (`LUMOS_SHADOW_WATCH_*`)
- Panel/Chat kopyası, Agent Wall ekranı
- OD indeksi / ROADMAP / CONSTITUTION değişikliği
- Gerçek takip protokolü, OS hook, network sniff tasarımı

---

## İlişkili

- [ADR-010](ADR-010-guard-policy-trust-terminology.md) — guard ≠ trust; consent ≠ confirmation
- [ADR-012](ADR-012-lumos-security-codex.md) — tek dış kapı; amaç sınırı
- [ADR-018](ADR-018-internal-layers-core-local-sentinel.md) + [OD-006](../memory/internal-communication-sentinel-decision.md)
- [ADR-024](ADR-024-lumos-identity-multi-subject-model.md) N8 — otorite kendine yetki üretemez
- [ADR-027](ADR-027-controlled-core-writer.md) — Watch writer değildir
- [ADR-028](ADR-028-standing-low-risk-merge-approval.md) + [TD-20](../TECHNICAL_DEBT.md)
- [ADR-031](ADR-031-task-execution-grant.md) + [sözleşme](../contracts/task-execution-grant-v1.md)
- WebMCP consent: [webmcp-challenge-2026.md](../webmcp-challenge-2026.md) §1b; `candasoz01-cmd/lumos-core#821` · MERGED · `4b4a909` · git · 2026-09-02
- CU4 `scope_hash`: `src/policy/confirmation_policy.py`
- Kernel: `src/security/shadow_watch.py` · `tests/test_shadow_watch.py`
- [lumos-karar-sozlesmesi.md](../lumos-karar-sozlesmesi.md)
