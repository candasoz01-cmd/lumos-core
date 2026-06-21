# Lumos — 30 Günlük Release Readiness Gap Analizi

## Executive Summary

- **Mevcut checkout, sınırlı web paneli için güçlü bir test tabanına sahip; fakat tek bir
  “paketlenebilir Lumos sürümü” tanımı yok.** `ui` üretim build’i ve yerel panel
  yolculukları geçiyor. Buna karşılık README ürünü erken geliştirme olarak tanımlıyor,
  end-user installer olmadığını söylüyor ve bağlı/official release’in yayımlanmadığını belirtiyor;
  `docs/LUMOS_V1_READINESS.md` ise web panel v1’i kapanmış sayıyor.
- **30 gün içinde sürüm çıkarılmasını doğrudan engelleyen ana boşluklar paket üretimi,
  temiz kurulum, ilk çalıştırma, sürüm/migration, rollback ve release otomasyonunda.** Repo
  wheel/sdist veya platform paketi üretip doğrulayan, artifact yayımlayan ya da tag’den release
  oluşturan bir workflow içermiyor.
- **Connected/full-mode sürüm ayrıca kimlik doğrulama ve bridge operasyon sınırları nedeniyle
  hazır değil.** Mevcut bridge yerel loopback + paylaşımlı secret modeliyle belgelenmiş;
  README uzak bridge için ayrı güvenlik ve hosting politikasına ihtiyaç olduğunu açıkça söylüyor.
- **Kalite kapıları çalışıyor ama release kapısı eksik.** Repo içindeki hazır Python ortamında
  1.056 test geçti, 3 test skip edildi; UI build ve dört yerel E2E yolculuğu geçti. Temiz shell’de
  `make test` eksik bağımlılıklar yüzünden collection aşamasında durdu. UI build iki duplicate
  i18n key uyarısı verdi. CI Python/UI testlerini çalıştırıyor fakat artifact install-smoke,
  backend migration/test, platform matrisi ve otomatik production smoke içermiyor.

**Denetim sonucu:** Limited web panel, mevcut haliyle yayımlanabilir bir deploy yüzeyidir;
ancak versioned, yeniden kurulabilir ve geri alınabilir “ürün sürümü” olarak paketlenmesi için
aşağıdaki zorunlu boşlukların kapanması gerekir. Connected/full-mode, aynı 30 günlük release’e
dahil edilecekse bridge auth/ops maddeleri de zorunlu kapsam olur.

## Denetim sınırı ve release hedefleri

Bu analiz yalnızca repo içindeki kaynak, test, workflow ve belgeleri kullanır. Harici altyapı,
GitHub’daki güncel check durumu veya private ops vault doğrulanmamıştır. Enforcement, Trust veya
ADR tercihi yapılmamıştır.

| Kod | Release hedefi |
|---|---|
| R1 | Temiz makinede tekrarlanabilir kaynak kurulumu |
| R2 | Sürüm numaralı ve doğrulanmış dağıtım artifact’i |
| R3 | İlk açılışta anlaşılır limited/local deneyim |
| R4 | Kimliği doğrulanmış connected/full-mode deneyimi |
| R5 | Veri kaybetmeden güncelleme ve önceki sürüme dönüş |
| R6 | Üretim deploy, gözlem ve hata kurtarma operasyonu |
| R7 | CI ile kanıtlanmış kritik kullanıcı yolculukları |

Etki seviyeleri: **Kritik** release’i doğrudan durdurur; **Yüksek** desteklenebilir sürüm
iddiasını zayıflatır; **Orta** ilk sürümde kontrollü kapsam dışı bırakılabilir; **Düşük** kalite
ve bakım iyileştirmesidir. Karmaşıklık tahminleri göreli olup **Düşük / Orta / Yüksek**
ölçeğindedir.

## Kanıtlanan mevcut taban

