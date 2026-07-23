<!-- markdownlint-disable MD013 -->

# Lumos kapsam muhasebesi — başlangıç kaydı

| Alan | Değer |
| --- | --- |
| Belge türü | Operasyonel kapsam ve kanıt kaydı |
| Tarih | 2026-07-18 (son kanıt güncellemesi: 2026-07-23) |
| Repo kanıtı | `origin/main` @ `56e1e8a5ce22a09a48e9b25489e4ee682c536614` |
| Kapsam | Lumos Orkestratör, ortak durum, onay, entegrasyon ve veri egemenliği için ilk 10 açık alan |
| Sınır | Bu belge P0/P1 triage, release blocker veya Karar Duvarı yerine geçmez |

## Amaç

Bir özelliğin konuşulmuş, kararlaştırılmış, kodlanmış, canlıya alınmış ve gerçek koşulda doğrulanmış hâllerini birbirinden ayırmak. Bir alt parçanın ilerlemesi, bütün kapsamın durumunu otomatik yükseltmez.

## Tek durum sözlüğü

| Durum | Zorunlu kanıt | Bu kanıt yoksa |
| --- | --- | --- |
| **FİKİR** | Kaynak konuşma, taslak veya vizyon kaydı | Kayıt dışı |
| **KARAR** | Kabul edilmiş karar kaydı, kapsam ve tarih | FİKİR |
| **KOD** | Kapsamın çalışan uygulaması + commit/PR + geçen test | KARAR |
| **CANLI** | Deploy/release kimliği + ortam + canlı sağlık kanıtı | KOD |
| **DOĞRULANDI** | Gerçek cihaz/kullanıcı senaryosu + tarih + sonuç + inceleyen | CANLI |

**Yükseltme kuralı:** Her durum önceki durumun kanıtını da gerektirir. `KOD`, yalnız iskelet, stub, katalog kaydı veya alt parça bulunduğu anlamına gelmez. `CANLI`, readiness bayrağı veya statik ekran değildir. `DOĞRULANDI`, yalnız kullanıcı beyanı veya ajanın kendi sonucu değildir.

## Zorunlu iz zinciri

Bir kayıt **KOD** veya üstüne çıkarılırken şu alanlar boş bırakılamaz:

| Alan | Beklenen değer |
| --- | --- |
| `source` | Talebin geldiği konuşma, issue veya kayıt |
| `decision` | Karar/ADR kimliği; karar yoksa açıkça `yok` |
| `owner` | Uygulayan ajan/kişi/ekip |
| `change` | Commit ve PR |
| `verification` | Test komutu ve sonucu |
| `release` | Deploy/release kimliği ve ortam; canlı değilse `yok` |
| `validation` | Gerçek cihaz/kullanıcı, tarih ve inceleyen; doğrulanmadıysa `yok` |
| `supersedes` | Değişen/iptal edilen önceki karar veya `yok` |

## İlk 10 açık alan

Ana durum, **bütün kapsam için kanıtlanan en ileri basamaktır**. “Parça kanıtı” sütunu, ana durumu yükseltmeye yetmeyen mevcut bileşenleri gösterir.

