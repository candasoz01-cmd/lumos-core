import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_chat_domain_redirects_to_canonical_lumos_surface() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    redirects = config["redirects"]

    assert redirects[:2] == [
        {
            "source": "/",
            "has": [{"type": "host", "value": "chat.welockai.com"}],
            "destination": "https://welockai.com/panel",
            "permanent": True,
        },
        {
            "source": "/(.*)",
            "has": [{"type": "host", "value": "chat.welockai.com"}],
            "destination": "https://welockai.com/$1",
            "permanent": True,
        },
    ]
