# Lumos X-Ray — Ingress/Egress Guard

| Alan | Değer |
|------|-------|
| Durum | **FİKİR** — tarihli çalışma notu; karar değil; kod yok |
| Tarih | 2026-08-21 |
| Faz | FAZ-1 dışı. FAZ-2+ / Lumos Cyber adayı. STOP LIST ihlali yok |
| Merdiven | FİKİR (KARAR / KOD / CANLI değil) |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md) §11, [`ROADMAP.md`](../ROADMAP.md) STOP LIST, ADR-006/008/010/012/018/021/025 |
| İsim kaydı | Aday isimler; [`lumos-approved-naming-registry.md`](lumos-approved-naming-registry.md) §A'ya **yazılmaz** — kilit ayrı kullanıcı kararı |

Bu not, 2026-08-21 sohbetindeki **giriş/çıkış hesap verebilirliği** modelini mevcut Lumos katmanlarına oturtur ve X-Ray metaforunun eklediği iki aşamayı kaydeder. Yeni ajan, yeni orkestrasyon katmanı veya FAZ-1 özelliği **değildir**.

---

## 1. Kayıt edilen kullanıcı modeli

Temel soru:

> Bu ajan sisteme ne getirdi, neye erişti, ne üretti ve dışarı ne çıkarmaya çalıştı?

Üç parça:

| Parça | Soru | Tek başına yeter mi? |
|-------|------|----------------------|
| **Ingress X-Ray** | Girerken ne taşıyor? | Hayır — yalnız envanter |
| **Egress X-Ray** | Çıkarken ne götürüyor? | Hayır — bağlam yoksa DLP kördür |
| **Provenance ledger** | O fark nereden geldi? | Karar omurgası |

Hacim (ör. 100 MB girdi / 140 MB çıktı) **davranış sensörüdür**, hırsızlık hükmü değildir. Asıl değer: **o 40 MB farkın hesabı**.

Kontrol, üreten ajana emanet edilmez. Ajan «ben kötü bir şey göndermiyorum» diyemez. Bu, Anayasa §11 ile aynı çizgidir: Lumos kendi güvenlik politikasını gevşetemez.

---

## 2. Ad ayrımı (kilit değil)

