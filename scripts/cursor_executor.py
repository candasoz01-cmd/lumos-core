"""last_cursor_executor.json veya last_execution.constraints.execution özetini yazdırır."""
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def run() -> None:
    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos")).resolve()
    bridge = base / "cursor_bridge"
    ce = bridge / "last_cursor_executor.json"
    if ce.is_file():
        print(ce.read_text(encoding="utf-8"))
        return
    le = bridge / "last_execution.json"
    if not le.is_file():
        print("execution yok")
        return
    data = json.loads(le.read_text(encoding="utf-8"))
    ex = data.get("constraints", {}).get("execution") or data.get("execution")
    if ex:
        print(json.dumps(ex, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data.get("constraints", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
