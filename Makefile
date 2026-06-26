PYTHON := python
PYTEST := pytest
TEST_PYTHONPATH := $(CURDIR)/src:$(CURDIR)/packages/kando_runtime/src:$(CURDIR)/packages/kando_bridge/src

.PHONY: help install compile test test-rust test-api smoke cli web check run cleanlog install-git-hooks setup-commit-guard e2e-package e2e-package-api e2e-tasks-offline-online

help:
	@echo "Targets:"
	@echo "  make install   -> pip install -e ."
	@echo "  make compile   -> py_compile"
	@echo "  make test      -> CI parity: PYTHONPATH + KANDO_MOCK=1, pytest -q"
	@echo "  make test-rust -> cargo test (AnchorUSB crates)"
	@echo "  make e2e-package -> panel paket kapısı (local/demo)"
	@echo "  make e2e-package-api -> panel paket kapısı (REST /tasks + POST + offline/online)"
	@echo "  make e2e-tasks-offline-online -> yalnız görev API offline/online e2e"
	@echo "  make test-api  -> ./test_api.sh (Express backend ayakta olmalı)"
	@echo "  make smoke     -> bash scripts/smoke_presence.sh"
	@echo "  make cli       -> bash scripts/smoke_cli.sh"
	@echo "  make web       -> bash scripts/smoke_web.sh"
	@echo "  make check     -> make test ile aynı (CI pytest ortamı)"
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
	PYTHONPATH=$(TEST_PYTHONPATH) KANDO_MOCK=1 $(PYTEST) -q

test-rust:
	cargo test -p anchorusb-core -p anchorusb-cli

e2e-package:
	cd panel && npm run e2e:package

e2e-package-api:
	cd panel && npm run e2e:package:api

e2e-tasks-offline-online:
	cd panel && npm run e2e:tasks-offline-online

test-api:
	./test_api.sh

smoke:
	bash scripts/smoke_presence.sh

cli:
	bash scripts/smoke_cli.sh

web:
	bash scripts/smoke_web.sh

check: test

run:
	$(PYTHON) -m lumos_core

cleanlog:
	mkdir -p .lumos/logs
	: > .lumos/logs/log.txt
