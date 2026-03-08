PYTHON := python
# Her yerde python -m kullan (pytest/ruff komutuna güvenme)
PYTEST := $(PYTHON) -m pytest
RUFF   := $(PYTHON) -m ruff

.PHONY: help install compile test lint format smoke cli web check run cleanlog

help:
	@echo "Targets:"
	@echo "  make install   -> pip install -e ."
	@echo "  make compile   -> py_compile"
	@echo "  make test      -> python -m pytest -q"
	@echo "  make lint      -> python -m ruff check ."
	@echo "  make format    -> python -m ruff format ."
	@echo "  make smoke     -> bash scripts/smoke_presence.sh"
	@echo "  make cli       -> bash scripts/smoke_cli.sh"
	@echo "  make web       -> bash scripts/smoke_web.sh"
	@echo "  make check     -> compile + test + smoke + cli + web"
	@echo "  make run       -> run main (interactive)"
	@echo "  make cleanlog  -> truncate .lumos/log.txt"

install:
	$(PYTHON) -m pip install -e ".[dev]"

compile:
	@find src/lumos_core -name '*.py' ! -path '*/__pycache__/*' -print0 | xargs -0 -n 50 $(PYTHON) -m py_compile

test:
	$(PYTEST) -q

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

smoke:
	bash scripts/smoke_presence.sh

cli:
	bash scripts/smoke_cli.sh

web:
	bash scripts/smoke_web.sh

check: install compile test smoke cli web

run:
	$(PYTHON) -m lumos_core

cleanlog:
	: > .lumos/log.txt
