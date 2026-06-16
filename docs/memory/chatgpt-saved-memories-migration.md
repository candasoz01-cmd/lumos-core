# ChatGPT Saved Memories — taşıma rehberi

## Amaç

ChatGPT **Saved Memories** ekranındaki kişisel/çalışma tercihlerini Lumos repo’suna taşımak. Taşınan maddeler burada **tek kaynak (canonical)** olarak tutulur; ajanlar ve geliştirme akışı bu dokümanları referans alır.

Bu dosya taşıma sürecinin kaydı ve kontrol listesidir; otomatik senkron veya API entegrasyonu yoktur.

---

## Kaynak

| Alan | Değer |
|------|--------|
| **Kaynak** | ChatGPT → Settings → Personalization → **Saved Memories** |
| **Yöntem** | Manuel kopyala-yapıştır |
| **Hedef** | `docs/memory/` altındaki ilgili dosyalar (bu rehber, `project-journal.md`, `open-decisions.md` vb.) |
| **Sıklık** | İhtiyaç oldukça; toplu taşıma oturumları tercih edilir |

Kaynak metni olduğu gibi arşivlemek gerekirse, madde altına `Kaynak (ChatGPT): …` notu eklenir; asıl anlam repo metnine göre güncellenir.

---

## Taşıma politikası

1. **ChatGPT Saved Memories canonical değildir.** Güncel ve bağlayıcı kayıt repo’daki `docs/memory/**` dosyalarıdır.
2. **Repo `docs/memory/` canonical’dır.** Çelişki varsa repo metni esas alınır; ChatGPT’deki karşılık güncellenir veya oradan kaldırılır.
3. **Tek yönlü taşıma:** ChatGPT → repo. Repo’dan ChatGPT’ye otomatik geri yazma yok.
4. **Çekirdek sözleşme:** Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; memory maddeleri bunları gevşetemez.
5. **Public repo sınırı:** Taşınan içerik public `lumos-core` sınırına uymalıdır (gizli anahtar, PII, production URL vb. taşınmaz).

---

## Durum tanımları

Her madde veya taşıma partisi için aşağıdaki durumlardan biri işaretlenir.

| Durum | İngilizce | Anlam |
|-------|-----------|--------|
| **Taşındı** | `migrated` | Repo’ya aktarıldı, hedef dosyada yer alıyor, gerekirse kaynak ChatGPT maddesi silindi veya “repo’da” diye işaretlendi. |
| **Kuyrukta** | `queued` | Kaynaktan kopyalandı veya taşınmaya aday; henüz hedef dosyaya işlenmedi. |
| **İncelenecek** | `needs-review` | Taşındı veya kuyrukta; ifade belirsiz, çelişkili, güncelliği şüpheli veya sözleşmeyle hizalanması gerekiyor. |
| **Eski / kullanılmıyor** | `superseded` | Yeni repo kararı veya madde ile geçersiz; arşiv notu bırakılır, aktif referans değildir. |

**Örnek işaretleme (madde satırı):** `[migrated]` · `[queued]` · `[needs-review]` · `[superseded]`

---

## Manuel eklenecek maddeler

Aşağıdaki tabloya ChatGPT Saved Memories’ten kopyalanan maddeleri yapıştırın. Taşıma tamamlanınca durumu güncelleyin ve hedef dosyaya taşıyın.

| # | Durum | ChatGPT metni (yapıştır) | Hedef dosya | Not |
|---|--------|---------------------------|-------------|-----|
| 1 | `[queued]` | | | |
| 2 | `[queued]` | | | |
| 3 | `[queued]` | | | |
| 4 | `[queued]` | | | |
| 5 | `[queued]` | | | |

*(Boş satırlar kasıtlıdır; gerektiğinde yeni satır ekleyin.)*

---

## Kısa kontrol listesi

- [ ] ChatGPT Saved Memories ekranı açıldı; güncel liste gözden geçirildi.
- [ ] Her madde için durum (`migrated` / `queued` / `needs-review` / `superseded`) atandı.
- [ ] Taşınan maddeler uygun `docs/memory/` dosyasına yazıldı (journal, open-decisions vb.).
- [ ] Gizli/PII/production içerik taşınmadı (public repo sınırı).
- [ ] Memory maddeleri çekirdek sözleşmeyle çelişmiyor.
- [ ] ChatGPT tarafında taşınan maddeler güncellendi veya kaldırıldı (tek kaynak: repo).
- [ ] Bu dosyadaki tablo ve durumlar güncellendi.

---

*Son güncelleme: 2026-06-17*
