# Lumos-social: tek komutla ayağa kalkma + kalite kapısı
# Kurulum: make setup
# Kalite: make check  (veya ruff check . && ruff format . && pytest -q)

.PHONY: setup lint format test check

setup:
	python -m pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

test:
	pytest -q

check: format lint test
	@echo "OK: format + lint + test"
