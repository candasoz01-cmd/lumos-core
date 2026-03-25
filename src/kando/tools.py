import ast
import os


def get_status():
    return "Lumos Core aktif. Sistem stabil."


def get_project():
    return "Proje çalışıyor. Ana modüller aktif."


def get_suggestion():
    return (
        "Repo search + intent sistemi geliştirilebilir. "
        "Sonraki adım: gerçek dosya aramaya bağla."
    )


def do_continue():
    return "Hazırım, devam ediyorum."


def get_stability():
    return "Belirli scope içinde stabil."


def repo_search(query: str) -> str:
    base = "src"
    q = query.replace("detay", "").strip().lower()
    tokens = q.split()

    def extract_symbol_block(path: str, symbol: str) -> str | None:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
            tree = ast.parse(source)
            lines = source.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name.lower() == symbol:
                    start = max(0, node.lineno - 1)
                    end = getattr(node, "end_lineno", node.lineno)
                    return "\n".join(lines[start:end])
        except Exception:
            return None
        return None

    hits = {}

    for root, _, files in os.walk(base):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    for i, line in enumerate(fp):
                        line_lower = line.lower()

                        score = 0
                        for t in tokens:
                            if t in line_lower:
                                score += 1

                        if score > 0:
                            key = path
                            if key not in hits or hits[key][0] < score:
                                hits[key] = (score, i, line.strip())
            except Exception:
                continue

    if not hits:
        return "Sonuç bulunamadı"

    # dict → liste
    hits = [(s, p, ln, txt) for p, (s, ln, txt) in hits.items()]
    hits.sort(reverse=True, key=lambda x: x[0])

    if len(tokens) >= 2:
        symbol = tokens[-1]
        symbol_hits = []
        for path in [p for (_, p, _, _) in hits[:5]]:
            block = extract_symbol_block(path, symbol)
            if block:
                symbol_hits.append(f"{path}\n{block}")
        if symbol_hits:
            return "\n\n".join(symbol_hits[:3])

    out = []
    for s, p, ln, txt in hits[:3]:
        block = []
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                lines = fp.readlines()

                start = max(0, ln - 3)
                end = min(len(lines), ln + 5)

                for i in range(start, end):
                    block.append(lines[i].rstrip())
        except Exception:
            block = [txt]

        out.append(f"{p}:{ln}\n" + "\n".join(block))

    return "\n\n".join(out)
