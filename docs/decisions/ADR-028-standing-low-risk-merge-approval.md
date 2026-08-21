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
   dosyalar). CheckRun adı: `standing-class`. Hariç veya boş diff → fail.
   PR gövdesindeki “standing hattı yok” cümlesi kanıt değil; yol listesi
   esastır. `#777` fixture: `docs/contracts/` → excluded.
1. Gerekli CI yeşil (`ci.yml`: `test`, `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`)
2. `Cursor Security Agent: Security Reviewer` complete + SUCCESS (queued / in_progress / missing = pending)
3. `Cursor Bugbot` complete + SUCCESS
4. Unresolved review thread yok
5. Merge conflict yok (`MERGEABLE` + çakışmasız)

Hepsi yoksa merge yok. Standing onay kapıları atlatmaz. `standing-class`
fail insan merge yasağı değildir; standing merge yasağıdır.

Olgu/norm ikinci filtresi (başka ADR’lerde “ne doğrudur?”) **otomatik
değildir**; yalnız hariç liste makine-okunur.

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
otorite onayı. Kapı 0 bu deliği ajan sözleşmesinde kapatır; GitHub
`required_status_checks` boşluğu Settings/admin işidir ve bu ADR onu
açmaz.
