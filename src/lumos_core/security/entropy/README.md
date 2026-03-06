# Entropy (güvenlik)

Çekirdek, kriptografik rastgelelik için bir **entropy provider** arayüzü kullanır. Varsayılan: işletim sisteminin CSPRNG’i (`os`).

- **`os`** — `os.urandom` (varsayılan, ek bağımlılık yok).
- **`qiskit_aer`** — Opsiyonel; Qiskit Aer simülatör ile entropy (deneysel). `qiskit` ve `qiskit-aer` kurulu olmalı.
- **`ibm_runtime`** — Opsiyonel; IBM Quantum runtime hazırsa kullanır, yoksa `os`’a düşer.

Provider seçimi: ortam değişkeni `LUMOS_ENTROPY_PROVIDER` (`os` | `qiskit_aer` | `ibm_runtime`).  
API: `get_random_bytes(n)`, `entropy(n, provider="os")`. Demo ve Qiskit araçları **lumos-quantum** tarafında; çekirdek sadece bu arayüzü kullanır.
