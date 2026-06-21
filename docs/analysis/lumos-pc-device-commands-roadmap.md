# Lumos PC — İlk 20 Gerçek Cihaz Komutu Önceliklendirme Yol Haritası

| Alan | Değer |
|------|-------|
| Durum | **Analiz** — kod yok; private executor öncesi karar belgesi |
| Tarih | 2026-06-22 |
| Şema | `lumos.pc_remote_tools.v1` (genişleme adayları bu belgede) |
| İlgili | [lumos-pc-remote-bridge-plan.md](lumos-pc-remote-bridge-plan.md), [pc-remote-pending-approval-contract.md](pc-remote-pending-approval-contract.md), [lumos-mobile-approval-mvp-plan.md](lumos-mobile-approval-mvp-plan.md), [ADR-012](../decisions/ADR-012-lumos-security-codex.md), `packages/kando_bridge/src/kando_bridge/pc_remote_tools.py` |

---

## 1. Amaç ve kapsam

Bu belge, Lumos PC remote-control köprüsünde **stub zinciri tamamlandıktan sonra** private katmanda gerçek OS executor ile hayata geçirilecek **ilk 20 komutun** öncelik, risk ve onay sınıflandırmasını tanımlar.

### Public OSS vs private executor

| Katman | Repo | İçerik |
|--------|------|--------|
| **Public OSS** (`lumos-core`) | Bu repo | Tool şeması, stub yürütme (`execute_tool_stub`), onay kapısı, pending disk sözleşmesi, poll/approve HTTP uçları |
| **Private / professional** | Ayrı katman | Gerçek OS API: uygulama başlatma, accessibility/OCR, klavye/fare, native file picker, medya tuşları |

**Kural:** Public repoda gerçek cihaz kontrolü **commitlenmez** ([public-repo-boundary](../memory/public-repo-boundary.md)). Bu yol haritası private executor sırasını belirler; OSS tarafında yalnızca şema genişlemesi ayrı PR'larla ve demo-safe sınırlarla yapılır.

### Kapsam dışı (20 komut listesine dahil değil)

- Shell / terminal / subprocess yüzeyi (`surface_blocked` ile reddedilir)
- Kalıcı silme, trash dışı dosya yok etme
- Dış servise otomatik yazma
- Kritik sistem ayarı değişikliği
- Otomatik tıklama (`pc_click`) — yalnızca `pc_suggest_click` öneri olarak kalır; gerçek tıklama ayrı kapı + v2

---

## 2. Önceliklendirme kriterleri

### 2.1 Risk seviyesi

Mevcut `pc_remote_tools.py` katmanları genişletilir; **critical** yalnızca SECURITY_NEVER_AUTO veya geri dönüşsüz / yüksek exfil yüzeyi için kullanılır.

| Seviye | Tanım | Örnek |
|--------|-------|-------|
| **low** | Salt okuma; OS state değiştirmez veya yalnızca pasif sorgu | `pc_get_battery_status` |
| **medium** | Sınırlı etki; kullanıcı bağlamında geri alınabilir; onay ile güvenli | `pc_open_url`, `pc_suggest_click` |
| **high** | Geniş etki; yanlış kullanımda veri sızıntısı veya istenmeyen UI değişikliği | `pc_open_app`, `pc_type_text` |
| **critical** | SECURITY_NEVER_AUTO adayı veya köprü yüzeyinde **asla otomatik** olmamalı | `pc_quit_app` (veri kaybı riski), shell benzeri yüzey |

Kaynak risk sabitleri: `RISK_LOW`, `RISK_MEDIUM`, `RISK_HIGH` — `pc_remote_tools.py` L50–53.

### 2.2 Onay gereksinimi

| Değer | Anlam |
|-------|-------|
| **yes** | Her yürütmede disk pending + `approval_token` + `status=approved` zorunlu (RB-04 sözleşmesi) |
| **no** | Onay kapısı atlanır; yine de loopback + `KANDO_BRIDGE_SECRET` geçerli |
| **conditional** | Düşük riskli okuma; ancak pano/ekran içeriği hassas olabileceği için profil veya kullanıcı tercihi ile onay istenebilir |

Onay akışı: `POST /tools/execute` → pending → Mobile/panel poll → `POST /approve` → token ile tekrar execute ([pc-remote-pending-approval-contract.md](pc-remote-pending-approval-contract.md)).

### 2.3 MVP uygunluğu

| Değer | Anlam |
|-------|-------|
| **yes** | Stub zinciri + onay hattı hazır veya minimal private executor ile hemen uygulanabilir |
| **defer** | Güvenlik, platform API karmaşıklığı veya bağımlılık (accessibility, OCR) nedeniyle P1/P2 |
| **no** | MVP dışı; tasarım only veya bilinçli erteleme |

