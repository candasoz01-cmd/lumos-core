<!-- markdownlint-disable MD013 -->

# ADR-036 — AI inceleme kanıt kapısı (tek kurucu modeli)

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted — hedef mimari (2026-11-09)**; kurucu kararı (chat, birinci el): A + B + C hedef mimari olarak kabul. **Ayar değişikliği onayı yok** |
| Uygulama durumu | Aşama 0: doğrulayıcı + workflow + policy + testler bu dalda. `main`'de yok; required check değil; GitHub ayarı değişmedi |
| Tarih | 2026-11-09 |
| Kapsam muhasebesi | KARAR + KOD. CANLI yok |
| Üst ilişki | [CONSTITUTION §11](../CONSTITUTION.md) · [ADR-027](ADR-027-controlled-core-writer.md) · [ADR-028](ADR-028-standing-low-risk-merge-approval.md) · ADR-035 merge-authority (`candasoz01-cmd/lumos-core#893`, açık) |
| Board claim | `AI-REVIEW-GATE-PRG-20261109` (`4db5e77f`) |

## 1. Sorun

Depoda bağımsız insan inceleyici yok. GitHub'ın "1 onay" kuralı tek
hesaplı depoda kimsenin karşılayamayacağı bir şart. İnsan onayının yerine
konacak kanıt; SHA'ya bağlı, doğrulanabilir ve birden fazla sağlayıcıdan
gelmeli. Ama insan onayı gibi gösterilmemeli.

## 2. Karar

- **Kanıt kaynağı yalnız GitHub App kimliğidir.** Cursor: `cursor` App'inin
  `Cursor Security Agent: Security Reviewer` CheckRun'ı (`head_sha` alanı).
  Codex: `chatgpt-codex-connector[bot]` (`type: Bot`,
  `performed_via_github_app.slug = chatgpt-codex-connector`) yorumundaki
  `codex-review-state:v1` bloğunun `code_review.commit_sha` alanı.
  Kullanıcı yorumu, işaretleyici metni veya yazar adı kanıt değildir.
- **Tam SHA eşitliği.** Kanıt yalnız 40 hex head SHA'ya eşitse sayılır.
  Head değişince sayaç sıfırlanır.
- **En az iki farklı sağlayıcı.** Aynı sağlayıcının ikinci kaydı sayılmaz.
- **Kritik yollar daha sıkı** (`.github/`, `src/lumos_board/`,
  `src/standing_merge/`, yayın kapısı, claim guard, policy dosyası,
  anayasa/AGENTS/CONTRIBUTING): bütün sağlayıcılar, Codex'te hiç bulgu yok,
  head'de Cursor review kaydı, head'de AI inline bulgusu yok. Yol listesi
  boşsa veya yol `-`/`..` içeriyorsa kritik sayılır.
- **Güven kökü base SHA'dır.** Workflow ve doğrulayıcı
  `pull_request_target` ile base'den koşar; PR ağacı checkout edilmez.
  Kapıyı tanıtan PR kendini kanıtlayamaz (bootstrap).
- **SKIPPED yok.** İşte `if` yoktur; draft PR'da da koşar ve bekler/düşer.
  SKIPPED sonucu required check'i karşılar; bu yüzden yasak.
- **AI kanıtı insan onayı değildir; kurucu merge yetkisi de değildir.**
  Kurucu yetkisinin kanıtı ADR-035'teki SSH imzalı
  `repo + pr + head_sha + action` yüküdür. GitHub Environment onayı kurucu
  kanıtı olarak kullanılmaz: ajanlar kurucunun GitHub oturumunda
  çalışabilir (ADR-035 §1), dolayısıyla hesap tabanlı onay "kurucu yaptı"
  ile "ajan kurucu oturumunda yaptı"yı ayırmaz.

## 3. Bilinen sınırlar (gizlenmez)

1. **Ad tabanlı required check fiziksel kilit değildir** (ADR-035 §4). Bu
   işin CheckRun'ını GitHub Actions üretir. Başka bir base dalına açılan
   PR, aynı head SHA için değiştirilmiş workflow kopyasıyla aynı adlı
   "başarılı" sonuç üretebilir. Bu sınır mevcut 10 zorunlu kontrolün
   hepsinde vardır. Fiziksel kilit için kaynağı sabitlenmiş ayrı App
   gerekir (ADR-035 §4).
2. **Codex başarı değeri doğrulanmadı.** Depodaki tüm Codex kayıtları
   `status: failed` (kullanım limiti, `#945`/`#946`, 2026-10-16). Policy
   `pass_status: []` ile gelir; Codex canlı bir başarılı kayıtla değer
   doğrulanana kadar geçemez (kapı kapalı kalır).
3. **AI incelemesi kurucudan bağımsız değildir.** App'leri, istemleri ve
   policy'yi kurucu yönetir. Modeller aynı açığı birlikte kaçırabilir.
   PR içeriği prompt injection taşıyabilir.
4. **Erişilebilirlik.** Sağlayıcı limiti/kesintisi kritik PR'ları bekletir.
   Bypass yoktur.
5. **İnsan onay şartının kaldırılması** (hedef mimari B) GitHub'daki ikinci
   göz kaydını kaldırır. Bu ADR o ayarı değiştirmez; ayrı kurucu onayı ister.

## 4. Bilinçli yapılmaz

- Branch protection, ruleset, Environment veya required check değişikliği.
- Kurucu onay taşıyıcısı (ADR-035 kapsamı, `#893`).
- `docs/TECHNICAL_DEBT.md` güncellemesi: dosya açık `#961` kapsamında;
  kayıt o PR'dan sonra ayrı yapılır.