| Alan | Sonuç | Kanıt |
|---|---|---|
| Python testleri | **PASS** — 1.056 passed, 3 skipped | Repo `.venv`, `PYTHONPATH` ve `KANDO_MOCK=1` ile `pytest -q` |
| Varsayılan `make test` | **FAIL** — collection’da `cryptography` ve `requests` yok | Sistem Python’ı; kurulum adımı uygulanmamış shell |
| UI production build | **PASS, 2 uyarı** | Astro build; TR/EN `readinessReport` duplicate key |
| UI static smoke | **PASS** | `ui/e2e/smoke-panel.mjs` |
| Local package journey | **PASS** | `ui/e2e/package-local.mjs` |
| Tasks API journey | **PASS** | `ui/e2e/package-api.mjs` |
| Confirmation API journey | **PASS** | `ui/e2e/confirmation-panel-api.mjs` |
| Offline/online tasks | **PASS** | `ui/e2e/tasks-offline-online.mjs` |
| Production smoke | Workflow var, **manuel** | `.github/workflows/prod-smoke.yml` yalnız `workflow_dispatch` |
| Backend release kapısı | **Yok** | CI’da backend install, Prisma schema/migration veya API smoke job’ı yok |
| Artifact yayınlama | **Yok** | Workflow’larda build artifact, tag release veya publish adımı yok |

## Bulgular

### Kurulum ve ilk çalıştırma tek bir ürün akışı oluşturmuyor

| ID | Eksik ve kanıt | Etki seviyesi | Kullanıcı etkisi | Tahmini çözüm karmaşıklığı | Engellediği release hedefi |
|---|---|---|---|---|---|
| GAP-01 | **Canonical release kapsamı yok.** README “early active development”, “packaged end-user installer yok” ve official release yayımlanmadı derken `LUMOS_V1_READINESS.md` web panel v1’i closed sayıyor. | Kritik | Kullanıcı hangi bileşenin desteklenen ürün olduğunu ve neyin çalışacağını bilemez. | Düşük | R1, R2, R3, R4 |
| GAP-02 | **Tek komutlu temiz kurulum yok.** UI, Python CLI, task server, bridge ve Express backend ayrı komut, env ve portlarla kuruluyor. README Quick Start yalnız UI’yı açıyor. | Kritik | Kullanıcı paneli açsa bile bağlı özellikleri çalıştırmak için birden fazla dokümanı elle birleştirmek zorunda kalır. | Orta | R1, R3, R4 |
| GAP-03 | **Temiz kurulum doğrulaması yok.** `make test` mevcut shell’de bağımlılıklar kurulmadığı için collection’da durdu; README Python ortamı ve `make install` akışını Quick Start’a bağlamıyor. | Yüksek | Yeni kurulumun bozuk mu eksik mi olduğu ayrıştırılamaz; destek yükü artar. | Düşük | R1, R7 |
| GAP-04 | **Root build tekrarlanabilir değil.** Kök `npm run build`, `ui` altında `npm install` çalıştırıyor; CI ise `npm ci` kullanıyor. | Yüksek | Aynı commit farklı zamanda farklı dependency çözümüyle build olabilir. | Düşük | R1, R2, R7 |
| GAP-05 | **İlk çalıştırma/onboarding orkestrasyonu yok.** `.env.example`, `ui/.env.example`, iki Python server ve opsiyonel backend kullanıcı tarafından elle hazırlanıyor. Port/secret/URL uyumu otomatik kontrol edilmiyor. | Kritik | İlk açılışta limited/full ayrımı, eksik servis ve yanlış env sorunları kullanıcıya kurulum hatası olarak döner. | Orta | R3, R4 |
| GAP-06 | **Kimlik/keystore hata mesajlarının işaret ettiği init komutları repoda yok.** `security/identity.py` `scripts/init_identity.py`, `security/keystore.py` ise `python -m src.scripts.init_keystore` öneriyor; `src/scripts/` altında bu dosyalar bulunmuyor. | Kritik | İlk kez identity/keystore yoluna giren kullanıcı belgelenen recovery adımını çalıştıramaz. | Orta | R3, R4, R6 |
| GAP-07 | **Desteklenen platform matrisi yok.** Python `>=3.10`, CI yalnız 3.12/Linux; UI Node `>=22.12`; macOS’a özel kamera probe’u var. Windows/macOS/Linux kurulum desteği tanımlı değil. | Yüksek | Paket bir platformda çalışırken diğerinde kurulum, izin veya path davranışı belirsiz kalır. | Orta | R1, R2, R7 |

