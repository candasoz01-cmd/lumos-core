"""Production panel source must not read PUBLIC_KANDO_TOKEN."""
from __future__ import annotations

import re
from pathlib import Path


def test_production_kando_token_branch_is_empty() -> None:
    source = Path("ui/src/pages/panel.astro").read_text(encoding="utf-8")
    match = re.search(
        r"const kandoToken = import\.meta\.env\.DEV\s*"
        r"\?\s*import\.meta\.env\.PUBLIC_KANDO_TOKEN \|\| \"test123\"\s*"
        r":\s*\"\";",
        source,
    )
    assert match, "production kandoToken branch must be a literal empty string"
