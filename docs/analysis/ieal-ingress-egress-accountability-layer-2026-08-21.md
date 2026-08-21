# Ingress/Egress Accountability Layer (IEAL) — tarihli çalışma notu

| Alan | Değer |
|------|-------|
| Durum | **FİKİR** / tarihli çalışma notu / **karar değil** |
| Tarih | 2026-08-21 |
| Kapsam muhasebesi | **FİKİR** — KARAR değil, KOD değil, CANLI değil |
| Faz | **FAZ-1 dışı.** FAZ-2 Altyapı fikir notu. STOP LIST ihlali yok; yeni ajan/orkestrasyon/ürün kodu yok |
| Ürün bağlamı | **Lumos Cyber** (planlı We Lock AI güvenlik-ops varyantı) — ayrı FAZ-1 ürünü değil |
| Aday ADR | **Aday** ADR-031+ (numara tahsis edilmedi; bu not ADR açmaz) |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md) §1 · §4 · §5 · §9 · §11; [`ROADMAP.md`](../ROADMAP.md) STOP LIST |
| Bu turda yapılmaz | Runtime katmanı, ROADMAP/MODULES yüzdesi, canonical çekirdek belge, detector imzası, merge önerisi |

Bu belge Constitution §1 gereği dört çekirdek belgeye **sığmayan** yeni bilgiyi tarihli çalışma notu olarak tutar. Dört belgeye referans verir; onların yerine geçmez.

**Çekirdek soru:** *Bu ajan ne getirdi, neye erişti, ne üretti ve neyi dışarı göndermeye çalıştı?*

Hacim farkı (`kaç MB girdi / kaç MB çıktı`) bu sorunun cevabı değildir. Anomali **sensörüdür**. Karar mekanizması değildir.

---

## 0. Bu notun katkısı (özet)

Kullanıcı modeli doğru ve yeterlidir: içerik DLP + hacim + fail-closed + ajanı güvenmeme. Bu not o modeli **yeniden anlatmaz**. Lumos'ta zaten duran katmanlara oturtur ve şu ekleri önerir:

1. **IEAL yeni ajan değildir.** Sentinel-komşu **enforcement plane**'dir; Lumos geçidinin (ADR-012 C1) üzerinde oturur. Sentinel gözler ve raporlar; IEAL **çıkışı keser**. Sentinel'i executor yapmak ADR-018 ve OD-006 ihlalidir.
2. **İki ayrı firewall vardır.** ADR-006 *eylem* sorar (*bu adım yürüsün mü?*). IEAL *veri-akış* sorar (*bu bayt bu hedefe gidebilir mi?*). İzinli yazı ≠ izinli çıkış.
3. **Taint biletleri içerik DLP'den serttir.** Ajan confidential dosya A'yı okuyunca **ajanın basamadığı** bir yetenek bileti alır. Şifreli/parçalı sızıntı içerik taramasını yener; bilet-hedef uyumsuzluğu yenemez.
4. **Çift defter:** ingress **makbuz** (receipt) + egress **izin** (permit). İkisi uzlaşmazsa fail-closed. Evidence journal fazlarına map edilir; yeni orkestrasyon katmanı açılmaz.
5. **HTTP tek kanal değildir.** Model sağlayıcı, MCP, git/PR, panel/köprü, clipboard, sandbox dışı yazım, robotik telemetri, bellek yazımı ve **denetim kanalının kendisi** (journal, Board, ekran görüntüsü) egress'tir.
6. **Hacim bütçeyi besler; bütçe kontrol eder.** `controlled_bridge` içindeki `MAX_READ_BYTES` / `MAX_WRITE_BYTES` proto-kota'dır; sınıf-bilinçli bütçeye büyütülür.
7. **Robotik RSL-02 şablondur, istisna değil.** İmzalı izin = veri sınıfı + amaç + hedef + süre + sahip onayı. IEAL bunu bütün ajan oturumlarına geneller.
8. **Lumos Cyber yüzeyi MB panosu değildir.** Oturum provenance grafı sorgulanır: kim okudu → hangi taint → hangi hedef denendi → hangi karar.