### Paketleme, sürümleme ve dağıtım zinciri release üretmiyor

| ID | Eksik ve kanıt | Etki seviyesi | Kullanıcı etkisi | Tahmini çözüm karmaşıklığı | Engellediği release hedefi |
|---|---|---|---|---|---|
| GAP-08 | **Dağıtım artifact’i tanımlı değil.** Root Python paketi var; bridge/runtime ayrı pyproject’ler; UI statik dist; backend ayrı npm uygulaması. Bunları tek sürüm veya açıkça ayrı release artifact’leri olarak üreten tarif yok. | Kritik | Kullanıcı hangi dosyayı indireceğini ve hangi bileşenlerin birlikte uyumlu olduğunu bilemez. | Yüksek | R2 |
| GAP-09 | **Release workflow yok.** Git tag’den wheel/sdist/UI bundle üretme, artifact upload, checksum, provenance veya release notes adımı bulunmuyor. | Kritik | Sürüm yeniden üretilemez ve indirilen artifact’in kaynağı doğrulanamaz. | Orta | R2, R6 |
| GAP-10 | **Artifact install-smoke yok.** CI editable source + geniş `PYTHONPATH` kullanıyor; üretilmiş wheel’in temiz ortamda `lumos --version`/CLI import testi yok. | Kritik | Testler yeşil olsa bile yayımlanan pakette eksik modül veya dependency olabilir. | Orta | R1, R2, R7 |
| GAP-11 | **Sürüm kaynakları tam hizalı değil.** `pyproject.toml` ve `lumos_core.__version__` 0.1.0; `src/core/version.py` 0.0.0; UI 0.0.1; backend 1.0.0; bridge/runtime 0.1.0. Uyum matrisi yok. | Yüksek | Hata raporu ve rollback sırasında hangi bileşen kombinasyonunun çalıştığı belirlenemez. | Düşük | R2, R5, R6 |
| GAP-12 | **Release checklist bağlantısı kırık.** README `docs/GITHUB_RELEASE_CHECKLIST.md` dosyasına bağlanıyor fakat dosya yok. `README.tr.md` bağlantısı da kırık. | Yüksek | Release operatörü canonical kontrol listesini; Türkçe kullanıcı ise ana kurulum belgesini bulamaz. | Düşük | R1, R2, R6 |
| GAP-13 | **Changelog/release notes yüzeyi canonical değil.** Geliştirme günlüğü var; kullanıcıya dönük versioned değişiklik, breaking change ve migration notu akışı yok. | Orta | Kullanıcı güncellemenin etkisini ve geri dönüş ihtiyacını değerlendiremez. | Düşük | R5, R6 |

### Güncelleme ve hata kurtarma ürün seviyesinde tanımlı değil

| ID | Eksik ve kanıt | Etki seviyesi | Kullanıcı etkisi | Tahmini çözüm karmaşıklığı | Engellediği release hedefi |
|---|---|---|---|---|---|
| GAP-14 | **Güncelleme akışı yok.** Release channel, uyumluluk kontrolü, update komutu veya web deploy ile state/schema uyumluluğu sözleşmesi bulunmuyor. | Kritik | Kullanıcı yeni sürüme nasıl geçeceğini ve mevcut verisinin korunup korunmayacağını bilemez. | Yüksek | R5 |
| GAP-15 | **Kalıcı state migration planı yok.** `.lumos` altında tasks, trash, confirmation, outbox, identity, keystore ve log formatları var; genel schema inventory/version/migration runner yok. | Kritik | Yeni sürüm eski state’i okuyamazsa görev, onay veya kimlik verisi kaybı/bozulması yaşanabilir. | Yüksek | R5, R6 |
| GAP-16 | **Release rollback ve backup/restore prosedürü yok.** Kod içi patch/task restore mekanizmaları ürün sürümü rollback’i değildir; public ops belgeleri private vault’a işaret ediyor. | Kritik | Hatalı deploy veya migration sonrası önceki çalışan sürüme ve veriye güvenli dönüş yapılamaz. | Orta | R5, R6 |
| GAP-17 | **Kullanıcıya dönük recovery/doctor komutu yok.** Health parçaları ayrı endpoint ve modüllerde; env, port, state, bridge, backend ve package sürümlerini tek raporda toplayan tanı yok. | Yüksek | “Panel açılıyor ama çalışmıyor” durumunda kullanıcı ve destek ekibi nedeni hızlı ayıramaz. | Orta | R3, R4, R6 |

