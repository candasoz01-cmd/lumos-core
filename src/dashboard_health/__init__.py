"""Dashboard Health observe-slice helpers.

`bridge.llm → Observe` is granted. Dashboard Health ownership is not.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RESPONSIBILITY_PATH = Path(__file__).with_name("responsibility.json")


def load_responsibility() -> dict[str, Any]:
    return json.loads(_RESPONSIBILITY_PATH.read_text(encoding="utf-8"))


RESPONSIBILITY = load_responsibility()