Kapsam: **FİKİR**. Uygulama FAZ-1 bitene kadar yok.

---

## 1. Yerleşim — Sentinel-komşu enforcement plane

```
Dış dünya / ajan / model / köprü
        │
        ▼
┌─────────────────────────────────────────┐
│  Lumos geçidi (ADR-012 C1 tek dış kapı) │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │ IEAL        │    │ Sentinel        │ │
│  │ enforce     │◄───│ observe/report  │ │
│  │ (kes /     │    │ (anomali,      │ │
│  │  karantina │    │  sinyal)       │ │
│  │  / onay)   │    │                │ │
│  └─────────────┘    └─────────────────┘ │
│         │                    │          │
│         ▼                    ▼          │
│  Core / Local / policy / evidence       │
└─────────────────────────────────────────┘
```

| Katman | Rol | Yapmaz |
|--------|-----|--------|
| **Lumos geçidi** | Tek dış yüzey; bütün etkili akış buradan | İç motorlara atlamalı komut iletmek |
| **IEAL** | Egress/ingress hesabı + fail-closed kesme | Ajan olmak, orkestre etmek, secret tutmak |
| **Sentinel** | Gözlem, anomali, Lumos'a rapor (ADR-018, OD-006) | Yürütmek, dış komut almak, secret tutmak, IEAL kararını tek başına vermek |
| **Üreten ajan** | İş üretir | Kendi çıkışına karar vermek, bilet basmak, IEAL'i kapatmak |

**§11 izomorfizmi.** Constitution §11: Lumos kendi güvenlik politikasını gevşetemez. RSL-04: Lumos fiziksel güvenlik denetleyicisini devre dışı bırakamaz. IEAL aynı kuralın veri düzlemidir: üreten ajan (ve Lumos'un kendisi) bilet basamaz, sınıf düşüremez, IEAL'i kapatamaz. Bunlar yalnız insan kararıyladır.

Sentinel ile IEAL **birleştirilmez**. Sentinel executor yapılırsa OD-006 / ADR-018 bozulur. IEAL yeni orkestrasyon ajanı yapılırsa STOP LIST + ADR-008 bozulur. Gözlem ve kesme ayrı kalır; kesme kararı üreten ajana görünmeden kilitlenir (kör inceleme, §8).

---

## 2. Mevcut ADR / kural haritası

| Kaynak | Bugün ne diyor | IEAL'e katkısı |
|--------|----------------|----------------|
| **CONSTITUTION §11** | Dış ajan çekirdeği sahiplenmez; politika gevşetilemez | IEAL ajan-dışı kapı; self-disable yasak |
| **ADR-006** | Parçalı AI Firewall; 11 risk (PII tespiti **yok**); 7 karar tipi | IEAL, PII/sır kategorisinin **veri düzlemi**; `deny` / `ask_confirmation` / `defer_to_private_layer` egress'e taşınır |
| **ADR-008** | Yatay AI→AI komut yok; dağıtık doğrulama; risk #5 private veri sızıntısı | Kör ikinci sınıflandırıcı; bellek üzerinden gecikmeli sızıntı |
| **ADR-010** | guard ≠ trust; consent ≠ confirmation | IEAL = **guard + policy + evidence**. Trust = kim/kilit/rıza. Confirmation = şüpheli çıkışta insan |
| **ADR-012 C1–C3, C6** | Tek dış kapı; kanıt; stop-on-risk | IEAL C1 üzerinde choke-point; her kesme journal'a düşer |
| **ADR-018 / OD-006** | Sentinel = güvenlik/gözlem/anomali; executor değil | IEAL Sentinel'in yanındaki kesme düzlemi; Sentinel kalır |
| **ADR-021 RSL-02 / RSL-04** | İmzalı egress izni; fail-closed; Lumos fiziksel denetleyiciyi kapatamaz | Genel ajan oturumu için şablon |
| **ADR-025 / SEC-033–037** | Amaç-kapsamlı model; yerleşim; ham ses kalıcı değil | Model sağlayıcı **hedef**tir, "sadece API" değil |
| **SEC-003, 010–013, 021–022, 040–041** | Geçit; secret taşıma yasağı; bridge kontrollü; demo-safe public | IEAL public notta imza/cookbook yazmaz |
| **KA-010** | Bağımsız AI değerlendirme (KARAR; otomatik kapı yok) | Kör dual-classifier'ın kapsam kaydı |

**Terminoloji (ADR-010, zorunlu):**

| Terim | IEAL'de anlam |
|-------|----------------|
| **guard** | Bu egress olsun mu? |
| **policy** | Sınıf × hedef × amaç matrisi |
| **permission** | Oturumun elindeki taint bileti |
| **trust** | Kim, kilit, rıza — IEAL bunları tüketir, yerine geçmez |
| **confirmation** | Yüksek sınıf / şüpheli çıkışta insan onayı |
| **consent** | Identity/keystore rızası — tek adım çıkış onayı değildir |

---

## 3. Kanal sayımı — HTTP yetmez

Bugünkü repo **parçalı** choke-point'ler taşır. IEAL bunları birleştirmez (birleşik motor ADR-006'da da yok); her kanalı **aynı hesap sözleşmesine** bağlar.

