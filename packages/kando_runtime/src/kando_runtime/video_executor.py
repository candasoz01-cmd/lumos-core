def run(task_ctx):
    """Video yürütücü çıktısı: type video + url + title (üretim bağlandığında url güncellenir)."""
    _ = task_ctx
    return {
        "status": "done",
        "output": {
            "type": "video",
            "url": "/out.mp4",
            "title": "generated_video",
        },
    }
