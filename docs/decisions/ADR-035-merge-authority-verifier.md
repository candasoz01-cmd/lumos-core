<!-- markdownlint-disable MD013 -->

# ADR-035 — Merge-authority doğrulayıcısı (TD-20)

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-09-26)** — kurucu kararı (chat, birinci el): A (imza yükü ve kapsam), B (yalnız doğrulayıcı dilimi); C (required check) **yasak** |
| Uygulama durumu | Doğrulayıcı çekirdeği + boş güven kökü + testler. **Taşıyıcı, workflow ve GitHub zorlaması yok** |
| Tarih | 2026-09-26 |
| Kapsam muhasebesi | KARAR + KOD (çekirdek). CANLI yok: hiçbir merge'ü açmaz veya kapatmaz |
| Tetikleyen | [TD-20](../TECHNICAL_DEBT.md) — fiziksel kilit ayrı `merge-authority` modeli ister ([ADR-028](ADR-028-standing-low-risk-merge-approval.md) §194, §240) |
| Üst ilişki | [CONSTITUTION §11](../CONSTITUTION.md) · [ADR-027](ADR-027-controlled-core-writer.md) · [`lumos-wall-v1`](../contracts/lumos-wall-v1.md) § Onay şeması v1 · [`PUBLICATION_GATE.md`](../PUBLICATION_GATE.md) |
| Board claim | `TD-20-MERGE-AUTHORITY-VERIFIER` (`637505f1`) |

## 1. Sorun

Ajanlar kurucunun GitHub kimliğiyle çalışır. GitHub bu yüzden «kurucu
yaptı» ile «ajan kurucunun kimliğiyle yaptı» ayrımını fiziksel olarak
zorlayamaz. `founder_approval` mantıksal kaydı tutar ama merge'ü kilitlemez;
`#777` ve `#886` bot eliyle, görünür insan onayı olmadan merge edilebildi.
İkinci insan hesabı bu sorunu çözmez: sözleşme tek nihai yetkili tanımlar
ve hesap sayısı kimlik ayrımını değiştirmez.

## 2. Karar

**Güven kökü hesap değil, anahtardır.** Merge yetkisinin kanıtı, yalnız
insan etkileşimiyle kullanılabilen ve ajanların erişemediği bir
merge-authority anahtarının SSH imzasıdır. Hesap, yorum veya servis
yalnız taşıyıcıdır.

İmzalı yük tam kapsama bağlıdır ve doğrulayıcı onu güvenilir PR
kimliğinden **yeniden kurar**; zarf içindeki değerlerden almaz:

```text
lumos.merge_authority.v1
repo=<owner/repo>
pr=<numara>
head_sha=<40 hex>
action=merge
```

Head SHA değişirse onay geçersizdir. Başka PR, repo, SHA veya eylem için
atılmış imza bu kapsamda geçmez. Namespace `lumos-merge-authority`'dir;
yayın imzası (`lumos-publication`) merge yetkisi yerine geçmez.

Güven kökü `config/merge_authority/allowed_signers`'dır; yayın kökünden
ayrıdır ve **boş başlar**. İki yetki aynı insan-kapılı altyapıdan
yararlanabilir ama ayrı kök, ayrı namespace olarak kalır. Ajan erişimine
açık bulunan genel amaçlı GitHub anahtarı (2026-09-18 iptali) burada da
kök olamaz.

### Lumos entegrasyon ilkesi (kurucu, 2026-09-26)

> **Lumos başka sistemlere bağlanır; güven kökünü bağlandığı sisteme bırakmaz.**

