# Güvenlik mimarisi — kalıcı repo kaydı

**Durum:** Aktif referans belgesi (kod değildir).  
**Üst sınır:** `docs/lumos-karar-sozlesmesi.md`  
**Genişletilmiş canonical:** `docs/memory/security-architecture.md`, `docs/memory/data-vault-user-data.md`

Bu dosya, sohbet/bellek kaybına karşı repo içinde kalıcı tutulan **güvenlik kuralları** özetidir. **Gerçek secret, token veya production credential yazılmaz.**

---

## Kaynak ve öncelik

| Kaynak | Rol |
|--------|-----|
| `docs/lumos-karar-sozlesmesi.md` | Bağlayıcı çekirdek sözleşme |
| `docs/security-architecture.md` (bu dosya) | Güvenlik özeti — hızlı erişim |
| `docs/memory/security-architecture.md` | Detaylı canonical kayıt |

---

## Güvenlik ilkeleri

| # | Madde | Statü |
|---|--------|--------|
| SEC-001 | Kullanıcı onayı olmadan ödeme, domain satın alma, veri taşıma, kalıcı silme, e-posta okuma/gönderme/silme yapılmaz. | **güvenlik kuralı** |
| SEC-002 | Silinen içerik kalıcı yok edilmez; trash/silinen alana taşınır. | **güvenlik kuralı** |
| SEC-003 | İç katmanlar dışarıdan komut veya veri doğrudan kabul etmez; akış Lumos geçidinden geçer. | **güvenlik kuralı** |
| SEC-004 | Offline modda dış/network erişimi yok; online modda yalnızca çağrıldığında çalışır. | **güvenlik kuralı** |
| SEC-005 | Emin olunmayan durumda dış etkili işlem yapılmaz. | **güvenlik kuralı** |
| SEC-006 | **İzinli yol da denetlenir.** Güvenlik yalnız erişimi kesmek değil; izin verilen yolların davranışını izlemektir. Guardrails dosyası gerçek izolasyon + izleme sayılmaz. Ajan doğrudan internete çıkmasa bile paket yöneticisi, log veya depo gibi izinli servisler yan kanal olabilir. | **güvenlik kuralı** — gerekçe 2026-08-28; uygulama izni değil — [`lumos-self-governance-surface.md`](analysis/lumos-self-governance-surface.md) |

---

## Gizli bilgi ve kasa modeli

| # | Madde | Statü |
|---|--------|--------|
| SEC-010 | Lumos tüm gizli bilgileri ve şifreleri **üzerinde taşımaz**. | **güvenlik kuralı** |
| SEC-011 | Gizli bilgiler mümkünse **ayrı güvenli kasa / iç katmanda** tutulur. | **güvenlik kuralı** |
| SEC-012 | Lumos yetkili **geçit / orchestrator** olarak çalışır; secret'lar ideal olarak Lumos yüzeyinde tutulmaz. | **güvenlik kuralı** |
| SEC-013 | Token ve credential'lar Lumos yüzeyinde açık tutulmaz; güvenli vault/katman tercih edilir. | **ileride değerlendirilecek** (vault uygulama spec — OD-001/002) |

---

## Kimlik, bridge ve kullanıcı verisi

| # | Madde | Statü |
|---|--------|--------|
| SEC-020 | Dış dünya ile kimlik ve oturum akışı Lumos geçidi üzerinden yönetilir. | **güvenlik kuralı** |
| SEC-021 | Bridge yalnızca yetkili, onaylı ve Lumos kontrollü dış iletişim kanalıdır. | **güvenlik kuralı** |
| SEC-022 | **Kullanıcı verisinin sahibi kullanıcıdır.** Lumos temsilci ve kontrollü katmandır. | **güvenlik kuralı** |
| SEC-023 | Diğer platformlardaki kişisel veriler ileride Lumos kasasına taşınabilir; yalnızca izinli, şeffaf, geri alınabilir ve kullanıcı kontrollü. | **ileride değerlendirilecek** |

---

## Ses / STT güvenlik sınırı

