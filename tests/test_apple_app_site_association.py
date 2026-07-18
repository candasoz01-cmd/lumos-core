import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AASA_PATHS = [
    ROOT / "ui" / "public" / "apple-app-site-association",
    ROOT / "ui" / "public" / ".well-known" / "apple-app-site-association",
]


def test_aasa_matches_signed_lumos_target() -> None:
    for path in AASA_PATHS:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        assert payload["applinks"]["details"] == [
            {
                "appID": "VQH79C5QU7.com.welockai.Lumos",
                "paths": ["/panel", "/panel/*", "/"],
            }
        ]
        assert "XXXXXXXXXX" not in raw
