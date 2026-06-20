# Mail — dar v1 hedef tanımı (OD-031)

> **Durum:** `scope-approved` (dar v1 hedef) / **`implementation-partial`** (public demo stub; private Gmail/vault impl bekliyor).  
> **Bu belge:** Dar v1 kapsam sınırı only — **mail ürün kodu yok**, **credential yok**, **send otomasyonu yok**.  
> **Üst ilke modeli:** [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) (OD-031 tam model — dar v1 bunun **alt kümesi**).

**Kaynak OD:** OD-031  
**Onay omurgası:** OD-041 ([`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md))  
**Vault bağımlılığı:** OD-001/002 + [`od-vault-dar-v1-design.md`](./od-vault-dar-v1-design.md)

---

## 1. Dar v1 özeti

| Boyut | Dar v1 | Tam OD-031 modeli (sonra) |
|-------|--------|---------------------------|
| Kanal | **Yalnızca mail (e-posta)** | Telegram, WhatsApp, SMS, sosyal DM vb. |
| Provider | **Tek provider** (seçim impl paketinde) | Çoklu hesap / provider |
| İzin seviyeleri | **`read` + `notify`** (+ **`draft_prep` opsiyonel**) | `send_reply`, `archive`, `label`, `delete`, kural-kapsamlı otomasyon |
| Otomasyon | **Yok** — kural editörü dar v1 dışı | Kullanıcı tanımlı kurallar, tam otomasyon (CC3) |
| Credential | Vault'ta — **OD-001/002 impl sonrası** | Aynı ilke |
| Dış etki | Bildirim + okuma; taslak **göndermez** | Gönder, arşiv, sil — ayrı grant |

**Firm:** Dar v1, OD-031 **ilkelerini gevşetmez**; yalnızca **ilk pilot kapsamını** daraltır. Tam model [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) canonical kalır.

---

## 2. Tek provider kuralı

| Madde | Dar v1 |
|-------|--------|
| Hesap sayısı | **1** mail hesabı / 1 provider bağlantısı |
| Provider adayı | **Gmail OAuth** (resmi Gmail API) — **M1 onaylı** | Tek seçim impl paketinde (M1) |
| Resmi API | Zorunlu — platform bypass / scraping **yok** (CC11) |
| Çoklu kutu / paylaşımlı hesap | **Dar v1 dışı** — needs-review |

**Not:** Provider seçimi **Gmail OAuth** — resmi API, push/watch (M5), vault OAuth credential modeli (M2). IMAP dar v1 birincil değil.

---

## 3. İzin seviyeleri — dar v1 alt kümesi

Tam tablo: [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) §İzin seviyeleri.

| Seviye | Kod | Dar v1 | Onay (OD-041) |
|--------|-----|--------|---------------|
| Okuma | `read` | **Dahil** | Oturum + kanal/kapsam (CA1) |
| Bildirim | `notify` | **Dahil** | Oturum + kapsam; `read` grant gerekir |
| Taslak hazırlama | `draft_prep` | **Opsiyonel** — impl paketinde açık/kapalı karar | Kural/işlem bazlı; **göndermez** |
| Yanıt gönderme | `send_reply` | **Hariç** | — |
| Arşivleme | `archive` | **Hariç** | — |
| Etiketleme | `label` | **Hariç** | — |
| Silme | `delete` | **Hariç** | — |
| Kalıcı silme | — | **Asla** (CC6) | Kullanıcı açık komutu |

### 3.1 `draft_prep` opsiyonel notu

| Seçenek | Davranış | Öneri |
|---------|----------|-------|
| **A — Kapalı** | Dar v1 yalnızca okuma + bildirim | En dar pilot; düşük risk |
| **B — Açık** | Taslak üretir; **send_reply yok**; her taslak kullanıcı onayı | Orta risk; E4 örneğine yakın |

**Dar v1 design kararı:** Opsiyonel bırakıldı; impl paketi başlamadan **A veya B** kullanıcı/onaylı paket seçer. Default öneri: **A (kapalı)** — ilk smoke en dar.

### 3.2 Yasak (dar v1)

| # | Yasak | Gerekçe |
|---|--------|---------|
| MY1 | `send_reply` — otomatik veya manuel connector gönderimi | Dar v1 dış etki sınırı |
| MY2 | Kural-kapsamlı otomatik yanıt (E2 örnekleri) | CC3 tam model — dar v1 değil |
| MY3 | Çoklu kanal / çoklu hesap | Dar v1 tek provider |
| MY4 | Credential Lumos yüzeyinde | CC8; OD-001/002 |
| MY5 | Mesaj içeriği public repo / gereksiz kalıcı log | CC9 |

---

## 4. Vault credential (OD-001 / OD-002)

| Konu | Dar v1 |
|------|--------|
| Mail OAuth / IMAP credential | **Vault/kasa katmanında** — Lumos yüzeyinde açık değil |
| Bağlantı zamanı | **Vault dar v1 impl onaylandıktan sonra** (M2) |
| Amaç kodu (taslak) | `integration.mail.read`, `integration.mail.notify` — [`od-vault-dar-v1-design.md`](./od-vault-dar-v1-design.md) §4.1 |
| Bridge | Kontrollü geçit ilkesi; **OD-B05 merge ertelendi** — mevcut bridge sınırı korunur |

**Sıra (firm):** Vault purpose + credential şeması (private) → mail connector pilot (onaylı impl) → M7 smoke.

---

## 5. OD-041 hizası (dar v1)

| OD-041 ilkesi | Mail dar v1 karşılığı |
|---------------|------------------------|
| CA1 — düşük risk okuma oturum bazlı | `read` + isteğe bağlı `notify` oturum grant |
| CA2 — dış etkili aksiyon işlem bazlı | Dar v1'de **dış etkili gönder/sil yok** |
| CA4 — sessiz / carry-forward yok | Mail grant açık opt-in |
| CA6 — oturum ≠ send | `read` oturumu **`send_reply` vermez** — dar v1'de send zaten kapalı |
| CA7 — ne/nerede/etki | Bağlantı/onay: hangi hesap, okuma/bildirim kapsamı |

**Canonical:** Oturum izni yalnızca okuma/bildirim katmanını açar; dar v1 bu sınırı **genişletmez**.

---

## 6. M1–M7 checklist — dar v1 alt kümesi

Kaynak: [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) §Mail pilot implementation checklist.

| # | Madde | Tam checklist | **Dar v1** | Not |
|---|--------|---------------|------------|-----|
| **M1** | Mail provider seçimi (Gmail OAuth / IMAP) | implementation-pending | **dar v1 — gerekli** | **Gmail OAuth seçildi** — public stub only |
| **M2** | Vault mail credential şeması | implementation-pending | **dar v1 — gerekli** | Demo vault bridge stub; Infisical private |
| **M3** | Granüler izin grant UI | implementation-pending | **dar v1 — kısmi** | `read`/`notify` grant modeli kodda (OD-041) |
| **M4** | Kural editörü (kişi/kaynak/içerik) | implementation-pending | **dar v1 — hariç** | Tam OD-031 modeli |
| **M5** | Sync modeli (poll vs push) | implementation-pending | **dar v1 — gerekli** | Tek hesap; minimum viable |
| **M6** | Çakışma algoritması (taslak vs otomatik) | implementation-pending | **dar v1 — hariç** | `send_reply` / kural yok |
| **M7** | İlk kanal smoke | blocked | **dar v1 — hedef** | Onaylı private impl paketi + CI dışı smoke |

### 6.1 Dar v1 uygulama paketi (sıra)

```
M1 (tek provider) → M2 (vault credential) → M3 (read/notify grant UI) → M5 (sync) → M7 (smoke)
```

**Paralel olmaz:** M2, vault impl onayı olmadan başlamaz.

---

## 7. Dahil / hariç (dar v1)

| Dahil | Hariç |
|-------|--------|
| Tek mail hesabı okuma | Çoklu hesap |
| Kullanıcıya bildirim (`notify`) | Otomatik yanıt (`send_reply`) |
| Opsiyonel taslak (`draft_prep` — paket kararı) | Kural editörü (M4) |
| Vault credential ilkesi | Credential Lumos yüzeyinde |
| OD-041 oturum onayı (read/notify) | Kanal genişlemesi (Telegram vb.) |
| Resmi API provider | Scraping / unofficial API |

---

## 8. OD eşleme

| OD | Konu | Bu belge | Durum |
|----|------|----------|--------|
| **OD-031** | İletişim kanalları — mail ilk kanal | Dar v1 alt kümesi | **scope-approved / implementation-partial** |
| OD-041 | Hibrit onay | §5 | decision-approved / UX impl-pending |
| OD-001 | Vault uygulaması | §4 bağımlılık | decision-approved / impl-pending |
| OD-002 | Token / vault entegrasyonu | §4 M2 | decision-approved / impl-pending |
| OD-012 | Computer Use | Tarayıcı mail — **dar v1 dışı** | Ayrı değerlendirme |

**İndeks:** `open-decisions-needs-review.md` OD-031 satırı dar v1 scope referansı ile güncellenir.

---

## 9. Sonraki adım

1. **Private impl:** Infisical vault PoC + Gmail OAuth connector ([`od-vault-v1-technology-selection.md`](./od-vault-v1-technology-selection.md)).
2. **Public stub tamam:** `src/integrations/mail/` — grant model, demo connector, vault bridge mock.
3. **Genişleme:** M3 UI, M5 sync, M7 smoke — private/onaylı paket.

**Yasak (bu aşamada):** connector kodu, OAuth secret, production endpoint, otomatik gönderim, çoklu kanal.

---

Son güncelleme: 2026-06-20 (dar v1 hedef tanımı — docs only)
