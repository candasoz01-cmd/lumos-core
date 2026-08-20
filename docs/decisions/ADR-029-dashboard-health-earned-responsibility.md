# ADR-029 — Dashboard Health: ilk earned responsibility alanı

> 2026-08-20 kurucu kararı: kod yok. Dashboard Health bir vitrin ekranı
> değil; bir alan sahibinin **davranış sözleşmesidir**. Yetki sınırı
> ([ADR-028](ADR-028-standing-low-risk-merge-approval.md)) ile alan
> sorumluluğu ancak birlikte kontrollü özerklik olur. **Bu ADR kod yazma
> izni değildir.** State sözleşmesi, uygulama, canlı kanıt ve alan devri
> ayrı adımlardır; otomatik açılmaz.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (sorumluluk, 2026-08-20)** — üç cümle + meta-kural kilitli |
| Uygulama durumu | `bridge.llm → Observe` **granted** (2026-08-20). Kayıt: [`src/dashboard_health/responsibility.json`](../../src/dashboard_health/responsibility.json). Fix / Escalate / alan sahipliği **kapalı** |
| Tarih | 2026-08-20 |
| Üst ilişki | [ADR-028](ADR-028-standing-low-risk-merge-approval.md) (yetki sınırı); [CONSTITUTION](../CONSTITUTION.md) §2 / §9; TD-13 park (eski CSS/hero bu sözleşme **değil**) |
| STOP LIST | Yeni sayfa / yeni özellik yok. Vitrin/UI bu merdivenin en sonunda |

## Çekirdek üç cümle

1. **İzler:** Lumos, tanımlı dashboard alanlarının canlı durumunu ve
   freshness bilgisini doğrulanabilir kaynaklardan izler; ölçmediği şeyi
   sağlıklı varsaymaz.
2. **Düzeltir:** Sorun açıkça tanımlanmış, geri alınabilir ve kendisine
   devredilmiş düşük-risk yetki sınırı içindeyse düzeltmeyi uygular,
   doğrular ve kanıtını kaydeder.
3. **Yükseltir:** Durum belirsizse veya çözüm
   security/privacy/permission/governance/prod/core sınırına dokunuyorsa
   kendi yetkisini genişletmez; işlemi durdurur ve yetkili insana yükseltir.

## Meta-kural

**Lumos bir alanın sorumluluğunu üstlenebilir; o alanı yönetmek için kendi
yetki sınırını değiştiremez.**

Dashboard kart rengi, layout veya `id="canli-durum"` bağlama bu ADR’nin
konusu değildir. Eski `lumos-platform.css` / `LumosPlatformHero.astro`
kurtarması (TD-13, park) bu alanın uygulaması sayılmaz ve bağlanmaz.

## Merdiven (sıra bağlayıcı)

```text
sorumluluk (bu ADR)
  → state sözleşmesi
  → uygulama
  → canlı kanıt
  → en son: alanı Lumos’a devretme
```

Vitrin/UI bunun çok daha sonrasında. Bir basamak atlanırsa alan
**devredilmiş sayılmaz.**

## Mikro-sorumluluk kaydı (yeni ADR değil)

Kurucu grant (2026-08-20), makine-okunur dosya:

[`src/dashboard_health/responsibility.json`](../../src/dashboard_health/responsibility.json)

`action_class=Observe` · `data_scope=bridge.llm` · `delegable=false`.
Fix / Remediate / runtime escalation / diğer kartlar / yetki genişletme
**denied**. Bu kayıt Dashboard Health sahipliği **değildir**.

## Kazanılmış sorumluluk, miras yok

Dashboard Health, bu merdiven tamamlanınca Lumos’un ilk gerçek **earned
responsibility** alanı olur. Aynı kalıp sonra başka alanlara taşınabilir;
her yeni alan **ayrıca kazanılır**, otomatik miras alınmaz.

## Fail-closed

Belirsiz durum = yükselt. Ölçülmeyen = sağlıklı değil. Düzeltme yetkisi
ADR-028 düşük-risk sınıfını (ve ileride bu alana özel açık devri)
aşamaz. Yetki sınırını bu alanı “yönetmek için” genişletmek yasaktır.

`candasoz01-cmd/lumos-core#764` (kontrollü writer / üçlü kapı) bu ADR’den
uygulanmaz ve bu PR’da dokunulmaz.