| Kanal | Bugünkü parça (kanıt) | IEAL boşluğu |
|-------|----------------------|--------------|
| Dosya yazımı | `write_interceptor`, `workspace_contract`, `change_sensitivity` (path sınıfı: CRITICAL/HIGH/NORMAL) | Yazım = potansiyel *local egress*; içerik sınıfı yok; unsandboxed path |
| Köprü HTTP | `controlled_bridge` (`MAX_READ_BYTES=120_000`, `MAX_WRITE_BYTES=64_000`, yüzey regex bloğu); `kando_bridge` POST `/task` | Byte tavanı proto-kota; hedef allowlist ve taint yok |
| LLM / plan | `lumos_gate` — `ingress_payload` bugün `{mode, payload_len}` / `{is_substep, step_type}` | İsim tuzak: hacim kırıntısı, makbuz değil |
| Görev / profil | `profiles.py` `SECURITY_NEVER_AUTO`; `action_policy`; `confirmation_policy` | Eylem yasağı var; veri çıkış yasağı yok |
| Onay grant | `ConfirmationGrant` — TTL, `scope_hash`, tek kullanımlık, ajan bağlamı dışında `.lumos/pending_confirmations/` | Taint bileti için **kalıp**; veri sınıfı alanı yok |
| Permission lease | `security/permissions.py` `PermissionManager.acquire` — **no-op stub** | İsim var, yetenek yok |
| Kanıt | `evidence_continuity` JSONL; `guard_audit`; phase `before/after/result` | Makbuz/izin defteri yok; journal'ın kendisi sızıntı kanalı olabilir |
| Model sağlayıcı | `OPENAI_MODEL_CHAT` / `CYBER` / `STT` (ADR-025 amaç ayrımı) | Prompt/completion = egress; retention ayrı hedef politikası |
| Robotik | `SovereigntySimulator.export_sensor_data` — imza + sahip onayı + allowlist hedef; aksi `destination_not_allowlisted` | Genel ajan oturumuna henüz genellenmedi |
| Kuantum katalog | `egress_risk` alanı (katalog etiketi) | Sensör/etiket; kontrol değil |
| Git / PR / commit | Ajan `commit`/`push` (STOP LIST dışı bu notta) | PR gövdesi, commit mesajı, diff = egress |
| Panel / upload | `panel_tasks_server` | Dışarı giden gövde sınıflandırılmıyor |
| Bellek | ADR-005 graph yok; ADR-008 risk #5 | Yazılan bellek başka ajanın ingress'i olur (**gecikmeli egress**) |
| MCP / araç | Köprü executor'lar, cursor bridge | Araç argümanı = egress |
| Yan kanal | Board kaydı, journal, log, ekran görüntüsü, clipboard | Denetim kanalı kırmızı çizgi sınıfı taşırsa sızdırır |

