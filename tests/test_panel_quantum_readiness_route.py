"""PR-2: GET /quantum-readiness panel route (ADR-013 Faz-2)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _load_panel_tasks_server():
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    return pts


def test_panel_server_quantum_readiness_route_wiring() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert "/quantum-readiness" in src
    assert "build_quantum_readiness_response" in src
    assert "_get_quantum_readiness" in src
    assert "scan_quantum_readiness" in src


def test_build_quantum_readiness_response_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    report = pts.build_quantum_readiness_response()
    assert report["meta"]["report_type"] == "quantum_readiness"
    assert report["meta"]["evidence_basis"] == "local_scan"
    assert report["meta"]["read_only"] is True
    assert "crypto_inventory" in report
    assert "entropy_lab" in report


def test_panel_astro_quantum_readiness_fetch_wiring() -> None:
    text = (_REPO_ROOT / "ui" / "src" / "pages" / "panel.astro").read_text(encoding="utf-8")
    assert "/quantum-readiness" in text
    assert "fetchQuantumReadiness" in text
    assert "refreshQuantumReadinessPanel" in text
    assert 'id === "kuantum"' in text
    assert 'id="panel-quantum-badge-local-scan"' in text
