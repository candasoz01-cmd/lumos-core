#!/usr/bin/env python3
"""Quantum Readiness yerel tarama — stdout JSON (ADR-013)."""
from __future__ import annotations

import json
import sys

from security.readiness.scanner import scan_quantum_readiness


def main() -> None:
    report = scan_quantum_readiness()
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