**Yan kanal uyarısı.** Ajan "HTTP yok" diye temiz sayılmaz. Board claim, evidence journal, PR açıklaması ve ekran görüntüsü, DLP'siz ikinci bir çıkış kapısıdır. IEAL denetim yazımını da sınıfa bağlar: secret parmak izi journal'a **açık** düşmez (SEC-040, SEC-041).

---

## 4. İki firewall: eylem ≠ veri akışı

ADR-006 bugün şunu sorar: *bu niyet / adım / araç çağrısı yürüsün mü?*

IEAL şunu sorar: *bu oturumun elindeki veri, bu hedefe, bu amaçla, bu hacimde çıksın mı?*

| Senaryo | Eylem firewall (ADR-006) | Veri-akış firewall (IEAL) |
|---------|--------------------------|---------------------------|
| Sandbox içi dosya yaz | `sandbox_only` / allow | Local scratch; taint kalır; oturum sonu residue taraması |
| Köprü `write` allowlist path | Yüzey izinli, byte tavanı var | Hedef hâlâ workspace; dış API değil — yine makbuz |
| `profiles` `write_local` + genel onay | Adım yürür | Yazılan içerik confidential ise dış API'ye **ayrı** permit gerekir |
| Robot `export_sensor_data` | Yetenek grant + imza | RSL-02 zaten IEAL-biçimli |
| Chat modeli prompt | Gate `allow` sohbet | Prompt'taki taint + sağlayıcı retention = egress kararı |
| `SECURITY_NEVER_AUTO` | Eylem asla otomatik değil | Secret-sınıf egress için **aynı sertlik**: asla otomatik gönderme |

Sonuç: bugünkü parçalı guard **niyeti** keser, **veriyi izlemez**. IEAL o boşluğu doldurur; ADR-006'nın yerine geçmez.

---

## 5. Taint bileti — içerik DLP'nin üstüne yetenek

### 5.1 Neden içerik taraması yetmez

Kullanıcının modeli doğru: şifreleme, parçalama, steganografi, "normal trafik"e gizleme %100 blok'u imkânsız kılar. İçerik DLP **kalır** (bilinen sır, token, PII, kaynak kod parmak izi) ama **tek kapı olmaz**.

Daha sert kapı: ajanın **hiç sahip olmadığı** bir hedefe göndermesi, içerik ne olursa olsun reddedilir.

### 5.2 Bilet yaşam döngüsü (kalıp; şema kararı değil)

Ingress (okuma, vault_ref çözümü, API yanıtı, MCP sonucu) yakalanınca geçit **ajan bağlamının dışında** bir bilet basar. Kalıp mevcut `ConfirmationGrant` ile aynı aileden olsun diye önerilir — yeni orkestrasyon nesnesi değil, aynı "ajan basamaz, TTL'li, scope'lu, tek kullanımlık tüketim" fikri:

| Alan (fikir) | Analog |
|--------------|--------|
| `taint_id` | `confirmation_id` |
| `data_class` | public / internal / confidential / secret |
| `purpose` | ADR-012 amaç sınırı; ADR-025 amaç-kapsamlı model |
| `source_receipt` | path / vault_ref / API scope — ham içerik değil |
| `dest_allowlist` | RSL-02 `owner_allowlisted_destinations` |
| `budget_bytes` | proto: `MAX_WRITE_BYTES` |
| `ttl` | confirmation TTL; **aşağıdaki sticky kurala tabi** |
| `issued_by` | Lumos geçidi — ajan değil |
| `scope_hash` | grant'teki `scope_hash` |

