# İlk yol arkadaşı — Qiskit ve Qiskit Aer

| Alan | Değer |
|------|-------|
| Durum | **Planlı** — öncelik kilidi; otomatik bağlantı yok |
| Tarih | 2026-06-26 |
| İlgili | [`lumos-quantum-layer-architecture.md`](./lumos-quantum-layer-architecture.md), [`lumos-quantum-provider-catalog.md`](./lumos-quantum-provider-catalog.md) |

---

## Kısa hikâye

Quantum Layer ağacında kökten çıkan **ilk dal** Qiskit ve yerel Qiskit Aer simülatörüdür. Kullanıcı vizyonu net: önce tanıdık, yerel ve düşük riskli bir spike; IBM, Azure ve Braket dalları **sonra** gelir — Aer kanıtlandıktan sonra.

Bu bir «hemen bağlan» kararı değil. Lumos'un kuantum omurgası değişmez: **bul → sınıflandır → onay → bağlan**. İlk yol arkadaşı yalnızca *hangi sağlayıcıyla pilot connect spike'ının anlamlı olduğunu* kilitler.

---

## Neden Qiskit önce?

1. **Olgun ekosistem** — dokümantasyon, örnekler, topluluk ve iş gücü; ilk entegrasyon için öğrenme eğrisi düşük.
2. **Yerel Aer** — API anahtarı ve bulut faturası olmadan devre çalıştırma; maliyet ve egress riski katalogda düşük.
3. **Repo hizası** — Entropy Lab envanterinde `qiskit_aer` zaten deneysel olarak geçiyor; Layer connect ayrı katman, ama teknik zemin tanıdık.
4. **Dürüst sınır** — Simülatör QPU değildir; «kuantum bağlandı» iddiası yok.

---

## Ne anlama gelmiyor?

| Yanlış okuma | Gerçek |
|--------------|--------|
| «Qiskit seçildi → otomatik connect» | Hayır. `connect` her zaman onay kapısı + private impl. |
| «Aer yerel → auto-doc yeter» | Katalog salt okunur (`list_catalog`) auto-doc; **connect** yine `needs-owner`. |
| «API key gerekmez → sessiz bağlan» | Anahtar yok ≠ izin yok. NEVER_AUTO (Q-01–Q-03) geçerli. |

---

## Sonraki dal

**IBM Quantum (cloud)** — `connect_priority: 2`. Yerel Aer spike'ı risk/ücret/izin matrisinde kanıtlandıktan sonra ilk bulut dalı. Azure Quantum ve Amazon Braket planlı sonraki dallar.

---

*Bu belge ürün taahhüdü değil; öncelik ve hikâye kilididir. Canlı bağlantı yalnızca onaylı private katmanda.*
