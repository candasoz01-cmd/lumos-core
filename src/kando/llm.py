
def _response_text(resp):
    try:
        txt = getattr(resp, "output_text", None)
        if txt is not None:
            return txt
    except Exception:
        pass
    try:
        return str(resp)
    except Exception:
        return ""

def llm(prompt: str) -> str:
    p = prompt.strip()
    lower = p.lower()

    if lower.startswith("repo:"):
        from kando.tools_repo import repo_search

        query = p.split("repo:", 1)[1].strip()
        return repo_search(query)

    from engine.online_engine import OnlineEngineV1

    engine = OnlineEngineV1()
    result = engine.process(p)

    resp = (result.get("response") or "").strip()
    if not resp:
        return "Geçerli yanıt yok"

    return resp