`PermissionManager.acquire(name, purpose, ttl)` bugün no-op. İsim olarak taint biletinin boş iskeletidir; FAZ-1'de doldurulmaz.

### 5.3 Sticky taint (bu notun ek kuralı)

TTL ile "bekle-sızdır" oyunu kapatılır:

| Sınıf | Taint davranışı |
|-------|-----------------|
| **secret** | Sticky. TTL dolmaz; insan **açık deklasifikasyonu** olmadan düşmez. `SECURITY_NEVER_AUTO` ile aynı sertlik. |
| **confidential** | Sticky veya çok uzun TTL; destinasyon allowlist dar; fail-closed |
| **internal** | TTL ile zayıflayabilir; allowlist + kota |
| **public** | Taint tutulmayabilir; yine de hacim bütçesi ve audit |

Bilet **ajan prompt'una yazılmaz** (ajan taklit eder). `.lumos/` altında grant gibi durur. Ajan "benim confidential taint'im yok" diyemez; geçit deftere bakar.

### 5.4 Bellek = gecikmeli egress (ADR-008 risk #5)

Taint **oturumu değil veriyi** izler. Ajan A confidential A dosyasını okur, özeti belleğe yazar, ajan B (veya sonraki tur) o özeti API C'ye gönderir. Bilet A'nın oturumu bitince ölmemelidir; bellek kaydı taint taşır. Aksi halde IEAL HTTP'yi keser, Board/bellek yan kanalı açık kalır.

Bu, Memory Graph (ADR-005, henüz yok) oturmadan bile **kayıt düzeyinde** tutulabilir: "bu memory node confidential taint taşır". Graph ürünü beklemez; FİKİR olarak işaretlenir.

---

## 6. Çift defter: makbuz ve izin

Kullanıcı "ne girdi / ne çıktı" diyor. Bu not onu iki **uzlaşması zorunlu** kayda ayırır.

```
ingress receipt  ──►  taint ticket  ──►  egress permit request
     (ne girdi)         (ne taşıyor)         (ne gitmek istiyor)
            \                               /
             \____ reconcile / diff _______/
                        │
                        ▼
              allow | deny | confirm | quarantine
                        │
                        ▼
              evidence journal (before / after / result)
```

**Makbuz (ingress):** path veya vault_ref, sınıf heuristiği, byte, API scope, amaç, zaman, ajan kimliği. Ham secret journal'a yazılmaz — parmak izi / sınıf / ref.

**İzin (egress):** hedef, kanal, byte, içerik sınıfı tahmini, bilet kümesi, bütçe bakiyesi, karar.

**Uzlaşma kuralları (fikir):**

1. Hedef, hiçbir biletin allowlist'inde değilse → fail-closed (RSL-02 `destination_not_allowlisted`).
2. Amaç eşleşmiyorsa → fail-closed (ADR-012 amaç sınırı; ADR-025 model düşmeme).
3. Sınıf, hedefin tavanının üstündeyse → fail-closed.
4. Bütçe aşımı → fail-closed (hacim burada **kontrol** olur).
5. Çıktıda ingress'te olmayan yeni secret parmak izi → şüpheli (halüsinasyon veya gizli ikinci kaynak). Kes + insan.
6. Ingress'te okunmuş secret'ın çıktıda birebir parmak izi → DLP hit; bilet yoksa kes.
7. Hacim şişmesi tek başına hırsızlık değildir (sıkıştırma, log, model çıktısı). Bütçe + taint + hedef ile birlikte okunur.

Evidence journal'daki `PHASE_BEFORE` / `PHASE_AFTER` / `PHASE_RESULT` bu defterin mevcut evine oturur. Yeni "IEAL motoru" FAZ-1'de açılmaz; post-FAZ-1 diliminde mevcut mirror fonksiyonlarına (`mirror_guard_event_to_evidence_journal`, köprü outbox mirror) **receipt/permit alanı** eklenmesi yeterlidir — o da şimdi değil.

