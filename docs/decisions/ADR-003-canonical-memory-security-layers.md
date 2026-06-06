# ADR-003: Canonical Memory ve Trust/Security Katmanları (Taslak Karar)

| Alan | Değer |
|------|-------|
| Durum | **Kabul edilmiş taslak / belgelenmiş karar** — gelecek import-audit ile doğrulanacak |
| Tarih | 2026-06-06 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, ADR-001, ADR-002 |

## Amaç

Lumos kod tabanında **bellek (memory)** ve **güven / politika (trust/security)** katmanlarının hangi dizinlerin **canonical** (tek doğru kaynak) olduğunu repo analizine dayalı olarak kayıt altına almak. Bu belge **yalnızca dokümantasyondur**; bu turda kod taşıma, import değişikliği veya paket silme **kapsam dışıdır**.

## Bağlam

Lumos çekirdeğinde güvenlik, yetki ve workspace sözleşmesi önceliklidir. Repo içinde hem `src/` altında çalışan katmanlar hem de `packages/` altında aynı veya benzer sorumlulukları taşıyan paketler bir arada bulunmaktadır. Haziran 2026 repo taraması, aktif çalışma yolunun büyük ölçüde `src/` katmanlarına dayandığını; bazı `packages/` altı paketlerin ise **ayna (mirror)** niteliğinde kaldığını ve **drift riski** taşıdığını göstermektedir.

Bu ADR'deki ifadeler **repo analiz bulgusudur**; kesin mimari hüküm veya tamamlanmış konsolidasyon kararı olarak sunulmamalıdır.

## Analiz bulguları (Haziran 2026)

### Canonical bellek katmanı: `src/memory`

Aktif import taramasında çalışan kod yolu `memory.*` modüllerini **`src/memory`** üzerinden kullanmaktadır. Örnek tüketiciler (analiz bulgusu, eksiksiz liste değildir):

- `src/core/lumos.py`, `src/core/lumos_runtime.py`
- `src/engine/online_engine.py`
- `packages/kando_runtime` (`lumos_runtime.py`)
- `packages/kando_core` (`lumos.py`)
- İlgili testler (`tests/test_workspace_contract.py` vb.)

**Analiz bulgusu:** `packages/kando_memory` altında benzer modüller (`memory.py`, `schema.py`, `secure_store.py`) mevcuttur; ancak `kando_memory` paket adına yapılan **aktif import tespit edilmemiştir** (sıfır eşleşme). Paket, pratikte kullanılmayan bir ayna gibi durmaktadır.

**Drift örneği (analiz bulgusu):** `src/memory/memory.py` içinde `from context.context import Context` kullanılırken, `packages/kando_memory/src/kando_memory/memory.py` içinde `from kando_context.context import Context` görülmektedir. İki kopya aynı sorumluluğu taşısa da import yolları farklılaşmıştır; bu, sessiz sapma (drift) riskine işaret eder.

### Canonical trust/security katmanı: `src/security` ve `src/policy`

Aktif güvenlik ve politika akışı **`src/security`** (kripto, keystore, kimlik, kilit, entropy vb.) ve **`src/policy`** (kurallar, offline engine, action policy vb.) üzerinden ilerlemektedir. Örnek tüketiciler (analiz bulgusu):

- `src/core/lumos.py`, `src/core/lumos_runtime.py`
- `src/engine/online_engine.py`
- `src/cli/` altı CLI modülleri
- `packages/kando_runtime` (`lumos_runtime.py`, `lumos_gate.py`, `controlled_bridge.py`)
- İlgili testler

**Yetki profilleri (kısa not):** Görev motoru yetki sınırları `task_engine/profiles.py` üzerinden tanımlanır; güvenlik ve politika katmanlarıyla birlikte çekirdek onay/yetki modelinin parçasıdır. Bu ADR, profil davranışını değiştirmez; yalnızca canonical katman konumunu kaydeder.

**Analiz bulgusu:** `packages/kando_policy` altında `identity.py`, `keystore.py`, `lock.py`, `rules.py` vb. benzer modüller vardır; fakat `kando_policy` paket adına yapılan **aktif import tespit edilmemiştir** (sıfır eşleşme). Öte yandan `packages/kando_policy` içindeki bazı dosyalar (ör. `identity.py`) doğrudan `from security.crypto import ...` ile **`src/security`** katmanına bağlanmaktadır — yani paket hem ayna hem de kısmen `src/` bağımlısıdır; tutarlılık riski taşır.

### Aktif paketler: `kando_runtime` ve `kando_bridge`

Repo analizinde **aktif** görülen paketler `packages/kando_runtime` ve `packages/kando_bridge`'dir. Bu paketler doğrudan veya dolaylı olarak **`src/memory`**, **`src/security`**, **`src/policy`** ve ilgili `src/core` modüllerine dayanmaktadır.

**Analiz bulgusu:** Çalışan köprü ve runtime yolu, `kando_memory` / `kando_policy` paketlerine değil; `src/` canonical katmanlarına bağlıdır.

### Ayna / drift riski özeti