Model: platform güvenliği + Lumos'un kendi güven zinciri. Biri diğerinin
yerine geçmez. Merkezde insan-kapılı yetki durur; uçlarda dar ve
deterministik doğrulayıcılar çalışır. Doğrulayıcı karar vermez,
yorumlamaz, yetki üretmez. Yalnız şunu sorar: «bu imza doğru mu ve tam
olarak bu işlem için mi?» Özel yetki anahtarı Lumos'un güvenilir
sınırından çıkmaz. Dış servis hesabı ele geçirilse bile tek başına kurucu
onayı üretememesi hedeftir. Her entegrasyonda yeni bir güven sistemi
icat edilmez.

## 3. Uygulanan dilim (B)

- `src/merge_authority/verify.py` — taşıyıcıdan bağımsız çekirdek: kapsam
  doğrulama, zarf ayrıştırma, `ssh-keygen -Y verify`, güven kökü denetimi.
  Fail-closed: kök yok / boş / çözülemeyen satır / iptal edilmiş anahtar /
  `ssh-keygen` yok / bozuk zarf → `authorized: false`. CLI: 0 yetkili,
  2 değil.
- `config/merge_authority/allowed_signers` — boş, kapalı varsayılan.
- `tests/test_merge_authority.py` — gerçek anahtar ve imzayla her ret
  yolu.

Zarf, düz metin bir blokdur (`lumos-merge-authority-v1`, `principal`,
dört kapsam alanı, SSH imzası). Hangi kanaldan geldiği çekirdeği
ilgilendirmez.

## 4. Açık: taşıyıcı ve GitHub zorlaması (C öncesi karar)

A maddesi, taşıyıcıyı PR yorumu olarak **dondurmadı**. Kurucu yönü:
Lumos cihazdaki imzayı kendisi taşır; GitHub tarafında dar yetkili bir
doğrulayıcı sonucu üretir (GitHub App / Check Run). Değerlendirme:

- **Workflow ile yayımlanan status/check adı sahtelenebilir.**
  `pull_request_target` workflow tanımını PR'ın *base* dalından çalıştırır.
  Ajan başka bir dal açıp oradaki workflow kopyasını değiştirebilir,
  aynı commit için o dala PR açabilir ve aynı adla «başarılı» sonucu
  yazabilir. Commit status'ları PR'a değil SHA'ya bağlıdır. Yalnız ad
  eşleşmesine dayanan bir required check bu yüzden fiziksel kilit değildir.
- **Kaynağı sabitlenmiş check bu açığı kapatır.** Kendi özel anahtarıyla
  çalışan ayrı bir GitHub App'in check run'ı, required check'te o App'e
  sabitlenirse, workflow'lar ve kurucu hesabıyla çalışan ajanlar aynı
  kaynaktan sonuç yazamaz. Bu, kurucu yönüyle örtüşür ve yolu kısaltır:
  yorum bulma ve ayrıştırma adımları kalkar.
- **Kalan sınır dürüstçe:** App'in platform anahtarı ele geçirilirse
  sahte «geçti» sonucu yazılabilir. Bu, *kilidi* bozar, *onayı* üretmez:
  kurucu imzası yine sahtelenemez. Zarflar doğrulanabilir kanıt olarak
  kaldığı için her merge sonradan aynı çekirdekle denetlenebilir; geçerli
  zarfı olmayan merge tespit edilir (gözetim katmanı).
- **Barındırma:** App servisi operasyonel altyapıdır; bu public repoya
  girmez (CONTRIBUTING § Public repository boundary). Çekirdek burada
  kalır ve servis aynı çekirdeği kullanır.

## 5. Bilinçli yapılmaz

- Anahtar üretimi veya `allowed_signers` kaydı (kurucu).
- Branch protection / ruleset / required check değişikliği (C, yasak).
- Taşıyıcı adaptörü, workflow veya GitHub App (karar §4 bekliyor).
- `founder_approval` deposuna veya Observer'a bağlantı; onay kaydı
  üretimi.
- `docs/TECHNICAL_DEBT.md` TD-20 satırının güncellenmesi. Dosya şu an
  açık `#892`'nin kapsamında; güncelleme o PR'dan sonra ayrı yapılır.
