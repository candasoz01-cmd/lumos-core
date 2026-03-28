import os
import json
import urllib.request
from openai import OpenAI

BRIDGE_URL = "http://127.0.0.1:8766"
MODEL = "gpt-4.1-mini"

SYSTEM = """You convert user input into a single task sentence.

STRICT RULES:
- Output ONLY the task itself
- DO NOT include "goal:"
- DO NOT explain
- DO NOT ask questions
- DO NOT add extra text

Example:
Input: test
Output: Acknowledge the test input.
"""

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _strip_task_prefixes(text: str) -> str:
    t = (text or "").strip()
    for _ in range(8):
        low = t.lower()
        if low.startswith("goal:"):
            t = t.split(":", 1)[1].strip()
            continue
        if low.startswith("[goal]:"):
            t = t.split(":", 1)[1].strip()
            continue
        break
    return t


def call_llm(user_text: str) -> str:
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_text},
        ],
    )
    raw = resp.output_text.strip().split("\n")[0]
    return _strip_task_prefixes(raw)


def post_goal(goal: str) -> None:
    clean = _strip_task_prefixes((goal or "").strip())
    data = json.dumps({"goal": clean}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BRIDGE_URL,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        print("[relay]:", r.read().decode())


def main():
    print("ChatGPT client hazır.")
    while True:
        try:
            user = input("> ").strip()
            if not user:
                continue

            goal = call_llm(user)
            print(goal)

            post_goal(goal)

        except KeyboardInterrupt:
            print("\nçıkıldı")
            break
        except Exception as e:
            print("hata:", e)


if __name__ == "__main__":
    main()
