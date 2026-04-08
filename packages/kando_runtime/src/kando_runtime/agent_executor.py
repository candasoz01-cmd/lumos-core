import os


def run(task_ctx):
    prompt = str(task_ctx.get("prompt", ""))

    if "video plan" in prompt.lower() or "video oluşturma planı" in prompt.lower():
        return {
            "status": "done",
            "output": {
                "type": "route",
                "target": "video_executor",
                "task": {
                    "type": "video.generate",
                    "prompt": prompt,
                },
            },
        }

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "status": "done",
            "output": {
                "type": "text",
                "value": (
                    "Gerçek bir yanıt üretilemedi: OPENAI_API_KEY tanımlı değil. "
                    "Yapılandırma olmadan model çıktısı sunulmuyor."
                ),
            },
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Lumos agent. Be concise and useful."},
                {"role": "user", "content": prompt},
            ],
        )

        text = (response.choices[0].message.content or "").strip()
        if not text:
            return {
                "status": "done",
                "output": {
                    "type": "text",
                    "value": (
                        "Gerçek bir model çıktısı alınamadı (boş yanıt). "
                        "Sahte içerik üretilmiyor."
                    ),
                },
            }

        return {
            "status": "done",
            "output": {
                "type": "text",
                "value": text,
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "output": {
                "type": "text",
                "value": (
                    f"Gerçek bir yanıt alınamadı (hata): {e!s}. "
                    "Sahte veya yer tutucu çıktı üretilmiyor."
                ),
            },
        }
