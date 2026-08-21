# ADR-028 — Sınırlı standing merge onayı (düşük risk)

> 2026-08-20 kurucu kararı: her docs PR’ında insan bekleten kapı sürtünme
> üretiyor. Düşük riskli işler kapıları geçince yürür; yüksek riskte insan
> kapısı kalır. Writer / otomasyon borusu bu ADR’den **uygulanmaz**. CI /
> Security Reviewer / Bugbot gevşetilmez. `#764` (üçlü kapı / kontrollü
> writer) bu onaya **girmez**. 2026-08-21 kurucu kararı: hariç sınıf merge
> öncesi `python -m standing_merge.classify` ile zorunludur ([TD-20](../TECHNICAL_DEBT.md));
> bu, writer izni değildir.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-20)** — kurucu; chat kararı |
| Uygulama durumu | Yürürlükte — **sınıf önce**. Classifier hariç/belirsiz ise standing merge yok. Kapılar yeşil olsa bile otorite onayı ayrıdır ([TD-20](../TECHNICAL_DEBT.md) / `#777`) |
| Tarih | 2026-08-20; sınıf kapısı 2026-08-21 |
| Üst ilişki | [CONSTITUTION](../CONSTITUTION.md) §2 / §11; [ADR-027](ADR-027-controlled-core-writer.md) (`#764` · MERGED · 2026-08-21T07:19:13Z) — bu ADR onu ezmez |

## Karar

Bundan sonra ajan, **ayrıca “merge edilsin mi?” diye sormadan** merge
edebilir; yalnız **sınıf** ve **kapı** birlikte tutulursa.

### Sınıf (dahil)

- docs-only
- teknik borç kaydı (`docs/TECHNICAL_DEBT.md` satır düzeltmesi dahil)
- mekanik ve prod davranışını değiştirmeyen değişiklikler

### Sınıf (hariç — açık insan onayı gerekir)

- security / policy / governance
- permissions
- secrets / credentials
- prod / deploy davranışı
- veri sınırı / mahremiyet
- ödeme / finans
- controlled-writer / merge kuralları
- çekirdek sözleşmeler (`docs/contracts/`, anayasa, ADR-027 kapsamı)

Sınıf belirsizse **hariç** sayılır (fail-closed).

### Sınıflandırma ölçütü (2026-08-21)

Bir dosyanın ADR olması tek başına standing onay dışında bırakmaz. Mevcut olguyu
düzelten ve yeni normatif karar, yetki, güvenlik sınırı veya çalışma davranışı
üretmeyen ADR düzeltmeleri düşük-risk sınıfına girebilir.

Ayırt edici soru:

| Değişiklik neyi güncelliyor | Sınıf |
|-----------------------------|-------|
| **"Ne doğrudur?"** — mevcut gerçeği kayda geçirir, bayat olguyu düzeltir | Standing'e **uygun olabilir** |
| **"Bundan sonra neye izin verilir?"** — kural, yetki, sınır veya davranış tanımlar | **Açık insan onayı gerekir** |

Belirsizlikte hariç sayılır.

**Bu ölçüt ikinci filtredir, birincinin yerine geçmez.** Yukarıdaki *Sınıf (hariç)*
listesi — security, policy, governance, permissions, secrets, veri sınırı/mahremiyet,
prod/deploy, finans, merge kuralları, çekirdek sözleşmeler ve ADR-027 kapsamı — bir
değişiklik salt olgu düzeltmesi görünse **bile** her durumda açık insan onayı ister.
Önce hariç listesi uygulanır; ancak liste dışındaysa bu ölçüte bakılır.

Bu ADR’nin kendisi merge-kuralı kaydıdır; **hariç sınıfa** girer. Kaydı
`main`'e indiren merge, 2026-08-20 kurucu metninin kendisidir — sonraki
revizyonlar yine açık insan onayı ister.

`candasoz01-cmd/lumos-core#764` governance’dır; standing onaya **girmez**.

### Kapı (güncel head SHA)

