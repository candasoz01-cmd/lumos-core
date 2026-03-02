"""Web v1: server ayağa kalkıyor mu, /health 200 ve ok:true dönüyor mu."""
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_web_health_200_ok():
    """Start server in subprocess, GET /health returns 200 and ok:true."""
    app = ROOT / "web" / "app.py"
    if not app.exists():
        pytest.skip("web/app.py not found")
    proc = subprocess.Popen(
        [sys.executable, str(app)],
        cwd=str(ROOT),
        env={**__import__("os").environ, "PORT": "18765"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(0.5)
        req = urlopen(Request("http://127.0.0.1:18765/health"), timeout=5)
        assert req.status == 200
        data = json.loads(req.read().decode("utf-8"))
        assert data.get("ok") is True
        assert "version" in data
    finally:
        proc.terminate()
        proc.wait(timeout=3)
