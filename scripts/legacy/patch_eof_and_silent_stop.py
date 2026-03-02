from pathlib import Path
import re

def die(msg):
    raise SystemExit(msg)

root = Path(".")
main_p = root / "src" / "main.py"
pl_p = root / "src" / "security" / "presence_lock.py"

if not main_p.exists():
    die(f"ERR: bulunamadı: {main_p}")
if not pl_p.exists():
    die(f"ERR: bulunamadı: {pl_p}")

main = main_p.read_text(encoding="utf-8")

target = 'raw = pending if pending is not None else input("Sen: ").strip()'
if target in main:
    repl = (
        'if pending is not None:\n'
        '            raw = pending\n'
        '        else:\n'
        '            try:\n'
        '                raw = input("Sen: ").strip()\n'
        '            except EOFError:\n'
        '                print("OK")\n'
        '                return\n'
    )
    main = main.replace(target, repl, 1)
else:
    # daha esnek yakala (format farkı olabilir)
    pat = re.compile(r'raw\s*=\s*pending\s*if\s*pending\s*is\s*not\s*None\s*else\s*input\("Sen:\s*"\)\.strip\(\)\s*')
    m = pat.search(main)
    if not m:
        die("ERR: main.py içinde 'input(\"Sen: \")' satırı bulunamadı (format farklı olabilir).")
    repl = (
        'if pending is not None:\n'
        '            raw = pending\n'
        '        else:\n'
        '            try:\n'
        '                raw = input("Sen: ").strip()\n'
        '            except EOFError:\n'
        '                print("OK")\n'
        '                return\n'
    )
    main = main[:m.start()] + repl + main[m.end():]

main_p.write_text(main, encoding="utf-8")
print("OK: main.py EOF guard eklendi.")

pl = pl_p.read_text(encoding="utf-8")

# silent stop log'u kapat: presence_stopped logu varsa "if not silent:" ile sar
# (Sadece ilk eşleşmeyi yapıyoruz; dosyada birden çok olabilir ama genelde 1.)
pat1 = re.compile(r'^(?P<indent>[ \t]*)_append_log\(\s*[\'"]presence_stopped[\'"]\s*(?:,.*?)?\)\s*$', re.M)
m1 = pat1.search(pl)
if m1:
    indent = m1.group("indent")
    line = m1.group(0)
    guarded = f"{indent}if not silent:\n{indent}    {line.strip()}\n"
    pl = pl[:m1.start()] + guarded + pl[m1.end():]
    pl_p.write_text(pl, encoding="utf-8")
    print("OK: presence_lock.py silent stop log guard eklendi.")
else:
    # Alternatif: farklı isimle log basıyor olabilir
    if "presence_stopped" in pl:
        die("ERR: presence_stopped var ama _append_log satırı beklenen formatta değil. 1-2 satırını kopyala gönder, tek atış düzelteyim.")
    print("SKIP: presence_stopped log satırı bulunamadı (zaten yoksa sorun değil).")
