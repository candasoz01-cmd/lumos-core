# Lumos X-Ray — Ingress/Egress Guard

| Alan | Değer |
|------|-------|
| Durum | **FİKİR** — tarihli çalışma notu; karar değil; kod yok |
| Tarih | 2026-08-21 |
| Faz | FAZ-1 dışı. FAZ-2+ / Lumos Cyber adayı. STOP LIST ihlali yok |
| Merdiven | FİKİR (KARAR / KOD / CANLI değil) |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md) §11, [`ROADMAP.md`](../ROADMAP.md) STOP LIST, ADR-006/008/010/012/018/021/025 |
| İsim kaydı | **Kilitli aday (2026-08-21):** ürün yüzü Lumos X-Ray; teknik katman Ingress/Egress Guard. Registry [`lumos-approved-naming-registry.md`](lumos-approved-naming-registry.md) §A'ya **bu turda yazılmaz** — §A, ürün metninde ekstra onaysız kullanılan adlar içindir; §A kaydı ayrı, FAZ-1 sonrası / vitrin kararı |

Bu not, 2026-08-21 sohbetindeki **giriş/çıkış hesap verebilirliği** modelini mevcut Lumos katmanlarına oturtur. Yeni ajan, yeni orkestrasyon katmanı veya FAZ-1 özelliği **değildir**. Runtime kod **yok**; merdiven **FİKİR**'de kalır.

