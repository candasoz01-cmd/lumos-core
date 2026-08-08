# ADR-019 — Ürün yüzü ayrımı ve ModelRegistry sınırı

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-08)** — sınır ve adlandırma kararı kabul edildi |
| Uygulama durumu | **Uygulanmadı** — bu turda kod, provider entegrasyonu, router veya UI değişikliği yok |
| OD | OD-062 |
| Üst sınır | `docs/lumos-karar-sozlesmesi.md`, [`CONSTITUTION.md`](../CONSTITUTION.md), [`ROADMAP.md`](../ROADMAP.md) STOP LIST |
| İlgili | ADR-004 (Router), ADR-006 (Firewall), ADR-007 (Trust), ADR-008 (Agent Network / Board), ADR-018 (iç katman adları), [`product-rules.md`](../product-rules.md) PR-001/002/005/010/011 |

## Kapsam notu

Bu belge **yalnızca karar kaydıdır**. Bu turda kod, import, test, router davranışı, model çağrısı, provider entegrasyonu, panel veya operatör arayüzü **kapsam dışıdır**. ROADMAP STOP LIST'i delmez.

## Bağlam

İki ihtiyaç aynı anda büyüyor ve tek bir yüzeyde çakışıyordu:

- **Son kullanıcı**, "şunu yap" deyip sonucu almak istiyor. İç işleyiş onun ürünü değil.
- **Operatör (biz)**, hangi görevin hangi sağlayıcıya gittiğini, hangi oturumun çalıştığını, ne kadar sürdüğünü, hata alıp almadığını ve devir olup olmadığını görmek zorunda.

Bu iki ihtiyaç aynı panele konursa, kullanıcı ürünü bir "model seçme ekranına" dönüşür ve Lumos'un asıl değeri — doğru motora yönlendirip sonucu getirmesi — görünmez olur.

Repo tarafındaki bugünkü durum (2026-08-08, salt-okuma analizi):

| Alan | Durum | Kanıt |
|------|-------|-------|
| Model erişimi | Tek OpenAI yolu; model seçimi `OPENAI_MODEL` ortam değişkeni | `src/engine/model_client.py` |
| Model/provider soyutlaması | **Yok** | ADR-004 "Provider / model seçimi: tek provider + env model" |
| `IntegrationRegistry` | **Var** — ama bu bir *entegrasyon* kaydıdır (`(provider, action) → handler`; mail, takvim, medya, katalog vb.) | `src/integrations/registry.py` |
| Birleşik Router | **Yok** — ADR-004 taslak | ADR-004 |
| Operatör durum çekirdeği | **Kısmen var**, yalnız CLI | `src/lumos_board/` (`agent_status.py`, `task_claim.py`, `coordination_gateway.py`) |

## Karar

### 1. Dört katman, iki yüzey

Hedef mimari **kilitlenmiştir**:

```text
Son kullanıcı akışı
  Lumos User Surface  →  AI Runtime / Router  →  ModelRegistry  →  Providers

Operatör akışı
  Command Wall  →  AI Runtime / Router  +  Agent / Session / Task state
```

| Katman | Rol | Kime görünür |
|--------|-----|--------------|
| **Lumos User Surface** | Piyasaya çıkacak kullanıcı ürünü | Son kullanıcı |
| **Command Wall** | **İç operatör / yönetici yüzeyi** — ürün değil | Yalnız yetkili operatör |
| **AI Runtime / Router** | Ortak beyin; her iki yüzeyin de kullandığı tek yönlendirme katmanı | Doğrudan hiçbirine |
| **ModelRegistry** | Model/ajan sağlayıcılarının takıldığı kayıt katmanı | Doğrudan hiçbirine |

İki yüzey **aynı motoru** kullanır; ayrı motor, ayrı router veya ayrı model yolu **kurulmaz**.

### 2. Command Wall bir son kullanıcı ürünü değildir

Command Wall, bu ADR kapsamında **internal operator/admin surface** olarak tanımlanır. Ayrı bir ticari ürün, ayrı bir marka veya ayrı bir kullanıcı segmenti **değildir**. Bu tanım bilinçlidir: yeni bir son kullanıcı ürünü ilan etmek, ROADMAP STOP LIST'indeki "yeni agent / orchestration katmanı" yasağını delerdi.

Command Wall'un görme yetkisi (hedef kapsam, uygulanmadı): görev → sağlayıcı/model → instance/session → durum → süre → hata/fallback zinciri; branch/PR durumu; heartbeat; onay kapıları; ileride maliyet ve performans.

### 3. Kullanıcı yüzüne sızmayacaklar — normatif

Aşağıdakiler **son kullanıcı yüzeyinde hiçbir biçimde görünmez** (metin, etiket, hata mesajı, tooltip, URL, HTML yorumu, ağ yanıtı dahil):

- Sağlayıcı ve model adı (OpenAI, Claude, Gemini, DeepSeek, Kimi/Moonshot vb.)
- `session_id`, `instance_id`, çalışma dizini / worktree yolu
- Heartbeat, stale/lag sinyalleri
- PR / merge / deploy kapıları
- İç ajan koordinasyonu, devir (fallback) zinciri, claim durumu
- İç katman adları (ADR-018: Core / Local / Sentinel)

Kullanıcı **yalnız Lumos görür**. Bu, PR-001 / PR-002 / PR-010 / PR-011 kurallarının model katmanına genişletilmiş halidir ve [`product-rules.md`](../product-rules.md) PR-005 olarak kayda geçer.

