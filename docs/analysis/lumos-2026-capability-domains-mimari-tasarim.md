# Identity / Memory / Voice / Vision / Connect — mimari analiz ve tasarım önerisi

| Alan | Değer |
|------|-------|
| Durum | **Karar destek — analiz + tasarım önerisi**; kod yazılmadı, karar verilmedi |
| Tarih | 2026-07-23 |
| Kapsam | Bu 5 alanın `lumos-core` içindeki gerçek kod karşılığı, Core/Local/Sentinel ile ilişkisi; teknik tanımlayıcı cutover **ayrı** ele alınır |
| Önkoşul | [`lumos-2026-service-mimari-rapor.md`](./lumos-2026-service-mimari-rapor.md) — Core/Local/Sentinel isimlendirme kararının durumu |
| Kapsam notu | Bu rapor, inceleme tarihindeki (2026-07-23) depo durumuna göre hazırlanmıştır; sonraki geliştirmeler bulguları değiştirebilir. Aşağıdaki tüm gözlemler kod ve doküman kanıtına dayanır; "değerlendirme" bölümleri kanıttan çıkarılan durum tespitidir, normatif bir "doğru/yanlış" hükmü değildir. |

## 0. Çerçeve

`candasoz01-cmd/Lumos` reposundaki ADR-018/`katmanlar.md` kendi "büyüme" listesinde şunu yazıyor: *"İleride görev adına göre büyür (örnek): **Memory · Vision · Voice · Cloud · Studio**."* Bu liste **Identity ve Connect'i içermiyor** — bu tesadüf değil, aşağıda §1 ve §5'te gösterildiği gibi ikisinin de zaten kendi adıyla kabul edilmiş ayrı ADR'leri var (Lumos ID / ADR-016, Lumos Service API Gateway / ADR-015). Yani beş alanı "Core/Local/Sentinel'e eklenecek eşit sekiz katman" gibi ele almak — önceki raporda da düzeltilen hata — burada da geçerli bir uyarı: **beşi birbirinden farklı olgunluk ve konumda.**

---

## 1. Identity

### Kod kanıtı

| Konum | Ne yapıyor |
|-------|-----------|
| `src/security/identity.py` (103 satır) | `DeviceIdentity` — ed25519 anahtar çifti, cihaz-yerel kimlik, AES-GCM şifreli saklama |
| `src/.lumos/identity.json` | Canlı runtime state — yukarıdaki sınıfın gerçek çıktısı |
| `src/integrations/providers/lumos_id_provider.py` (100 satır) | **"Lumos ID" sözleşmesi** — `contract_version: lumos.id_memory_gateway.v1`, `status: public_foundation`; ilkeler: `lumos_id_is_singular_and_provider_independent`, `no_provider_owns_the_identity`, `per_provider_data_segregation`, `cross_use_requires_explicit_approval`. **Stub**: `real_identity_storage: False` |
| `src/integrations/providers/service_gateway_provider.py` | `SERVICE_FAMILIES` içinde `identity` bir **capability ailesi** (`/v1/verify`, `identity_verification`) — Connect gateway'in altında bir yetenek olarak modelleniyor, ayrı bir katman değil |

### Karar durumu vs uygulama durumu

- **Karar durumu:** ADR-016 (Lumos ID + Memory Gateway) — kabul edilmiş (public foundation).
- **Uygulama durumu:** Kısmen — cihaz kimliği (`security/identity.py`) gerçek ve çalışır durumda; "Lumos ID" servis sözleşmesi (`lumos_id_provider.py`) kod olarak mevcut ama `real_identity_storage: False` ile stub olarak işaretli.

### Değerlendirme

Kod tabanında Identity **iki ayrı yerde, farklı olgunlukta** gözlemlendi:
1. Düşük seviye, gerçek: cihaz kriptografik kimliği (`security/identity.py`) — konum olarak Sentinel'in (eski: Bando) komşusu değil, Core/Local tarafında bulunuyor.
2. Yüksek seviye, stub/sözleşme: "Lumos ID" — ADR-016'nın ilkelerini taşıyor ama gerçek depolama yok; kod olarak **Connect'in bir provider'ı** (`lumos_id_provider`) içinde duruyor, bağımsız bir modül olarak bulunamadı.