Aynı gün erken paralel taslak (IEAL adı): [`ieal-ingress-egress-accountability-layer-2026-08-21.md`](ieal-ingress-egress-accountability-layer-2026-08-21.md) (`cursor/ieal-working-note-359d`). IEAL açık sorular 1–3 **bu dosyada kilitlendi**; IEAL dalı bu turda güncellenmedi (paylaşılan worktree'yi ezmemek için). Adlandırma veya kilit çelişirse **bu dosya** esas alınır (Constitution §2).

---

## Kilitli yön (2026-08-21)

Kullanıcı bu oturumda üç tasarımı **kilitledi** (Anayasa §2: en yeni açık kullanıcı kararı otoritedir). Aşağıdakiler fikir notunun çerçevesidir; ADR numarası **atanmaz**, FAZ-1 kodu **açılmaz**.

- **Ürün adı Lumos X-Ray** / teknik katman **Ingress/Egress Guard**. Kullanıcı/ürün yüzü = X-Ray; mimari bileşen = Guard. Bu ayrım temiz tutulur.
- **Provenance Ledger**, `evidence_continuity` **kardeşidir** (kısaca: evidence_continuity kardeşi). Ayrı, ilgisiz bir journal değildir; görev-mutasyon evidence journal'ına gömülmez. Aynı aile (append-only, ham payload yok) ama semantik farklıdır: malzeme soyağacı ≠ görev mutasyonu.
- **Karantina private katmandadır** (kısaca: **private karantina**). Public OSS: yalnız sözleşme/stub (arayüz, olay şeması, test fikstürü, sahte karar motoru). Gerçek karantina hassas içeriği görür, secret/PII politikasına bağlanır, operasyonel yürütme yapar — private kalır.
- **Beş fiil sırası kilitli** (opsiyonel değil): **girdi → erişti → bıraktı/kopyaladı → üretti → çıkarmaya çalıştı**
- **Dört kova:** `accounted_from_ingress`, `generated`, `wrapping_overhead`, `unaccounted`
- **`unaccounted != otomatik saldırı`.** Karar veri sınıfı ile birlikte verilir: `unaccounted` + confidential/secret + yetkisiz hedef = deny/quarantine
- **Katman haritası:**
  - Lumos X-Ray = ürün yüzü
  - Ingress/Egress Guard = enforcement
  - Provenance Ledger = hesap/kanıt
  - Sentinel = gözlem/yorum, yürütme yok
- Bu üç katmanı (X-Ray / Guard / Ledger) hiçbir ajan kapatamaz veya atlayamaz — Anayasa §11 devamı.
- Merdiven hâlâ **FİKİR**; kod yok.
- FAZ-1 sonrası ilk deney hâlâ dar dilim: **ingress receipt + bilinmeyen hedefte fail-closed egress**. Şimdi değil.

---

## 1. Kayıt edilen kullanıcı modeli

Temel soru (beş fiil, kilitli sıra):

> Bu ajan sisteme ne getirdi, neye erişti, ne bıraktı/kopyaladı, ne üretti ve dışarı ne çıkarmaya çalıştı?

Üç parça:

| Parça | Soru | Tek başına yeter mi? |
|-------|------|----------------------|
| **Ingress X-Ray** (ürün yüzü) | Girerken ne taşıyor? | Hayır — yalnız envanter |
| **Egress X-Ray** (ürün yüzü) | Çıkarken ne götürüyor? | Hayır — bağlam yoksa DLP kördür |
| **Provenance Ledger** (`evidence_continuity` kardeşi) | O fark nereden geldi? | Karar omurgası |

Hacim (ör. 100 MB girdi / 140 MB çıktı) **davranış sensörüdür**, hırsızlık hükmü değildir. Asıl değer: **o 40 MB farkın hesabı**.

Kontrol, üreten ajana emanet edilmez. Ajan «ben kötü bir şey göndermiyorum» diyemez; X-Ray / Guard / Ledger'ı kapatamaz. Bu, Anayasa §11 ile aynı çizgidir: Lumos kendi güvenlik politikasını gevşetemez.

---

## 2. Ad ayrımı (kilitli — 2026-08-21)

Kullanıcı ürün adını kilitledi. İki ad **aynı şeyi adlandırmaz**; karıştırılırsa Sentinel, guard ve ürün yüzü yine birbirine yapışır (ADR-010 drift'inin tekrarı).

| Ad | Katman | Kullanım |
|----|--------|----------|
| **Lumos X-Ray** | Ürün yüzü / metafor | Kullanıcıya «ajanın içinden geçen malzeme taranır» anlatımı. Yeni ajan adı **değil**. |
| **Ingress/Egress Guard (IEG)** | ADR-010 **enforcement / guard** | «Bu çıkış şimdi yapılsın mı?» — allow / deny / ask_confirmation / quarantine |
| **Provenance Ledger** | ADR-012 **hesap/kanıt** | «girdi → erişti → bıraktı/kopyaladı → üretti → çıkarmaya çalıştı» — append-only; `evidence_continuity` kardeşi |
| **Sentinel** | Gözlem / yorum | Yürütmez, secret tutmaz, kapıyı açmaz |

Cyber vitrininde **Lumos X-Ray**; teknik sözleşmede **Ingress/Egress Guard + Provenance Ledger**. Registry §A kaydı bu turda **yok** — kilitli aday; vitrin metnine düşmesi ayrı karar.

X-Ray **makinedir**, Sentinel **radyologdur**, IEG **kapı koludur**. Üçünü tek ajan yapmak STOP LIST + ADR-008 + ADR-018 ihlalidir.

```
Dış dünya
    │
    ▼
Lumos geçidi (ADR-012 C1 — tek dış kapı)
    │
    ├─ Lumos X-Ray (ürün yüzü)  →  malzeme tarama + taint bileti
    ├─ Provenance Ledger        →  hesap/kanıt (evidence_continuity kardeşi)
    ├─ Core / Local (yürütme)   →  X-Ray / Guard / Ledger'ı atlayamaz
    ├─ Ingress/Egress Guard     →  allow | deny | confirm | quarantine
           │
           ▼
      Sentinel  →  gözlem / anomali raporu (yürütmez, secret tutmaz)
```

---

## 3. Bu notun katkısı — kullanıcı modelinin üzerine

Aşağıdakiler sohbetteki tarifi **tekrar etmez**; boşlukları kapatır.

### 3.0 İki firewall — eylem ≠ veri akışı

ADR-006 *eylem* sorar: bu adım yürüsün mü? X-Ray / IEG *veri akışı* sorar: bu bayt bu hedefe gidebilir mi? Köprüde `write` izinli olsa bile confidential içerik dış API'ye **ayrı permit** olmadan çıkamaz. `SECURITY_NEVER_AUTO` eylem için neyse, secret-sınıf egress için aynı sertlik önerilir: asla otomatik gönderme.

### 3.1 Farkın kaynağı (40 MB sorusu)

Hacim farkı dört kovaya ayrılmadan «şüpheli» denmez:

| Kova | Anlam | Örnek |
|------|--------|--------|
| `accounted_from_ingress` | Çıkış, giriş makbuzundaki özetlere bağlanır | Dosya A'nın parçaları API C'ye |
| `generated` | Oturumun ürettiği yeni malzeme | Model çıktısı, log sarmalayıcı, sıkıştırma şişmesi |
| `wrapping_overhead` | Protokol/JSON/mime kabuğu | multipart, base64, tool-call zarfı |
| `unaccounted` | Hiçbir giriş makbuzu veya üretim kaydı karşılamıyor | Sinyal — tek başına hüküm değil |

**Hüküm kuralı (kilitli):** `unaccounted != otomatik saldırı`. Karar veri sınıfı ile birlikte verilir:

`unaccounted` + confidential/secret + yetkisiz hedef = **deny / quarantine**

`generated` tek başına hırsızlık değildir; sınıf yükseltmesi (aşağı) varsa DLP + confirmation.

Bu, 100/140 karşılaştırmasını **davranış sensöründen karar mekanizmasına** çevirmeden, «40 MB nereden?» sorusunu ledger'a bağlar.

### 3.2 Taint / yetki bileti (içerik DLP'sinden sert)

Şifreleme, parçalama ve steganografi içerik taramasını deler. Buna karşı X-Ray yalnız payload'a bakmaz; **oturumun taşıdığı yetkiyi** taşır.

- Ajan dosya A'yı (confidential) okuyunca `taint_ticket` alır: sınıf, amaç, TTL, izinli hedefler.
- Egress, biletsiz hedefe **içerik temiz görünse bile** gitmez.
- Vault yalnız `vault_ref` verir; ham secret ajan yüzeyine düşmez (SEC-010…013). Çıkışta vault parmak izi varsa ve bilette `vault_ref` yoksa → `unaccounted` secret; yetkisiz hedefte deny/quarantine.

İçerik DLP tamamlayıcıdır; **asıl kapı yetki biletidir**. Robotics RSL-02'deki imzalı çıkış izninin ajan oturumuna indirgenmiş hâlidir. Kalıp mevcut `ConfirmationGrant` ailesindendir (TTL, `scope_hash`, ajan bağlamı dışında `.lumos/`); yeni orkestrasyon nesnesi değildir. `PermissionManager.acquire` bugün no-op — isim var, yetenek yok.

**Sticky taint (hâlâ açık — §8 soru 4):** secret sınıfı TTL ile düşmez önerisi duruyor; kullanıcı bu turda kilitlemedi. Bilet ajan prompt'una yazılmaz (taklit edilir); geçit deftere bakar. Taint **oturumu değil veriyi** izler: belleğe yazılan özet gecikmeli egress'tir (ADR-008 risk #5).

Çift defter: ingress **makbuz** + egress **izin**. Uzlaşmazsa kesilir. Ev, yeni motor değil; `evidence_continuity` **kardeşi** (görev-mutasyon journal'ına gömülmez).

### 3.3 Taranacak yüzey HTTP değildir

Ajan sızıntısı çoğu zaman «POST /exfil» değildir:

| Kanal | Neden X-Ray kapsamı |
|-------|---------------------|
| Model/provider prompt (chat, cyber, STT) | ADR-025 zaten amaç-ayrımı yapıyor; X-Ray aynı sınırı **malzeme** için tekrarlar |
| Tool / MCP / köprü | `controlled_bridge` yüzey blok + `MAX_READ_BYTES` / `MAX_WRITE_BYTES` proto-kota; hedef allowlist ve taint yok |
| Git push, PR gövdesi, commit mesajı | Kaynak kod + secret klasik kaçış |
| Panel yükleme, outbox, clipboard | Dosya v0.5 yüzeyi |
| Sandbox dışı path yazımı | `write_interceptor` path korur, sınıf/provenance yazmaz |
| Board kaydı, evidence satırı, ekran görüntüsü | Yan kanal: tarayıcı kendisi sızdırabilir |
| Robot telemetrisi | RSL-02 imzalı izin; X-Ray aynı sözleşmenin dijital eşi |

### 3.4 Sınıf yükseltmesi

Hacim eşit olsa da sınıf yükselebilir: public özet okundu, çıkışta secret parmak izi var. Ingress sınıfı ≤ egress sınıfı kuralı. Yükseltme → IEG `ask_confirmation` veya `deny`.

ADR-006 kategori 11 (PII) bugün **tespit yok**. X-Ray bu boşluğu dolduracak ilk somut guard yüzeyi olur; birleşik AI Firewall iddiası taşımaz.

### 3.5 Beş fiil — bıraktı/kopyaladı birinci sınıftır

Sızıntı yalnız çıkış değildir. Ledger **beş fiili** tutar; sıra kilitlidir ve beşinci fiil opsiyonel değildir:

1. **girdi** — sisteme ne geldi
2. **erişti** — neye dokundu
3. **bıraktı/kopyaladı** — residue: scratch, sağlayıcı retention, journal, clipboard
4. **üretti** — oturumun yeni malzemesi
5. **çıkarmaya çalıştı** — egress denemesi (başarılı veya kesilmiş)

«Göndermedik» ≠ «çalınmadı» — bırakılan kopya sonraki ajanın ingress'i olur.

Negatif hacim okuması aynı fiile bağlanır: girişte vardı, çıkışta yok → sağlayıcıda / scratch'te kopya kalmış olabilir; çıkışta var, girişte yok ve `generated` değil → hayali secret veya gerçek vault kaçışı; parmak izi karşılaştırması ayırır.

### 3.6 Fail-closed matrisi

| Sınıf veya sinyal | Ağ/hedef bilinmiyor (yetkisiz) | Allowlist hedef |
|-------------------|-------------------------------|-----------------|
| `secret` / `confidential` | **deny** + karantina | DLP + bilet + confirmation |
| `internal` | deny veya confirm | kota içinde allow + audit |
| `public` | düşük hacim allow + audit | allow + audit |
| Sınıflandırıcı belirsiz | **confidential say** | aynı |
| `unaccounted` (tek başına) | **hüküm değil** — sınıfa bak | sınıfa bak |

Kilitli kesişim: **`unaccounted` + confidential/secret + yetkisiz hedef = deny/quarantine**. `unaccounted` tek başına deny değildir; otomatik saldırı ilanı da değildir. Bilinmeyen hedef = confidential varsayılanı. Robotics fail-closed ve Anayasa §11 ile aynı çizgi.

### 3.7 X-Ray kendi sızıntı kanalı olmasın

Tarayıcı tam payload'ı journal'a yazarsa DLP, DLP olur. Mevcut audit sözleşmesi (`lumos-audit-log-contract.md`) zaten ham içeriği kopyalamaz.

Ledger'a yazılır: sınıf, byte, hedef, taint id, parmak izi **özeti**, karar. Yazılmaz: ham dosya, secret, PII, tam prompt.

**Karantina (kilitli):** gerçek store private katmandadır — hassas içeriği görebilir, secret/PII politikasına bağlanır, operasyonel enforcement yapar. Public OSS yalnız sözleşme/stub taşır: arayüz, olay şeması, test fikstürü, sahte karar motoru. Demo-safe; gerçek karantina public'e inmez.

### 3.8 Kör ikinci okuma (ADR-008)

IEG kararını üreten ajan vermez. İsteğe bağlı ikinci sınıflandırıcı (Cyber yüzeyi ≠ Sentinel) diğerinin verdiktini kilitlenene kadar görmez. İnsan, yüksek sınıfta üçüncü kapıdır. Dağıtık doğrulama; yeni «validator agent» imparatorluğu değil.

### 3.9 Işın kolime — amaç sınırı

X-Ray küresel paket dump'ı değildir. Oturum + amaç (ADR-012 purpose boundary) ile sınırlı tarama. «Madem tarıyorum her şeyi arşivleyeyim» yasaktır. Amaç dışı Ingress de Egress kadar olaydır (beklenmeyen payload).

### 3.10 Kota, allowlist, least privilege

Hacim sensörü **kota**yı besler. Kota per-agent × per-destination × per-class'tır ve fail-closed'dur. `MAX_READ_BYTES` / `MAX_WRITE_BYTES` hedef-kör proto-kotadır; sınıf-bilinçli bütçeye büyür. Allowlist + least privilege + provenance + DLP + kota + anomali birlikte durur; hiçbiri tek başına «%100 engel» iddiası taşımaz.

Lumos Cyber yüzeyi MB panosu değildir; oturum grafıdır: kim okudu → hangi taint → hangi hedef denendi → hangi karar.

---

## 4. Mevcut repo karşılığı (kanıt, abartısız)

| Parça | Bugün var | X-Ray'e katkısı | Boşluk |
|-------|-----------|-----------------|--------|
| `write_interceptor` + `workspace_contract` | Path/sandbox guard | Egress yakalama kancası | Sınıf, taint, hacim yok |
| `lumos_gate` / `controlled_bridge` | Niyet + yüzey blok | IEG karar tiplerinin alt kümesi | Malzeme soyağacı yok |
| `guard_audit` + `evidence_continuity` | Append-only **görev-mutasyon** izi | Ledger'ın **kardeşi** — aynı aile (append-only, ham payload yok); **aynı journal'a gömülmez**, alan olarak şişirilmez | Ingress makbuzu / beş fiil / fark kovası yok |
| `profiles.py` `SECURITY_NEVER_AUTO` | Kritik adım yasağı | Secret-sınıf egress için aynı sertlik (asla otomatik) | Veri sınıfı boyutu yok |
| `ConfirmationGrant` | TTL, `scope_hash`, ajan dışı `.lumos/` | Taint bileti kalıbı | Veri sınıfı / dest allowlist yok |
| `PermissionManager.acquire` | **no-op stub** | Bilet iskeleti | Yetenek yok |
| ADR-006 PII kategorisi | Sözleşme | Egress DLP hedefi | Tespit kodu yok |
| Sentinel (ADR-018) | Karar onaylı, runtime yok | Anomali raporu; yürütme yok | Executor olamaz |
| RSL-02 imzalı çıkış izni | Robot şartnamesi | Bilet modelinin kanıtı | Ajan oturumuna inmemiş |
| ADR-025 STT sınırı | Amaç-ayrımlı model | Ingress kanal örneği | Genel X-Ray değil |
| Audit log taslağı | Komut yaşam döngüsü | Karar ≠ kayıt ayrımı | Malzeme ledger'ı değil |

**Teşhis:** Lumos'ta **eylem guard'ı** parçalı duruyor; **malzeme guard'ı** yok. X-Ray bu ikinci ekseni adlandırır. Provenance Ledger, `evidence_continuity` ailesinin kardeşidir: görev mutasyonu değil, malzeme soyağacı. Birleşik AI Firewall (ADR-006) hâlâ yok; bu not onu ilan etmez.

---

## 5. Tehdit modeli — dürüst sınır

X-Ray sızıntıyı **ciddi azaltır**; yok etmez.

| Saldırı | Bilet + allowlist | İçerik DLP | Hacim anomali | Ledger |
|---------|-------------------|------------|---------------|--------|
| Açık secret/PII POST | Evet | Evet | Zayıf | Evet |
| Şifreli blob, yetkisiz hedef | **Evet** (bilet) | Hayır | Orta | Evet |
| Küçük parçalar, allowlist hedef | Zayıf | Parmak izi | Kota | Kısmen |
| Normal trafikte stego | Zayıf | Zayıf | Zayıf | Zayıf |
| Sağlayıcı retention (giriş kaldı) | — | — | — | **bıraktı/kopyaladı** kaydı |
| Ajan «ben taramayı kapattım» | Mümkün değil — X-Ray / Guard / Ledger ajan dışında | — | — | Olay |

%100 iddiası yok. En sağlam yığın kullanıcı cümlesiyle aynıdır: **allowlist + least privilege + provenance + DLP + kota + anomali**.

Public repo'da üretim imza/detector tarifnamesi **yazılmaz** (ADR-006 public/private sınır). Bu not sınıflar ve kovalar tutar; parmak izi motoru ve gerçek karantina private/professional katmandadır.

---

## 6. Bilinçli yapılmaz (şimdi)

| Yapılmaz | Gerekçe |
|----------|---------|
| FAZ-1 kod, yeni ajan, yeni orkestrasyon | STOP LIST; ADR-008 gating |
| ROADMAP / MODULES yüzdesi güncellemesi | Kanıt yok; merdiven FİKİR |
| İsim kaydı §A'ya «Lumos X-Ray» yazmak | Kilitli **aday**; §A vitrin/FAZ-1 sonrası ayrı karar |
| `write_interceptor` / köprü makbuzu uygulamak | Bu tur yalnız fikir notu |
| Prompt'a «sızdırma» emanet etmek | Ajan kendi kapısı olamaz |
| Sentinel'i executor yapmak | ADR-018 |
| Evidence journal'a ham payload veya ledger gömmek | Ledger kardeş journal; §3.7 |
| Public OSS'te gerçek karantina store | Kilit: private katman; OSS yalnız stub |
| «Tam AI Firewall / %100 DLP» vaadi | ADR-006; tehdit modeli |
| Bu PR'ı merge-ready saymak | Üçlü kapı + FAZ-1 dışı fikir |

---

## 7. FAZ-1 sonrası ilk dilim (kod değil, sıra)

Yalnız FAZ-1 kapandıktan ve ayrı kullanıcı kararı + Board claim'inden sonra. **Şimdi değil.** Dar dilim kilitli:

1. Köprü + `write_interceptor` üzerinde **ingress makbuzu**: path, byte, sınıf sezgisi, taint id — ham içerik yok.
2. Köprü HTTP/tool çıkışında **egress intercept**: hedef allowlist; **bilinmeyen hedef fail-closed**.

Sonraki merdiven (bu dilimin parçası değil, sıra kaydı):

3. Ledger satırı: **beş fiil** + dört fark kovası; `evidence_continuity` **kardeşi**, içine gömülmez.
4. Kota + hacim sensörü (karar değil).
5. DLP parmak izi, dual-scan ve gerçek karantina — **private katman**. Public OSS'te yalnız sözleşme/stub.

Kabul cümlesi (ileride): «Ajan, biletinin olmadığı hedefe **gönderemez**; `unaccounted` + confidential/secret + yetkisiz hedef **deny/quarantine**; insan onayı IEG dışından gelir.»

---

## 8. Açık sorular (kullanıcı hakemliği)

1. **KİLİTLİ (2026-08-21).** Ürün adı **Lumos X-Ray**; teknik katman **Ingress/Egress Guard**. Kullanıcı/ürün yüzü ile mimari bileşen ayrı tutulur. Registry §A kaydı ayrı (FAZ-1 sonrası / vitrin).
2. **KİLİTLİ (2026-08-21).** Provenance Ledger, `evidence_continuity` **kardeşidir**. Ayrı ilgisiz journal değildir; görev-mutasyon evidence journal'ına gömülmez. Aynı aile (append-only, ham payload yok), farklı semantik (malzeme soyağacı ≠ görev mutasyonu).
3. **KİLİTLİ (2026-08-21).** Karantina **private katmandadır**. Public OSS: yalnız sözleşme/stub (arayüz, olay şeması, test fikstürü, sahte karar motoru).
4. Secret taint sticky (TTL düşmez, insan deklasifikasyonu) anayasa-sertliğinde mi, yoksa TTL'li mi? — **hâlâ açık**; bu turda kilitlenmedi.

---

## 9. Sonuç

Üç tasarım kilitlendi; merdiven **FİKİR**; kod yok. Hacim tek başına yetmez; soyağacı ve ajan-dışı kapı gerekir. 40 MB dört kovaya ayrılır; `unaccounted` tek başına saldırı değildir.

X-Ray tarar. Guard durdurur. Ledger hesaplar. Sentinel raporlar. Ajan hiçbirini gevşetmez.

Aday ADR numarası **atanmaz**. Koda dönüşmesi FAZ-1 sonrası, ayrı kullanıcı kararı ve Board claim ister. Sıradaki kritik adım hâlâ o dar dilimdir: ingress receipt + bilinmeyen hedefte fail-closed egress — **şimdi değil**.
