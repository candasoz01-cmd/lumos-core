"""Online path: CLI unknown → on_live_brain → handle_live_brain → online_engine.process. Without API key: 'Online hazır değil.'; with API key: model response."""
import os
import subprocess
import sys

def run():
    env = os.environ.copy()
    env["LUMOS_MODE"] = "online"

    p = subprocess.run(
        [sys.executable, "src/main.py"],
        input=b"selam\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    out = p.stdout.decode("utf-8", errors="ignore")

    assert "Lumos başlatılıyor" in out, "Boot mesajı yok"
    assert "Mod: online" in out or "online" in out.lower(), "Online moda geçmemiş"
    # Free-text in online: either fallback (no key/signer) or model response
    assert "Online hazır değil." in out or "Yanındayım." in out or "Yanıt" in out or "selam" in out.lower(), (
        f"Beklenmeyen çıktı: {out[:500]}"
    )

    print("OK: online")

if __name__ == "__main__":
    run()
