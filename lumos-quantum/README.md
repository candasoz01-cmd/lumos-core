# lumos-quantum

Quantum demoları ve isteğe bağlı Qiskit tabanlı entropy kaynağı. **lumos-core** ile birlikte kullanılır; çekirdek içinde demo kodu yok.

- **qc_demo.py** — Minimal Qiskit demo (1 qubit, H, ölçüm, AerSimulator).
- **requirements-qiskit.txt** — `qiskit`, `qiskit-aer` (entropy provider için).

Çekirdekte quantum entropy kullanmak için: `LUMOS_ENTROPY_PROVIDER=qiskit_aer` ve `pip install qiskit qiskit-aer` (veya bu dizindeki requirements-qiskit.txt).
