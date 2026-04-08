def run(task_ctx):
    prompt = task_ctx.get("prompt", "")
    return {"outcome": "applied", "result": f"video_created_for: {prompt}"}