---

## 7. Negatif alan: "hiç okumadı" ve "geride bıraktı"

Kullanıcı "ingress'te olmayan yeni hassas veri" sinyalini verdi. İki ek negatif:

### 7.1 Sahip olmadığı şeyi göndermek

- Çıktıdaki token/parmak izi, oturumun çözdüğü `vault_ref` kümesiyle **eşleşmiyorsa**: ya halüsinasyon, ya ikinci kanal, ya önceki oturum artığı. Üçü de otomatik "gönder" değildir.
- Vault içeriğinin kendisi ajan bağlamına konmaz (SEC-010–013). Karşılaştırma **parmak izi / ref** düzeyindedir; public notta algoritma yok.

### 7.2 Residue (geride kalan kopya)

Oturum sonu (ve fail-closed kesme sonrası) sorulacak soru: *göndermedi ama kopya duruyor mu?*

| Yer | Risk |
|-----|------|
| Local scratch / temp / unsandboxed yazım | Sonraki ajanın ingress'i |
| Model sağlayıcı retention | ADR-025'in konusu; amaç-dışı model = ayrı hedef |
| Ekran görüntüsü, log, journal | Yan kanal |
| Clipboard | OS düzlemi; IEAL göremezse en azından **bilinçli kör nokta** yazılır |
| Trash | SEC-002; trash kaynak değildir ama kopyadır |

"Göndermedik" ≠ "çalınmadı". Cyber sorusu her iki tarafı da kapsar.

---

## 8. Kör inceleme (ADR-008 dağıtık doğrulama)

IEAL kararını **üreten ajan vermez**. İsteğe bağlı ikinci bağımsız sınıflandırıcı (Cyber yüzeyi vs Sentinel gözlemi) birbirinin verdiktini kilit anına kadar görmez. Çelişki → fail-closed + insan (Constitution §2 ruhu: çelişkide dur).

Bu KA-010'un veri-düzlemi okumasıdır: bağımsız değerlendirme otomatik kurul değildir; yüksek sınıfta **insan kapı 3**'tür (CU4 confirmation / elevated confirmation).

| Sınıf | Kim karar verir |
|-------|-----------------|
| public, düşük hacim, allowlist hedef | IEAL otomatik allow + audit |
| internal | IEAL; anomali varsa Sentinel raporu + confirm |
| confidential / secret | IEAL fail-closed; insan confirmation; kör ikinci oy isteğe bağlı |
| sınıflandırıcı unknown | confidential muamelesi (fail-closed) |

---

## 9. Fail-closed / fail-open matrisi

Robotik simülatör bilinmeyen eylemi `unknown_action_fail_closed` ile keser. IEAL aynı varsayılanı veri sınıfına bağlar.

| Veri sınıfı | Hedef | Sınıflandırıcı | Hacim / profil | Kapı |
|-------------|-------|----------------|----------------|------|
| secret | herhangi | herhangi | herhangi | **fail-closed** + insan; asla auto |
| confidential | allowlist dışı veya unknown | — | — | **fail-closed** + karantina + audit |
| confidential | allowlist + amaç uyumlu | known | bütçe içinde | allow + audit; anomali → confirm |
| internal | allowlist | known | bütçe içinde | allow + audit |
| public | allowlist | known | düşük | fail-open + audit (sensör çalışır) |
| herhangi | unknown dest | — | — | **fail-closed** (RSL-02) |
| herhangi | — | **unknown** | — | confidential say → **fail-closed** |
| herhangi | — | — | bütçe aşımı | **fail-closed** |

Fail-open yalnız "düşük sınıf + tanıdık hedef + bütçe içinde" içindir. Unknown'u public saymak, ajanın sınıflandırıcıyı körlemesine eşdeğerdir — yasak.

