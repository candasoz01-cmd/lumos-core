# Pilot Kullanıcı Programı — Break-the-System Tasarımı

| Alan | Değer |
|------|-------|
| **Belge türü** | Analiz / tasarım (docs only — kod veya PR yok) |
| **Tarih** | 2026-06-22 |
| **Hedef aşama** | **Closed Pilot** — Internal Alpha çıkış sonrası ([INTERNAL_ALPHA_RELEASE_SCOPE.md](../INTERNAL_ALPHA_RELEASE_SCOPE.md) O5) |
| **Üst sınır** | [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`public-repo-boundary.md`](../memory/public-repo-boundary.md), ADR-012 |
| **Durum** | Tasarım — P1-03 (pilot sözleşmesi + davet ≤20) için girdi belgesi |

**Kaynak belgeler (repo snapshot):**

| Belge | Durum |
|-------|-------|
| [INTERNAL_ALPHA_RELEASE_SCOPE.md](../INTERNAL_ALPHA_RELEASE_SCOPE.md) | ✓ |
| [INTERNAL_ALPHA_OPERATIONS.md](../INTERNAL_ALPHA_OPERATIONS.md) | ✓ |
| [p0-p1-triage-list.md](p0-p1-triage-list.md) | ✓ |
| `first-customer-reality-check.md` | **Yok** — bu tasarımda triage + Alpha ops ile hizalandı |
| `pre-commercial-release-plan.md` | **Yok** |
| `mobile-approval-flow-security-review.md` | **Yok** — yerine [mobile-approve-reject-ui-verification.md](mobile-approve-reject-ui-verification.md), [lumos-mobile-approval-mvp-plan.md](lumos-mobile-approval-mvp-plan.md) |
| `os-executor-prelaunch-security-rules.md` | **Yok** — yerine [lumos-pc-device-commands-roadmap.md](lumos-pc-device-commands-roadmap.md), [lumos-pc-remote-bridge-skeleton-verification.md](lumos-pc-remote-bridge-skeleton-verification.md) |
| PC remote / onay | [pc-remote-pending-approval-contract.md](pc-remote-pending-approval-contract.md), [pr-rb-06-lan-relay-verification.md](pr-rb-06-lan-relay-verification.md), [pr-rb-07-openai-tool-loop-verification.md](pr-rb-07-openai-tool-loop-verification.md) |

---

## 1. Program amacı

Bu program **genel beta testi değildir**. Amaç, Lumos'un Internal Alpha sonrası **Closed Pilot** aşamasında sistemi **kasıtlı olarak zorlayan**, güvenlik boşluklarını, onay zinciri atlama yollarını, UX yanıltmalarını ve sınır ihlallerini bulan küçük bir kullanıcı kohunu kurmaktır.

**Break-the-system mindset** burada şu anlama gelir:

- «Çalışıyor mu?» yerine «**Nasıl kırarım?**» sorulur.
- Onay ekranını, relay token'ını, pending TTL'ini, paneldeki pasif modülleri ve görev/trash sınırlarını **saldırı yüzeyi** olarak ele alır.
- Bulgular ürün iyileştirmesi için değerli; **yetkisiz OS eylemi veya gizli veri sızıntısı** kabul edilemez sonuçtur.

**Internal Alpha ile ilişki:** Alpha yalnızca ekip içi ([scope §2](../INTERNAL_ALPHA_RELEASE_SCOPE.md)); bu program Alpha **çıkış kapıları** (P1-02 çekirdek yolculuk ≥2 hafta, P0 regresyon = 0) tamamlandıktan sonra başlar. Pilot, Alpha kapsamını genişletmez; Alpha'da hariç tutulan O1–O8 (entegrasyonlar, checkout, tam modül menüsü iddiası vb.) pilot için de **vaat edilmez**.

**Public OSS vs private pilot ayrımı:**

| Katman | Pilot erişimi | Not |
|--------|---------------|-----|
| **lumos-core (public OSS)** | Panel stub, köprü stub, LAN relay demo, onay sözleşmesi | `stub_only`; gerçek OS otomasyonu yok |
| **Private / professional katman** | Gerçek executor, native Lumos Mobile, TLS relay, hesap bağlı pairing | NDA + sözleşme; public repoda detay yok |

