"""Web v1: server ayağa kalkıyor mu, /health 200 ve ok:true dönüyor mu."""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_web_health_200_ok():
    """Start server in subprocess, GET /health returns 200 and ok:true."""
    app = ROOT / "web" / "app.py"
    if not app.exists():
        pytest.skip("web/app.py not found")
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(app)],
        cwd=str(ROOT),
        env={**__import__("os").environ, "PORT": str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(0.5)
        req = urlopen(Request(f"http://127.0.0.1:{port}/health"), timeout=5)
        assert req.status == 200
        data = json.loads(req.read().decode("utf-8"))
        assert data.get("ok") is True
        assert "version" in data
    finally:
        proc.terminate()
        proc.wait(timeout=3)
