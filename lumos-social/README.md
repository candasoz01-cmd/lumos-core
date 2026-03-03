# lumos-social

Lumos **social layer**: connector interface, event bus, and message pipeline skeleton. Modular, testable, minimal—ready to grow.

- **No tokens or secrets in the repo.** Config via env and optional TOML only.
- **First version:** no real platform integration; **connector interface + mock connector** only.
- **Code quality:** ruff (format + lint), mypy, pytest.

## Geliştirici notu

Python kodunu terminale satır satır yapıştırma; kod ya dosyaya (heredoc vb.) yazılır ya da `python -c '...'` ile tek satır çalıştırılır.

## Structure

- `src/lumos_social/` — package
  - `connector.py` — `BaseConnector` interface and `ConnectorEvent`
  - `mock_connector.py` — in-memory mock (no external calls)
  - `bus.py` — in-process event bus
  - `config.py` — env + optional `config.toml`
  - `cli.py` — CLI entrypoint
- `tests/` — pytest tests

## Setup — tek komutla ayağa kalkma

```bash
cd lumos-social
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Veya: `make setup` (venv aktifken).

Optional: copy `.env.example` to `.env` and adjust (never commit real secrets).

## Kalite kapısı (lokal komutlar)

```bash
ruff check .
ruff format .
pytest -q
```

Veya tek seferde: `make check` (format + lint + test).

## Run

**CLI (after install):**

```bash
lumos-social status
```

**Without installing (from repo root):**

```bash
PYTHONPATH=src python -m lumos_social status
```

**Example output:**

```
lumos-social status
  env: dev
  connector: mock
  connected: True
  poll_count: 0
```

## Config

- **Env:** `LUMOS_SOCIAL_ENV`, `LUMOS_SOCIAL_LOG_LEVEL` (defaults: `dev`, `INFO`).
- **Optional:** `config.toml` in current directory (see `.env.example` for a template). TOML is only read if the file exists; use `tomli` on Python &lt; 3.11.

No API keys or secrets are read from the repo; set them via env or a local, gitignored file.

## Quality

```bash
ruff check src tests && ruff format src tests
mypy src
pytest
```

## Extending

- Add a new connector: implement `BaseConnector` in a new module and register it (e.g. in config or a registry).
- Event pipeline: subscribe to `EventBus` from connectors and forward to your handlers.
- Real platforms: add dependencies and connector implementations in separate packages or optional extras; keep tokens out of the repo.