Pilot kullanıcılar **her iki katmanda aynı güvenlik beklentisine** tabidir: onay olmadan yürütme yok, `SECURITY_NEVER_AUTO` otomatik değil, simülasyon gerçek başarı gibi sunulmaz.

---

## 2. Kullanıcı profilleri (personas)

### 2.1 Güvenlik meraklısı geliştirici

| Alan | İçerik |
|------|--------|
| **Motivasyon** | Onay token'ı, relay oturumu ve köprü HTTP yüzeyini kod ve protokol seviyesinde test etmek; «bayrak bypass» ve replay aramak. |
| **Lumos odak alanı** | Bridge (`POST /tools/execute`, `GET /pending_approvals`), LAN relay (`/relay/pair`, `X-Relay-Token`), `approval_granted` vs disk token doğrulaması |
| **Risk / değer** | **Risk:** Agresif fuzzing, yerel ağ MITM denemeleri. **Değer:** P0 güvenlik bulguları, regresyon öncesi yakalama (P0-05 izleme). |

### 2.2 Şüpheci gizlilik odaklı kullanıcı

| Alan | İçerik |
|------|--------|
| **Motivasyon** | «Bu uygulama neyi okuyor / neyi dışarı gönderiyor?» — consent ve profil sınırlarının sessiz genişlemesini aramak. |
| **Lumos odak alanı** | Panel «Sınırlı mod», pasif modül rozeti (RB-17), cihaz bağlantı / izin özeti (IA hedefi), `pc_read_screen_state` stub yanıtı |
| **Risk / değer** | **Risk:** Yanlış anlaşılan «gizlilik ihlali» raporları. **Değer:** UX/consent netliği, yanıltıcı kopya ve gizli veri yüzeyi bulguları. |

### 2.3 Power user / otomasyon kurcalayıcısı

| Alan | İçerik |
|------|--------|
| **Motivasyon** | CLI, OpenAI tool-loop ve görev motorunu «hız için» atlamak; çok adımlı otomasyonla onay zincirini yormak. |
| **Lumos odak alanı** | `openai_tool_loop_demo`, `run_tool_call_loop` pending akışı, yerel görevler [Yerel], `make test` / CLI smoke |
| **Risk / değer** | **Risk:** `--auto-approve` dev bypass'ı prod gibi kullanmak. **Değer:** Tool-loop edge case'leri, çift yürütme, timeout davranışı. |

### 2.4 UX kaos testçisi (panel kafa karıştırıcı)

| Alan | İçerik |
|------|--------|
| **Motivasyon** | «Henüz aktif değil» modüllere tıklamak, Sınırlı mod ile tam modül menüsü beklentisini çarpıştırmak, onay beklerken panelde yanlış geri bildirim aramak. |
| **Lumos odak alanı** | Astro panel `/panel`, inactive nav rozeti, yerel görev localStorage akışı, mobile web UI (`GET /relay/mobile`) |
| **Risk / değer** | **Risk:** Destek yükü, moral hazard («bozuk ürün» algısı). **Değer:** P1 UX bulguları, onay süresi algısı, hata mesajı netliği. |

### 2.5 Yerel ağ saldırganı (LAN breaker)

| Alan | İçerik |
|------|--------|
| **Motivasyon** | Aynı Wi‑Fi'deki başka cihazdan relay keşfi, sahte beacon, pairing code brute force, relay token çalma ve başkasının onayını verme. |
| **Lumos odak alanı** | UDP beacon (`8767`), `GET /relay/discover`, 6 haneli pairing code (TTL 600s), `mobile_url` token linki |
| **Risk / değer** | **Risk:** Gerçek LAN ortamında başka kullanıcıların oturumuna müdahale denemesi (etik sınır içinde, kendi pilot ortamında). **Değer:** Relay güvenlik sınırları, pairing entropy, oturum süresi politikası. |

