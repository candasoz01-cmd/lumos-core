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
        env=env
    )

    out = p.stdout.decode("utf-8", errors="ignore")

    assert "Lumos core başlatılıyor" in out, "Boot mesajı yok"
    assert "Mod: online" in out, "Online moda geçmemiş"
    assert "Yanındayım." in out, f"Beklenmeyen çıktı: {out}"
    assert "İstersen birlikte sadeleştirebiliriz." in out, f"Beklenmeyen çıktı: {out}"
    assert "Buradaki asıl mesele sence ne?" in out, f"Beklenmeyen çıktı: {out}"

    print("OK: online")

if __name__ == "__main__":
    run()
