ROUTES = {
    "text.generate": "text_executor",
    "video.generate": "video_executor",
    "agent": "agent_executor",
}

FALLBACK = "text_executor"


def resolve_executor(task_type: str) -> str:
    return ROUTES.get(task_type, FALLBACK)
