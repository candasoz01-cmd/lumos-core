#!/usr/bin/env bash
# Repo hygiene doğrulama. lumos-social kökünde çalıştır: ./scripts/hygiene_verify.sh

set -e
echo "=== ruff check ==="
python -m ruff check .
echo "=== ruff format (check) ==="
python -m ruff format .
echo "=== pytest ==="
python -m pytest -q
echo "=== git status -sb ==="
git status -sb
echo "=== git ls-files .data/ *.db ==="
git ls-files | grep -E '(^.data/|\.db$)' || true
echo "=== Done ==="