**Model seçtirme geri çekildi.** Kullanıcıya "Auto / GPT / Claude / Kimi" gibi bir sağlayıcı seçimi sunulmaz. Teknik şeffaflık gerektiğinde (hukuki, sözleşmesel veya kullanıcının açık sorusu) doğru biçimde açıklanır; ürün kimliği olarak sunulmaz.

### 4. ModelRegistry ≠ IntegrationRegistry — normatif

Bu iki kayıt katmanı **ayrıdır ve birbirinin yerine kullanılamaz**:

| | `IntegrationRegistry` | `ModelRegistry` |
|---|---|---|
| Konum | `src/integrations/registry.py` (mevcut) | Henüz yok — hedef |
| Anahtar | `(provider, action)` | model/ajan yeteneği |
| İçerik | Dış servisler: mail, takvim, medya, katalog, cihaz | LLM / ajan sağlayıcıları |
| Soru | "Bu eylemi hangi servis yapar?" | "Bu görevi hangi motor düşünür?" |
| Çağıran | Görev yürütme | Router |

Normatif kurallar:

1. `ModelRegistry`, `IntegrationRegistry`'ye kayıt olarak **eklenmez**; ayrı bir katmandır.
2. `src/integrations/providers/openai_provider.py` bir **entegrasyon** sağlayıcısıdır; model sağlayıcı katmanı sayılmaz ve `ModelRegistry`'nin temeli olarak kullanılmaz.
3. Yeni belge, ADR veya kodda "provider registry" ifadesi **tek başına kullanılmaz**; hangisi kastediliyorsa tam adıyla yazılır.
4. `ModelRegistry` yalnız Router tarafından çağrılır; kullanıcı yüzeyi veya entegrasyon katmanı doğrudan çağırmaz.

### 5. Sıralama değişmez

ADR-008'deki öncelik sırası geçerlidir: **Firewall → Trust → Router → Memory → Agent Network**. `ModelRegistry`, Router'ın **altında** konumlanır; Router'ın önüne geçmez ve Firewall/Trust kararlarından **sonra** devreye girer. Bu ADR o sırayı değiştirmez, yalnız Router adımının içine eksik olan parçayı yazar.

### 6. Kimi/Moonshot bugün entegre edilmez

Kimi/Moonshot, **FAZ-1 sonrası provider evaluation backlog**'una eklenir. Mevcut sıra (OpenAI → Claude pilotu → DeepSeek) **bozulmaz**. O aşamada "Kimi ekle" denmez; adaylar ortak ölçütlerle değerlendirilip Router'a hangilerinin alınacağına karar verilir. Ölçütler: **kalite, maliyet, gecikme, tool-use, coding, context penceresi, güvenilirlik.** Ayrıntı: [`ROADMAP.md`](../ROADMAP.md) § FAZ-1 sonrası provider stratejisi.

## Sonuçlar

- Yeni bir model çıktığında kullanıcı arayüzü yeniden tasarlanmaz; `ModelRegistry`'ye sağlayıcı eklenir.
- Lumos mimari olarak tek modele bağımlı kalmaz.
- Command Wall ile piyasaya çıkacak Lumos birbirine karışmaz; motor ortak kalır.
- Router çalışmasına başlandığında tasarım kararı hazırdır; sıfırdan tartışma açılmaz.

## Bilinçli yapılmaz

- Provider entegrasyonu (Kimi/Moonshot dahil) — STOP LIST
- `ModelRegistry` kodu, Router birleştirme, `model_client.py` refaktörü
- Command Wall için yeni UI veya yeni orchestration kodu
- Mevcut `IntegrationRegistry` yeniden adlandırma veya taşıma
- FAZ-1 provider sırasının değiştirilmesi

## Bekleyen (ayrı karar / ayrı iş)

- `ModelRegistry` arayüz sözleşmesi ve yetenek modeli
- Router'ın model seçim sinyalleri (maliyet / gecikme / risk)
- Command Wall operatör yüzeyinin teknik paketi ve yetkilendirme sınırı
- **Kullanıcı yüzü sızıntısı guard testi** (ADR-018'in `tests/test_legacy_layer_names_retired.py` deseniyle benzer). Kapsam tanımı — 2026-08-08 kararı: yalnız model adı değil, tüm internal-only alanlar doğrulanır: `provider`, `agent_id`, `instance_id`, `session_id`, `workspace_path` / worktree, heartbeat, PR/merge gate, iç ajan koordinasyonu. Doğrulama yüzeyi yalnız UI metni değil, **public Lumos API yanıtları dahil** tüm kullanıcıya açık yüzeylerdir. Kod bu turda yazılmaz; bu madde testin kabul kriteridir.
- FAZ-1 sonrası provider evaluation paketi

## İlişkili

- [ADR-004](ADR-004-ai-router-routing-layer.md) § Router altında ModelRegistry sınırı
- [ADR-008](ADR-008-agent-network-boundary.md) — öncelik sırası ve Board sınırı
- [ADR-018](ADR-018-internal-layers-core-local-sentinel.md) — iç katman adları kullanıcıya gösterilmez
- [`product-rules.md`](../product-rules.md) PR-005
- [`ROADMAP.md`](../ROADMAP.md) STOP LIST + FAZ-1 sonrası provider stratejisi
