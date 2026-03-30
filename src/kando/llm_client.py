import os
import requests

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# Default follows Anthropic model list; override with ANTHROPIC_MODEL if needed.
_DEFAULT_MODEL = "claude-sonnet-4-6"


def call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    data = {
        "model": os.getenv("ANTHROPIC_MODEL", _DEFAULT_MODEL),
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    response = requests.post(url, headers=headers, json=data, timeout=60)
    response.raise_for_status()

    body = response.json()

    if "error" in body:
        raise RuntimeError(f"Anthropic API error: {body['error']}")

    parts = body.get("content", [])
    texts = [p.get("text", "") for p in parts if p.get("type") == "text"]
    return "\n".join(t for t in texts if t).strip()