Head değişince sayaç sıfırlanır. **Sınıf, kapılardan önce gelir.** Hariç
sınıfta standing merge yoktur; aşağıdaki 1–5 yeşil olsa bile açık insan
onayı gerekir. Checks yeşili otorite onayının yerine geçmez.

Merge yalnız **o anki head SHA** için:

0. Sınıf **eligible** — `python -m standing_merge.classify` (değişen
   dosyalar). CheckRun adı: `standing-class`. **Üç durum vardır:**
   `excluded` (standing kesinlikle yasak) · `semantic_review` (yol tek başına
   karar vermeye yetmez; olgu/norm değerlendirmesi **o anki head SHA için**
   insan tarafından yapılır, otomatik standing yetkisi doğmaz) · `eligible`
   (yalnız dar ve açıkça makinece güvenli sınıf). Yalnız `eligible` standing
   hattını açar; `semantic_review` ve `excluded` açmaz. CLI çıkış kodu:
   0 / 3 / 2. `docs/decisions/**` varsayılan olarak **semantic_review**'dır —
   komple hariç yapılmadı, çünkü ADR'de salt olgu düzeltmesi (bkz.
   §Sınıflandırma ölçütü) standing'e girebilmelidir; ayrımı yol değil semantik
   değerlendirme yapar. Genel `docs/` allowlist'i **kaldırıldı**: isim
   listesinden kaçan yeni bir governance veya veri sınırı belgesi eligible olamaz.

   **`semantic_review` kalıcı yasak değildir; karar verilmemiş durumdur.**
   Yol sinyali yetmediğinde olgu/norm değerlendirmesi yapılır ve sonuç
   **o anki head SHA'ya bağlı bir attestation** olarak taşınır:

   ```
   python -m standing_merge.classify <paths> \
       --head-sha <head> --attest factual|normative --attest-sha <head>
   ```

   | Attestation | Sonuç |
   |-------------|-------|
   | `factual` (SHA eşleşir) | `eligible` — standing hattı açılır |
   | `normative` | `excluded` — açık insan onayı gerekir |
   | yok, bayat SHA, veya tanınmayan değer | `semantic_review` kalır (fail-closed) |

   Attestation **hard-exclusion'ı terfi ettiremez**: ADR-029 ne söylenirse
   söylensin `excluded` kalır; listelenmeyen yol da öyle. Attestation head
   SHA'ya bağlıdır ve sonraki head'e **taşınmaz** — ADR-027'nin SHA kuralıyla
   aynı ilke.

   `standing-class` CheckRun'ı attestation'sız çalışır; yalnız **yol sınıfını**
   raporlar. Kırmızı + `excluded` = standing yasak. Kırmızı + `semantic_review`
   = standing için önce attestation gerekir.

   **Güven kökü (2026-08-21, Security Reviewer HIGH):** Bir PR'ı sınıflandıran
   kod o PR'dan gelemez. `standing-class`, classifier'ı ve kural dosyasını
   PR'ın **sabit `base.sha`** commit'inden ayrı bir dizine çıkarıp oradan
   çalıştırır; PR ağacındaki `src/standing_merge/**` kendi sınıfını
   belirleyemez. Base commit'te classifier yoksa **fail-closed FAILURE** verilir
   ve PR sürümüne **fallback yapılmaz**. `main` canlı okunmaz — kontrol
   çalıştıktan sonra `main` değişebilir, `base.sha` değişmez.

   > Bootstrap istisnası: classifier'ı ilk getiren PR'ın kendi `standing-class`
   > kontrolü bu nedenle kırmızı kalır. Kabul edilir; o PR zaten governance
   > sınıfındadır ve açık insan onayıyla geçer.

   **Yol taşıma:** değişen yollar NUL-delimited alınır (`git diff --name-only -z`)
   ve classifier'a `--` option terminator'ından sonra geçilir. Ek olarak `-` ile
   başlayan her yol fail-closed `excluded` sayılır. Gerekçe: Git dosya adları
   `--help` veya `--attest=factual` olabilir ve newline içerebilir; bunlar
   argparse'a bayrak gibi geçerse sahte yeşil üretir. Hariç kuralı (önek, dosya,
   yol jetonu: security/privacy/permission/secret/credential/payment/deploy/
   governance/policy/vault/…) **veya listelenmeyen yol** veya boş diff →
   fail (fail-closed). `eligible` yalnız allowlist önekine düşen ve hariç
   kuralına çarpmayan yollar içindir (`docs/`, `tests/`). Eşleşme yoksa
   `eligible` **yoktur**. PR gövdesindeki “standing hattı yok” cümlesi
   kanıt değil; yol listesi esastır. `#777` fixture: `docs/contracts/` →
   excluded. `src/security/` → excluded. `src/policy/` → excluded.
   `docs/` altındaki security/privacy/permission adlı dosya → excluded.
   `standing-class` kırmızısını GitHub `required_status_checks` listesine
   koymayın — o, insan onaylı hariç PR’ı da fiziksel bloke eder; fiziksel
   kilit ayrı `merge-authority` modeli ister.
