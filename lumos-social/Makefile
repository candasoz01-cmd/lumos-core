# Lumos-social: repo hygiene + kalite kapısı
# make setup  -> kurulum
# make check  -> lint + fmt + test

.PHONY: setup lint fmt format test check

setup:
	python -m pip install -e ".[dev]"

lint:
	python -m ruff check .

fmt:
	python -m ruff format .

format: fmt

test:
	python -m pytest -q

check: lint fmt test
	@echo "OK: lint + fmt + test"
