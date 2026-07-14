import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AASA_PATH = ROOT / "ui" / "public" / "apple-app-site-association"


def test_aasa_matches_signed_lumos_target() -> None:
    payload = json.loads(AASA_PATH.read_text(encoding="utf-8"))
    details = payload["applinks"]["details"]

    assert details == [
        {
            "appID": "VQH79C5QU7.com.welockai.Lumos",
            "paths": ["/panel", "/panel/*", "/"],
        }
    ]
    assert "XXXXXXXXXX" not in AASA_PATH.read_text(encoding="utf-8")