### Identity ve bridge yüzeyleri connected release için yeterli değil

| ID | Eksik ve kanıt | Etki seviyesi | Kullanıcı etkisi | Tahmini çözüm karmaşıklığı | Engellediği release hedefi |
|---|---|---|---|---|---|
| GAP-18 | **Ürün hesabı/session auth akışı yok.** Backend `POST /users` ile rating token üretir; bu login/logout/refresh/revoke hesabı değildir. Panelde ürün hesabı oturum yolculuğu bulunmuyor. | Kritik (connected release) | Kullanıcı kim adına bağlandığını, oturumu nasıl sonlandıracağını veya erişimi nasıl geri çekeceğini yönetemez. | Yüksek | R4 |
| GAP-19 | **Bridge auth yalnız yerel paylaşımlı secret modelinde doğrulanmış.** `kando_bridge` loopback kabul eder; README uzak bridge için ayrı security/hosting politikası gerektiğini söyler. `PUBLIC_KANDO_TOKEN` gerçek production secret olamaz. | Kritik (connected release) | Uzak/çok kullanıcılı bridge güvenli biçimde bağlanamaz; full-mode genel kullanıma açılamaz. | Yüksek | R4, R6 |
| GAP-20 | **Bridge lifecycle ve bağlantı kurtarma pakete bağlı değil.** Kullanıcı bridge, tasks server ve UI’yı ayrı başlatıyor; process supervision, restart, readiness dependency ve graceful shutdown sözleşmesi yok. | Yüksek | Servislerden biri düşerse panel sınırlı moda geçebilir ama bağlı işlem bütünlüğü ve otomatik toparlanma garanti edilmez. | Orta | R4, R6 |
| GAP-21 | **Full-mode kritik yolculuk CI’da gerçek deployment topolojisiyle doğrulanmıyor.** Local E2E task server kullanıyor; remote bridge auth, proxy, reconnect ve outbox sonucu tek uçtan uca testte birleşmiyor. | Kritik (connected release) | Bağlı modun en önemli vaadi release artifact’i üzerinde kanıtlanmaz. | Yüksek | R4, R7 |

### Backend, CI/CD ve kritik yolculuklarda release kapıları eksik