### 2.4 Öncelik dilimleri (P0 / P1 / P2)

| Dilim | Hedef |
|-------|-------|
| **P0** | Private executor **ilk dilim** (5–7 komut): en yüksek kullanıcı değeri + düşük entegrasyon riski |
| **P1** | İkinci dalga: orta karmaşıklık, onaylı yazma/etkileşim |
| **P2** | Üçüncü dalga: yüksek risk, platform farkları veya CU (computer use) bağımlılığı |

---

## 3. Mevcut 7 stub komut — yol haritası eşlemesi

Kaynak: `COMMAND_SPECS` — `pc_remote_tools.py` L85–135.

| Stub komut | Yol haritası # | Kategori | Risk (stub) | Onay (stub) | MVP dilimi | Not |
|------------|----------------|----------|-------------|-------------|------------|-----|
| `pc_open_app` | #5 | uygulama açma | high | yes | **P0** | Private: macOS `open`, Windows `ShellExecute` |
| `pc_open_url` | #1 | tarayıcı | medium | yes | **P0** | Varsayılan tarayıcı / deep link |
| `pc_read_screen_state` | #12 | sistem bilgisi | low | no | **P0** | Demo snapshot → accessibility/OCR tree |
| `pc_type_text` | #19 | uygulama/UI | high | yes | **P2** | Klavye enjeksiyonu; `irreversible_user_op` adayı |
| `pc_suggest_click` | #20 | uygulama/UI | medium | yes | **P1** | Öneri only; otomatik tıklama yok |
| `pc_request_file_picker` | #8 | dosya işlemleri | medium | yes | **P0** | Native dialog; kullanıcı seçimi zorunlu |
| `pc_request_user_approval` | — | meta kapı | meta | no | — | 20 komut listesine dahil değil; onay altyapısı |

