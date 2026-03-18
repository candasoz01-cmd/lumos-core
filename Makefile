PYTHON := python
PYTEST := pytest

.PHONY: help install compile test test-api smoke cli web check run cleanlog install-git-hooks setup-commit-guard

help:
	@echo "Targets:"
	@echo "  make install   -> pip install -e ."
	@echo "  make compile   -> py_compile"
	@echo "  make test      -> pytest -q"
	@echo "  make test-api  -> ./test_api.sh (Express backend ayakta olmalı)"
	@echo "  make smoke     -> bash scripts/smoke_presence.sh"
	@echo "  make cli       -> bash scripts/smoke_cli.sh"
	@echo "  make web       -> bash scripts/smoke_web.sh"
	@echo "  make check     -> compile + test + smoke + cli + web"
	@echo "  make run       -> run main (interactive)"
	@echo "  make cleanlog  -> truncate .lumos/logs/log.txt"
	@echo "  make setup-commit-guard -> git pre-commit: ruff + pytest (bir kez)"

install:
	pip install -e .

# Tek komut: commit guard (ruff + pytest). Ayrıntı: docs/dev-commit-guard.md
setup-commit-guard:
	chmod +x .githooks/pre-commit 2>/dev/null || true
	git config core.hooksPath .githooks
	@echo "Commit guard aktif: her commit öncesi ruff check . && pytest -q"
	@echo "venv: pip install -e . && pip install -U ruff pytest"
	@echo "Bypass: git commit --no-verify"

install-git-hooks: setup-commit-guard

compile:
	$(PYTHON) -m py_compile src/main.py src/core/startup_health.py src/security/presence_lock.py src/security/entropy/__init__.py src/security/entropy/provider.py src/security/entropy/providers/os_urandom.py src/security/entropy/providers/qiskit_aer.py src/security/entropy/providers/ibm_runtime.py src/security/crypto.py src/core/state.py src/core/engine.py src/core/config.py src/core/logfmt.py src/security/presence_fsm.py

test:
	$(PYTEST) -q

test-api:
	./test_api.sh

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
	mkdir -p .lumos/logs
	: > .lumos/logs/log.txt
