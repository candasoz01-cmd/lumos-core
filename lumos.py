import os
import sys
import json
from pathlib import Path

def _lumos_dir() -> Path:
    p = Path("src/.lumos")
    if p.exists():
        return p
    return Path(".lumos")

def _read_pub_b64() -> str:
    base = _lumos_dir()
    p = base / "identity.json"
    if not p.exists():
        return ""
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return str(d.get("public_key_b64", "")).strip()
    except Exception:
        return ""

def main_cli() -> None:
    args = [a.strip().lower() for a in sys.argv[1:]]

    if "--online" in args:
        os.environ["LUMOS_MODE"] = "online"
    if "--offline" in args:
        os.environ["LUMOS_MODE"] = "offline"

    if "--sim" in args:
        os.environ["LUMOS_SERVER_SIM"] = "1"

    if "--debug" in args:
        os.environ["LUMOS_DEBUG"] = "1"

    for a in args:
        if a.startswith("--pass="):
            os.environ["LUMOS_PASSPHRASE"] = a.split("=", 1)[1]

    mode = os.getenv("LUMOS_MODE", "offline").strip().lower()
    sim = os.getenv("LUMOS_SERVER_SIM", "0") == "1"

    if mode == "online" and sim and not os.getenv("LUMOS_SERVER_PUB_B64"):
        pub = _read_pub_b64()
        if pub:
            os.environ["LUMOS_SERVER_PUB_B64"] = pub

    if str(Path("src").resolve()) not in sys.path:
        sys.path.insert(0, str(Path("src").resolve()))

    from main import main as lumos_main
    lumos_main()

if __name__ == "__main__":
    main_cli()