| ID | Kapsam | Ana durum | Parça kanıtı | Bir sonraki geçiş koşulu |
| --- | --- | --- | --- | --- |
| KA-001 | Çalışan ajanların ortak görünürlüğü | **KOD** (2026-07-20) | Main'de merge: #630 tipli v1 sözleşmesi (`src/core/agent_status_contract.py`), #629 çoklu-kaynak salt-okunur Board projeksiyonu (`src/lumos_board/agent_status.py`), #631 claim/lease deposu, #632 tek-okuyucu gateway. Gerçek çok-ajanlı claim kullanımı `TECHNICAL_DEBT.md` TD-04 kapanışında kayıtlıdır | Ortak Board yüzeyinin release/deploy kimliği ve canlı sağlık kanıtı (CANLI) |
| KA-002 | Tek görev/ajan koordinatörü | **FİKİR** | Brain tek ürün içi akışı orkestre eder; birleşik çok-ajan koordinatörü değildir. Parça kanıtı (2026-07-20): #631 task claim/lease sözleşmesi ve #632 single-reader coordination gateway main'de — dar teknik sözleşmeler var, genel koordinatör inşa kararı ve güvenlik bağımlılıkları hâlâ açık | Agent Network genel inşa kararı + güvenlik bağımlılıkları (ADR-008 gating) |
| KA-003 | Karar → ajan → commit → PR → canlı iz zinciri | **KARAR** | Evidence continuity ve agent-result kayıtları bazı adımları taşır; uçtan uca PR/deploy/validation zinciri yok | Tek correlation kimliğiyle bütün halkaları bağlayan uygulama ve kopuk-halka testleri |
| KA-004 | Tüm entegrasyonlarda ortak onay sözleşmesi | **KARAR** | Birçok provider `approval_required` / `awaiting_credentials` uygular; birleşik süre, iptal ve eski izin denetimi yok | Ortak sözleşme, adapter uyumluluk matrisi ve entegrasyonlar arası sözleşme testleri |
| KA-005 | “Lumos’u aç” birleşik durum ekranı | **FİKİR** | Panel, startup health, görevler ve köprü sağlığı ayrı yüzeylerde bulunur | Tek başlangıç sözleşmesi + veri kaynağı haritası + ekran ve durum birleştirme testi |
| KA-006 | Entegrasyonlarda var/hazır/bağlı/test edildi/canlı ayrımı | **KARAR** | Katalog, `connection_status`, approval/credential durumları ve “katalog canlı bağlantı değildir” sınırı bazı adapterlerde kod/dokümanda var; bütün kapsam uygulanmış değil | Tüm adapterlerde ortak durum şeması, son doğrulama zamanı, sağlık/yetki kapsamı; commit/PR ve sözleşme testleri |
| KA-007 | Model seçimi ve gerekçe kaydı | **KARAR** | `LUMOS-0017` model-bağımsız seçim ilkesini kaydeder; birleşik otomatik seçim/gerekçe/fallback hattı yok | Görev bazlı seçim uygulaması + gerekçe olayı + fallback ve karşılaştırma testleri |
| KA-008 | Çoklu cihaz senkronizasyonu ve güvenli devir | **FİKİR** | Cihaz/pairing taslakları var; v1’de full cloud/multi-device sync bilinçli kapsam dışı | Ayrı ürün kararı, tehdit modeli, revoke protokolü ve private/public sınırı |
| KA-009 | Kullanıcı kontrollü depolama ve veri konumu | **FİKİR** | Storage choice M0 vizyon tohumu; güvenlik/gizlilik metinleri gerçek akışla eşleşme ilkesini kaydeder | Karar kaydı + veri türü/konum sözleşmesi + taşıma/silme ve ağ-akışı doğrulama planı |
| KA-010 | Bağımsız AI değerlendirme ve karşılaştırma | **KARAR** | ADR-008 yatay komut yasağı ve bağımsız kanıt ilkesini tanımlar; otomatik kurul/karşılaştırma kapısı yok | Tipli teslim/inceleme protokolü + bağımsız kanıt zorunluluğu + çelişki senaryosu testleri |

## Kanıt dayanakları

