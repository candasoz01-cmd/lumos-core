#!/bin/zsh
cd "$(dirname "$0")/.."

PYTHONPATH=src python3 tests/test_offline.py || exit 1
PYTHONPATH=src python3 tests/test_online.py  || exit 1

echo "ALL TESTS OK"
