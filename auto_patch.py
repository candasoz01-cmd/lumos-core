from pathlib import Path
import json

outbox = Path(".lumos/outbox/last_execution.json")

if not outbox.exists():
    print("no execution")
    exit()

data = json.loads(outbox.read_text())
instr = data.get("instruction") or data.get("plan") or data.get("intent") or ""

if "print ekle" in instr:
    file_path = Path("src/core/lumos_runtime.py")
    text = file_path.read_text()

    if 'print("agent auto")' not in text:
        text += '\n\nprint("agent auto")\n'
        file_path.write_text(text)
        print("AUTO PATCH APPLIED")
    else:
        print("ALREADY EXISTS")
else:
    print("NO MATCH")
