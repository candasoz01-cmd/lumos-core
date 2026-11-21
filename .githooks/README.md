# Git hooks (geliştirme)

Tek resmi hook seti bu klasördür (`core.hooksPath=.githooks`).
`ops/claim_guard/hooks` yalnız uyumluluk girişidir ve buraya devreder;
hangisi seçilirse seçilsin aşağıdaki korumaların hiçbiri düşmez.

## `pre-commit`

Her `git commit` öncesi, bu sırayla:

1. **Merkezi claim kapısı** (`ops/claim_guard/claim-pre-commit`): staged
   dosyaların bu dalda `LUMOS_AGENT` ajanının aktif merkezi claim'i içinde
   olduğu ve başka ajanın aktif claim'ine girmediği doğrulanır. Merkezi pano
   (`refs/heads/claude/lumos-board`) erişilemezse commit reddedilir.
2. `ruff check .`
3. `pytest -q`

## `commit-msg`

`Lumos-Claim` / `Lumos-Agent` trailer'larını mesajın **son trailer
bloğuna** yazar (`Co-authored-by` ile aynı blok). Git ve `claim-guard`
yalnız son bloğu okur; ayrı paragrafta kalan Lumos satırı yok sayılır.

## `pre-push`

Her `git push` öncesi yayın kapısı koşar: `python3 ops/publication_gate/gate.py`.
Public remote'a giden içerik push anında yayımlanmış olur; bu kanca son yerel
bariyerdir. `--no-verify`, kancasız klon veya API push'u bunu atlayabilir —
detay ve kalan risk: `docs/PUBLICATION_GATE.md`.

## Kurulum (repo kökünde, tek komut)

```bash
make setup-commit-guard
export LUMOS_AGENT=<merkezi claim sahibi, ör. cando-mac>
```

Sonra venv içinde: `pip install -e .` ve `pip install -U ruff pytest`.
`--no-verify` tüm kancaları atlar; CI'daki `claim-guard` aynı kuralları PR
üzerinde yine denetler.