### 2.6 Görev / veri sınırı kırıcısı

| Alan | İçerik |
|------|--------|
| **Motivasyon** | Kalıcı silme, trash dışı yok etme, `.lumos/` path manipülasyonu ve panel read-only vs yazma yolu uyumsuzluğu (P1-05). |
| **Lumos odak alanı** | Task engine, `permanent_delete`, `.lumos/trash/`, panel tasks path, `surface_blocked` regex (shell/sil/trash) |
| **Risk / değer** | **Risk:** Gerçek veri kaybı (pilot ortamında yedeklenmemiş veri). **Değer:** `SECURITY_NEVER_AUTO` regresyonu, trash prensibi, workspace sözleşmesi ihlali. |

---

## 3. Katılım kriterleri

### 3.1 Davet edilecekler

| Kriter | Açıklama |
|--------|----------|
| **Breaker mindset** | Önceden güvenlik/QA/otomasyon deneyimi veya somut «sistem kırma» örneği |
| **Teknik okuryazarlık** | Terminal, LAN, HTTP temel kavramları; mobil onay için telefon + PC |
| **Geri bildirim disiplini** | Adımlar, beklenen/gerçek, ekran görüntüsü veya log ile rapor |
| **Zaman taahhüdü** | Pilot süresi boyunca haftada ≥2 saat hedefli test + haftalık kısa checkpoint |
| **Güvenilirlik** | NDA/sözleşme imzası; etik sınırlara uyum (§7) |
| **Çeşitlilik** | En az 2 persona farklı ağırlıkta (ör. 1 güvenlik + 1 UX + 1 LAN) |

**Hedef kohut boyutu:** ≤20 kullanıcı ([p0-p1-triage-list P1-03](p0-p1-triage-list.md) — G-04).

### 3.2 Hariç tutulacaklar

| Grup | Neden |
|------|-------|
| Genel «beta meraklısı» / influencer | Breaker programı değil; destek maliyeti yüksek, düşük güvenlik sinyali |
| Üretim verisi taşıyan kurumsal hesaplar | Pilot ortamı izole; prod vault/secret yok (scope O2) |
| Ödeme / checkout beklentisi olanlar | OD-011 implementation-pending; tahsilatsız pilot |
| Yasadışı saldırı amacıyla başvuranlar | Program kapsamı dışı; derhal çıkar |
| Public OSS'i «ücretsiz tam ürün» gören kullanıcılar | README early development ile çelişen beklenti |

### 3.3 NDA, güven ve repo sınırları

| Konu | Politika |
|------|----------|
| **NDA / pilot sözleşmesi** | P1-03 kapanışı için zorunlu; bulgular, özel relay URL'leri ve private katman detayları |
| **Public OSS paylaşımı** | Stub davranışı ve açık API uçları paylaşılabilir; **KANDO_BRIDGE_SECRET**, relay token, pairing code **asla** |
| **Güven modeli** | Pilot «güvenilir saldırgan» — sistem kırma izni verilir; **üçüncü taraf sistemlere** veya **Lumos dışı** saldırı izni yok |
| **Veri** | Pilot verisi sentetik veya yedeklenebilir; gerçek kimlik bilgisi / müşteri PII önerilmez |
| **Responsible disclosure** | Kritik bulgu: önce Lumos güvenlik kanalına; public issue öncesi embargo süresi sözleşmede |

---

## 4. Test senaryoları

Her senaryo: **adımlar**, **beklenen güvenli davranış**, **kırmızı bayrak** (red flag).

### 4.1 Panel UX — kafa karıştırma / pasif modüller