- [Lumos Orkestratör v1 vizyon tohumu](../drafts/lumos-2040-vision-draft.md#lumos-orkestratör-v1--orkestra-şefi-katmanı): birleşik koordinasyon katmanının M0 olduğu ve implementasyon sayılmadığı kayıtlıdır.
- [ADR-008 Agent Network sınırı](../decisions/ADR-008-agent-network-boundary.md): Lumos Board adı ve bileşen taksonomisi karardır; genel Agent Network inşası hâlâ taslak/gated durumdadır.
- [Lumos Constitution](../CONSTITUTION.md): kanıt merdiveni, tek hedef ve sahiplik/claim kuralları canonical çalışma sınırıdır.
- [Lumos Master Roadmap](../ROADMAP.md): aktif faz ve STOP LIST bu belgedeki sıra önerilerinden üstündür.
- [Teknik borç kaydı](../TECHNICAL_DEBT.md): TD-04 gerçek çok-ajanlı Board/claim kullanımının kapanış kanıtını taşır.
- [Brain flow](../BRAIN_FLOW.md): mevcut tek ürün içi yüksek seviye akışı gösterir; çapraz-araç çok-ajan koordinasyonu kanıtlamaz.
- [Karar Duvarı — LUMOS-0017](../drafts/BACKLOG.md): model/ajan seçiminin gerekçeli ve model-bağımsız olması kararını taşır.
- [iOS review kapsamı](../app-store-review-prep.md): full Lumos cloud ve multi-device sync v1 kapsamı dışındadır.
- [Entegrasyon özeti](../integrations-overview.md): katalog/discovery ile canlı bağlantı sınırını gösterir.
- `src/kando/agent_runner.py`: yerel iş bazlı `agent_status_{job_id}.json` üretimini gösterir; ortak Board değildir.
- `src/integrations/providers/` ve ilgili testler: provider bazlı onay, credential bekleme ve bağlantı durumu parçalarını gösterir.

## Güncelleme akışı

1. Her turda yalnız bir `KA-*` maddesi ele alınır.
2. İş başlamadan hedef durum ve gerekli kanıtlar yazılır.
3. İş bitince kayıt yalnız üretilen kanıt kadar yükseltilir.
4. Eski karar değiştiyse `supersedes` doldurulur; eski kayıt silinmez.
5. Sonraki iş varsayılan olarak tablodaki en düşük numaralı, geçiş koşulu net madde olur.

## KA-001 KOD yükseltmesi — iz zinciri (2026-07-20)

| Alan | Değer |
| --- | --- |
| `source` | 2026-07-19/20 Claude oturumu; kullanıcı kararı "sıralı dilim: #630 sözleşme → #629 projeksiyon → #631 claim → #632 gateway" |
| `decision` | ADR-008 `Agent Status` bileşeni; sözleşmeler `docs/contracts/agent-status-v1.md`, `task-claim-v1.md`, `single-reader-gateway-v1.md` |
| `owner` | Claude (canonical sözleşme + entegrasyon); Codex paralel oturumu (projeksiyon/claim/gateway ilk taslakları, onaylı takeover ile devralındı) |
| `change` | Merge'ler: #630 `956c486`, #629 `6f731b2`, #631 `3fd9802`, #632 `3bcb389` |
| `verification` | #630–#632 merge kapılarında hedef testler ve CI geçti; sözleşme, sahiplik/çakışma, maskeleme ve izolasyon testleri main'de |
| `release` | `yok` — deploy/release kimliği yok, bu yüzden CANLI değil |
| `validation` | Kısmi operasyonel kanıt: 2026-07-20/21 gerçek çok-ajanlı claim kullanımı TD-04 kapanışında kayıtlı; CANLI önkoşulu ve release kimliği olmadığı için ana durum yükseltilmedi |
| `supersedes` | KA-001'in 2026-07-18 KARAR satırı (yükseltme; içerik değişmedi) |

## Güncel yönlendirme

Bu tablonun sıra kuralı, canonical [`ROADMAP.md`](../ROADMAP.md) faz kararına
tabidir. Aktif **FAZ 1** sırasında yeni agent/orchestration katmanı STOP LIST
kapsamındadır; bu nedenle KA-003 yeni uygulama hedefi olarak açılmaz. Ürün
çalışması ROADMAP'teki v0.5 Dosya + Görev hedefine göre yürür. Bu belge
uygulamanın kendisi değildir; yalnız durum ve geçiş kanıtını sabitler.