Kullanıcı iki ad önerdi. İkisi de işe yarar; **aynı şeyi adlandırmazlar**. Karıştırılırsa Sentinel, guard ve ürün yüzü yine birbirine yapışır (ADR-010 drift'inin tekrarı).

| Aday | Katman | Kullanım |
|------|--------|----------|
| **Lumos X-Ray** | Lumos Cyber ürün yüzü / metafor | Kullanıcıya «ajanın içinden geçen malzeme taranır» anlatımı. Yeni ajan adı **değil**. |
| **Ingress/Egress Guard (IEG)** | ADR-010 **guard** | «Bu çıkış şimdi yapılsın mı?» — allow / deny / ask_confirmation / quarantine |
| **Provenance Ledger** | ADR-012 **kanıt** + log-vs-approval'daki **kayıt** | «Ne girdi, neye erişildi, ne üretildi, ne çıktı?» — append-only |

Öneri (karar bekler): Cyber vitrininde **Lumos X-Ray**; teknik sözleşmede **IEG + Provenance Ledger**. İsim kaydına ancak açık kilit kararıyla girer.

X-Ray **makinedir**, Sentinel **radyologdur**, IEG **kapı koludur**. Üçünü tek ajan yapmak STOP LIST + ADR-008 + ADR-018 ihlalidir.

```
Dış dünya
    │
    ▼
Lumos geçidi (ADR-012 C1 — tek dış kapı)
    │
    ├─ Ingress X-Ray  →  malzeme tarama + taint bileti
    ├─ Provenance Ledger  →  ne / nereden / hangi amaç
    ├─ Core / Local (yürütme)  →  X-Ray'i atlayamaz
    ├─ Egress X-Ray  →  fark + DLP + hedef allowlist
    └─ IEG kararı  →  allow | deny | confirm | quarantine
           │
           ▼
      Sentinel  →  gözlem / anomali raporu (yürütmez, secret tutmaz)
```

---

## 3. Bu notun katkısı — kullanıcı modelinin üzerine

Aşağıdakiler sohbetteki tarifi **tekrar etmez**; boşlukları kapatır.

### 3.1 Farkın kaynağı (40 MB sorusu)

Hacim farkı dört kovaya ayrılmadan «şüpheli» denmez:

| Kova | Anlam | Örnek |
|------|--------|--------|
| `accounted_from_ingress` | Çıkış, giriş makbuzundaki özetlere bağlanır | Dosya A'nın parçaları API C'ye |
| `generated` | Oturumun ürettiği yeni malzeme | Model çıktısı, log sarmalayıcı, sıkıştırma şişmesi |
| `wrapping_overhead` | Protokol/JSON/mime kabuğu | multipart, base64, tool-call zarfı |
| `unaccounted` | Hiçbir giriş makbuzu veya üretim kaydı karşılamıyor | Fail-closed adayı |

**Hüküm kuralı:** `unaccounted` + confidential/secret sınıfı → gönderme. `generated` tek başına hırsızlık değildir; sınıf yükseltmesi (aşağı) varsa DLP + confirmation.

Bu, 100/140 karşılaştırmasını **davranış sensöründen karar mekanizmasına** çevirmeden, «40 MB nereden?» sorusunu ledger'a bağlar.

### 3.2 Taint / yetki bileti (içerik DLP'sinden sert)

Şifreleme, parçalama ve steganografi içerik taramasını deler. Buna karşı X-Ray yalnız payload'a bakmaz; **oturumun taşıdığı yetkiyi** taşır.

- Ajan dosya A'yı (confidential) okuyunca `taint_ticket` alır: sınıf, amaç, TTL, izinli hedefler.
- Egress, biletsiz hedefe **içerik temiz görünse bile** gitmez.
- Vault yalnız `vault_ref` verir; ham secret ajan yüzeyine düşmez (SEC-010…013). Çıkışta vault parmak izi varsa ve bilette `vault_ref` yoksa → `unaccounted` secret.

İçerik DLP tamamlayıcıdır; **asıl kapı yetki biletidir**. Robotics RSL-02'deki imzalı çıkış izninin ajan oturumuna indirgenmiş hâlidir.

### 3.3 Taranacak yüzey HTTP değildir

Ajan sızıntısı çoğu zaman «POST /exfil» değildir:

| Kanal | Neden X-Ray kapsamı |
|-------|---------------------|
| Model/provider prompt (chat, cyber, STT) | ADR-025 zaten amaç-ayrımı yapıyor; X-Ray aynı sınırı **malzeme** için tekrarlar |
| Tool / MCP / köprü | `controlled_bridge` bugün yüzey bloklar; hacim+sınıf yok |
| Git push, PR gövdesi, commit mesajı | Kaynak kod + secret klasik kaçış |
| Panel yükleme, outbox, clipboard | Dosya v0.5 yüzeyi |
| Sandbox dışı path yazımı | `write_interceptor` path korur, sınıf/provenance yazmaz |
| Board kaydı, evidence satırı, ekran görüntüsü | Yan kanal: tarayıcı kendisi sızdırabilir |
| Robot telemetrisi | RSL-02 imzalı izin; X-Ray aynı sözleşmenin dijital eşi |

### 3.4 Sınıf yükseltmesi

Hacim eşit olsa da sınıf yükselebilir: public özet okundu, çıkışta secret parmak izi var. Ingress sınıfı ≤ egress sınıfı kuralı. Yükseltme → IEG `ask_confirmation` veya `deny`.

ADR-006 kategori 11 (PII) bugün **tespit yok**. X-Ray bu boşluğu dolduracak ilk somut guard yüzeyi olur; birleşik AI Firewall iddiası taşımaz.

### 3.5 Negatif hacim — «ne bıraktı?»

Sızıntı yalnız çıkış değildir:

- girişte vardı, çıkışta yok → sağlayıcıda / scratch'te kopya kalmış olabilir;
- çıkışta var, girişte yok ve `generated` değil → hayali secret veya gerçek vault kaçışı; parmak izi karşılaştırması ayırır.

Ledger dört fiili tutar: **getirdi / erişti / üretti / çıkardı**. Beşincisi isteğe bağlı: **bıraktı** (oturum sonu imha kanıtı).

### 3.6 Fail-closed matrisi

| Sınıf veya sinyal | Ağ/hedef bilinmiyor | Allowlist hedef |
|-------------------|---------------------|-----------------|
| `secret` / `confidential` | **deny** + karantina | DLP + bilet + confirmation |
| `internal` | deny veya confirm | kota içinde allow + audit |
| `public` | düşük hacim allow + audit | allow + audit |
| Sınıflandırıcı belirsiz | **confidential say** | aynı |
| `unaccounted` | **deny** | deny veya elevated confirmation |

Bilinmeyen = confidential. Robotics fail-closed ve Anayasa §11 ile aynı varsayılan.

### 3.7 X-Ray kendi sızıntı kanalı olmasın

Tarayıcı tam payload'ı journal'a yazarsa DLP, DLP olur. Mevcut audit sözleşmesi (`lumos-audit-log-contract.md`) zaten ham içeriği kopyalamaz.

Ledger'a yazılır: sınıf, byte, hedef, taint id, parmak izi **özeti**, karar. Yazılmaz: ham dosya, secret, PII, tam prompt. Karantina ayrı, erişimi kısıtlı store'dadır (public OSS'te demo-safe stub).

### 3.8 Kör ikinci okuma (ADR-008)

IEG kararını üreten ajan vermez. İsteğe bağlı ikinci sınıflandırıcı (Cyber yüzeyi ≠ Sentinel) diğerinin verdiktini kilitlenene kadar görmez. İnsan, yüksek sınıfta üçüncü kapıdır. Dağıtık doğrulama; yeni «validator agent» imparatorluğu değil.

### 3.9 Işın kolime — amaç sınırı

X-Ray küresel paket dump'ı değildir. Oturum + amaç (ADR-012 purpose boundary) ile sınırlı tarama. «Madem tarıyorum her şeyi arşivleyeyim» yasaktır. Amaç dışı Ingress de Egress kadar olaydır (beklenmeyen payload).

### 3.10 Kota, allowlist, least privilege

Hacim sensörü **kota**yı besler. Kota per-agent × per-destination × per-class'tır ve fail-closed'dur. Allowlist + least privilege + provenance + DLP + kota + anomali birlikte durur; hiçbiri tek başına «%100 engel» iddiası taşımaz.

---

## 4. Mevcut repo karşılığı (kanıt, abartısız)

| Parça | Bugün var | X-Ray'e katkısı | Boşluk |
|-------|-----------|-----------------|--------|
| `write_interceptor` + `workspace_contract` | Path/sandbox guard | Egress yakalama kancası | Sınıf, taint, hacim yok |
| `lumos_gate` / `controlled_bridge` | Niyet + yüzey blok | IEG karar tiplerinin alt kümesi | Malzeme soyağacı yok |
| `guard_audit` + `evidence_continuity` | Append-only karar izi | Ledger'ın kardeşi; **aynı journal'a ham veri gömülmez** | Ingress makbuzu / fark kovası yok |
| `profiles.py` `SECURITY_NEVER_AUTO` | Kritik adım yasağı | IEG deny ile hizalanır | Veri sınıfı boyutu yok |
| ADR-006 PII kategorisi | Sözleşme | Egress DLP hedefi | Tespit kodu yok |
| Sentinel (ADR-018) | Karar onaylı, runtime yok | Anomali raporu | Executor olamaz |
| RSL-02 imzalı çıkış izni | Robot şartnamesi | Bilet modelinin kanıtı | Ajan oturumuna inmemiş |
| ADR-025 STT sınırı | Amaç-ayrımlı model | Ingress kanal örneği | Genel X-Ray değil |
| Audit log taslağı | Komut yaşam döngüsü | Karar ≠ kayıt ayrımı | Malzeme ledger'ı değil |

**Teşhis:** Lumos'ta **eylem guard'ı** parçalı duruyor; **malzeme guard'ı** yok. X-Ray bu ikinci ekseni adlandırır. Birleşik AI Firewall (ADR-006) hâlâ yok; bu not onu ilan etmez.

---

## 5. Tehdit modeli — dürüst sınır

X-Ray sızıntıyı **ciddi azaltır**; yok etmez.

| Saldırı | Bilet + allowlist | İçerik DLP | Hacim anomali | Ledger |
|---------|-------------------|------------|---------------|--------|
| Açık secret/PII POST | Evet | Evet | Zayıf | Evet |
| Şifreli blob, yetkisiz hedef | **Evet** (bilet) | Hayır | Orta | Evet |
| Küçük parçalar, allowlist hedef | Zayıf | Parmak izi | Kota | Kısmen |
| Normal trafikte stego | Zayıf | Zayıf | Zayıf | Zayıf |
| Sağlayıcı retention (giriş kaldı) | — | — | — | **bıraktı** kaydı |
| Ajan «ben taramayı kapattım» | Mümkün değil — IEG ajan dışında | — | — | Olay |

%100 iddiası yok. En sağlam yığın kullanıcı cümlesiyle aynıdır: **allowlist + least privilege + provenance + DLP + kota + anomali**.

Public repo'da üretim imza/detector tarifnamesi **yazılmaz** (ADR-006 public/private sınır). Bu not sınıflar ve kovalar tutar; parmak izi motoru private/professional katmandadır.

---

## 6. Bilinçli yapılmaz (şimdi)

| Yapılmaz | Gerekçe |
|----------|---------|
| FAZ-1 kod, yeni ajan, yeni orkestrasyon | STOP LIST; ADR-008 gating |
| ROADMAP / MODULES yüzdesi güncellemesi | Kanıt yok; merdiven FİKİR |
| İsim kaydına «Lumos X-Ray» kilidi | Ayrı kullanıcı kararı |
| Prompt'a «sızdırma» emanet etmek | Ajan kendi kapısı olamaz |
| Sentinel'i executor yapmak | ADR-018 |
| Evidence journal'a ham payload | §3.7 |
| «Tam AI Firewall / %100 DLP» vaadi | ADR-006; tehdit modeli |
| Bu PR'ı merge-ready saymak | Üçlü kapı + FAZ-1 dışı fikir |

---

## 7. FAZ-1 sonrası ilk dilim (kod değil, sıra)

Yalnız FAZ-1 kapandıktan ve ayrı kullanıcı kararı + Board claim'inden sonra:

1. Köprü + `write_interceptor` üzerinde **ingress makbuzu**: path, byte, sınıf sezgisi, taint id — ham içerik yok.
2. Köprü HTTP/tool çıkışında **egress intercept**: hedef allowlist; bilinmeyen hedef fail-closed.
3. Ledger satırı: dört fiil + fark kovası; `evidence_continuity` kardeşi, içine gömülmez.
4. Kota + hacim sensörü (karar değil).
5. DLP parmak izi ve dual-scan — private katman.

Kabul cümlesi (ileride): «Ajan, biletinin olmadığı hedefe ve `unaccounted` confidential çıkışa **gönderemez**; insan onayı IEG dışından gelir.»

---

## 8. Açık sorular (kullanıcı hakemliği)

1. Ürün adı **Lumos X-Ray** olarak kilitlensin mi, yoksa yalnız metafor kalıp teknik ad **Ingress/Egress Guard** mı olsun?
2. Provenance Ledger yeni journal mı, `evidence_continuity` şema uzantısı mı? (Öneri: kardeş journal; mevcut evidence görev mutasyonu içindir.)
3. Karantina store public OSS'te stub mu, yoksa yalnız private katman mı?

---

## 9. Sonuç

Kullanıcı modeli doğrudur: hacim tek başına yetmez; soyağacı ve ajan-dışı kapı gerekir. Bu notun eklediği şey, o modeli Lumos'ta **yanlış yere koymamak** ve 40 MB'ı **kovaya ayırmaktır**.

X-Ray tarar. Ledger hesaplar. IEG durdurur. Sentinel raporlar. Ajan hiçbirini gevşetmez.

Aday ADR numarası **atanmaz**. Karara dönüşmesi ayrı kullanıcı kararı, FAZ-1 sonrası ve isim kilidi ister.