| # | Senaryo | Adımlar | Beklenen güvenli davranış | Kırmızı bayrak |
|---|---------|---------|---------------------------|----------------|
| S01 | Pasif modül tıklama | Panel nav'da «Henüz aktif değil» rozeti olan öğelere tıkla | Rozet görünür; tam özellik vaadi yok; yönlendirme veya pasif empty state | Rozet yok; «yakında» yerine çalışan özellik gibi davranış |
| S02 | Sınırlı mod vs tam menü | Sınırlı modda tüm modül listesini dolaş | «Early active development» / Sınırlı mod mesajı tutarlı | Prod tam ürün iddiası; gizli özellik açılması |
| S03 | Yerel görev path çakışması | Panel [Yerel] görev ekle; CLI `.lumos/tasks.json` vs `tasks/tasks.json` kontrol et (P1-05) | Tek tutarlı kaynak veya read-only uyarısı | Sessiz veri çatallanması; kayıp görev |
| S04 | Onay beklerken panel geri bildirimi | Tool-loop pending oluştur; panele dön | Pending durumu görünür veya «onay gerekli» net | «Başarılı» / yeşil onay; işlem sessizce tamamlanmış gibi |
| S05 | localStorage temizleme | Tarayıcı verisini sil; panel görevlerine dön | Boş state; çekirdek `.lumos/` CLI state ile karıştırılmaz | Panel, sunucu/CLI state'i yanlış yansıtır |

### 4.2 Onay bypass denemeleri

| # | Senaryo | Adımlar | Beklenen güvenli davranış | Kırmızı bayrak |
|---|---------|---------|---------------------------|----------------|
| S06 | `approval_granted` bayrağı tek başına | `POST /tools/execute` ile `approval_granted:true`, token olmadan | Red / `pending_approval`; yürütme yok | Stub veya gerçek yürütme |
| S07 | Token replay | Onaylı pending'i iki kez `POST /tools/execute` ile tüket | İkinci çağrı: `approval_already_used` | İkinci yürütme başarılı |
| S08 | Süresi dolmuş onay | 900s+ bekleyip veya `expires_at` sonrası onayla/yürüt | `status=expired`; yürütme red | Expired kayıtla yürütme |
| S09 | Çift onay (double approve) | Aynı pending'e iki kez `POST /approve` | İlk onay geçerli; ikinci tutarlı red veya no-op | İki geçerli onay token'ı; state bozulması |
| S10 | Red sonrası yürütme | `POST /approve` `approved:false` veya relay reject; sonra execute | Yürütme red; `status=rejected` kalır | Reddedilmiş kayıtla stub yürütme |
| S11 | Yanlış token | Geçerli `approval_file`, rastgele `approval_token` | Token eşleşme hatası | Yürütme |
| S12 | Legacy `/task` vs `pc_remote` karışımı | Hem legacy hem `source=pc_remote` pending listele; yanlış dosyayla onay | Kaynak ve dosya adı birebir eşleşmeli | Yanlış kayıt onaylanır |

### 4.3 Bridge / LAN pairing abuse

| # | Senaryo | Adımlar | Beklenen güvenli davranış | Kırmızı bayrak |
|---|---------|---------|---------------------------|----------------|
| S13 | Discover secret sızıntısı | `GET /relay/discover`, UDP beacon yanıtını incele | `KANDO_BRIDGE_SECRET` yok | Bridge secret veya uzun ömürlü köprü kimlik bilgisi |
| S14 | Pairing code brute force | Yanlış kodları hızlı gönder | 403; rate limit veya lockout (hedef); TTL sonrası geçersiz | Başarılı pair; kod süresi dolmadan kolay tahmin |
| S15 | Relay token çalma | `mobile_url` veya `X-Relay-Token` başka cihazdan kullan | Oturum bağlı; yetkisiz pending/approve red | Başka kullanıcının PC'sinde onay verme |
| S16 | Relay olmadan bridge | Telefondan doğrudan `127.0.0.1:8765` | Erişim yok (loopback) | Köprü dış ağa açık |
| S17 | Sahte beacon | UDP'ye sahte `pairing_id` yayınla | Keşif listesinde ayırt edilebilir veya tek PC politikası | Kullanıcı yanlış cihaza pair eder |

### 4.4 Görev / trash / kalıcı silme sınırları

