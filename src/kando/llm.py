
import os

def _response_text(response):
    try:
        txt = getattr(response, "output_text", None)
        if txt:
            return txt.strip()
    except Exception:
        pass
    try:
        return str(response)
    except Exception:
        return "Model hatası"

def _valid(resp: str) -> bool:
    if not resp:
        return False
    keys = ["PATCH_TARGET:", "CHANGE:", "COMMAND:", "VERIFY:"]
    return all(k in resp for k in keys)

def llm(prompt: str) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "OPENAI_API_KEY yok"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        for _ in range(3):
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
            )
            resp = _response_text(response)
            s = (resp or "").strip()
            if not s or len(s) < 5:
                return "Geçerli yanıt alınamadı"

            if _valid(resp):
                return resp

            prompt = prompt + "\n\nSADECE FORMATTA YANIT VER. EKSİKSİZ."

        return resp

    except Exception as e:
        return f"Model hatası: {e}"