| ID | Eksik ve kanıt | Etki seviyesi | Kullanıcı etkisi | Tahmini çözüm karmaşıklığı | Engellediği release hedefi |
|---|---|---|---|---|---|
| GAP-22 | **Express/Prisma backend CI dışında.** `backend` install, Prisma generate/schema doğrulama, API smoke ve migration testi workflow’da yok. | Kritik (backend dahilse) | Backend değişikliği ana CI yeşilken production’da schema veya endpoint hatası verebilir. | Orta | R4, R6, R7 |
| GAP-23 | **Prisma migration geçmişi yok; setup `db push` kullanıyor.** `backend/prisma/schema.prisma` ve test DB var, ancak versioned migrations dizini görünmüyor. | Kritik (backend dahilse) | Mevcut kullanıcı verisiyle güvenli, geri alınabilir schema yükseltmesi yapılamaz. | Orta | R5, R6 |
| GAP-24 | **Production smoke manuel ve salt okunur.** Workflow yalnız `workflow_dispatch`; push/tag/deploy sonrası zorunlu değil ve connected write journey test etmiyor. | Yüksek | Deploy sonrası temel panel kırılması otomatik fark edilmeyebilir; connected yol hiç ölçülmez. | Düşük–Orta | R6, R7 |
| GAP-25 | **CI platform ve sürüm matrisi yok.** Tek Python 3.12/Ubuntu ve Node 22 kullanılıyor; package metadata Python `>=3.10` diyor. | Yüksek | Desteklendiği iddia edilen Python sürümlerindeki paket/import hataları release sonrası çıkar. | Orta | R1, R2, R7 |
| GAP-26 | **Build warning’leri kapı değil.** UI build, TR ve EN mesajlarında duplicate `readinessReport` key uyarısıyla geçiyor. | Yüksek | Önceki çeviri bloğu sessizce ezilir; kullanıcı metni beklenmeyen sürüme dönüşebilir. | Düşük | R3, R7 |
| GAP-27 | **Fresh-install/upgrade/recovery yolculukları test edilmiyor.** E2E mevcut checkout ve hazırlanmış dependency ortamından başlıyor; boş home/state, eski state migration, bozuk config ve rollback senaryoları yok. | Kritik | Release’in kurulabilir ve güncellenebilir olduğu testlerle kanıtlanmaz. | Yüksek | R1, R3, R5, R7 |
| GAP-28 | **Skipped test politikası görünür değil.** Son koşuda 3 test skip edildi; release kapısı allowed-skip listesi veya “unexpected skip” kontrolü içermiyor. | Orta | Kritik bir entegrasyon fark edilmeden skip’e dönebilir. | Düşük | R7 |

### Dokümantasyon birbiriyle ve mevcut canonical yüzeyle hizalı değil

| ID | Eksik ve kanıt | Etki seviyesi | Kullanıcı etkisi | Tahmini çözüm karmaşıklığı | Engellediği release hedefi |
|---|---|---|---|---|---|
| GAP-29 | **Canonical kullanım belgeleri parçalı.** README, backend README, panel README, bridge README ve local runbook farklı giriş noktalarını anlatıyor; tek desteklenen topoloji ve port/env tablosu yok. | Yüksek | Kullanıcı legacy/dev/production akışlarını karıştırabilir. | Orta | R1, R3, R4 |
| GAP-30 | **Stale dokümanlar aktif kanıtla çelişiyor.** `STABILIZASYON_LISTESI.md` `panel/index.html`i giriş olarak gösterirken güncel `panel/README.md` legacy panelin archive’a taşındığını ve üretimin `ui` olduğunu söylüyor. Backend checklist `/posts/feed` için 200 beklerken backend README endpoint’in 410 olduğunu söylüyor. | Yüksek | Yanlış smoke komutu veya yanlış yüzey release doğrulaması sanılabilir. | Düşük–Orta | R6, R7 |
| GAP-31 | **Support, katkı ve güvenlik raporlama belgeleri eksik.** README `CONTRIBUTING.md`in daha sonra ekleneceğini söylüyor; repo kökünde `SECURITY.md` ve support policy görünmüyor. | Orta | Kullanıcı sorun/güvenlik açığını nereye bildireceğini ve destek sınırını bilemez. | Düşük | R6 |

## Kritik kullanıcı yolculuğu kapsamı

| Yolculuk | Mevcut kanıt | Release boşluğu |
|---|---|---|
| Panel açılışı ve ilk paint | UI smoke PASS | Clean deploy sonrası otomatik prod gate değil |
| Limited mode yerel görev | Local/package/offline-online E2E PASS | Fresh browser/profile ve version upgrade state testi yok |
| Görev CRUD + confirmation | API ve confirmation E2E PASS | Release artifact’i ve eski state üzerinde çalışmıyor |
| Chat/bridge connected mode | Birim/entegrasyon testleri ve local runbook | Remote auth + proxy + reconnect + result E2E yok |
| Kimlik/keystore ilk kurulum | Modül testleri var | Kullanıcı komutu/scripti yok; first-run journey yok |
| Backend feed/rating | Kaynak ve manuel smoke scriptleri var | CI job, migration geçmişi ve production topology testi yok |
| Güncelleme | Kanıt yok | Version compatibility + state migration + rollback yok |
| Hata kurtarma | Bazı task restore ve presence recovery testleri var | Ürün düzeyi doctor, backup/restore ve release rollback yok |