Karantina: gönderilmez, payload workspace dışında tutulmaz, journal'a **sınıf + hash + neden** düşer, insan onayı olmadan silinmez (SEC-002 ruhu).

---

## 10. Oturum bütçesi yetenektir, metrik değil

Hacim örneği davranış sensörü olarak kalır. Kontrol şu üçlü kotadır:

- ajan / oturum
- hedef
- veri sınıfı

Aşım → fail-closed. Sensör bütçeyi besler.

Repo'da proto:

- `controlled_bridge.MAX_READ_BYTES` / `MAX_WRITE_BYTES` — hedef-kör, sınıf-kör tavan
- `lumos_gate.ingress_payload["payload_len"]` — kırıntı
- kuantum `egress_risk` — katalog etiketi

Post-FAZ-1 ilk dilim bu tavanları **sınıf × hedef** ile çarpar; birleşik anomali motoru yazmaz.

---

## 11. Tehdit modeli (dürüst sınır)

IEAL **%100 blok vaat etmez.** Aşağıdakiler bilinçli olarak yenilmez veya kısmen yenilir:

| Tehdit | DLP | Taint bilet | Kota / allowlist | Not |
|--------|-----|-------------|------------------|-----|
| Düz metin sır / token | Kısmen (private detector) | Güçlü | Güçlü | Public repo'ya imza yazılmaz |
| PII | ADR-006: tespit **yok** | Path/sınıf heuristiği | Orta | Private katman |
| Şifreli blob | Zayıf | **Güçlü** (hedef bilette yoksa kes) | Güçlü | Asıl gerekçe: taint |
| Parçalama / chunking | Zayıf | Orta (aynı hedefe kota) | Güçlü | |
| Steganografi / normal trafiğe gizleme | Zayıf | Orta | Orta | %100 imkânsız |
| Model provider retention | — | Sağlayıcı = hedef | ADR-025 | Amaç-dışı modele düşme yasak |
| Bellek → başka ajan | DLP kaçırır | Taint takip ederse güçlü | — | Risk #5 |
| Journal / PR / screenshot | Kaçırır | Denetim kanalı sınıfa bağlıysa kısmen | — | Yan kanal |
| Clipboard / OS | Kör nokta | Kör nokta | Kör nokta | Bilinçli sınır olarak yazılır |
| Ajanın kendi DLP'yi kapatması | — | Bilet ajan dışında | §11 | Self-disable yasak |

**En güçlü pratik model (vaat değil, hedef bileşim):** allowlist + least privilege (bilet) + provenance (çift defter) + DLP (private) + egress kota + anomali (Sentinel). Hacim tek başına karar vermez.

---

## 12. Lumos Cyber ürün okuması

Naming registry: Lumos Cyber, We Lock AI altında güvenlik operasyonları / risk görünürlüğü / politika katmanıdır; cyberpunk UI değildir.

IEAL o varyantın **sorgu yüzeyini** tarif eder, FAZ-1 ekranı değil:

- Oturum grafı: ajan → okunan ref'ler → taint kümesi → denenen hedefler → kararlar
- "Ne çalındı?" sorusu: permit reddi + DLP hit + residue listesi — MB delta değil
- Operatör MB grafiğini **sensör** olarak görür; karar kuyruğu fail-closed + confirmation'dır

Public landing (`/cyber`) bu nottaki detector veya bilet şemasını anlatmaz.

---

## 13. Yapılmayacaklar