**Core/Local/Sentinel ile ilişki:** Kod tabanında Identity şu an **peer katman olarak modellenmemiş** — hem Core/Local'a gömülü (cihaz kimliği) hem Connect'e gömülü (kimlik doğrulama servisi) durumda. ADR-016 "Lumos ID" adını ayrıca kilitlemiş durumda; bu iki ev arasındaki sınırın (hangi kod cihaz kimliği, hangisi servis kimlik doğrulama) hangi ADR'de netleştirileceği açık bir soru olarak kalıyor.

---

## 2. Memory

### Kod kanıtı

| Konum | Ne yapıyor |
|-------|-----------|
| `src/memory/memory.py` (72 satır) | `Memory` — not listesi, TTL temizliği, `SecureNotesStore`'a şifreli yaz/oku, `Context.enrich()` |
| `src/memory/schema.py` | `MemoryNote` dataclass — kind, content, source, ttl |
| `src/memory/secure_store.py` | `SecureNotesStore` — AES-GCM, `notes.enc.json`, merkezi sink guard'lı |
| `src/memory/session_memory.py` | `SessionMemory.enrich()` — **neredeyse boş stub**, sadece `Context`'i geri döndürüyor |
| ADR-003 (Canonical Memory), ADR-005 (Memory Graph, taslak), ADR-016 (Memory Gateway, foundation) | Üç ayrı taslak/foundation ADR — hiçbiri yukarıdaki 4 dosyayla birebir örtüşmüyor |

### Karar durumu vs uygulama durumu

- **Karar durumu:** ADR-003 (Canonical Memory) — kabul edilmiş taslak; ADR-005 (Memory Graph) — taslak, karar bekliyor; ADR-016'nın Memory Gateway kısmı — kabul edilmiş (public foundation).
- **Uygulama durumu:** Kod tabanında bu üç ADR'nin hiçbiri birebir uygulanmış olarak bulunamadı — mevcut kod, ADR'lerin tarif ettiği kapsamdan daha dar.

### Değerlendirme

Kod tabanında Memory = **basit, yerel, şifreli not deposu**; TTL'li, tek kullanıcı, tek cihaz. ADR'lerin tarif ettiği "Memory Graph" (node/ilişki tipleri) veya "Memory Gateway" (sağlayıcı bazlı segregasyon — `lumos_id_provider.py`'deki `KNOWN_MEMORY_SOURCES` bunun stub'ı) kod tabanında bulunamadı.

**Core/Local/Sentinel ile ilişki:** Mevcut kodda Memory fiilen **Core'un bir alt bileşeni** olarak çağrılıyor (Context enrichment zinciri üzerinden, kendi başına yetki üretmiyor — ADR-018'in Core tanımıyla tutarlı: *"kendi başına yetki üretmez"*). ADR'ler peer katman kapsamı öngörüyor; bununla mevcut kod arasındaki fark, isim/konum kararından önce kapanması gereken bir açık.

---

## 3. Voice

### Kod kanıtı