## 30 günlük release kapısı

### Release öncesi zorunlu maddeler

Bu sınıflandırma, **limited web panel + versioned kaynak/CLI artifact’i** en küçük paketlenebilir
sürüm kabul edilerek yapılmıştır. Connected/full-mode release kapsamına alınırsa aşağıdaki koşullu
maddeler de zorunlu olur.

1. **Release kapsamını ve artifact setini sabitle:** GAP-01, GAP-08.
2. **Temiz ve tekrarlanabilir kurulum oluştur:** GAP-02, GAP-03, GAP-04, GAP-05, GAP-06.
3. **Versioned artifact üret ve temiz ortamda doğrula:** GAP-09, GAP-10, GAP-11.
4. **Canonical checklist ve temel belgeleri onar:** GAP-12, GAP-29, GAP-30.
5. **Güncelleme/state migration/rollback minimumunu tanımla ve test et:** GAP-14, GAP-15,
   GAP-16, GAP-27.
6. **Release CI kapılarını tamamla:** GAP-24, GAP-25, GAP-26; unexpected skip kontrolü
   GAP-28’in minimum release dilimidir.
7. **Desteklenen platformları açıkça sınırla:** GAP-07. Tek platform release seçilirse diğer
   platformlar açıkça unsupported olarak belgelenir.
8. **Connected/full-mode release kapsamındaysa zorunlu:** GAP-18, GAP-19, GAP-20, GAP-21.
9. **Express/Prisma backend release kapsamındaysa zorunlu:** GAP-22, GAP-23.

### Release sonrası ertelenebilir maddeler

Bu maddeler yalnız ilgili özellik release vaadinden açıkça çıkarıldığında ertelenebilir:

- GAP-13 — kapsamlı kullanıcı changelog otomasyonu; ilk release için manuel versioned notes yeterli olabilir.
- GAP-17 — birleşik `doctor` deneyiminin gelişmiş sürümü; release öncesinde minimum kurulum
  doğrulama komutu bulunması şartıyla.
- GAP-28 — gelişmiş skip bütçesi/raporlaması; release öncesinde unexpected skip’in görünür
  ve manuel onaylı olması şartıyla.
- GAP-31 — geniş katkı rehberi; fakat minimum güvenlik ve support iletişim yolu release
  öncesinde görünür olmalıdır.
- Connected mode kapsam dışıysa GAP-18–GAP-21.
- Express/Prisma backend kapsam dışıysa GAP-22–GAP-23.
- Native installer, service worker/offline-first, mobil native shell ve otomatik self-update;
  mevcut `LUMOS_V1_READINESS.md` bunları v1 dışında tanımlar. Release bu yetenekleri vaat etmemelidir.

## Açık sorular ve varsayımlar

- 30 günlük hedef yalnız hosted limited panel mi, yoksa CLI + bridge + backend içeren indirilebilir
  ürün mü? Bu seçim GAP-18–GAP-23’ün zorunluluk durumunu değiştirir.
- Artifact hedefi Python wheel, kaynak arşivi, container, desktop installer veya bunların bir
  kombinasyonu mu? Repo bugün bunlardan yalnız kaynak checkout ve UI static build’i doğrular.
- Private ops vault’ta deploy/rollback prosedürü bulunabilir; bu denetim repo dışına çıkmadığı
  için R6 kanıtı olarak kabul edilmemiştir.
- Harici production durumu ve GitHub Actions’ın güncel yeşil/kırmızı hali doğrulanmamıştır;
  rapor yalnız mevcut checkout’taki yerel test sonuçlarını ve workflow tanımlarını kullanır.

## Sonuç

Lumos’un limited web panel yüzeyi çalışır ve testlidir; 30 günlük release riski esas olarak
ürün fonksiyonundan değil **release mühendisliği ve operasyon sözleşmesinden** gelir. Mevcut repo,
deploy edilebilir UI üretir fakat kullanıcıya verilecek tekil, sürümlü, temiz kurulmuş, update
edilmiş ve geri alınabilir bir ürün artifact’ini henüz üretip kanıtlamaz.
