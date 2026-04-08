def run(task_ctx):
    prompt = str(task_ctx.get("prompt", "")).strip()
    return {
        "status": "done",
        "output": {
            "type": "video",
            "url": "mock://video/generated.mp4",
            "prompt": prompt,
        },
    }
