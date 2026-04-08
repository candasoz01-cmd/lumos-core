def run(task_ctx):
    prompt = task_ctx.get("prompt", "")
    return {
        "outcome": "applied",
        "result": {
            "type": "video",
            "url": "mock://video/generated.mp4",
            "prompt": prompt,
        },
    }