| # | Madde | Statü |
|---|--------|--------|
| SEC-030 | Sesli konuşma metne çevrildikten sonra yazılı kanaldakiyle **aynı güvenlik ve niyet sınırından** geçer. | **güvenlik kuralı** |
| SEC-031 | Bağlam, niyet, güvenlik sınırı ve önceki kararlarla tutarlılık kontrolü atlanmaz. | **güvenlik kuralı** |
| SEC-032 | Belirsiz niyette kısa netleştirme; otomatik varsayım yok. | **güvenlik kuralı** |
| SEC-033 | Gerçek Meet sesi yalnız `POST /v1/audio/transcriptions` (batch). Realtime Meet-sesi kapsam dışı. | **güvenlik kuralı** — [stt-data-boundary-v1](contracts/stt-data-boundary-v1.md) |
| SEC-034 | STT ayrı OpenAI API projesinde; model yalnız `OPENAI_MODEL_STT` (`whisper-1` / `gpt-4o-transcribe` / `gpt-4o-mini-transcribe`). Sohbet/cyber env'ine düşülmez. | **güvenlik kuralı** |
| SEC-035 | Depolama **ve** işleme `eu.api.openai.com` (Avrupa). Bölgesel işleme ayrı onaydır; veri yerleşimi uçlarında %10 ek ücret kabul. | **güvenlik kuralı** |
| SEC-036 | Ham ses log/artifact olarak kalıcı saklanmaz. Katılımcı açık onayı olmadan gerçek toplantı sesi gönderilmez. | **güvenlik kuralı** |
| SEC-037 | Avrupa yerleşimi + MAM/ZDR organizasyonda **yazılı** doğrulanana kadar yalnız sentetik/hassas olmayan test sesi. | **açılış kapısı** — ADR-025 |

---

## Public repo sınırları

| # | Madde | Statü |
|---|--------|--------|
| SEC-040 | Bu belgeye production secret, PII veya operasyonel credential yazılmaz. | **güvenlik kuralı** |
| SEC-041 | Public repo içeriği demo-safe olmalıdır. | **güvenlik kuralı** |
| SEC-042 | Yürütme üç parçalıdır: Task Registry (görev resmi kaydı) + Capability Token (göreve özel kısa ömürlü anahtar; ajan/kullanıcı üretmez) + Immutable Ledger (kanıt; kapı değil). Kayıtlı görev zincirine bağlanmayan işlem yürümez. Deny default + `unclassified` şüphe; "saldırgan" etiketi yok. Grant `SECURITY_NEVER_AUTO` açmaz. Kullanıcı onayı her adımda değil, yalnız riskli kapılarda. | **güvenlik kuralı** — [ADR-031](decisions/ADR-031-task-execution-grant.md), opt-in `LUMOS_TASK_EXECUTION_GRANT_ENABLED` |

---

## CI / kapsam dışı bırakılan güvenlik maddeleri

| ID | Madde özeti | Statü | Not |
|----|-------------|--------|-----|
| SEC-D01 | Vault katman uygulama modeli | **ileride değerlendirilecek** | OD-001 — `docs/memory/vault-secret-token-decision.md` |
| SEC-D02 | Token/bridge entegrasyon akışı | **ileride değerlendirilecek** | OD-002 |
| SEC-D03 | Computer Use onay kapısı teknik spec | **ileride değerlendirilecek** | OD-012 |
| SEC-D04 | Üretim auth / cihaz presence | **public'ten çıkarıldı, private/internal'a taşınacak** | ADR-007 trust engine katmanı |

---

## İlişkili belgeler

- `docs/product-rules.md` — ürün yüzeyi ve kullanıcı sahipliği
- `docs/tool-watchlist.md` — dış araç değerlendirme listesi
- `docs/decision-log.md` — karar ve erteleme günlüğü
- `docs/contracts/stt-data-boundary-v1.md` — Meet STT veri sınırı (ADR-025)
- `docs/contracts/task-execution-grant-v1.md` — görev yürütme anahtarı (ADR-031)
- `docs/analysis/lumos-self-governance-surface.md` — denetim merceği; izinli yol gerekçesi (SEC-006)

---

Son güncelleme: 2026-08-28 (SEC-006 izinli yol denetimi — yeni yön değil)