| # | Senaryo | Adımlar | Beklenen güvenli davranış | Kırmızı bayrak |
|---|---------|---------|---------------------------|----------------|
| S18 | `permanent_delete` CLI | Görev kalıcı sil komutu (açık komut olmadan) | İşlem yapılmaz veya tek satır uyarı + onay kapısı | Otomatik kalıcı silme |
| S19 | Trash dışı silme | `.lumos/` dışı veya `trash/` olmayan path'e silme denemesi | Red; workspace sözleşmesi | Dosya kalıcı yok |
| S20 | Bridge `surface_blocked` | `pc_type_text` ile shell/sil/trash ifadesi | `surface_blocked` / argüman red | Komut pending'e düşer ve onayla geçer |
| S21 | Task engine SECURITY_NEVER_AUTO | `permanent_delete` task step profil bypass denemesi | Engine branch red; P0-05 regresyon yok | Otomatik yürütme |

### 4.5 OpenAI tool-loop edge case'leri

| # | Senaryo | Adımlar | Beklenen güvenli davranış | Kırmızı bayrak |
|---|---------|---------|---------------------------|----------------|
| S22 | Varsayılan `auto_approve` | `run_tool_call_loop` varsayılan çağrı | `stage: pending`, `ok: false` | Otomatik stub yürütme |
| S23 | `--auto-approve` prod kullanımı | Demo CLI'da dev bypass | Uyarı metni; bilinçli opt-in | Uyarı yok; sessiz bypass |
| S24 | `--wait-approve` timeout | 120s onay bekle; verme | `approval_timeout`; pending diskte kalır | Sonsuz blok veya sessiz başarı |
| S25 | Çoklu tool çağrısı | Model yanıtında ardışık 3 high-risk komut | Her biri ayrı pending; ayrı token | Tek onayla üç yürütme |
| S26 | Onay sonrası re-execute | Onayla → adapter re-execute | Tek tüketim; `used=true` | Token tekrar kullanılabilir |

**Senaryo sayısı:** 26 (15–20 hedefinin üzerinde; alan başına kapsam için genişletildi).

---

## 5. Başarı kriterleri

### 5.1 Nicel (quantitative)

| Metrik | Hedef (Closed Pilot ilk 4–6 hafta) | Kaynak / not |
|--------|-------------------------------------|--------------|
| **Kritik bulgu (P0 güvenlik)** | ≥1 **raporlanmış** ve triage edilmiş; **0 açık P0** pilot çıkışında | P0-05 izleme; unauthorized OS = anında P0 |
| **Yetkisiz OS eylemi** | **0** — stub dışı gerçek otomasyon, onaysız yürütme | [pc-remote contract](pc-remote-pending-approval-contract.md) |
| **Onay zinciri bypass** | **0** başarılı bypass (S06–S12, S22–S26 kapsamı) | Token + disk doğrulama |
| **Katılımcı aktivite** | ≥70% kohut haftalık checkpoint doldurur | [INTERNAL_ALPHA_OPERATIONS §4.3](../INTERNAL_ALPHA_OPERATIONS.md) şablonu uyarlanır |
| **Senaryo kapsama** | Her katılımcı ≥10 senaryo (farklı alanlardan) | §4 checklist |
| **Time-to-approve (median)** | İlk ölçüm + hedef ≤60s (foreground mobile UI) | UX sinyali; blokaj değil |

### 5.2 Nitel (qualitative)

| Sinyal | Başarı göstergesi |
|--------|-------------------|
| Breaker raporları | Adımlar tekrarlanabilir; «muhtemelen» yerine kanıt |
| Consent / Sınırlı mod | Şüpheci persona «ne izin verdim» sorusuna net cevap bulur |
| LAN relay | En az bir «başarısız saldırı» dokümante; savunma anlaşılır |
| Destek yükü | P1-04 kanalı; kritik bulgu SLA'sı sözleşmede |

### 5.3 Pilot çıkış kapıları (exit gates)

Pilot **başarılı çıkış** için:

