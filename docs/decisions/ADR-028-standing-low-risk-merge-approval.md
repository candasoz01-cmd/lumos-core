# ADR-028 — Sınırlı standing merge onayı (düşük risk)

> 2026-08-20 kurucu kararı: her docs PR’ında insan bekleten kapı sürtünme
> üretiyor. Düşük riskli işler kapıları geçince yürür; yüksek riskte insan
> kapısı kalır. **Bu ADR kod yazma izni değildir.** CI / Security Reviewer /
> Bugbot gevşetilmez. `#764` (üçlü kapı / kontrollü writer) bu onaya
> **girmez**.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-20)** — kurucu; chat kararı |
| Uygulama durumu | Yürürlükte — ajan, aşağıdaki sınıf + kapı koşulu sağlanınca `main`'e merge edebilir |
| Tarih | 2026-08-20 |
| Üst ilişki | [CONSTITUTION](../CONSTITUTION.md) §2 (en yeni açık kullanıcı kararı); açık PR `#764` (ADR-027 / §11) henüz `main`'de değil — bu ADR onu ezmez |

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

Bu ADR’nin kendisi merge-kuralı kaydıdır; **hariç sınıfa** girer. Kaydı
`main`'e indiren merge, 2026-08-20 kurucu metninin kendisidir — sonraki
revizyonlar yine açık insan onayı ister.

`candasoz01-cmd/lumos-core#764` governance’dır; standing onaya **girmez**.

### Kapı (güncel head SHA)

Head değişince sayaç sıfırlanır. Merge yalnız **o anki head SHA** için:

1. Gerekli CI yeşil (`ci.yml`: `test`, `rust`, `macos-app-build`, `ui-smoke`, `ui-e2e`)
2. `Cursor Security Agent: Security Reviewer` complete + SUCCESS (queued / in_progress / missing = pending)
3. `Cursor Bugbot` complete + SUCCESS
4. Unresolved review thread yok
5. Merge conflict yok (`MERGEABLE` + çakışmasız)

Hepsi yoksa merge yok. Standing onay kapıları atlatmaz.

## Örnek

`#766` (TD-13 park kaydı, docs-only): kayıt düzeltilip yeni head’de kapılar
yeniden yeşile dönerse ajan ayrıca beklemeden merge edebilir.