| Yasak | Neden |
|-------|--------|
| DLP'yi LLM prompt'una koymak ("sızdırma") | Ajan güvenilmez; §11 |
| IEAL'i yeni orkestrasyon / Cyber ajanı yapmak | STOP LIST; ADR-008 yatay komut |
| Sentinel'i executor / kesici yapmak | ADR-018, OD-006 |
| %100 önleme iddiası | Tehdit modeli |
| FAZ-1 runtime kodu, ROADMAP'e faz özelliği, MODULES yüzdesi | Constitution §5, §8 |
| Bu notu KARAR / ADR saymak | Kullanıcı katkı istedi, karar istemedi |
| Public repo'ya üretim detector imzası, regex cookbook, gerçek secret örneği | ADR-006 public/private; SEC-040/041 |
| Ajanın bilet basması veya sınıf düşürmesi | §11 izomorfizmi |
| Unknown sınıfı public saymak | Fail-closed varsayılan |
| Hacim delta'sını otomatik hırsızlık saymak | Sıkıştırma / log / model çıktısı |
| TECHNICAL_DEBT'e borç satırı | Bu gelecek fikir, borç değil |
| Dört çekirdek belgeyi bu fikirle güncellemek | Constitution §1 |

---

## 14. Post-FAZ-1 ilk dilim (şimdi değil)

Ad: **IEAL-S0 — receipt + bridge intercept** (FAZ-1 sonrası, ayrı karar + ADR adayı).

Kapsam (dar):

1. `write_interceptor` / okuma yollarına **ingress makbuzu**: path, `change_sensitivity` heuristiği, byte. Ham içerik yok.
2. `controlled_bridge` + köprü HTTP üzerinde **egress intercept**: unknown hedef fail-closed; mevcut byte tavanı bütçe gibi işlesin.
3. `evidence_continuity` kaydına `ingress_receipt_id` / `egress_decision` alanı (şema genişlemesi ayrı sözleşme).
4. Unknown dest → gönderilmez, audit, insan yoksa drop.

**S0 dışı:** provenance grafı, taint bileti runtime, PII detector, kör dual-classifier, robotics dışı imzalı permit, Memory Graph, UI, Lumos Cyber ürün kodu.

S0, mevcut guard parçalarına **alan ekler**; yeni ajan ve yeni "IEAL servisi" açmaz.

---

## 15. Aday ADR (tahsis yok)

İleride (FAZ-1 bitince, insan kararıyla) açılabilecek kayıt:

- **Aday ad:** ADR-031+ Ingress/Egress Accountability Layer
- **Numara tahsis edilmedi.** Bu dosya ADR değildir.
- **Karar öncesi zorunlu:** FAZ-1 kapanışı, public/private detector sınırı, S0'ın hangi choke-point ile başlayacağı, Sentinel ile çakışmama cümlesi.

---

## 16. Açık sorular (insan hakemi)

1. Secret taint sticky kuralı anayasa-sertliğinde mi, yoksa TTL'li mi?
2. Denetim kanalı (journal/PR) kırmızı sınıf taşıyınca red mi, kırmızı aksan mı?
3. Kör ikinci sınıflandırıcı Cyber mi, Sentinel mi, yoksa ikisi de değil (yalnız insan)?
4. Clipboard / OS kör noktası ürün vaadine yazılacak mı, yoksa bilinçli "görmüyoruz" mu?

Bu sorular `DECISION_CONFLICT` üretmez; henüz çelişen kabul edilmiş karar yok. Yalnız FİKİR çatallanmasıdır.

---

## 17. Kapsam muhasebesi kapanışı

| Basamak | Bu belge |
|---------|----------|
| **FİKİR** | Evet — 2026-08-21 tarihli çalışma notu |
| KARAR | Hayır — ADR yok |
| KOD | Hayır — runtime yok |
| CANLI | Hayır |
| DOĞRULANDI | Hayır |

Merge önerisi yok. Üçlü kapı (CI + güvenlik incelemesi + insan) bu FİKİR notuna uygulanmaz; FAZ-1 işi değildir.

---

*Bu not ürün taahhüdü değildir. Lumos Cyber varyantının güvenlik-ops diline, mevcut geçit/guard/robotik izin kalıplarına oturan bir fikir kaydıdır.*