| Konum | Ne yapıyor |
|-------|-----------|
| `packages/kando_bridge/src/kando_bridge/transcribe.py` + `transcribe_engine.py` | Gerçek STT pipeline |
| `tests/test_bridge_transcribe.py`, `tests/test_bridge_transcribe_integration.py` | Test kapsamı var |
| Panel UI (browser `speechSynthesis`, bkz. `lumos-core` PR #179 "lang-only TTS") | TTS — tarayıcı tarafında, backend'de değil |
| `docs/memory/voice-media-experience.md` (canonical, 2026-06-17) | Ürün ilkeleri **kilitli**: STT→metin→**aynı güvenlik/niyet kontrolü**; ses-yazı devamlılığı; "ses katmanı UI-only değil" |

### Karar durumu vs uygulama durumu

- **Karar durumu:** `docs/memory/voice-media-experience.md` — canonical, ürün ilkeleri çoğunlukla `[migrated]` (kabul edilmiş) durumda; kamera/görsel destek maddeleri `[needs-review]` (karar verilmemiş).
- **Uygulama durumu:** Kısmen ve dağınık — STT kod olarak mevcut (`transcribe.py`, testli); TTS UI tarafında mevcut (panel, PR #179); doğrulanmış ilkedeki "STT sonrası aynı güvenlik/niyet kontrolü" tek bir kod noktası olarak bulunamadı.

### Değerlendirme

Kanıt tabanında Voice'un **ürün ilkeleri** belgelenmiş ve kabul edilmiş durumda (voice-media-experience.md `[migrated]` maddeleri) ama **implementasyon dağınık** gözlemlendi: STT `kando_bridge` içinde (teknik olarak Local/cihaz-köprü tarafına yakın), TTS panel/UI (Core'un kullanıcı yüzeyi) tarafında. Backend'de STT sonrası "aynı güvenlik/niyet kontrolünden geçmeli" ilkesinin karşılığı olan tek bir kod noktası bulunamadı.

**Core/Local/Sentinel ile ilişki:** Mevcut kodda Voice **cross-cutting** durumda — STT girişi Local/bridge katmanından, güvenlik kontrolü Sentinel'in ilgi alanından, kullanıcı deneyimi Core'dan geçiyor. Üç katmanı kesen bir akış zaten var ve ürün ilkeleri bunu tarif ediyor; kod tabanında karşılığı bulunamayan tek şey, bu akışı birleştiren bir orkestrasyon noktası.

---

## 4. Vision

### Kod kanıtı

| Konum | Ne yapıyor |
|-------|-----------|
| `packages/kando_runtime/src/kando_runtime/task_dispatch.py:36` | `TaskType = Literal["video", "image", "audio", "file", "shell", "generic"]` — "image" tip olarak tanımlı |
| `task_dispatch.py:39` | `"image_executor_pending"` — **literal olarak "henüz yok" durumu**, kuyruk adı olarak kodda var |
| `packages/kando_runtime/executors/` | `content_executor.py` (YouTube arama), `text_executor.py`, `video_executor.py` (Replicate video **üretimi**) — **`image_executor.py` yok** |
| `archive/panel/camera.html` | Arşivlenmiş, ölü |
| Mobil chat kamera (LUMOS_V1_READINESS.md) | Yalnızca dosya/fotoğraf **yükleme** UI'ı (native file input) — görsel **anlama/işleme** değil |
| `docs/memory/voice-media-experience.md` §"Kamera ve fotoğraf fikri", §"Görsel üretim / görsel destek" | Her ikisi de **`[needs-review]`** — ürün kapsamı netleşmemiş |

### Karar durumu vs uygulama durumu

- **Karar durumu:** Ürün kapsamı kararı bulunamadı — `voice-media-experience.md`'deki ilgili maddeler `[needs-review]`.
- **Uygulama durumu:** Uygulanmamış — kod tabanında `image_executor` bulunamadı; dispatcher'da yalnızca `"image_executor_pending"` adlı bir yer tutucu durum sabiti var.

### Değerlendirme

Kod kanıtına göre Vision, beş alanın **en az olgunu**: gerçek işleme kodu bulunamadı, dispatcher'da "image" tipi tanınıyor ve executor durumu literal olarak "pending" işaretli. Ürün tarafında da bir kapsam kararı bulunamadı (`needs-review`).

**Core/Local/Sentinel ile ilişki:** Kod tabanında hiçbir katmanla ilişkisi gözlemlenmedi çünkü karşılığı bulunamadı. Peer katman olarak konumlandırma, `image_executor` gibi bir yürütme biriminin var olmasına ve bir ürün kapsamı kararına dayanır — ikisi de şu an kanıt olarak yok.

---

## 5. Connect

### Kod kanıtı

| Konum | Ne yapıyor |
|-------|-----------|
| `src/integrations/` | `providers/` (**26 dosya**), `clients/`, `github/`, `mail/` (OAuth dahil), `vault/`, `registry.py`, `quantum_*` |
| `src/integrations/providers/service_gateway_provider.py` | **ADR-015'in doğrudan kod karşılığı** — `SERVICE_FAMILIES`: ai, security, **identity**, tools, integrations, regional, public_services; her biri `/v1/...` path + capability listesiyle |
| `src/integrations/providers/lumos_id_provider.py`, `device_provider.py`, `communications_provider.py`, `meetings_provider.py`, `mail_provider.py`, `web_search_provider.py`, `openai_provider.py`, `quantum_provider.py`, + 10 sosyal platform provider'ı | Geniş, gerçek yüzey |

### Karar durumu vs uygulama durumu

- **Karar durumu:** ADR-015 (Lumos Service API Gateway) — kabul edilmiş (public foundation).
- **Uygulama durumu:** Geniş ölçüde uygulanmış — `src/integrations/` altında 26 provider dosyası, OAuth akışları, `service_gateway_provider.py` ADR-015'in service-family modelini birebir taşıyor.

### Değerlendirme

Kanıt tabanında Connect, beş alanın **en olgun ve en geniş kod kapsamına sahip olanı** — kabul edilmiş bir ADR'i (ADR-015, foundation) ve geniş bir kod tabanı (`src/integrations/`, 26+ provider) bulundu. Buradaki fark büyük ölçüde **isimlendirme/konsolidasyon** ile mevcut kodun ADR-018'in omurga ağacına bağlanması arasında; yeni kod inşası için kanıt gerekmiyor.

**Core/Local/Sentinel ile ilişki:** Kod tabanında Connect, kendi `TRUST_STAGES` zincirine sahip (request_validation → trust_snapshot → policy_decision → confirmation_gate → provider_route → execute_or_deny → redacted_audit) — Core'un orkestrasyonundan ayrı bir akış olarak gözlemlendi. "Connect" adı henüz ADR-018'in omurga ağacında resmi olarak yer almıyor.

---

## 6. Sentez — beş alanın olgunluk/konum özeti

| Alan | Kod olgunluğu (gözlemlenen) | Bugünkü ev (gözlemlenen) | Peer katman kanıtı |
|------|---------------|------------|------------------------------|
| **Connect** | Yüksek (26 provider, ADR-015 kabul) | Fiilen bağımsız akış (`src/integrations/`) | Var — isimlendirme dışında ek kod kanıtı gerekmiyor |
| **Voice** | Orta (gerçek STT, TTS var) ama dağınık | Local/bridge (STT) + Core/UI (TTS) | Kısmi — orkestrasyon noktasına dair kod bulunamadı, ürün ilkeleri kayıtlı |
| **Identity** | Orta, iki ayrı yerde | Sentinel-komşusu (cihaz kimlik) + Connect (servis kimlik doğrulama) | Bulunamadı — iki ev arası sınırı tanımlayan bir karar kaydı yok |
| **Memory** | Düşük (yerel not deposu) | Core'un alt bileşeni | Bulunamadı — ADR'lerin tarif ettiği kapsamla mevcut kod arasında fark var |
| **Vision** | Yok (yalnızca `image_executor_pending` sabiti) | Yok | Bulunamadı — ne kod ne ürün kararı mevcut |

---

## 7. Tasarım seçenekleri (öneri niteliğinde, karar bekliyor)

Bu bölümdeki maddeler **seçenek/öneridir**, karar değil — ADR-018'in kilitlediği Core/Local/Sentinel'e dokunmuyor, yalnızca kanıta dayanarak beşinin nereye oturabileceğine dair bir yol haritası sunuyor. Karara bağlanması gereken sıra, sahiplik ve zamanlama bu raporun kapsamı dışında.

1. **Connect** — kanıt: kod ve ADR zaten olgun (§5). Buna dayanarak düşünülebilecek düşük riskli seçenek: `src/integrations/` + ADR-015'i `katmanlar.md` ağacına dördüncü peer olarak ekleyen kısa bir ADR; kod taşınmaz, yalnızca isim/doküman hizası. OD-027 ile aynı desen: envanter bu raporda mevcut, eksik olan karar.
2. **Voice** — kanıt: akış üç katmanı kesiyor, orkestrasyon noktası kod olarak bulunamadı (§3). Bir "Voice" modülü altında toplama kararından önce, STT (Local/bridge) → güvenlik/niyet kontrolü (Sentinel) → yanıt (Core) → TTS (UI) zincirinde hangi parçanın nerede kalacağını tanımlayan bir ADR ihtiyacı gözlemlendi — bu raporun kapsamı dışında, ayrı bir görev.
3. **Identity** — kanıt: iki ayrı ev, aralarındaki sınırı tanımlayan bir karar kaydı bulunamadı (§1). Peer katman kararından önce, `security/identity.py` (cihaz kimliği) ile `lumos_id_provider.py` (servis kimlik doğrulama) arasındaki ilişkiyi (hangisi authoritative, hangisi adapter) netleştiren bir ADR ihtiyacı gözlemlendi.
4. **Memory** — kanıt: mevcut kod ile ADR-003/005/016'nın tarif ettiği kapsam arasında fark var (§2). Konum kararından önce, hangi ADR hedefinin (Canonical Memory / Memory Graph / Memory Gateway) inşa edileceğine dair bir karar ihtiyacı gözlemlendi.
5. **Vision** — kanıt: ne kod ne ürün kararı mevcut (§4). Mimari konum, `docs/memory/voice-media-experience.md`'deki `[needs-review]` maddelerinin kapanmasına bağlı görünüyor; `image_executor_pending` kodda halihazırda bir yer tutucu olarak duruyor.

---

## 8. Teknik tanımlayıcı cutover — ayrı plan (bu raporun kapsamı dışı, yalnızca çerçeve)

ADR-018 madde 5 ve `Lumos` reposundaki `legacy-naming.md` §EXC bunu zaten **bilinçli olarak ayırmıştı**: `kando_bridge`, `kando_runtime`, `KANDO_*`, `X-Kando-Token`, `src/kando/`, `cando_local.py`, `tests/kando/`, `tests/cando/` — bunlar mimari ad değil, teknik tanımlayıcı; ayrı bir OD/cutover gerektiriyor. Bu domain analizinde bunlara **dokunulmadı** — yukarıdaki §1-§5'teki tüm kod referansları mevcut teknik isimleriyle bırakıldı, çünkü onları değiştirmek ayrı bir kararın konusu.

Ayrı plan bir sonraki oturumda şu iskeleti izleyebilir (OD-027 deseni):
1. Envanter — bu raporda ve önceki raporda (`lumos-2026-service-mimari-rapor.md` §6) zaten toplandı.
2. Kapsam — env var mı (`KANDO_*`), HTTP header mı (`X-Kando-Token`, geri uyumluluk riski yüksek), paket dizini mi (`packages/kando_*`), test dizini mi (`tests/kando/`, `tests/cando/`).
3. Kesme kriterleri — OD-027'nin K1-K8 checklist'i (entrypoint, test, CI, import, güvenlik sınırı, rollback, workspace, public sınır) doğrudan uygulanabilir.
4. Faz sırası — düşük risk (test dizini adları) önce, yüksek risk (HTTP header, env var — geri uyumluluk kırar) sonra veya ayrı bir deprecation penceresiyle.

Bu rapor bu planı **başlatmıyor**, yalnızca nereye bağlanacağını işaretliyor.

---

## 9. Küçük adımlara bölünmüş sonraki işler (yalnız plan)

| # | İş | Risk | Bağımlılık |
|---|-----|------|------------|
| 1 | Connect ADR'i (§7.1) — `src/integrations/` + ADR-015'i resmi peer olarak `katmanlar.md`'ye bağla | Düşük, docs-only | Core/Local/Sentinel'in `lumos-core`'a uygulanması (önceki rapor) |
| 2 | Identity sınır ADR'i (§7.3) — `security/identity.py` vs `lumos_id_provider.py` | Düşük-orta, docs-only | Yok |
| 3 | Voice orkestrasyon tasarımı (§7.2) | Orta, ayrı ADR + muhtemelen kod | #2'den sonra önerilir (Identity netleşmeden Voice'un güvenlik kontrol noktası belirsiz kalır) |
| 4 | Memory hedef kararı (§7.4) | Orta-yüksek, ADR-003/005/016 arası seçim gerektirir | Yok, ama büyük |
| 5 | Vision ürün kararı (§7.5) | Belirsiz — ürün kapsamı henüz yok | `voice-media-experience.md` needs-review maddelerinin kapanması |
| 6 | Teknik tanımlayıcı cutover (§8) | Değişken, `X-Kando-Token` gibi geri-uyumluluk riski yüksek maddeler var | Core/Local/Sentinel'in `lumos-core`'a uygulanması |

**Bu rapor hiçbir kararı vermedi, hiçbir kod yazmadı.**
