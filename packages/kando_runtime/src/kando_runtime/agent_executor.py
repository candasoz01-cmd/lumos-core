import os


def run(task_ctx):
    prompt = str(task_ctx.get("prompt", ""))

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "status": "done",
            "output": {
                "type": "text",
                "value": f"[AGENT fallback] {prompt}"
            }
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Lumos agent. Be concise and useful."},
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content

        return {
            "status": "done",
            "output": {
                "type": "text",
                "value": text
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
