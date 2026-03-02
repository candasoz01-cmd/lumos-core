from pathlib import Path
import re

p = Path("src/security/presence_lock.py")
if not p.exists():
    raise SystemExit("ERR: src/security/presence_lock.py bulunamadı.")

s = p.read_text(encoding="utf-8")
if "presence_stopped" not in s:
    print("SKIP: presence_stopped geçmiyor.")
    raise SystemExit(0)

lines = s.splitlines(True)

def wrap_line(i: int):
    line = lines[i]
    if "presence_stopped" not in line:
        return
    if "was_running" in line:
        return
    indent = re.match(r'^(\s*)', line).group(1)
    stripped = line.strip()
    if stripped.startswith("if "):
        return
    lines[i] = f"{indent}if (not silent) and was_running:\n{indent}    {stripped}\n"

txt = "".join(lines)
m = re.search(r'(^def\s+stop_presence_lock\s*\(.*?\)\s*:\s*\n)(?P<body>(?:[ \t]+.*\n)+)', txt, flags=re.M)
if not m:
    raise SystemExit("ERR: stop_presence_lock fonksiyonu bulunamadı.")

header = m.group(1)
body = m.group("body")

if not re.search(r'^\s*was_running\s*=\s*', body, flags=re.M):
    first_indent = re.match(r'^([ \t]+)', body).group(1)
    body = f"{first_indent}was_running = is_running()\n" + body
    txt = txt[:m.start()] + header + body + txt[m.end():]
    lines = txt.splitlines(True)

for i in range(len(lines)):
    if "presence_stopped" in lines[i]:
        if re.search(r'(_append_log|log_event|print)\(.*presence_stopped', lines[i]):
            wrap_line(i)

out = "".join(lines)
p.write_text(out, encoding="utf-8")
print("OK: presence_stopped sadece (not silent) and was_running iken loglanacak.")
