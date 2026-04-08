def run(task_ctx):
    prompt = str(task_ctx.get("prompt", ""))

    return {
        "status": "done",
        "output": {
            "type": "text",
            "value": f"[Lumos cevap]: {prompt[:200]}",
        },
    }