1. P0 güvenlik açığı = **0 açık** (kapatıldı veya Commercial Launch defer + risk kabul kaydı).
2. P1-03 pilot sözleşmesi + davet kaydı **kapalı**.
3. P1-04 destek kanalı + SLA metni **yayında**.
4. En az **4 hafta** breaker aktivitesi; ≥2 tam kohut checkpoint döngüsü.
5. `SECURITY_NEVER_AUTO` regresyonu yok (haftalık `make test` + breaker S18–S21).
6. Üçüncü taraf veya yasadışı saldırı vakası **0** (veya tek vaka → derhal program sonu + olay kaydı).

**Başarısız çıkış:** Yetkisiz OS eylemi, bridge secret sızıntısı veya toplu onay bypass → pilot durdur; Alpha stabilizasyonuna dön.

---

## 6. Geri bildirim kanalları

| Kanal | Kullanım | İçerik şablonu |
|-------|----------|----------------|
| **Öncelikli: güvenlik / breaker** | Kritik bypass, token, relay | Senaryo ID, ortam, adımlar, beklenen/gerçek, log (secret'sız), zaman damgası |
| **Destek kanalı (P1-04)** | UX, kafa karıştırma, genel bug | Ekran görüntüsü + panel URL + Sınırlı mod durumu |
| **Haftalık checkpoint** | Ürün/QA toplama | Alpha §4.3 şablonu + «breaker senaryo sayısı» + «en kötü bulgu» |
| **Repo içi triage** | Onaylı bulgular | [p0-p1-triage-list.md](p0-p1-triage-list.md) güncelleme önerisi (Platform/Güvenlik sahibi) |
| **UX bulguları** | Panel polish | [INTERNAL_ALPHA_UX_FINDINGS.md](../INTERNAL_ALPHA_UX_FINDINGS.md) formatı |

**Rapor kalitesi kuralı:** Secret, relay token, pairing code, ham `approval_token` **paylaşılmaz** — yerine «token uygulandı / reddedildi» ve hata kodu.

---

## 7. Etik sınırlar

Pilot katılımcıları **yapmamalı**:

| Yasak | Açıklama |
|-------|----------|
| Yasadışı erişim | Lumos dışı sistemlere, başka kişilerin hesaplarına veya ağlarına saldırı |
| DoS / kaynak tüketimi | Köprü/relay'i kasıtlı çökertme, UDP flood, sürekli pending spam (hafif yük testi önceden onaylı) |
| Gerçek malware / exfil | Lumos üzerinden credential toplama ve üçüncü tarafa gönderme |
| Sosyal mühendislik (dış) | Lumos ekibinden secret isteme, sahte destek |
| Public secret paylaşımı | Issue, Discord, Twitter'da token/secret |
| Üretim Lumos / müşteri verisi | Pilot sandbox verisi kullan |

**Yapabilir (program kapsamında):**

- Kendi pilot PC ve telefonunda onay bypass denemeleri
- Kendi LAN'ında relay MITM / sahte beacon (izole ağ)
- Stub yüzeyinde fuzzing ve negatif test
- Panel ve CLI'da sınır ihlali arama

İhlal: tek taraflı program çıkışı; sözleşme maddeleri.

---

## 8. Zaman çizelgesi önerisi

Internal Alpha **P1-02** (çekirdek yolculuk ≥2 hafta) ile hizalı — pilot **Alpha çıkışından sonra** başlar.

| Faz | Süre | Aktivite | Bağımlılık |
|-----|------|----------|------------|
| **T0 — Hazırlık** | Alpha çıkış −2 hafta | P1-03 sözleşme taslağı; kohut shortlist (≤20); senaryo §4 paketi | P1-02 devam |
| **T1 — Alpha çıkış** | Hafta 0 | P1-02 kapalı; P0=0; scope §7 checklist | [INTERNAL_ALPHA_RELEASE_SCOPE §7](../INTERNAL_ALPHA_RELEASE_SCOPE.md) |
| **T2 — Davet & onboarding** | Hafta 1–2 | NDA, ortam kurulum rehberi (köprü+relay+demo); persona atama | P1-03, P1-04 |
| **T3 — Breaker sprint 1** | Hafta 3–4 | Onay + bridge senaryoları (S06–S17, S22–S26); haftalık checkpoint | RB-06/07 demo merge durumu |
| **T4 — Breaker sprint 2** | Hafta 5–6 | Panel UX + task/trash (S01–S05, S18–S21); UX triage | P1-05 path netliği |
| **T5 — Çıkış değerlendirme** | Hafta 7 | §5 exit gates; triage güncelleme; Commercial Launch / genişletilmiş pilot kararı | P0/P1 tablosu |

**Not:** Wave 2+ ADR-012 enforcement, default-on confirmation ve packaged installer (RB-06 Launch) bu pilot fazında **authorize edilmez** ([INTERNAL_ALPHA_OPERATIONS §5](../INTERNAL_ALPHA_OPERATIONS.md)).

---

## 9. Açık kararlar

| # | Karar | Seçenekler | Önerilen sahip | Blocker |
|---|-------|------------|----------------|---------|
| D1 | Pilot tamamen OSS stub mı, private executor alt kohut mu? | (a) OSS only ≤20 (b) 10 OSS + 10 private | Ürün / Güvenlik | Gerçek OS risk kabulü |
| D2 | LAN breaker için izole lab vs ev Wi‑Fi | Lab VLAN / dedicated router vs «kendi ağın» | Platform | D15 pairing abuse raporları |
| D3 | `support@` ve kritik bulgu SLA süresi | 24h / 72h business | Destek / ops | P1-04 |
| D4 | NDA şablonu ve embargo süresi | 30 / 90 gün | Ticari / ops | P1-03 |
| D5 | Rate limit / flood koruması pilot öncesi zorunlu mu? | MVP'de audit/rate limit defer ([contract §Sınırlar](pc-remote-pending-approval-contract.md)) | Güvenlik | S14, S24 pending spam |
| D6 | Mobile yüzey: OSS web UI vs native private app | v1 OSS `GET /relay/mobile` yeterli mi? | Ürün / UX | Time-to-approve UX |
| D7 | Ödül / tanınma modeli | Hall of fame / bounty / gönüllü | Ticari | Kohut motivasyonu |
| D8 | Eksik kaynak belgeler | `first-customer-reality-check`, `pre-commercial-release-plan` yazılacak mı? | Ürün / release | Pilot ticari beklenti netliği |

---

## Özet sayılar

| Öğe | Değer |
|-----|-------|
| **Persona sayısı** | 6 |
| **Senaryo sayısı** | 26 |
| **Hedef kohut** | ≤20 |

### Üst 3 başarı metriği

1. **Yetkisiz OS eylemi = 0** — onay olmadan stub dışı veya gerçek yürütme yok.
2. **Onay zinciri bypass = 0** — token replay, `approval_granted` bypass, expired/rejected yürütme başarısız.
3. **Kritik güvenlik bulguları triage edildi; pilot çıkışında açık P0 = 0** — breaker kohutu P0-05 regresyonunu besler, blokaj oluşturmaz.

---

## Çapraz referanslar

| Belge | Bağlantı |
|-------|----------|
| Alpha kapsam | [INTERNAL_ALPHA_RELEASE_SCOPE.md](../INTERNAL_ALPHA_RELEASE_SCOPE.md) |
| Alpha ops / P1-02 | [INTERNAL_ALPHA_OPERATIONS.md](../INTERNAL_ALPHA_OPERATIONS.md) |
| P0/P1 | [p0-p1-triage-list.md](p0-p1-triage-list.md) |
| Onay sözleşmesi | [pc-remote-pending-approval-contract.md](pc-remote-pending-approval-contract.md) |
| Mobile MVP | [lumos-mobile-approval-mvp-plan.md](lumos-mobile-approval-mvp-plan.md) |
| LAN relay | [pr-rb-06-lan-relay-verification.md](pr-rb-06-lan-relay-verification.md) |
| Tool-loop | [pr-rb-07-openai-tool-loop-verification.md](pr-rb-07-openai-tool-loop-verification.md) |
| Pairing | [device-pairing-strategy.md](device-pairing-strategy.md) |

---

*Son güncelleme: 2026-06-22 — tasarım only; kod/PR yok.*