| Paket / alan | Analiz bulgusu |
|--------------|----------------|
| `packages/kando_memory` | Aktif import yok; `src/memory` ile paralel kopya; import yolu drift örneği mevcut |
| `packages/kando_policy` | Aktif import yok; `src/security` + `src/policy` ile paralel kopya; kısmi `security.*` bağımlılığı |
| `packages/kando_runtime` | Aktif; `src/` katmanlarına bağlı |
| `packages/kando_bridge` | Aktif; `kando_runtime` ve `src/` yolu üzerinden çalışır |

Bu tablo **anlık repo taramasına** dayanır; gelecek commit'lerde durum değişebilir. Kesin doğrulama için ayrı import-audit gerekir.

## Karar (belgelenmiş, uygulama bekliyor)

1. **Bellek için canonical kaynak:** `src/memory`
2. **Trust / güvenlik ve politika için canonical kaynak:** `src/security` ve `src/policy` (yetki profilleri: `task_engine/profiles.py` ile hizalı, davranış değişikliği yok)
3. **`packages/kando_memory` ve `packages/kando_policy`:** Analiz bulgusuna göre aktif tüketici görülmemiştir; **ayna / drift riski** taşıyan adaylar olarak işaretlenir — silinmez, taşınmaz, bu ADR turunda dokunulmaz
4. **`packages/kando_runtime` ve `packages/kando_bridge`:** Aktif paketler olarak kalır; canonical `src/` katmanlarına bağımlılık devam eder
5. **Büyük konsolidasyon PR'ı şimdi yapılmaz** — tek seferde paket birleştirme, toplu taşıma veya import dalgası riski yüksektir
6. **İlk güvenli adım:** Bu kararın ADR olarak belgelenmesi; ardından (ayrı, küçük kapsamlı) mirror-diff / import-audit doğrulaması

## Public repo sınırı

Bu depo Lumos'un **public açık kaynak temelidir**. ADR-003:

- Demo-safe / foundation kod sınırları içinde kalır
- Üretim kimlik doğrulama, gizli anahtar yönetimi, cihaz orkestrasyonu ve operasyonel backend altyapısı **private/professional Lumos katmanında** kalır; bu belge o katmanı genişletmez veya expose etmez
- Canonical katman kararı, public sınırını gevşetme veya production özelliği ekleme anlamına gelmez

## Ne yapılmamalı (bu ADR kapsamında ve hemen sonrasında)

Aşağıdaki işler **bilinçli olarak yapılmaz**; ayrı ADR, audit ve onay olmadan başlatılmamalıdır:

| Yapılmaması gereken | Gerekçe (kısa) |
|---------------------|----------------|
| Kod taşıma (move/refactor) | Davranış ve import zinciri riski; audit öncesi erken |
| Import değişikliği | Aktif yolu kırmadan toplu değişim güvenli değil |
| Paket silme (`kando_memory`, `kando_policy`) | Analiz bulgusu ≠ güvenli silme; bağımlılık kaçırma riski |
| Trust / Memory davranış değişikliği | Bu ADR yalnızca konum kararıdır; çekirdek davranış kapsam dışı |
| Agent Network genişlemesi | ADR-001 taslak alanı; bu kararla birleştirilmez |
| Quantum / IBM / Mail entegrasyon pivotu | ADR-001 ve ADR-002 ile çakışan yön değişikliği; kapsam dışı |

## İlk güvenli adım ve sonraki doğrulama

**Şimdi (bu tur):**

- Bu ADR'nin oluşturulması ve canonical katman kararının yazılı hale getirilmesi

**Sonra (ayrı, küçük kapsam):**

- `packages/kando_memory` ↔ `src/memory` mirror-diff (dosya / import farkları)
- `packages/kando_policy` ↔ `src/security` + `src/policy` mirror-diff
- Repo genelinde import-audit: `kando_memory`, `kando_policy` dışında gizli veya dolaylı referans var mı
- Bulgular ayrı checkpoint veya ADR revizyonu ile güncellenir

Audit tamamlanmadan konsolidasyon veya silme kararı **verilmez**.

## Sonuç (geçici)

Haziran 2026 repo analizine dayanarak **bellek canonical kaynağı `src/memory`**, **trust/security canonical kaynakları `src/security` ve `src/policy`** olarak belgelenmiştir. `packages/kando_memory` ve `packages/kando_policy` aktif import taşımıyor gibi görünmekte ve ayna/drift riski taşımaktadır; ancak bu turda dokunulmaz. Aktif `kando_runtime` ve `kando_bridge` paketleri `src/` katmanlarına bağlı kalmaya devam eder. Büyük birleştirme PR'ı ertelenmiştir.

## Sonraki gözden geçirme

- Mirror-diff / import-audit checkpoint sonuçları ile ADR revizyonu
- Audit sonrası: küçük, tek sorumluluklu düzeltme adayları (ayrı karar; bu ADR otomatik uygulama içermez)
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
- ADR-001 (ileri modüller) ve ADR-002 (mail) ile çakışmayan, dar kapsamlı ilerleme