1. Gerekli CI yeşil (`ci.yml`: `test`, `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`)
2. `Cursor Security Agent: Security Reviewer` complete + SUCCESS (queued / in_progress / missing = pending)
3. `Cursor Bugbot` complete + SUCCESS
4. Unresolved review thread yok
5. Merge conflict yok (`MERGEABLE` + çakışmasız)

Hepsi yoksa merge yok. Standing onay kapıları atlatmaz. `standing-class`
fail insan merge yasağı değildir; standing merge yasağıdır.

Olgu/norm ikinci filtresi (başka ADR’lerde “ne doğrudur?”) **otomatik
değildir** ve classifier `eligible` dedikten sonra ajan değerlendirmesidir.
Hariç liste birinci hard-exclusion’dır; `src/security/` gibi yollar ikinci
filtreye düşmez. Allowlist dışındaki yol `eligible` değildir. `docs/`
altında olsa bile security/policy/governance jetonu taşıyan yol hariçtir.
Olgu/norm, classifier `eligible` dedikten sonra ajan işidir.

## Örnek

`#766` (TD-13 park kaydı, docs-only): kayıt düzeltilip yeni head’de kapılar
yeniden yeşile dönerse ajan ayrıca beklemeden merge edebilir.

### Ölçütün uygulandığı iki gerçek vaka (2026-08-21)

| PR | İçerik | Sınıf | Neden |
|----|--------|-------|-------|
| `#785` | ADR-009 adres tablosu: hipotez → doğrulanmış durum | **Standing'e girdi** | *"Ne doğrudur?"* — bayat olguyu düzeltti, yeni kural veya yetki üretmedi, belgenin Taslak statüsü değişmedi |
| `#784` | ADR-023'e temsil yetki sınırı bölümü | **Girmedi — açık onay alındı** | *"Bundan sonra neye izin verilir?"* — bir yetki sınırını normatifleştirdi; hariç listesindeki governance/permissions kapsamına da girer |

İkisi de ADR dosyasıydı; sınıfı belirleyen dosya türü değil, **değişikliğin ne
yaptığıydı**.

### Kontrol olayı — `#777` (2026-08-20)

Canonical kayıt: [TD-20](../TECHNICAL_DEBT.md).

`candasoz01-cmd/lumos-core#777` standing-excluded sınıftaydı (çekirdek
sözleşme `docs/contracts/dashboard-health-v1.md`; PR gövdesi ve sözleşmenin
kendi merge satırı insan onayı istiyordu). Teknik kapılar `c50127b6`
üzerinde yeşildi. `cursor[bot]` açık insan merge onayı olmadan
2026-08-20T14:32:29Z merge etti (`339840f2`).

İçerik geri alınmaz. İhlal **yetki/prosedür**: eksik olan check değil,
otorite onayı. Kapı 0 bu deliği ajan sözleşmesinde kapatır. GitHub
`required_status_checks` boşluğu Settings/admin işidir; **`standing-class`
o listeye konmaz** — kırmızı standing yasağıdır, insan merge yasağı değil.
Fiziksel kilit ayrı `merge-authority` modeli ister.