**Özet:** 7 stub'tan 6'sı bu tabloda (#1, #5, #8, #12, #19, #20); meta kapı ayrı kalır. Kalan 14 komut yeni `komut_id` adaylarıdır.

---

## 4. İlk 20 komut tablosu

MVP önceliğine göre sıralı (P0 → P1 → P2). `#` sütunu uygulama sırası önerisidir.

| # | komut_id | kategori | açıklama | risk | onay | MVP uygun | not |
|---|----------|----------|----------|------|------|-----------|-----|
| 1 | `pc_read_screen_state` | sistem bilgisi | Aktif pencere veya tam ekran durumunu okur (başlık, odak, stub→a11y tree) | low | no | **yes** | Mevcut stub; private: AX/OCR |
| 2 | `pc_get_active_window` | sistem bilgisi | Ön plandaki uygulama adı, pencere başlığı, bundle/pid | low | no | **yes** | `read_screen_state` alt kümesi; daha hafif API |
| 3 | `pc_open_url` | tarayıcı | HTTPS URL'yi varsayılan tarayıcıda açar | medium | yes | **yes** | Mevcut stub; `bridge_medium_dispatch` |
| 4 | `pc_open_app` | uygulama açma | Uygulama adı veya bundle id ile başlatır | high | yes | **yes** | Mevcut stub; `bridge_high_risk_execute` |
| 5 | `pc_request_file_picker` | dosya işlemleri | Native dosya seçici açar; yol yalnızca kullanıcı seçiminden | medium | yes | **yes** | Mevcut stub; `cu_act_file_send` adayı |
| 6 | `pc_media_play_pause` | medya kontrolü | Sistem medya oturumunda oynat/duraklat (Spotify, Safari, vb.) | low | no | **yes** | OS medya tuşu API; geniş yan etki yok |
| 7 | `pc_get_battery_status` | sistem bilgisi | Pil yüzdesi, şarj durumu, güç kaynağı | low | no | **yes** | macOS IOPS / Windows `GetSystemPowerStatus` |
| 8 | `pc_reveal_in_finder` | dosya işlemleri | Verilen dosya/klasörü Finder/Explorer'da gösterir (silme yok) | medium | yes | **yes** | Yalnızca reveal; yazma/silme yok |
| 9 | `pc_focus_app` | uygulama açma | Çalışan uygulamayı ön plana getirir; yeni process açmaz | medium | yes | **yes** | `open_app`'ten düşük risk; yine onaylı |
| 10 | `pc_open_tab` | tarayıcı | Varsayılan veya hedef tarayıcıda yeni sekme + URL | medium | yes | **defer** | Tarayıcı hedefi belirsizliği; P1 |
| 11 | `pc_navigate_back` | tarayıcı | Aktif tarayıcı penceresinde geri git | medium | yes | **defer** | Odak penceresi + tarayıcı API gerekir |
| 12 | `pc_read_file_metadata` | dosya işlemleri | Dosya boyutu, mime, modified_at (içerik okumaz) | low | no | **defer** | Path kullanıcı/onay bağlamından gelmeli |
| 13 | `pc_get_clipboard_text` | sistem bilgisi | Panodaki metni okur (salt okuma) | medium | conditional | **defer** | Gizlilik: şifre/PII riski; profil bazlı onay |
| 14 | `pc_get_system_info` | sistem bilgisi | OS sürümü, hostname, uptime özeti | low | no | **defer** | Düşük risk; P1 batch |
| 15 | `pc_volume_set` | medya kontrolü | Sistem ses seviyesini 0–100 aralığında ayarlar | medium | yes | **defer** | Ani ses değişimi; onay zorunlu |
| 16 | `pc_volume_get` | medya kontrolü | Mevcut sistem ses seviyesini okur | low | no | **defer** | `volume_set` ile birlikte P1 |
| 17 | `pc_suggest_click` | uygulama/UI | UI öğesi için koordinat önerir; **tıklamaz** | medium | yes | **defer** | Mevcut stub; CU öneri hattı |
| 18 | `pc_close_tab` | tarayıcı | Aktif tarayıcı sekmesini kapatır | medium | yes | **defer** | Veri kaybı (form) riski; P2 |
| 19 | `pc_open_file` | dosya işlemleri | Dosyayı varsayılan uygulama ile açar | high | yes | **defer** | İstenmeyen uygulama/veri açılımı |
| 20 | `pc_type_text` | uygulama/UI | Odak alanına klavye ile metin yazar | high | yes | **defer** | Mevcut stub; klavye enjeksiyonu P2 |
| — | `pc_quit_app` | uygulama açma | Çalışan uygulamayı sonlandırır | **critical** | yes | **no** | Kaydedilmemiş veri; MVP dışı, v2+ ayrı kapı |
| — | `pc_request_user_approval` | meta | Genel onay kaydı oluşturur | meta | no | — | Altyapı; 20'lik liste dışı |

> **Not:** `pc_quit_app` bilinçli olarak 20'lik MVP setine alınmadı; critical risk ve `irreversible_user_op` yakınlığı nedeniyle ayrı değerlendirme gerektirir.

---

## 5. Kategori dağılımı özeti

| Kategori | P0 | P1 | P2 | Toplam (20) |
|----------|----|----|-----|-------------|
| tarayıcı | 1 (`open_url`) | 2 (`open_tab`, `navigate_back`) | 1 (`close_tab`) | **4** |
| uygulama açma | 2 (`open_app`, `focus_app`) | 0 | 1 (`type_text` UI) + stub `suggest_click` P1 | **4** * |
| dosya işlemleri | 2 (`file_picker`, `reveal_in_finder`) | 1 (`read_file_metadata`) | 1 (`open_file`) | **4** |
| sistem bilgisi | 3 (`read_screen`, `active_window`, `battery`) | 2 (`clipboard` conditional, `system_info`) | 0 | **5** |
| medya kontrolü | 1 (`play_pause`) | 2 (`volume_set`, `volume_get`) | 0 | **3** |

\* `pc_suggest_click` kategori olarak uygulama/UI etkileşimi sayılır; tabloda #17.

**Denge:** Sistem okuma (5) + dosya (4) + tarayıcı/uygulama (4+4) + medya (3) = 20. MVP P0 ağırlığı **okuma + düşük risk medya + onaylı açma** üzerinde.

---

## 6. MVP dilimi önerisi

Stub zinciri (RB-04+) tamamlandıktan sonra private katmanda **ilk uygulanacak 7 komut (P0)**:

| Sıra | komut_id | Gerekçe |
|------|----------|---------|
| 1 | `pc_read_screen_state` | Bağlam okuma; onaysız; CU/assistant temeli |
| 2 | `pc_get_active_window` | Hafif bağlam; ekran okumadan önce hızlı probe |
| 3 | `pc_open_url` | En sık kullanıcı niyeti; onay hattı kanıtlanmış |
| 4 | `pc_open_app` | İkinci temel niyet; yüksek risk → onay zorunlu |
| 5 | `pc_request_file_picker` | Dosya akışı; kullanıcı seçimi ile exfil sınırı |
| 6 | `pc_media_play_pause` | Düşük risk; hızlı “çalışıyor” doğrulaması |
| 7 | `pc_reveal_in_finder` | Güvenli dosya yüzeyi; silme/yazma yok |

**İkinci dalga (P1, +5):** `pc_focus_app`, `pc_open_tab`, `pc_read_file_metadata`, `pc_volume_set`, `pc_suggest_click`.

**Üçüncü dalga (P2):** `pc_type_text`, `pc_open_file`, `pc_close_tab`, `pc_navigate_back`, kalan okuma komutları.

**OSS tarafı:** P0 komutları için şema/stub genişlemesi gerekirse ayrı PR; gerçek executor yalnızca private swap.

---

## 7. Asla otomatik / SECURITY_NEVER_AUTO adayları

Kaynak: `SECURITY_NEVER_AUTO` — `src/task_engine/profiles.py` L47–52; köprü `surface_blocked` — `pc_remote_tools.py` L137–145.

| SECURITY_NEVER_AUTO üyesi | PC remote yüzeyi | Köprü davranışı |
|---------------------------|------------------|-----------------|
| `permanent_delete` | Sil/trash/kalıcı sil regex | **Reddedilir** (`surface_blocked`) |
| `external_write` | Dış API'ye otomatik POST/upload | Komut listesinde yok; eklenmez |
| `irreversible_user_op` | `pc_type_text`, `pc_quit_app`, otomatik `pc_click` | **Onay zorunlu**; otomatik yürütme yasak |
| `critical_system_config` | Sistem ayarı, firewall, kullanıcı hesabı | Komut listesinde yok |

### Critical / asla otomatik aday komutlar (20 listesi dışı veya P2+)

| komut_id | Neden | ADR-012 hizası |
|----------|-------|----------------|
| Shell / terminal | `surface_blocked` | Tek dış kapı; destructive probe |
| `pc_quit_app` | Kaydedilmemiş veri kaybı | `irreversible_user_op` adayı |
| `pc_type_text` (otomatik) | Kullanıcı adına geri alınamaz giriş | `cu_act_type`; yalnızca onaylı + tüketimli token |
| `pc_click` (gelecek) | Otomatik UI manipülasyonu | Stub'ta yok; `suggest_click` → ayrı kapı |
| Kalıcı dosya silme | — | **Asla**; trash prensibi geçerli |
| Pano yazma (`pc_set_clipboard`) | Exfil / injection | MVP dışı; `external_write` / yüksek risk |

**Mobile onay checklist (RB-05+):** Onay açık kullanıcı eylemi; red sonrası otomatik yeniden deneme yok; credential exfil yok ([lumos-mobile-approval-mvp-plan.md §8](lumos-mobile-approval-mvp-plan.md)).

---

## 8. Bağımlılıklar

| Bağımlılık | Durum | Etkilediği komutlar |
|------------|-------|---------------------|
| **RB-04** pending disk + token | ✓ Uygulandı | Tüm onaylı komutlar |
| **RB-05** Mobile poll client | ✓ OSS demo | Onaylı P0/P1 |
| **RB-06** LAN relay MVP | ✓ OSS demo | Mobile ↔ PC loopback |
| **RB-07+** Mobile onay UI (private) | Bekliyor | Kullanıcı onay deneyimi |
| **Private executor swap** | Bekliyor | Tüm P0 gerçek yürütme |
| **confirmation_policy** (opt-in CU4) | ✓ Wire var | `action_key` eşlemesi |
| **Platform API** | Private | macOS AX/OCR, Windows UI Automation |
| **OpenAI tool-loop adapter** | ✓ RB-07 OSS | Model → `/tools/execute` zinciri |

### Onay action_key hedefleri (genişleme)

| komut_id | action_key (hedef) |
|----------|-------------------|
| `pc_open_app`, `pc_focus_app` | `bridge_high_risk_execute` |
| `pc_open_url`, `pc_open_tab`, `pc_navigate_back`, `pc_close_tab` | `bridge_medium_dispatch` |
| `pc_request_file_picker`, `pc_reveal_in_finder`, `pc_open_file` | `cu_act_file_send` |
| `pc_type_text` | `cu_act_type` |
| `pc_suggest_click` | `cu_act_click` |
| `pc_volume_set` | `bridge_medium_dispatch` (yeni alias adayı) |
| Salt okuma komutları | — |

---

## Özet metrikler

| Metrik | Değer |
|--------|-------|
| Toplam komut | **20** |
| MVP **P0** komut sayısı | **7** |
| Mevcut stub ile örtüşen | **6** (+1 meta) |
| Onay gerektiren (yes) | **12** |
| Onay gerektirmeyen (no) | **7** |
| Conditional onay | **1** (`pc_get_clipboard_text`) |

### Top 5 P0 komut (private executor ilk dalga)

1. `pc_read_screen_state`
2. `pc_get_active_window`
3. `pc_open_url`
4. `pc_open_app`
5. `pc_request_file_picker`

---

## Sonraki adım (tek)

Private repoda P0 #1–#2 (salt okuma) executor'ını `execute_tool_stub` swap noktasında uygula; OSS'te yalnızca gerekirse `pc_get_active_window` şema PR'ı.
